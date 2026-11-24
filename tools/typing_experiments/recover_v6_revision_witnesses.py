"""Compare public Wikipedia revisions with the cleaned text in one pinned v6 shard."""

import argparse
import ast
from collections import Counter
import gzip
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from check_available_v6_articles import ARTICLES_SHA256, DIRECTORY
from recover_available_v6_articles import download, read_lock, sha_file


CLEANER_REVISION = 'b35d406bd9e81f08c68e7bf95d130d2f506dfe77'
CLEANER_SHA256 = 'bbae6bf05eaa833dec5c56fa75057dd01c14b418fccdb4d6ee4b363f476d455f'
CLEANER_URL = f'https://huggingface.co/datasets/wikimedia/wikipedia/raw/{CLEANER_REVISION}/wikipedia.py'
API = 'https://ru.wikipedia.org/w/api.php'
USER_AGENT = 'RuneCorpusProvenance/1.0 (https://github.com/Mesteriis/rune-keyboard; Wikipedia attribution review)'
UPPER_BOUND = '2023-11-03T00:00:00Z'
DUMP_DAY_END = '2023-11-01T23:59:59Z'
REVISION_LIMIT = 8
MAX_RESPONSE = 12_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download_bytes(url, limit=MAX_RESPONSE):
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip'})
    with urlopen(request, timeout=25) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('V6_REVISION_RESPONSE_LIMIT')
        if response.headers.get('Content-Encoding') == 'gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as archive:
                raw = archive.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('V6_REVISION_RESPONSE_LIMIT')
    return raw


def load_cleaner(content):
    if digest(content) != CLEANER_SHA256:
        raise ValueError('V6_REVISION_CLEANER_IDENTITY')
    syntax = ast.parse(content)
    symbols = {'re': re}
    for statement in syntax.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            name = statement.targets[0]
            if isinstance(name, ast.Name) and name.id in ('MEDIA_ALIASES', 'CAT_ALIASES'):
                symbols[name.id] = {'ru': ast.literal_eval(statement.value)['ru']}
    function, = [statement for statement in syntax.body if isinstance(statement, ast.FunctionDef)
                 and statement.name == '_parse_and_clean_wikicode']
    # Execute only the digest-pinned cleaning function, without importing the upstream dataset module.
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<pinned-wikipedia-cleaner>', 'exec'), symbols)
    return symbols[function.name]


def fetch_revisions(article):
    query = urlencode(dict(action='query', format='json', formatversion=2, pageids=article,
                           prop='revisions', rvprop='ids|timestamp|content', rvslots='main',
                           rvstart=UPPER_BOUND, rvlimit=REVISION_LIMIT, maxlag=5))
    for attempt in range(3):
        try:
            result = json.loads(download_bytes(API + '?' + query))
            if 'error' not in result:
                return result
            if result['error'].get('code') not in ('maxlag', 'ratelimited'):
                raise ValueError('V6_REVISION_API_ERROR')
        except (TimeoutError, URLError) as error:
            if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise
            if isinstance(error, HTTPError):
                retry = error.headers.get('Retry-After', '')
                if retry.isdecimal():
                    if int(retry) > 60:
                        raise OSError('V6_REVISION_API_RETRY_LATER') from error
                    if attempt < 2:
                        time.sleep(max(int(retry), 5 * (2 ** attempt)))
                    continue
        if attempt < 2:
            time.sleep(5 * (2 ** attempt))
    raise OSError('V6_REVISION_API_UNAVAILABLE')


