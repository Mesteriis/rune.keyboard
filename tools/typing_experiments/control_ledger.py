"""Language-qualified historical control identities, separate from lexical families."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

SCHEMA='rune-public-control-exclusions-v1'
KINDS=('punctuation','protected')
LANGUAGES=('en','ru','es')
HASH=re.compile('[0-9a-f]{64}\\Z')


def text(value):
    if not isinstance(value,str) or not value:raise ValueError('CONTROL_TEXT')
    return unicodedata.normalize('NFC',value)


def key_for(row,kind):
    if kind not in KINDS or row.get('language') not in LANGUAGES:raise ValueError('CONTROL_SCOPE')
    if kind=='punctuation':
        boundary=row.get('expectedBoundary')
        if boundary not in (' ', ', ', ': ', '. '):raise ValueError('CONTROL_BOUNDARY')
        # Expected labels must not make a disclosed context appear fresh.
        fields=[text(row.get('prefix')),text(row.get('currentWord'))]
    else:fields=[text(row.get('prefix')),text(row.get('typed'))]
    payload=[SCHEMA,kind,row['language'],*fields]
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def validate(ledger):
    if (not isinstance(ledger,dict) or ledger.get('schema')!=SCHEMA or ledger.get('publicDataOnly') is not True
            or ledger.get('coverageComplete') is not False or not ledger.get('pending')
            or not isinstance(ledger['pending'],list) or any(not isinstance(p,str) or not p for p in ledger['pending'])
            or not isinstance(ledger.get('entries'),list) or not ledger['entries']):raise ValueError('CONTROL_LEDGER_SCHEMA')
    ids=set()
    for entry in ledger['entries']:
        if (not isinstance(entry,dict) or not isinstance(entry.get('id'),str) or not entry['id'] or entry['id'] in ids
                or entry.get('kind') not in KINDS or entry.get('language') not in LANGUAGES
                or type(entry.get('rowCount')) is not int or entry['rowCount']<1
                or not isinstance(entry.get('bindings'),dict) or not entry['bindings']
                or any(not isinstance(p,str) or not p or not isinstance(h,str) or not HASH.fullmatch(h) for p,h in entry['bindings'].items())):
            raise ValueError('CONTROL_ENTRY')
        ids.add(entry['id']);keys=entry.get('keys')
        if (not isinstance(keys,list) or not keys or len(keys)>entry['rowCount']
                or any(not isinstance(k,str) or not HASH.fullmatch(k) for k in keys) or keys!=sorted(set(keys))):
            raise ValueError('CONTROL_KEYS')
    return ledger


def load(path):return validate(json.loads(Path(path).read_text()))


def assert_disjoint(rows,ledger,kind):
    validate(ledger);rows=list(rows)
    if not rows:raise ValueError('CONTROL_EMPTY_ROWS')
    keys={key_for(row,kind) for row in rows}
    blocked={k for e in ledger['entries'] if e['kind']==kind for k in e['keys']}
    if keys&blocked:raise ValueError('CONTROL_OVERLAP:'+kind)
    # A control registry alone never certifies overall corpus freshness.
    raise ValueError('CONTROL_COVERAGE_INCOMPLETE')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,default=Path(__file__).with_name('control-ledger.json'))
    parser.add_argument('--validate-only',action='store_true');parser.add_argument('--rows',type=Path)
    parser.add_argument('--kind',choices=KINDS);args=parser.parse_args();ledger=load(args.ledger)
    if args.validate_only:
        if args.rows or args.kind:parser.error('validation does not check rows')
        print(json.dumps(dict(schemaValid=True,coverageComplete=False,entries=len(ledger['entries']))));return
    if args.rows is None or args.kind is None:parser.error('--rows and --kind are required')
    assert_disjoint([json.loads(line) for line in args.rows.read_text().splitlines()],ledger,args.kind)


if __name__=='__main__':main()
