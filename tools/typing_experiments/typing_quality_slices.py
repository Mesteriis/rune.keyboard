#!/usr/bin/env python3
"""Report observed product quality by word length, context and edit count; never fit policy."""
import argparse
import hashlib
import json
from pathlib import Path


def edit_distance(left, right):
    """Unit optimal-string-alignment distance, including adjacent transposition."""
    matrix = [list(range(len(right) + 1))]
    for i, a in enumerate(left, 1):
        row = [i] + [0] * len(right)
        for j, b in enumerate(right, 1):
            row[j] = min(row[j - 1] + 1, matrix[i - 1][j] + 1,
                         matrix[i - 1][j - 1] + (a != b))
            if i > 1 and j > 1 and a == right[j - 2] and left[i - 2] == b:
                row[j] = min(row[j], matrix[i - 2][j - 2] + 1)
        matrix.append(row)
    return matrix[-1][-1]


def evaluate(rows, observations):
    ids = [row['id'] for row in rows]
    if len(set(ids)) != len(ids) or [o.get('id') for o in observations] != ids:
        raise ValueError('OBSERVATION_IDENTITY')
    groups = {}
    for row, observation in zip(rows, observations, strict=True):
        if observation.get('status') != 'COMPLETE':
            raise ValueError('INCOMPLETE_OBSERVATION')
        typed, prefix = row['typed'], row.get('prefix', '')
        if observation.get('typed') != typed or observation.get('prefix') != prefix:
            raise ValueError('INPUT_CONTEXT_CHANGED')
        typo = row['cohort'] == 'typo' and row['noAuto'] is False
        target = row.get('expectedSpelling', row.get('expectedCandidate')) if typo else typed
        if not isinstance(target, str) or not target:
            raise ValueError('MISSING_TARGET')
        expected_input = (prefix + ' ' if prefix else '') + typed
        before = observation.get('beforeBoundary', {}).get('text')
        after = observation.get('afterBoundary', {}).get('text')
        if not isinstance(before, str) or not isinstance(after, str) or not after.endswith(' '):
            raise ValueError('EDITOR_OUTPUT_CHANGED')
        transformed_input = before != expected_input
        if observation.get('inputChangedByTyping', False) != transformed_input:
            raise ValueError('INPUT_TRANSFORM_FLAG_MISMATCH')
        editor_prefix = before[:-len(typed)] if typed and before.casefold().endswith(typed.casefold()) else None
        prefix_changed = editor_prefix is None or not after.startswith(editor_prefix)
        changed = after != before + ' '
        if type(observation.get('boundaryChangedBeyondInsertedSpace')) is not bool or changed != observation['boundaryChangedBeyondInsertedSpace']:
            raise ValueError('CHANGE_FLAG_MISMATCH')
        correct = changed and after.casefold() != (before + ' ').casefold() and typo and not prefix_changed and after[len(editor_prefix):-1].casefold() == target.casefold()
        pool = observation.get('fullTokenGeneration') or {}
        retrieved = any(c.get('text', '').casefold() == target.casefold() for key in
                        ('alternatives', 'compactAlternatives') for c in pool.get(key, []))
        recovery = pool.get('neighborRecovery') or {}
        retrieved |= any(c.get('text', '').casefold() == target.casefold() for c in recovery.get('alternatives', []))
        manual_pool = observation.get('manualSearchGeneration') or {}
        manual_retrieved = retrieved or any(c.get('text', '').casefold() == target.casefold()
            for c in manual_pool.get('alternatives', []))
        length = 'tiny_1_2' if len(typed) <= 2 else 'short_3_4' if len(typed) <= 4 else 'long_5_plus'
        edits = edit_distance(typed.casefold(), target.casefold())
        labels = ['all', length, 'with_context' if prefix.strip() else 'without_context',
                  'multi_edit' if typo and edits >= 2 else 'single_edit' if typo else 'controls']
        for label in labels:
            item = groups.setdefault(label, dict(rows=0, typos=0, replacements=0, correct=0,
                incorrect=0, controlChanges=0, retrievedTypos=0, undoFailures=0, inputTransformations=0, prefixChanges=0, caseOnlyChanges=0, manualRetrievedTypos=0))
            item['inputTransformations'] += transformed_input
            item['prefixChanges'] += prefix_changed
            item['caseOnlyChanges'] += changed and after.casefold() == (before + ' ').casefold()
            item['rows'] += 1
            item['typos'] += typo
            item['replacements'] += changed
            item['correct'] += correct
            item['incorrect'] += changed and not correct
            item['controlChanges'] += changed and not typo
            item['retrievedTypos'] += typo and retrieved
            item['manualRetrievedTypos'] += typo and manual_retrieved
            item['undoFailures'] += changed and observation.get('restoredBeforeBoundaryExactly') is not True
    for item in groups.values():
        item['spellingReplacements'] = item['replacements'] - item['caseOnlyChanges']
        item['spellingPrecision'] = item['correct'] / item['spellingReplacements'] if item['spellingReplacements'] else None
        item['precision'] = item['correct'] / item['replacements'] if item['replacements'] else None
        item['recall'] = item['correct'] / item['typos'] if item['typos'] else None
    return {'schema': 1, 'purpose': 'descriptive_product_diagnostics_not_qualification', 'slices': groups}


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'observations', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(read(args.rows), read(args.observations))
    result['inputs'] = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in
                        [('rows', args.rows), ('observations', args.observations)]}
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
