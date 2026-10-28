#!/usr/bin/env python3
"""Deterministic authored stress cases and host-only diagnostics; never qualify a policy."""
import argparse
import base64
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from typing_quality_slices import evaluate, read

# Authored everyday words; no private text, frequency fitting or random sampling.
WORDS = ('дом', 'кот', 'суп', 'мир', 'час', 'день', 'ночь', 'вода', 'окно',
         'утро', 'рука', 'мама', 'друг', 'книга', 'письмо', 'работа', 'дорога',
         'молоко', 'машина', 'сегодня', 'завтра', 'спасибо', 'пожалуйста',
         'сообщение', 'встреча', 'позвонить', 'поговорим', 'хорошо', 'нужен', 'новый')
KEY_ROWS = ('йцукенгшщзхъ', 'фывапролджэ', 'ячсмитьбю')
CONTROLS = ('я', 'ты', 'он', 'мы', 'вы', 'не', 'ни', 'да', 'нет', 'ну', 'ага',
            'мда', 'хм', 'ок', 'лол', 'дань', 'грань', 'стал', 'стул', 'будки',
            'будут', 'позволить', 'Анна', 'Иван', 'Ольга', 'Юрий', 'Яна',
            'Москва', 'Rune', 'Google', 'Yandex', 'Fold', 'API', 'WiFi')


def variants(word):
    """One representative per edit family and position, with stable deduplication."""
    seen = {word}
    for i, char in enumerate(word):
        proposals = [('missing', word[:i] + word[i + 1:]),
                     ('repeated', word[:i] + char + word[i:])]
        if i + 1 < len(word):
            proposals.append(('transposed', word[:i] + word[i + 1] + char + word[i + 2:]))
        for keys in KEY_ROWS:
            if char in keys:
                j = keys.index(char)
                # Horizontal physical neighbours only; no guessed cross-row geometry.
                for k in (j - 1, j + 1):
                    if 0 <= k < len(keys):
                        proposals.append(('neighbour', word[:i] + keys[k] + word[i + 1:]))
        for family, typed in proposals:
            if typed and typed not in seen:
                seen.add(typed)
                yield family, typed


def cases():
    rows = []
    for word in WORDS:
        for family, typed in variants(word):
            # Both contexts are deliberately semantically neutral.
            for prefix in ('', 'ну'):
                rows.append(dict(typed=typed, prefix=prefix, expectedSpelling=word,
                                 cohort='typo', noAuto=False, family=family))
    for word in (*WORDS, *CONTROLS):
        for prefix in ('', 'ну'):
            rows.append(dict(typed=word, prefix=prefix, expectedSpelling=word,
                             cohort='correct', noAuto=True, family='control'))
    return [dict(id=f'stress-{i:04d}', **row) for i, row in enumerate(rows)]


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def audit(rows, observations):
    # Reuse strict identity, editor, flags, prefix and Undo accounting.
    result = evaluate(rows, observations)
    families = {}
    refusals = Counter()
    valid_originals = dict(rows=0, retained=0, caseOnlyChanges=0, spellingChanges=0)
    failures = []
    case_only_departures = []
    no_callback_evidence = Counter()
    timings = {}
    for row, obs in zip(rows, observations, strict=True):
        pool = obs.get('actualRequestGeneration') or {}
        valid = pool.get('isValidWord') is True
        if valid and row['cohort'] == 'typo':
            valid_originals['rows'] += 1
            changed = obs['boundaryChangedBeyondInsertedSpace']
            case_only = obs['afterBoundary']['text'].casefold() == (obs['beforeBoundary']['text'] + ' ').casefold()
            valid_originals['retained' if not changed else 'caseOnlyChanges' if case_only else 'spellingChanges'] += 1
        if row['cohort'] == 'typo' and not obs['boundaryChangedBeyondInsertedSpace']:
            reason = obs.get('automaticAdmissionRefusal')
            # Absence of an admission callback is not an invented refusal reason.
            reason = reason or ('VALID_ORIGINAL' if valid else 'NO_ADMISSION_CALLBACK')
            refusals[reason] += 1
            if reason == 'NO_ADMISSION_CALLBACK':
                recovery = pool.get('neighborRecovery') or {}
                joint = obs.get('jointSearch') or {}
                no_callback_evidence[json.dumps(dict(
                    baseline=pool.get('completion'), protection=pool.get('protectedReason'),
                    recovery=recovery.get('completion'), joint=joint.get('completion')),
                    sort_keys=True)] += 1
        after = obs['afterBoundary']['text']
        before = obs['beforeBoundary']['text']
        prefix = before[:-len(row['typed'])] if before.endswith(row['typed']) else None
        intended = prefix is not None and after.casefold() == (prefix + row['expectedSpelling'] + ' ').casefold()
        item = families.setdefault(row['family'], dict(rows=0, intendedOutput=0, retained=0))
        item['rows'] += 1
        item['intendedOutput'] += intended
        item['retained'] += not obs['boundaryChangedBeyondInsertedSpace']
        if obs['boundaryChangedBeyondInsertedSpace'] and not intended:
            departures = case_only_departures if after.casefold() == (before + ' ').casefold() else failures
            departures.append(dict(id=row['id'], typed=row['typed'], target=row['expectedSpelling'],
                                   actual=after, validOriginal=valid, family=row['family']))
        for stage, value in obs.get('hostStageNanos', {}).items():
            if type(value) is not int or value < 0:
                raise ValueError('INVALID_STAGE_TIMING')
            timings.setdefault(stage, []).append(value / 1_000_000)
    if timings and any(len(values) != len(rows) for values in timings.values()):
        raise ValueError('INCOMPLETE_STAGE_TIMING')
    result.update(families=families, automaticAbstentions=dict(refusals),
                  dictionaryValidSyntheticTypos=valid_originals, unintendedSpellingChanges=failures,
                  caseOnlyDepartures=case_only_departures,
                  noAdmissionCallbackEvidence=[dict(observed=json.loads(key), rows=count)
                      for key, count in sorted(no_callback_evidence.items())],
                  hostTimingMs={stage: dict(samples=len(values), first=values[0],
                      p50=percentile(values, .5), p95=percentile(values, .95), maximum=max(values))
                      for stage, values in timings.items()})
    result['limitations'] = [
        'Authored discovery stress set, not independent qualification or natural typing accuracy.',
        'Some synthetic edits form valid words; retaining them can be correct product behaviour.',
        'Host word-boundary replay, not physical full-phrase input or Android deadline validation.',
        'Stage timings include JVM warmup; observer score exports and serialization are excluded.',
        'Controller timing includes ranking and admission; it does not isolate model inference.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--output', type=Path, required=True)
    report = sub.add_parser('report')
    for name in ('rows', 'observations', 'output'):
        report.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        rows = cases()
        (args.output / 'rows.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        def encoded(value):
            return base64.b64encode(value.encode()).decode()
        (args.output / 'inputs.tsv').write_text(''.join(
            '\t'.join([str(i), encoded(row['id']), 'holdout', 'ru', encoded(row['prefix']), encoded(row['typed'])]) + '\n'
            for i, row in enumerate(rows)))
        manifest = dict(schema=1, purpose='authored_discovery_not_qualification', rows=len(rows),
                        files={name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
                               for name in ('rows.jsonl', 'inputs.tsv')})
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    else:
        result = audit(read(args.rows), read(args.observations))
        result['inputs'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for name, path in [('rows', args.rows), ('observations', args.observations)]}
        with args.output.open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')


if __name__ == '__main__':
    main()
