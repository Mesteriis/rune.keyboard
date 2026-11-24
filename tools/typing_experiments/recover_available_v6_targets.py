"""Match source-word and protected target keys, without recreating v6 rows.

Only existing registry keys and source anchors are retained. No article text,
typed errors, historical labels, model scores or independent holdout is emitted.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import tempfile
import unicodedata

import check_available_v6_contexts as context_check
import holdout_ledger
import prepare_external_spelling_holdout
import recover_available_v6_articles as articles
import recover_available_v6_contexts as contexts

ROOT = Path(__file__).resolve().parents[2]
ANCHORS = context_check.DIRECTORY / 'anchors.jsonl'
LEDGER = articles.LEDGER


def target_index(ledger):
    entries = {e['id']: e for e in ledger['entries']}
    result = {}
    for part in ('calibration', 'holdout'):
        keys = entries[articles.ENTRY + part]['keys']['context']
        if not keys:
            raise ValueError('V6_TARGET_EMPTY_PARTITION')
        for key in keys:
            if key in result:
                raise ValueError('V6_TARGET_PARTITION_OVERLAP')
            result[key] = part
    return result


def candidate_targets(text, anchor, generator):
    if not isinstance(text, str):
        raise ValueError('V6_TARGET_SOURCE_TEXT')
    text = unicodedata.normalize('NFC', text)
    folded = text.lower()
    if len(text) != len(folded):
        raise ValueError('V6_TARGET_SOURCE_FOLD')
    start, end = anchor['wordStart'], anchor['wordEnd']
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError('V6_TARGET_SOURCE_OFFSET')
    word = folded[start:end]
    if not re.fullmatch('[а-яё]{3,20}', word):
        raise ValueError('V6_TARGET_SOURCE_WORD')
    prefix = generator.bounded_prefix(text[max(0, start-256):start]).rstrip(' \t')
    suffix = text[end:end+128]
    normalized = ' '.join(unicodedata.normalize('NFC', prefix + ' ' + word + suffix).casefold().split())
    if hashlib.sha256(normalized.encode()).hexdigest() != anchor['contextHash']:
        raise ValueError('V6_TARGET_SOURCE_CONTEXT')
    return {variant: next(iter(holdout_ledger.keys_for([dict(prefix=prefix, typed=target,
                expectedSpelling=target)], 'context')))
            for variant, target in (('source-word', word), ('protected-source-word', '@' + word))}


def scan_shard(path, shard, article_rows, anchors, targets, generator):
    import pyarrow.parquet as parquet

    path = Path(path)
    if path.stat().st_size != shard['bytes'] or articles.sha_file(path) != shard['sha256']:
        raise ValueError('V6_TARGET_SOURCE_IDENTITY')
    needed = {row['article']: row for row in article_rows}
    if len(needed) != len(article_rows):
        raise ValueError('V6_TARGET_DUPLICATE_ARTICLE_MAPPING')
    by_article = defaultdict(list)
    for anchor in anchors:
        if anchor['source'] != shard['name'] or anchor['article'] not in needed:
            raise ValueError('V6_TARGET_ANCHOR_SOURCE')
        if anchor['articlePartition'] == anchor['sentencePartition']:
            by_article[anchor['article']].append(anchor)
    found_articles, matched, row_count, checked = set(), [], 0, 0
    candidate_counts = Counter()
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=64, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            row_count += 1
            article = str(article)
            if article not in needed:
                continue
            if article in found_articles:
                raise ValueError('V6_TARGET_DUPLICATE_SOURCE_ARTICLE')
            found_articles.add(article)
            for anchor in by_article[article]:
                checked += 1
                for variant, key in candidate_targets(text, anchor, generator).items():
                    candidate_counts[variant] += 1
                    if key in targets:
                        matched.append(dict(article=article, source=shard['name'],
                            wordStart=anchor['wordStart'], wordEnd=anchor['wordEnd'],
                            contextHash=anchor['contextHash'], sentenceKey=anchor['sentenceKey'],
                            sourcePartition=anchor['sentencePartition'], targetKey=key,
                            targetPartition=targets[key], variant=variant))
    if found_articles != set(needed):
        raise ValueError('V6_TARGET_SOURCE_ARTICLES_MISSING')
    if path.stat().st_size != shard['bytes'] or articles.sha_file(path) != shard['sha256']:
        raise ValueError('V6_TARGET_SOURCE_DRIFT')
    return matched, dict(sourceRows=row_count, articles=len(found_articles), checkedAnchors=checked,
                         candidates=dict(candidate_counts), matched=len(matched))


def summarize(targets, matches):
    eligible = Counter(m['targetKey'] for m in matches if m['sourcePartition'] == m['targetPartition'])
    return dict(uniqueTargets=sum(n == 1 for n in eligible.values()),
        ambiguousTargets=sum(n > 1 for n in eligible.values()),
        unmatchedTargets=len(set(targets) - set(eligible)),
        crossPartitionMatches=sum(m['sourcePartition'] != m['targetPartition'] for m in matches))


def recover(source_dir=None, download_temporary=False):
    if (source_dir is None) == (not download_temporary):
        raise ValueError('V6_TARGET_SOURCE_MODE')
    context_check.check()
    lock, lock_raw = articles.read_lock()
    ledger_sha = articles.sha_file(LEDGER)
    anchor_raw = ANCHORS.read_bytes()
    context_receipt = (context_check.DIRECTORY / 'receipt.json').read_bytes()
    mapping_raw = contexts.MAPPING.read_bytes()
    helpers = [Path(__file__).resolve(), Path(contexts.__file__).resolve(), Path(context_check.__file__).resolve(),
        Path(articles.__file__).resolve(), Path(contexts.article_check.__file__).resolve(),
        Path(holdout_ledger.__file__).resolve(), Path(prepare_external_spelling_holdout.__file__).resolve(),
        Path(contexts.selection.__file__).resolve(), prepare_external_spelling_holdout.GENERATOR.resolve(),
        ROOT / 'tools/typing_experiments/source_identities.py',
        ROOT / 'tools/typing_experiments/conversation_split_checks.py', articles.SELECTOR]
    bindings = {str(p.relative_to(ROOT)): articles.sha_file(p) for p in helpers}
    mapping = [json.loads(line) for line in mapping_raw.splitlines()]
    anchors = [json.loads(line) for line in anchor_raw.splitlines()]
    targets = target_index(holdout_ledger.load_ledger(LEDGER))
    generator = prepare_external_spelling_holdout.load_generator()
    matches, source_counts = [], {}
    with tempfile.TemporaryDirectory(prefix='rune-v6-target-shards-') as directory:
        temp = Path(directory)
        for shard in lock['shards']:
            path = (temp if download_temporary else Path(source_dir)) / shard['name']
            try:
                if download_temporary:
                    articles.download(shard, path)
                found, counts = scan_shard(path, shard, [r for r in mapping if r['shard'] == shard['name']],
                    [a for a in anchors if a['source'] == shard['name']], targets, generator)
                matches.extend(found)
                source_counts[shard['name']] = counts
                print('shard', shard['name'], 'checked anchors', counts['checkedAnchors'],
                      'matched target candidates', len(found), flush=True)
            finally:
                if download_temporary:
                    path.unlink(missing_ok=True)
    if (articles.LOCK.read_bytes() != lock_raw or articles.sha_file(LEDGER) != ledger_sha or
            ANCHORS.read_bytes() != anchor_raw or contexts.MAPPING.read_bytes() != mapping_raw or
            (context_check.DIRECTORY / 'receipt.json').read_bytes() != context_receipt or
            any(articles.sha_file(ROOT / p) != h for p, h in bindings.items())):
        raise ValueError('V6_TARGET_INPUT_DRIFT')
    matches.sort(key=lambda m: (m['targetPartition'], m['targetKey'], int(m['article']), m['wordStart'], m['variant']))
    report = dict(schema=1, scope='source-and-protected-target-candidate-diagnostic-not-corpus-reproduction',
        sourceLockSha256=hashlib.sha256(lock_raw).hexdigest(), ledgerSha256=ledger_sha,
        articleMappingSha256=hashlib.sha256(mapping_raw).hexdigest(), anchorSha256=hashlib.sha256(anchor_raw).hexdigest(),
        helperSha256=bindings, pyarrowVersion=importlib.metadata.version('pyarrow'),
        pythonVersion=platform.python_version(), unicodeVersion=unicodedata.unidata_version,
        sourceDecoderAttested=False, targetCounts=dict(Counter(targets.values())), totalTargets=len(targets),
        **summarize(targets, matches), sourceCounts=source_counts,
        corpusRowsRecovered=False, originalLabelsRecovered=False, independentQualification=False)
    return matches, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source-dir', type=Path)
    source.add_argument('--download-temporary', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('V6_TARGET_OUTPUT_EXISTS')
    matches, report = recover(args.source_dir, args.download_temporary)
    raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in matches).encode()
    report['matchesSha256'] = hashlib.sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v6-targets-', dir=output.parent) as d:
        stage = Path(d) / 'result'
        stage.mkdir()
        (stage / 'matches.jsonl').write_bytes(raw)
        (stage / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        os.rename(stage, output)
    print(json.dumps({k: report[k] for k in ('totalTargets', 'uniqueTargets', 'ambiguousTargets',
        'unmatchedTargets', 'crossPartitionMatches', 'matchesSha256', 'independentQualification')}, sort_keys=True))


if __name__ == '__main__':
    main()
