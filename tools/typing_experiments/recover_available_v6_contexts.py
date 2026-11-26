"""Locate disclosed v6 source contexts by digest; never reproduce corpus rows.

Only source offsets and hashes are retained. The source article text, synthetic
errors, labels and selection result are not emitted. A match is not independent
qualification. Use one temporary source shard at a time when downloading.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import tempfile
import unicodedata

import check_available_v6_articles as article_check
import holdout_ledger
import prepare_external_spelling_holdout
import recover_available_v6_articles as articles
import right_context_sentence_selection as selection

ROOT = Path(__file__).resolve().parents[2]
LEDGER = articles.LEDGER
MAPPING = article_check.DIRECTORY / 'articles.jsonl'
SELECTOR_SHA256 = '1c3ff47c8672f2acb8697999f5ab8183c328aff175dafc724e13a24ccef56b42'
GENERATOR_SHA256 = 'ed9928d64d80911c0182e03446d710a60abb990cb5fb1cff30730443db773225'


def sentence_targets(ledger):
    entries = {e['id']: e for e in ledger['entries']}
    targets = {}
    for part in ('calibration', 'holdout'):
        values = entries[articles.ENTRY + part]['keys']['sentence']
        if not values:
            raise ValueError('V6_CONTEXT_EMPTY_TARGET')
        for key in values:
            if key in targets:
                raise ValueError('V6_CONTEXT_PARTITION_OVERLAP')
            targets[key] = part
    return targets


def context_candidates(text, generator):
    if not isinstance(text, str):
        raise ValueError('V6_CONTEXT_SOURCE_TEXT')
    text = unicodedata.normalize('NFC', text)
    folded = text.lower()
    if len(text) != len(folded):
        return None
    def generate():
        for match in selection.adjacent_russian_pairs(folded):
            prefix = generator.bounded_prefix(text[max(0, match.start()-256):match.start()]).rstrip(' \t')
            end = match.end('word')
            suffix = text[end:end+128]
            normalized = ' '.join(unicodedata.normalize('NFC',
                prefix + ' ' + match['word'] + suffix).casefold().split())
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            key = next(iter(holdout_ledger.keys_for([{'contextHash': digest}], 'sentence')))
            yield match.start('word'), end, digest, key
    return generate()


def scan_shard(path, shard, article_rows, targets, generator):
    import pyarrow.parquet as parquet

    path = Path(path)
    if path.stat().st_size != shard['bytes'] or articles.sha_file(path) != shard['sha256']:
        raise ValueError('V6_CONTEXT_SOURCE_IDENTITY')
    needed = {row['article']: row for row in article_rows}
    if len(needed) != len(article_rows):
        raise ValueError('V6_CONTEXT_DUPLICATE_ARTICLE_MAPPING')
    found_articles, anchors = set(), []
    row_count = folding_refusals = 0
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=64, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            row_count += 1
            article = str(article)
            if article not in needed:
                continue
            if article in found_articles:
                raise ValueError('V6_CONTEXT_DUPLICATE_SOURCE_ARTICLE')
            found_articles.add(article)
            candidate_iter = context_candidates(text, generator)
            if candidate_iter is None:
                folding_refusals += 1
                continue
            owner = needed[article]['partition']
            for start, end, digest, key in candidate_iter:
                if key in targets:
                    anchors.append(dict(article=article, articlePartition=owner, source=shard['name'],
                        wordStart=start, wordEnd=end, contextHash=digest, sentenceKey=key,
                        sentencePartition=targets[key]))
    if found_articles != set(needed):
        raise ValueError('V6_CONTEXT_SOURCE_ARTICLES_MISSING')
    if path.stat().st_size != shard['bytes'] or articles.sha_file(path) != shard['sha256']:
        raise ValueError('V6_CONTEXT_SOURCE_DRIFT')
    return anchors, dict(sourceRows=row_count, articles=len(found_articles), foldingRefusals=folding_refusals)


def summarize(targets, anchors):
    # A context can also occur in an article assigned to the other partition.
    # Preserve every candidate but do not count the cross-partition occurrence
    # as the historical source location.
    eligible = Counter(a['sentenceKey'] for a in anchors
                       if a['articlePartition'] == a['sentencePartition'])
    return dict(uniqueTargets=sum(n == 1 for n in eligible.values()),
        ambiguousTargets=sum(n > 1 for n in eligible.values()),
        missingTargets=len(set(targets) - set(eligible)),
        crossPartitionAnchors=sum(a['articlePartition'] != a['sentencePartition'] for a in anchors))


def recover(source_dir=None, download_temporary=False):
    if (source_dir is None) == (not download_temporary):
        raise ValueError('V6_CONTEXT_SOURCE_MODE')
    article_check.check()
    lock, lock_raw = articles.read_lock()
    generator_file = prepare_external_spelling_holdout.GENERATOR.resolve()
    if articles.sha_file(Path(selection.__file__)) != SELECTOR_SHA256 or articles.sha_file(generator_file) != GENERATOR_SHA256:
        raise ValueError('V6_CONTEXT_HISTORICAL_HELPER')
    helpers = [Path(__file__).resolve(), Path(selection.__file__).resolve(), generator_file,
        Path(articles.__file__).resolve(), Path(article_check.__file__).resolve(),
        Path(holdout_ledger.__file__).resolve(), Path(prepare_external_spelling_holdout.__file__).resolve(),
        ROOT / 'tools/typing_experiments/source_identities.py',
        ROOT / 'tools/typing_experiments/conversation_split_checks.py', articles.SELECTOR]
    helper_hashes = {str(p.relative_to(ROOT)): articles.sha_file(p) for p in helpers}
    ledger_sha = articles.sha_file(LEDGER)
    mapping_bytes = MAPPING.read_bytes()
    article_receipt = (article_check.DIRECTORY / 'receipt.json').read_bytes()
    mapping = [json.loads(line) for line in mapping_bytes.splitlines()]
    targets = sentence_targets(holdout_ledger.load_ledger(LEDGER))
    generator = prepare_external_spelling_holdout.load_generator()
    anchors, source_counts = [], {}
    with tempfile.TemporaryDirectory(prefix='rune-v6-context-shards-') as directory:
        temp = Path(directory)
        for shard in lock['shards']:
            path = (temp if download_temporary else Path(source_dir)) / shard['name']
            try:
                if download_temporary:
                    articles.download(shard, path)
                selected = [r for r in mapping if r['shard'] == shard['name']]
                items, counts = scan_shard(path, shard, selected, targets, generator)
                anchors.extend(items)
                source_counts[shard['name']] = counts | {'anchors': len(items)}
                print('shard', shard['name'], 'articles', counts['articles'], 'candidate anchors', len(items), flush=True)
            finally:
                if download_temporary:
                    path.unlink(missing_ok=True)
    if (articles.LOCK.read_bytes() != lock_raw or articles.sha_file(LEDGER) != ledger_sha or
            MAPPING.read_bytes() != mapping_bytes or
            (article_check.DIRECTORY / 'receipt.json').read_bytes() != article_receipt or
            any(articles.sha_file(ROOT / p) != h for p, h in helper_hashes.items())):
        raise ValueError('V6_CONTEXT_INPUT_DRIFT')
    anchors.sort(key=lambda a: (a['sentencePartition'], a['sentenceKey'], int(a['article']), a['wordStart']))
    summary = summarize(targets, anchors)
    report = dict(schema=1, scope='source-context-anchor-diagnostic-not-corpus-reproduction',
        sourceLockSha256=hashlib.sha256(lock_raw).hexdigest(), ledgerSha256=ledger_sha,
        articleMappingSha256=hashlib.sha256(mapping_bytes).hexdigest(), helperSha256=helper_hashes,
        pyarrowVersion=importlib.metadata.version('pyarrow'), pythonVersion=platform.python_version(),
        unicodeVersion=unicodedata.unidata_version, sourceDecoderAttested=False,
        targetCounts=dict(Counter(targets.values())), totalTargets=len(targets),
        **summary, sourceCounts=source_counts,
        offsets='zero-based NFC Unicode code points', corpusRowsRecovered=False, independentQualification=False)
    return anchors, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source-dir', type=Path)
    source.add_argument('--download-temporary', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('V6_CONTEXT_OUTPUT_EXISTS')
    anchors, report = recover(args.source_dir, args.download_temporary)
    raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in anchors).encode()
    report['anchorsSha256'] = hashlib.sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v6-contexts-', dir=output.parent) as d:
        stage = Path(d) / 'result'
        stage.mkdir()
        (stage / 'anchors.jsonl').write_bytes(raw)
        (stage / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        os.rename(stage, output)
    print(json.dumps({k: report[k] for k in ('totalTargets', 'uniqueTargets', 'ambiguousTargets',
        'missingTargets', 'crossPartitionAnchors', 'anchorsSha256', 'independentQualification')}, sort_keys=True))


if __name__ == '__main__':
    main()
