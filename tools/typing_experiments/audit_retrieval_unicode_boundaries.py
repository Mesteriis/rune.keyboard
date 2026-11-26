"""Audit mark and underscore boundaries in the disclosed retrieval source."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import register_retrieval_history as fixture
from audit_wordrank_source_boundaries import digest

LOCK = ROOT / 'tools/model/rune-text-0.2/source-lock.json'


def category(char):
    if char == '_':
        return 'underscore'
    if char and unicodedata.category(char).startswith('M'):
        return 'combiningMark'
    return None


def analyze(rows, articles):
    counts = Counter({side + kind + suffix: 0 for side in ('left', 'right')
                      for kind in ('Underscore', 'CombiningMark')
                      for suffix in ('Rows', 'Matches')})
    ids = set()
    for row in rows:
        rid, article, prefix, target = (row.get(key) for key in ('id', 'articleId', 'prefix', 'expectedSpelling'))
        if (not isinstance(rid, str) or not rid or rid in ids or not isinstance(article, str) or
                not isinstance(prefix, str) or not prefix or not isinstance(target, str) or not target):
            raise ValueError('UNICODE_BOUNDARY_ROW')
        ids.add(rid)
        text = articles.get(article)
        if not isinstance(text, str):
            raise ValueError('UNICODE_BOUNDARY_ARTICLE')
        matches = list(re.finditer(re.escape(prefix + target), text))
        if not matches:
            raise ValueError('UNICODE_BOUNDARY_MISSING')
        counts['rows'] += 1
        counts['matches'] += len(matches)
        seen = set()
        for match in matches:
            start = match.start() + len(prefix)
            end = start + len(target)
            for side, char in (('left', text[start - 1:start] if start else ''), ('right', text[end:end + 1])):
                kind = category(char)
                if kind:
                    counts[side + kind[0].upper() + kind[1:] + 'Matches'] += 1
                    seen.add(side + kind[0].upper() + kind[1:] + 'Rows')
        counts.update(seen)
    if not ids:
        raise ValueError('UNICODE_BOUNDARY_EMPTY')
    return dict(sorted(counts.items()))


def run(parquet, output):
    import pyarrow.parquet as pq
    parquet = Path(parquet).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('UNICODE_BOUNDARY_OUTPUT')
    lock = LOCK.read_bytes()
    source = json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size != source['bytes'] or digest(parquet) != source['sha256']:
        raise ValueError('UNICODE_BOUNDARY_SOURCE')
    rows, _, bindings = fixture.inputs()
    wanted = {row['articleId'] for row in rows}
    articles = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            article = str(article)
            if article in wanted:
                if article in articles:
                    raise ValueError('UNICODE_BOUNDARY_DUPLICATE_SOURCE')
                articles[article] = unicodedata.normalize('NFC', text or '')
    if set(articles) != wanted:
        raise ValueError('UNICODE_BOUNDARY_ARTICLE')
    result = analyze(rows, articles)
    if LOCK.read_bytes() != lock or digest(parquet) != source['sha256'] or fixture.inputs()[2] != bindings:
        raise ValueError('UNICODE_BOUNDARY_DRIFT')
    result = {'counts': result, 'scope': 'historical-retrieval-boundary-diagnostic',
              'qualified': False, 'sourceSha256': source['sha256'],
              'sourceLockSha256': hashlib.sha256(lock).hexdigest(),
              'rowsSha256': fixture.ROWS_SHA, 'auditorSha256': digest(Path(__file__))}
    output.mkdir(parents=True, mode=0o700)
    (output / 'report.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.parquet, args.output)
