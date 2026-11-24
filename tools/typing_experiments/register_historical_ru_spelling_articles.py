#!/usr/bin/env python3
"""Mirror recovered RU spelling article exclusions into the Q6 control namespace."""
import argparse
import json
from pathlib import Path

import control_ledger as control
import holdout_ledger as lexical
from import_early_ru_history import PREFIX as LEXICAL_PREFIX
from register_historical_qualification_controls import ARCHIVES, CONTROL, ROOT, inputs, sha

HERE = Path(__file__).resolve().parent
PREFIX = 'historical-ru-spelling-articles-'
REPORT_HASHES = {
    'v2': '79242c87b30183488c1a30a2055b24096a1cfc41bbcda4a4caf2d61be368c83a',
    'v3': '9634db900dde9e7c814dbfc734353c28a0e09c7a2f576b15890047fccae5a7f3',
    'v4': '57d10208e37dee2866bc2b829c6284940f6c76eae02c46b94decb5e29de5a973',
}


def derive():
    sources = inputs()
    lex = {e['id']: e for e in lexical.load_ledger(HERE / 'holdout-ledger.json')['entries']}
    entries = []
    for version, expected in REPORT_HASHES.items():
        path = ARCHIVES / 'punctuation-ru-attribution' / f'{version}-ru.json'
        raw = path.read_bytes()
        if sha(raw) != expected:
            raise ValueError('HISTORICAL_RU_CONTROL_REPORT')
        report = json.loads(raw)
        frozen = sources[version]['spelling-ru.jsonl']
        mapping = report['ruSpelling']
        if ((report['version'], report['language']) != (version, 'ru')
                or sha(frozen) != report['ruSpellingRowsSha256']
                or set(mapping) != {json.loads(line)['id'] for line in frozen.splitlines()}
                or any(not group for group in mapping.values())):
            raise ValueError('HISTORICAL_RU_CONTROL_BINDINGS')
        rows = [{'article': article, 'language': 'ru'}
                for article in {a for ids in mapping.values() for a in ids}]
        component = 'qualification-v2' if version == 'v2' else f'compact-{version}'
        if lexical.keys_for(rows, 'article') != set(lex[LEXICAL_PREFIX + component]['keys']['article']):
            raise ValueError('HISTORICAL_RU_CONTROL_LEXICAL_DRIFT')
        keys = sorted({control.article_key(row) for row in rows})
        dependencies = (path, Path(__file__), HERE / 'control_ledger.py', HERE / 'holdout_ledger.py',
                        HERE / 'register_historical_qualification_controls.py',
                        HERE / 'recover_historical_punctuation_attribution.py')
        entries.append({
            'id': PREFIX + version, 'kind': 'source', 'language': 'ru', 'rowCount': len(keys),
            'keys': [], 'articleKeys': keys,
            'bindings': {str(dep.relative_to(ROOT)): sha(dep.read_bytes()) for dep in dependencies},
            'semantics': 'All possible source articles of disclosed RU spelling rows, mirrored from the lexical registry.',
        })
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--output', type=Path)
    args = parser.parse_args()
    original = CONTROL.read_bytes()
    ledger = control.validate(json.loads(original))
    entries = derive()
    existing = [entry for entry in ledger['entries'] if entry['id'].startswith(PREFIX)]
    if args.check:
        if existing != entries:
            raise ValueError('HISTORICAL_RU_CONTROL_REGISTRY_DRIFT')
    else:
        output = args.output.resolve()
        if existing or not output.is_relative_to(ROOT / 'build'):
            raise ValueError('HISTORICAL_RU_CONTROL_OUTPUT')
        ledger['entries'].extend(entries)
        control.validate(ledger)
        if CONTROL.read_bytes() != original or derive() != entries:
            raise ValueError('HISTORICAL_RU_CONTROL_INPUT_DRIFT')
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'entries': len(entries),
                      'articleKeys': len({key for entry in entries for key in entry['articleKeys']})}))


if __name__ == '__main__':
    main()
