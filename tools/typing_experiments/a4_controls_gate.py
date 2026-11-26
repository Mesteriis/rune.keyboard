#!/usr/bin/env python3
"""Verify the disclosed A4 control replays; never qualify natural accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/eval/smart-typing-0.3/pipeline'))
import replay_projection as projection
import control_ledger
from local_spelling_stress import restore_source_ids

COUNTS = {'abbreviation': 54, 'domain_label': 43, 'list_heading': 43}
BOUNDARIES = {'space': ' ', 'period': '.', 'colon': ':'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line, object_pairs_hook=projection.unique_object,
                       parse_constant=projection.invalid_constant)
            for line in Path(path).read_text(encoding='utf-8').splitlines() if line]


def evaluate(rows, observations, boundary):
    if boundary not in BOUNDARIES: raise ValueError('A4_BOUNDARY')
    if len(rows) != 140 or len(observations) != len(rows): raise ValueError('A4_ROW_COUNT')
    if Counter(row.get('family') for row in rows) != COUNTS: raise ValueError('A4_CATEGORIES')
    if len({row.get('id') for row in rows}) != len(rows): raise ValueError('A4_DUPLICATE_ID')
    char = BOUNDARIES[boundary]
    counts = {name: {'rows': 0, 'changes': 0, 'undoFailures': 0} for name in COUNTS}
    failures = []
    for row, obs in zip(rows, observations, strict=True):
        if (row.get('language') != 'ru' or row.get('prefix') != '' or row.get('split') != 'holdout'
                or row.get('cohort') != 'correct' or row.get('noAuto') is not True
                or not isinstance(row.get('typed'), str) or not row['typed']
                or row.get('expectedSpelling') != row['typed']): raise ValueError('A4_ROW_SHAPE')
        if any(obs.get(k) != row[k] for k in ('id', 'language', 'prefix', 'typed', 'split')) or obs.get('status') != 'COMPLETE':
            raise ValueError('A4_OBSERVATION_IDENTITY')
        if obs.get('boundaryResult') != 'HANDLED' or obs.get('backspaceResult') != 'HANDLED':
            raise ValueError('A4_ACTION_NOT_HANDLED')
        before = obs.get('beforeBoundary', {}).get('text')
        after = obs.get('afterBoundary', {}).get('text')
        back = obs.get('afterBackspace', {}).get('text')
        if before != row['typed'] or obs.get('inputChangedByTyping') is not False or not isinstance(after, str) or not isinstance(back, str):
            raise ValueError('A4_EDITOR_STATE')
        if boundary != 'space' and obs.get('boundary') != char: raise ValueError('A4_BOUNDARY_MISMATCH')
        flag = 'boundaryChangedBeyondInsertedSpace' if boundary == 'space' else 'boundaryChangedBeyondInsertion'
        changed = after != before + char
        if type(obs.get(flag)) is not bool or obs[flag] != changed: raise ValueError('A4_CHANGE_FLAG')
        restored = back == before
        if type(obs.get('restoredBeforeBoundaryExactly')) is not bool or obs['restoredBeforeBoundaryExactly'] != restored:
            raise ValueError('A4_UNDO_FLAG')
        item = counts[row['family']]; item['rows'] += 1; item['changes'] += changed; item['undoFailures'] += not restored
        if changed or not restored: failures.append({'id': row['id'], 'category': row['family'], 'changed': changed, 'undoFailed': not restored})
    return {'boundary': boundary, 'categories': counts, 'failures': failures, 'passed': not failures}


def run(rows_path, directories):
    rows_path = Path(rows_path).resolve(strict=True)
    rows = read_rows(rows_path)
    ledger = control_ledger.load(ROOT / 'tools/typing_experiments/control-ledger.json')
    entries = [entry for entry in ledger['entries'] if entry['id'] == 'review-a4-authored-controls-v1-ru']
    if (len(entries) != 1 or entries[0]['kind'] != 'regression' or entries[0]['language'] != 'ru'
            or entries[0]['rowCount'] != len(rows)
            or entries[0]['bindings'].get(rows_path.relative_to(ROOT).as_posix()) != sha(rows_path)
            or entries[0]['keys'] != sorted({control_ledger.key_for(row, 'regression') for row in rows})
            or entries[0].get('surfaceKeys') != sorted({control_ledger.surface_key('ru', row['typed']) for row in rows})):
        raise ValueError('A4_LEDGER_BINDING')
    results = {}
    shared_bindings = None
    for boundary, directory in directories.items():
        root = Path(directory).resolve(strict=True)
        receipt = json.loads((root / 'receipt.json').read_text(), object_pairs_hook=projection.unique_object)
        if (receipt.get('status') != 'COMPLETE' or receipt.get('exitCode') != 0 or receipt.get('boundary') != boundary
                or receipt.get('deterministic') is not True or receipt.get('rows') != len(rows)):
            raise ValueError('A4_RECEIPT')
        files = receipt.get('files')
        if not isinstance(files, dict) or not files: raise ValueError('A4_BINDINGS')
        corpus_key = rows_path.relative_to(ROOT).as_posix()
        if files.get(corpus_key) != sha(rows_path): raise ValueError('A4_CORPUS_BINDING')
        if shared_bindings is None: shared_bindings = files
        elif shared_bindings != files: raise ValueError('A4_BINDING_DRIFT')
        for path, digest in files.items():
            candidate = Path(path) if Path(path).is_absolute() else ROOT / path
            if not candidate.is_file() or sha(candidate) != digest: raise ValueError('A4_FILE_DRIFT:' + path)
        if sha(root / 'inputs.tsv') != receipt.get('labelFreeInputsSha256') or sha(root / 'input-identities.jsonl') != receipt.get('hostOnlyIdentitiesSha256'):
            raise ValueError('A4_INPUT_BINDING')
        outputs = [root / name / 'observations.jsonl' for name in ('first', 'second')]
        for name, output in zip(('first', 'second'), outputs, strict=True):
            if sha(output) != receipt[name]['observationsSha256']: raise ValueError('A4_OBSERVATION_BINDING')
        projections = [projection.read_projection(path) for path in outputs]
        if not projection.compare(*projections)['passed'] or sha(root / 'projection.jsonl') != receipt.get('projectionSha256'):
            raise ValueError('A4_NONDETERMINISTIC')
        if projection.projection_bytes(projections[1]) != (root / 'projection.jsonl').read_bytes():
            raise ValueError('A4_PROJECTION_BINDING')
        observations = restore_source_ids(rows, projections[0], read_rows(root / 'input-identities.jsonl'))
        results[boundary] = evaluate(rows, observations, boundary)
        results[boundary]['receiptSha256'] = sha(root / 'receipt.json')
    return {'schema': 1, 'purpose': 'disclosed_regression_not_qualification', 'inputSha256': sha(rows_path),
            'results': results, 'passed': all(item['passed'] for item in results.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=Path, required=True)
    for name in BOUNDARIES: parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.rows, {name: getattr(args, name) for name in BOUNDARIES})
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2); stream.write('\n')
    print(json.dumps({'passed': result['passed']}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr); sys.exit(2)
