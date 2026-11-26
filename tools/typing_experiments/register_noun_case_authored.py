"""Register historical authored noun-case training exposure from its exact source."""

import argparse
import copy
import json
from pathlib import Path
import sys

from audit_authored_training_history import verify_payload
from holdout_ledger import keys_for, validate_ledger
from noun_case_contrast_corpus import generate
from recover_available_v6_articles import LEDGER, ROOT, sha_file

EVIDENCE = ROOT / 'docs/acceptance/2026-10-26-noun-case-training-evidence.json'
PREFIX = 'authored-noun-case-training-v1-'
ORIGINAL = 'build/noun-case-training-20261026/corpus/train.jsonl'


def entries(lexicon):
    proof = json.loads(EVIDENCE.read_bytes())
    expected = proof['trainingSelection']['corpusSha256']
    rows, _ = generate(lexicon)
    verify_payload(rows, {'corpusSha256': expected, 'rows': 1140}, expected)
    families = set()
    contexts = []
    for row in rows:
        if (row['purpose'] != 'AUTHORED_CONTRAST_TRAINING_ONLY' or row['split'] != 'train'
                or row['language'] != 'ru' or len(set(row['contrastCandidates'])) != 2):
            raise ValueError('NOUN_AUTHORED_ROW_SCOPE')
        for target in row['contrastCandidates']:
            lemmas = {a.lemma for a in lexicon.analyses(target)}
            if not lemmas:
                raise ValueError('NOUN_AUTHORED_UNRESOLVED_FORM')
            families.update(lemmas)
            contexts.append(dict(prefix=row['prefix'], typed=row['typed'], expectedSpelling=target))
    bindings = {ORIGINAL: expected}
    for path in (EVIDENCE, Path(__file__),
                 ROOT / 'tools/typing_experiments/noun_case_contrast_corpus.py',
                 ROOT / 'tools/typing_experiments/grammar_contrast_corpus.py',
                 ROOT / 'tools/morphology/requirements.lock'):
        bindings[str(path.resolve().relative_to(ROOT))] = sha_file(path)
    keys = {
        'family': keys_for([{'families': sorted(families)}], 'family'),
        'context': keys_for(contexts, 'context'),
    }
    return [
        dict(id=PREFIX + 'families', usage='prepared-training-quarantine', bindings=bindings,
             keys={'family': sorted(keys['family'])}, missingAxes=[], rowCount=len(rows),
             notes='Exact authored training payload. Canonical exclusions use all dictionary analyses of both contrast forms.'),
        dict(id=PREFIX + 'contexts', usage='historical-context-exclusion', bindings=bindings,
             keys={'context': sorted(keys['context'])}, missingAxes=[], rowCount=len(rows),
             notes='Exact authored training payload. Excludes each template prefix with both contrast targets.'),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon

    expected = entries(PymorphyLexicon(cache_size=16384))
    ledger = json.loads(LEDGER.read_bytes())
    # Keep previously packed entries byte-stable in the output.
    decoded = validate_ledger(copy.deepcopy(ledger))
    present = [item for item in decoded['entries'] if item['id'].startswith(PREFIX)]
    if args.check:
        if present != expected:
            raise ValueError('NOUN_AUTHORED_REGISTRY_DRIFT')
    else:
        if present and present != expected:
            raise ValueError('NOUN_AUTHORED_REGISTRY_DRIFT')
        if not present:
            ledger['entries'].extend(expected)
            decoded['entries'].extend(expected)
        validate_ledger(decoded)
        with args.output.open('x') as out:
            out.write(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    print(json.dumps({axis: len(entry['keys'][axis])
                      for entry, axis in zip(expected, ('family', 'context'), strict=True)}))


if __name__ == '__main__':
    main()
