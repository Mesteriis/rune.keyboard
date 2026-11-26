"""Quarantine full historical selector segments, without claiming sentence parsing."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

import import_word_epoch_windows as windows
from holdout_ledger import _digest, validate_ledger, load_ledger
from recover_ranker_sources import BOUNDARY, WORD, HISTORICAL_SEEDS

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'public-word-epoch-selector-segments-'


def capture(article, text, rows):
    wanted = {row['id']: row for row in rows}
    if len(wanted) != len(rows) or any(row['articleId'] != article for row in rows):
        raise ValueError('SEGMENT_ROWS')
    found = {identity: set() for identity in wanted}
    text = unicodedata.normalize('NFC', text or '')
    segments = BOUNDARY.split(text)
    for segment in segments:
        for ordinal, match in enumerate(WORD.finditer(segment)):
            word = match.group()
            if ordinal < 3 or word != word.lower() or not 5 <= len(word) <= 12: continue
            prefix = segment[:match.start()][-128:].lstrip()
            if not prefix or not prefix[-1].isspace(): continue
            context = hashlib.sha256((prefix.lower() + '\0' + word).encode()).hexdigest()
            for kind, seed in HISTORICAL_SEEDS.items():
                components = [seed, article]
                if kind == 'extra': components.append(str(match.start()))
                components.append(context)
                identity = kind + '-' + hashlib.sha256(':'.join(components).encode()).hexdigest()[:24]
                if identity not in wanted: continue
                row = wanted[identity]
                if row['prefix'] != prefix or row['expectedSpelling'] != word:
                    raise ValueError('SEGMENT_CAPTURE_DIVERGENCE')
                normalized = ' '.join(segment.casefold().split())
                digest = hashlib.sha256(normalized.encode()).hexdigest()
                found[identity].add(_digest('sentence', ['tatoeba-full-sentence-normalized-v1', digest]))
    if any(not keys for keys in found.values()): raise ValueError('SEGMENT_CAPTURE_MISSING')
    return found


def build(base, read_batches):
    original = validate_ledger(base)
    if any(e['id'].startswith(PREFIX) for e in original['entries']): raise ValueError('SEGMENTS_ALREADY_IMPORTED')
    previous = {e['id']: e for e in original['entries'] if e['id'].startswith(windows.PREFIX)}
    if len(previous) != 4: raise ValueError('SEGMENT_WINDOW_PARENTS')
    stripped = copy.deepcopy(original)
    stripped['entries'] = [e for e in stripped['entries'] if not e['id'].startswith(windows.PREFIX)]
    captures = {}; partitions = {}
    original_capture = windows.recover_word_epoch_article
    def observe(article, text, rows, generator):
        recovered = original_capture(article, text, rows, generator)
        extra = capture(article, text, rows)
        if set(extra) != set(recovered) or set(captures).intersection(extra): raise ValueError('SEGMENT_DUPLICATE')
        captures.update(extra)
        for row in rows: partitions[row['id']] = row['id'].split('-', 1)[0] + '-' + row['partition']
        return recovered
    windows.recover_word_epoch_article = observe
    try: generated, receipt = windows.build(stripped, read_batches)
    finally: windows.recover_word_epoch_article = original_capture
    for entry in generated['entries']:
        if entry['id'].startswith(windows.PREFIX):
            old = previous.get(entry['id'])
            if not old or old['keys'] != entry['keys'] or old['rowCount'] != entry['rowCount']:
                raise ValueError('SEGMENT_WINDOW_PARITY')
    result = copy.deepcopy(original); counts = {}
    bindings = receipt['bindings'] | {str(Path(__file__).resolve().relative_to(ROOT)): windows.sha(Path(__file__))}
    for name in ('extra-test', 'wordrank-train', 'wordrank-dev', 'wordrank-test'):
        ids = [identity for identity, part in partitions.items() if part == name]
        keys = sorted({key for identity in ids for key in captures[identity]})
        if not ids or not keys: raise ValueError('SEGMENT_EMPTY')
        parent = windows.PREFIX + name
        result['entries'].append({'id': PREFIX + name, 'usage': 'historical-exclusion',
            'rowCount': len(ids), 'keys': {'sentence': keys}, 'missingAxes': ['article', 'family', 'context'],
            'bindings': bindings, 'parentEntries': [parent],
            'notes': 'Full historical selector segments; delimiter-based, not verified linguistic sentences.'})
        counts[name] = {'rows': len(ids), 'distinctSegments': len(keys)}
    return validate_ledger(result), {'purpose': 'HISTORICAL_SELECTOR_SEGMENTS_NOT_QUALIFICATION',
        'counts': counts, 'priorWindowParity': True, 'modelCalls': 0, 'globalCoverageComplete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); root = args.output.resolve()
    if root.exists() or not root.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()
    result, receipt = build(load_ledger(args.base), batches)
    root.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', result), ('receipt.json', receipt)):
        (root / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__': main()
