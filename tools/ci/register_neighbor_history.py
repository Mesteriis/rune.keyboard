"""Register disclosed historical neighbor rows as permanent public exclusions."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

FIXTURE = ROOT / 'tools/typing_experiments/neighbor-history-v1'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'historical-neighbor-recovery-public-v1'
PINS = {'manifest.json': '2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e',
        'articles.jsonl': 'a0b380cc8791985eb2a7e11641cbb6c69310836c08b7cfc4df0e0302912905ed',
        'NOTICE.md': '577756752127f06c3c6d1a2e28286b6fe0660dbb815da79c6a5b3703bc5ecbeb'}
GROUPS = ('adjacent2', 'adjacent3', 'mixed2', 'mixed3', 'correct', 'protected')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def project(rows):
    """Normalize only source-attested article, target context and public surfaces."""
    mapped = [dict(article=row['article'], language='ru', prefix=row['prefix'],
                   typed=row['typed'], expectedSpelling=row['word']) for row in rows]
    controls = [r | {'typed': value} for r in mapped for value in (r['typed'], r['expectedSpelling'])]
    contexts = mapped + [mapped[index] | {'expectedSpelling': row['expected']}
                         for index, row in enumerate(rows) if row['expected'] != row['word']]
    return {'article': sorted(lexical.keys_for(mapped, 'article')),
            'context': sorted(lexical.keys_for(contexts, 'context')),
            'regression': sorted({control.key_for(r, 'regression') for r in controls}),
            'surface': sorted({control.surface_key('ru', r['typed']) for r in controls}),
            'controlArticle': sorted({control.article_key(r) for r in mapped})}


def inputs():
    raw = {name: (FIXTURE / name).read_bytes() for name in PINS}
    if any(sha(raw[name]) != digest for name, digest in PINS.items()):
        raise ValueError('NEIGHBOR_HISTORY_FIXTURE_IDENTITY')
    manifest = json.loads(raw['manifest.json'])
    original = ROOT / 'tools/typing_experiments/historical_provenance_sources/joint-neighbor-receipts/neighbor-corpus-manifest.json'
    if (original.read_bytes() != raw['manifest.json'] or manifest.get('publicOnly') is not True or
            manifest.get('schema') != 1 or manifest.get('seed') != 'neighbor-recovery-v1-20260926' or
            set(manifest.get('files', {})) != {'train.jsonl', 'calibration.jsonl', 'holdout.jsonl'}):
        raise ValueError('NEIGHBOR_HISTORY_MANIFEST')
    rows = []
    for part, quota in (('train', 1000), ('calibration', 500), ('holdout', 1000)):
        name = part + '.jsonl'
        raw[name] = (FIXTURE / name).read_bytes()
        if sha(raw[name]) != manifest['files'][name]:
            raise ValueError('NEIGHBOR_HISTORY_ROWS')
        current = [json.loads(line) for line in raw[name].splitlines()]
        if len(current) != 6 * quota or Counter(r.get('group') for r in current) != {group: quota for group in GROUPS}:
            raise ValueError('NEIGHBOR_HISTORY_COUNTS')
        for row in current:
            if (row.get('split') != part or not isinstance(row.get('id'), str) or not row['id'] or
                    not isinstance(row.get('article'), str) or not row['article'].isascii() or not row['article'].isdecimal() or
                    not isinstance(row.get('prefix'), str) or not row['prefix'] or
                    any(not isinstance(row.get(key), str) or not row[key] for key in ('typed', 'word', 'expected', 'family')) or
                    not row['family'].isdecimal() or row.get('shard') not in range(11, 18) or
                    type(row.get('noAuto')) is not bool):
                raise ValueError('NEIGHBOR_HISTORY_ROW')
            if ((row['shard'] <= 13) != (part == 'train') or
                    (row['shard'] in (14, 15)) != (part == 'calibration') or
                    (row['shard'] >= 16) != (part == 'holdout')):
                raise ValueError('NEIGHBOR_HISTORY_SPLIT')
            if row['expected'] != (row['typed'] if row['group'] == 'protected' else row['word']):
                raise ValueError('NEIGHBOR_HISTORY_TARGET')
        rows.extend(current)
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('NEIGHBOR_HISTORY_DUPLICATE')
    articles = [json.loads(line) for line in raw['articles.jsonl'].splitlines()]
    ids = {row['article'] for row in rows}
    if (len(articles) != 2426 or len(ids) != 2426 or {row.get('articleId') for row in articles} != ids or
            any(not isinstance(row.get('title'), str) or not row['title'] or row.get('historyUrl') !=
                'https://ru.wikipedia.org/w/index.php?curid=' + row.get('articleId', '') + '&action=history'
                for row in articles)):
        raise ValueError('NEIGHBOR_HISTORY_ATTRIBUTION')
    paths = [Path(__file__).resolve(), original, ROOT / 'tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md',
             *(FIXTURE / name for name in raw)]
    bindings = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}
    return rows, bindings


def entries():
    rows, bindings = inputs()
    keys = project(rows)
    ledger = dict(id=ENTRY, usage='historical-exclusion', rowCount=len(rows), bindings=bindings,
                  keys={'article': keys['article'], 'context': keys['context']}, missingAxes=['family', 'sentence'],
                  notes='Disclosed public neighbor-recovery rows; numeric native family IDs are not canonical lemmas.')
    controls = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows) * 2, bindings=bindings,
                    keys=keys['regression'], surfaceKeys=keys['surface'], articleKeys=keys['controlArticle'],
                    semantics='Disclosed public typo and intended-word surfaces; not an independent holdout.')
    return ledger, controls


def check():
    entry, controls = entries()
    lex = lexical.load_ledger(LEXICAL)
    con = control.load(CONTROL)
    if ([item for item in lex['entries'] if item['id'] == ENTRY] != [entry] or
            [item for item in con['entries'] if item['id'] == ENTRY] != [controls]):
        raise ValueError('NEIGHBOR_HISTORY_REGISTRY_DRIFT')
    return entry['rowCount']


def run(output):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_HISTORY_OUTPUT')
    old_lex, old_con = LEXICAL.read_bytes(), CONTROL.read_bytes()
    stored, controls = json.loads(old_lex), json.loads(old_con)
    logical = lexical.validate_ledger(copy.deepcopy(stored))
    control.validate(controls)
    if any(item['id'] == ENTRY for item in logical['entries'] + controls['entries']):
        raise ValueError('NEIGHBOR_HISTORY_EXISTS')
    entry, new_controls = entries()
    stored['entries'].append(entry)
    controls['entries'].append(new_controls)
    lexical.validate_ledger(copy.deepcopy(stored))
    control.validate(controls)
    if LEXICAL.read_bytes() != old_lex or CONTROL.read_bytes() != old_con or entries() != (entry, new_controls):
        raise ValueError('NEIGHBOR_HISTORY_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('holdout-ledger.json', stored), ('control-ledger.json', controls)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': entry['rowCount'], 'articles': len(entry['keys']['article']),
                      'contexts': len(entry['keys']['context']), 'surfaces': len(new_controls['surfaceKeys']),
                      'regressionKeys': len(new_controls['keys']), 'independentQualification': False}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check and args.output is None:
        print(json.dumps({'rows': check(), 'independentQualification': False}))
    elif not args.check and args.output is not None:
        run(args.output)
    else:
        parser.error('choose --check or --output')
