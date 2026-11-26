#!/usr/bin/env python3
"""Screen disclosed case labels against pinned dictionary-only morphology."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/morphology'))
from ranker import PymorphyLexicon  # noqa: E402
from chat_case_review import LABELS, PURPOSE  # noqa: E402

PROPER = frozenset(('Name', 'Surn', 'Patr', 'Geox'))


def screen(review, lexicon):
    if review.get('schema') != 1 or review.get('purpose') != PURPOSE:
        raise ValueError('CASE_SCREEN_SCOPE')
    cases = review.get('cases')
    if not isinstance(cases, list) or not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('CASE_SCREEN_IDS')
    buckets = Counter()
    for case in cases:
        if set(case) != {'id', 'typed', 'baseline', 'label'} or case['label'] not in LABELS:
            raise ValueError('CASE_SCREEN_SCHEMA')
        analyses = lexicon.analyses(case['typed'])
        proper = any(PROPER & a.grammemes for a in analyses)
        other = any(not (PROPER & a.grammemes) for a in analyses)
        kind = 'proper_and_other' if proper and other else 'proper_only' if proper else 'other_only' if other else 'unknown'
        buckets[case['label'], kind] += 1
    return {'purpose': 'DISCLOSED_MORPHOLOGY_SCREEN_NOT_QUALIFICATION',
            'counts': [{'reviewLabel': label, 'dictionaryEvidence': kind, 'occurrences': count}
                       for (label, kind), count in sorted(buckets.items())],
            'independentQualification': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.review.read_bytes()
    lexicon = PymorphyLexicon()
    result = screen(json.loads(raw), lexicon)
    result['reviewSha256'] = hashlib.sha256(raw).hexdigest()
    result['toolSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['rankerSha256'] = hashlib.sha256((ROOT / 'tools/morphology/ranker.py').read_bytes()).hexdigest()
    result['lexiconReceipt'] = lexicon.receipt()
    if args.review.read_bytes() != raw:
        raise ValueError('CASE_SCREEN_INPUT_DRIFT')
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
