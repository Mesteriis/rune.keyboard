"""Reproduce both original authored grammar corpora and register their exclusions."""

import argparse
import copy
import json
from pathlib import Path
import sys

from audit_authored_training_history import verify_payload
from grammar_contrast_corpus import generate
from holdout_ledger import keys_for, validate_ledger
from recover_available_v6_articles import LEDGER, ROOT, sha_file

PREFIX = 'authored-grammar-contrasts-20261026-'
ACCEPTANCE = ROOT / 'docs/acceptance'
SOURCES = (
    ('build/grammar-contrasts-20261026/train.jsonl', '2026-10-26-grammar-contrast-diagnostic.json', False, 630),
    ('build/grammar-contrasts-profiles-20261026/train.jsonl', '2026-10-26-grammar-edit-profile-training-evidence.json', True, 978),
)


def exposure(rows, lexicon):
    families, contexts = set(), []
    for row in rows:
        forms = set(row['contrastCandidates'])
        if (row['purpose'] != 'AUTHORED_CONTRAST_TRAINING_ONLY' or row['language'] != 'ru'
                or row['split'] != 'train' or len(forms) != 2 or row['expectedSpelling'] not in forms):
            raise ValueError('GRAMMAR_AUTHORED_ROW_SCOPE')
        for form in forms:
            lemmas = {analysis.lemma for analysis in lexicon.analyses(form)}
            if not lemmas:
                raise ValueError('GRAMMAR_AUTHORED_UNRESOLVED_FORM')
            families.update(lemmas)
            contexts.append(dict(prefix=row['prefix'], typed=row['typed'], expectedSpelling=form))
    return {'family': keys_for([{'families': sorted(families)}], 'family'),
            'context': keys_for(contexts, 'context')}


def entries(lexicon):
    paths = [Path(__file__), Path(__file__).with_name('grammar_contrast_corpus.py'),
             ROOT / 'tools/morphology/requirements.lock']
    bindings = {str(p.resolve().relative_to(ROOT)): sha_file(p) for p in paths}
    projections = []
    for name, filename, profiles, count in SOURCES:
        path = ACCEPTANCE / filename
        proof = json.loads(path.read_bytes())
        expected = (proof['profileValidation'] if profiles else proof)['corpusSha256']
        rows, _ = generate(lexicon, edit_profiles=profiles)
        verify_payload(rows, {'corpusSha256': expected, 'rows': count}, expected)
        projections.append(exposure(rows, lexicon))
        bindings[name] = expected
        bindings[str(path.relative_to(ROOT))] = sha_file(path)
    original, profiled = projections
    if original != profiled:
        raise ValueError('GRAMMAR_AUTHORED_PROJECTION_DIFFERS')
    return [
        dict(id=PREFIX + 'families', usage='prepared-training-quarantine', bindings=bindings,
             keys={'family': sorted(original['family'])}, missingAxes=[],
             notes='Both exact authored grammar contrast payloads share these canonical family keys.'),
        dict(id=PREFIX + 'contexts', usage='historical-context-exclusion', bindings=bindings,
             keys={'context': sorted(original['context'])}, missingAxes=[],
             notes='Both exact authored grammar contrast payloads expose each prefix with both contrast targets.'),
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
    packed = json.loads(LEDGER.read_bytes())
    decoded = validate_ledger(copy.deepcopy(packed))
    present = [item for item in decoded['entries'] if item['id'].startswith(PREFIX)]
    if present != expected and (args.check or present):
        raise ValueError('GRAMMAR_AUTHORED_REGISTRY_DRIFT')
    if args.output:
        if not present:
            validate_ledger(dict(decoded, entries=[*decoded['entries'], *expected]))
            packed['entries'].extend(expected)
        with args.output.open('x') as output:
            output.write(json.dumps(packed, indent=2, sort_keys=True) + '\n')
    print(json.dumps({axis: len(keys) for entry in expected for axis, keys in entry['keys'].items()}))


if __name__ == '__main__':
    main()