def compare(article, partition, snapshot, response, clean):
    page, = response['query']['pages']
    if page.get('pageid') != int(article):
        raise ValueError('V6_REVISION_PAGE_IDENTITY')
    revisions = page.get('revisions', [])
    if len(revisions) > REVISION_LIMIT:
        raise ValueError('V6_REVISION_QUERY_LIMIT')
    matches = []
    compared = 0
    seen = set()
    for revision in revisions:
        revid, timestamp = revision['revid'], revision['timestamp']
        if (type(revid) is not int or revid < 1 or revid in seen or not isinstance(timestamp, str) or
                not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', timestamp) or timestamp > UPPER_BOUND):
            raise ValueError('V6_REVISION_CANDIDATE_IDENTITY')
        seen.add(revid)
        content = revision.get('slots', {}).get('main', {}).get('content')
        if content is None:
            continue
        compared += 1
        if clean(content).encode() == snapshot:
            matches.append({'revid': revid, 'timestamp': timestamp})
    if 'missing' in page:
        status = 'missing-page'
    elif not compared:
        status = 'no-readable-content'
    else:
        status = 'content-match' if matches else 'no-content-match'
    return dict(article=article, partition=partition, snapshotTextSha256=digest(snapshot),
                comparedRevisions=compared, matches=matches, status=status,
                hasEarlierContinuation='continue' in response)


def read_snapshot(path, shard, targets):
    import pyarrow.parquet as parquet

    if path.stat().st_size != shard['bytes'] or sha_file(path) != shard['sha256']:
        raise ValueError('V6_REVISION_SHARD_IDENTITY')
    texts = {}
    for batch in parquet.ParquetFile(path).iter_batches(columns=['id', 'text'], batch_size=256):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            if article in targets:
                if article in texts:
                    raise ValueError('V6_REVISION_DUPLICATE_PAGE')
                texts[article] = text.encode()
    if set(texts) != set(targets) or sha_file(path) != shard['sha256']:
        raise ValueError('V6_REVISION_SHARD_COVERAGE')
    return texts


def recover(shard_name, source, output):
    import mwparserfromhell

    parser_version = importlib.metadata.version('mwparserfromhell')
    pyarrow_version = importlib.metadata.version('pyarrow')
    if parser_version != '0.6.5' or pyarrow_version != '25.0.1':
        raise ValueError('V6_REVISION_DEPENDENCIES')
    lock, lock_bytes = read_lock()
    shard, = [entry for entry in lock['shards'] if entry['name'] == shard_name]
    index = (DIRECTORY / 'articles.jsonl').read_bytes()
    if digest(index) != ARTICLES_SHA256:
        raise ValueError('V6_REVISION_ARTICLE_INDEX')
    targets = {row['article']: row['partition'] for row in map(json.loads, index.splitlines())
               if row['shard'] == shard_name}
    clean_wikitext = load_cleaner(download_bytes(CLEANER_URL, limit=100_000))

    def clean(content):
        return clean_wikitext(content, mwparserfromhell, 'ru')

    with tempfile.TemporaryDirectory(prefix='.rune-v6-witnesses-', dir=output.parent) as folder:
        temporary = Path(folder)
        if source is None:
            source = temporary / shard['name']
            download(shard, source)
        texts = read_snapshot(source, shard, targets)
        rows = []
        for article in sorted(targets, key=int):
            rows.append(compare(article, targets[article], texts[article], fetch_revisions(article), clean))
            if len(rows) % 35 == 0:
                print(f'{shard_name}: {len(rows)}/{len(targets)} pages reviewed', flush=True)
            time.sleep(.35)
        result = temporary / 'verified'
        result.mkdir()
        encoded = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n' for row in rows).encode()
        report = dict(schema=1, purpose='historical-revision-content-shard', sourceShard=shard_name,
                      sourceShardSha256=shard['sha256'], sourceLockSha256=digest(lock_bytes),
                      sourceIndexSha256=ARTICLES_SHA256, cleanerRevision=CLEANER_REVISION,
                      cleanerSha256=CLEANER_SHA256, articlesSha256=digest(encoded), parserVersion=parser_version,
                      pyarrowVersion=pyarrow_version, apiUpperBound=UPPER_BOUND, dumpDateCutoff=DUMP_DAY_END,
                      apiRevisionLimitPerPage=REVISION_LIMIT, articles=len(rows),
                      statusCounts=dict(Counter(row['status'] for row in rows)),
                      comparedRevisions=sum(row['comparedRevisions'] for row in rows),
                      matchingRevisions=sum(len(row['matches']) for row in rows),
                      multipleMatches=sum(len(row['matches']) > 1 for row in rows),
                      earlierContinuation=sum(row['hasEarlierContinuation'] for row in rows),
                      withMatchOnOrBeforeDumpDate=sum(any(r['timestamp'] <= DUMP_DAY_END for r in row['matches'])
                                                       for row in rows),
                      originalDumpRevisionIdsVerified=False, independentQualification=False)
        (result / 'articles.jsonl').write_bytes(encoded)
        (result / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        result.rename(output)
    print(json.dumps(report['statusCounts'], sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', required=True, choices=[f'{i:04d}.parquet' for i in range(11, 21)])
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--source', type=Path)
    inputs.add_argument('--download-temporary', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('--output must be a fresh directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    recover(args.shard, args.source, output)


if __name__ == '__main__':
    main()
