"""Recover Diagnostic Rare Ranking dictionary and source-window exclusions."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

from holdout_ledger import load_ledger, pack_ledger
from import_joint_source_windows import GENERATOR_SHA
from import_legacy_context_history import captures, entries_for
from import_recovered_v6_history import PREFIX, ROOT, rare_ranking_payloads
from prepare_joint_correction import morphology
from recover_available_v6_articles import LOCK, read_lock
from recover_legacy_families import sha
from recover_legacy_holdout import ORIGINAL, load_generator


SOURCE = '0020.parquet'
PACKED_MORPHOLOGY = 'app/src/main/assets/smarttyping/lexicon/ru.morph'
MORPHOLOGY_REQUIREMENTS = 'tools/morphology/requirements.lock'
JOINT_PREPARER = 'tools/typing_experiments/prepare_joint_correction.py'


def recover_windows(jobs, batches, generator):
    wanted = defaultdict(set)
    for _, rows, _, _ in jobs:
        for row in rows:
            wanted[row['article']].add((row['word'], row['prefix']))
    windows = {}
    seen = set()
    for articles, texts in batches:
        for article, text in zip(articles, texts, strict=True):
            article = str(article)
            if article not in wanted:
                continue
            if article in seen:
                raise ValueError('RARE_RANKING_DUPLICATE_ARTICLE')
            seen.add(article)
            for frame, hashes in captures(text, wanted[article], generator).items():
                if len(hashes) != 1:
                    raise ValueError('RARE_RANKING_AMBIGUOUS_WINDOW')
                windows[(SOURCE, article, *frame)] = hashes
    if seen != wanted.keys():
        raise ValueError('RARE_RANKING_MISSING_ARTICLE')
    return windows


def project(recovery_dir, source, batches, lexicon):
    jobs = list(rare_ranking_payloads(recovery_dir))
    lock, _ = read_lock()
    pin = next(record for record in lock['shards'] if record['name'] == SOURCE)
    if source.stat().st_size != pin['bytes'] or sha(source) != pin['sha256']:
        raise ValueError('RARE_RANKING_SOURCE_DIGEST')
    words = {row['word'] for _, rows, _, _ in jobs for row in rows}
    packed = morphology(words)
    if any(len(rows) != size or any(row['source'] != SOURCE or packed.get(row['word']) != row['family']
                                    for row in rows) for _, rows, size, _ in jobs):
        raise ValueError('RARE_RANKING_NATIVE_FAMILY')
    windows = recover_windows(jobs, batches(source), load_generator(GENERATOR_SHA))
    if sha(source) != pin['sha256']:
        raise ValueError('RARE_RANKING_SOURCE_DRIFT')

    source_path = 'build/joint-correction-20261025/' + SOURCE
    common_bindings = {source_path: pin['sha256'], LOCK.relative_to(ROOT).as_posix(): sha(LOCK)}
    common_bindings.update({name: sha(ROOT / name) for name in (
        PACKED_MORPHOLOGY, MORPHOLOGY_REQUIREMENTS, JOINT_PREPARER,
        'tools/typing_experiments/import_legacy_context_history.py', 'tools/morphology/ranker.py',
    )})
    entries = []
    counts = {}
    for part, rows, _, bindings in jobs:
        bindings = bindings | common_bindings
        projections, counts[part] = entries_for('rare-ranking', part, rows, windows, lexicon, bindings)
        if counts[part]['unresolvedRows'] or len(projections) != 1:
            raise ValueError('RARE_RANKING_DICTIONARY_COVERAGE')
        keys = projections[0]['keys']
        parent = PREFIX + 'diagnostic-rare-ranking-' + part
        origin = dict(bindings=bindings, parentEntries=[parent], missingAxes=[])
        entries.extend([
            dict(origin, id=parent + '-windows', usage='historical-source-exclusion',
                 rowCount=len(rows), keys={axis: keys[axis] for axis in ('article', 'sentence')},
                 generatorBindings={ORIGINAL: GENERATOR_SHA},
                 notes='Unique selector-window projection from the pinned source articles.'),
            dict(origin, id=parent + '-dictionary-families', usage='historical-family-exclusion',
                 rowCount=len(rows), keys={'family': keys['family']},
                 notes='All pinned dictionary analyses of the source word and lexical target.'),
        ])
    receipt = dict(counts=counts, packedFamilyWords=len(packed), sourceWindows=len(windows),
                   sourceSha256=pin['sha256'], dictionary=lexicon.receipt(), modelCalls=0)
    return entries, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery-dir', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')

    import pyarrow.parquet as parquet
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon

    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()

    base = load_ledger(args.base)
    entries, receipt = project(args.recovery_dir, args.source, batches, PymorphyLexicon(cache_size=16384))
    by_id = {entry['id']: entry for entry in base['entries']}
    for entry in entries:
        if entry['id'] in by_id:
            raise ValueError('RARE_RANKING_ALREADY_REGISTERED')
        parent = by_id[entry['parentEntries'][0]]
        if any(entry['bindings'].get(path) != digest for path, digest in parent['bindings'].items()):
            raise ValueError('RARE_RANKING_PARENT_BINDING')
        if 'article' in entry['keys'] and entry['keys']['article'] != parent['keys']['article']:
            raise ValueError('RARE_RANKING_PARENT_ARTICLES')
    packed = pack_ledger(base | {'entries': entries})['entries']
    stored = json.loads(args.base.read_bytes())
    stored['entries'].extend(packed)
    args.output.mkdir(mode=0o700)
    for filename, payload in (('ledger.json', stored), ('receipt.json', receipt)):
        (args.output / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
