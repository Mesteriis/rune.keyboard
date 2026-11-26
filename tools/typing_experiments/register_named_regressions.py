"""Bind disclosed standalone named controls; never certify corpus freshness."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import control_ledger as controls

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / 'tools/eval/smart-typing-0.3/pipeline'
sys.path.insert(0, str(PIPELINE))
import run_local_qualification as runner


def entries():
    paths = (Path(__file__), Path(controls.__file__), Path(runner.__file__))
    bindings = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    rows = runner.named_rows()
    result = []
    for language in controls.LANGUAGES:
        selected = [r for r in rows if r['language'] == language]
        if not selected or any(r['prefix'] != '' or r['purpose'] != 'REGRESSION_ONLY_NOT_TRAINING'
                               for r in selected):
            raise ValueError('NAMED_DISCLOSURE_SCOPE')
        result.append(dict(id='public-named-common-confusion-regression-v1-' + language,
            kind='regression', language=language, rowCount=len(selected), bindings=bindings,
            keys=sorted({controls.key_for(r, 'regression') for r in selected}),
            surfaceKeys=sorted({controls.surface_key(language, r['typed']) for r in selected}),
            note='Disclosed public spelling examples and controls; no independent qualification or canonical-family claim.'))
    return result


def register(ledger):
    controls.validate(ledger)
    added = entries()
    if {e['id'] for e in ledger['entries']} & {e['id'] for e in added}:
        raise ValueError('NAMED_ALREADY_REGISTERED')
    return controls.validate(ledger | {'entries': ledger['entries'] + added})


def check(ledger):
    controls.validate(ledger)
    existing = {e['id']: e for e in ledger['entries']}
    if any(existing.get(e['id']) != e for e in entries()):
        raise ValueError('NAMED_REGISTRY_DRIFT')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=Path(__file__).with_name('control-ledger.json'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--output', type=Path)
    args = parser.parse_args()
    ledger = controls.load(args.ledger)
    if args.check:
        check(ledger)
        expected = entries()
        print(json.dumps(dict(namedRows=sum(e['rowCount'] for e in expected),
                              entries=len(expected), coverageComplete=False)))
    else:
        proposed = register(ledger)
        with args.output.open('x', encoding='utf-8') as out:
            json.dump(proposed, out, ensure_ascii=False, sort_keys=True, indent=2)
            out.write('\n')


if __name__ == '__main__': main()
