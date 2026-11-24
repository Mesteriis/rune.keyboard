"""Register source-token contexts of disclosed refinement historical text."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/typing_experiments'), str(ROOT / 'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical
import historical_data_fixtures as fixtures
from audit_selector_text_exposure import WORD
from audit_refinement_text_source_boundaries import HELPERS
from audit_wordrank_source_boundaries import TOKEN

ENTRY = 'historical-refinement-text-source-boundaries-v1'
FIXTURE = ROOT / 'tools/typing_experiments/refinement-text-boundary-origin-v1'
SOURCE = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
AUDIT = ROOT / 'tools/typing_experiments/audit_refinement_text_source_boundaries.py'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
PARTS = ('train', 'dev', 'test')

SNAPSHOTS = {
    'tools/typing_experiments/control_ledger.py': '0dc79fb6fa98cf5cd4ed28c5aa7379da6a4d16eecf736e77655f0e5e59eed045',
    'tools/typing_experiments/independent_corpus_guard.py': 'f8bf944977321d8f2864308a8b822a39c11e47f23b87793e28bf298f42de4ce6',
}


def helper_path(name):
    return FIXTURE / 'sources' / (SNAPSHOTS[name] + '.txt') if name in SNAPSHOTS else ROOT / name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inputs():
    raw = (FIXTURE / 'contexts.jsonl').read_bytes()
    receipt_bytes = (FIXTURE / 'receipt.json').read_bytes()
    receipt = json.loads(receipt_bytes)
    if receipt.get('contextsSha256') != sha(raw):
        raise ValueError('REF_SOURCE_BINDING')
    lock = SOURCE.read_bytes()
    archive = fixtures.verify()
    names = {p: f'typing-refinement/data/{p}-text.jsonl' for p in PARTS}
    archived = {p: [json.loads(line) for line in archive[name].splitlines()] for p, name in names.items()}
    by_article = {part: {row['articleId']: row for row in rows} for part, rows in archived.items()}
    if any(len(by_article[p]) != len(archived[p]) for p in PARTS):
        raise ValueError('REF_SOURCE_ARCHIVE_DUPLICATE')
    rows = [json.loads(line) for line in raw.splitlines()]
    counts = receipt.get('counts', {})
    if (not rows or receipt.get('scope') != 'disclosed-historical-refinement-text-source-boundary' or
            receipt.get('independentQualification') is not False or receipt.get('contextsSha256') != sha(raw) or
            receipt.get('sourceLockSha256') != sha(lock) or receipt.get('sourceSha256') !=
            json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
            receipt.get('archiveTextSha256') != {p: sha(archive[n]) for p, n in names.items()} or
            receipt.get('analyzerSha256') != sha(AUDIT.read_bytes()) or
            receipt.get('helperSha256') != {name: sha(helper_path(name).read_bytes()) for name in HELPERS} or
            counts.get('contexts') != len(rows) or counts.get('unknownSurfaces') != 10745 or
            counts.get('distinctFullForms') != 1370 or counts.get('newSurfaces') != 1291):
        raise ValueError('REF_SOURCE_BINDING')
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'id', 'partition', 'language', 'article', 'prefix',
                'typed', 'expectedSpelling', 'head', 'wordOrdinal', 'sourceStart', 'sourceEnd'}):
            raise ValueError('REF_SOURCE_ROW')
        part, article, token, head = row['partition'], row['article'], row['typed'], row['head']
        if (part not in PARTS or row['language'] != 'ru' or not isinstance(article, str) or
                article not in by_article[part] or not isinstance(token, str) or not TOKEN.fullmatch(token) or
                not isinstance(head, str) or not head or not isinstance(row['prefix'], str) or
                row['expectedSpelling'] != token or type(row['wordOrdinal']) is not int or
                type(row['sourceStart']) is not int or type(row['sourceEnd']) is not int or
                row['sourceStart'] < 0 or row['sourceEnd'] - row['sourceStart'] != len(token)):
            raise ValueError('REF_SOURCE_ROW')
        identity = f"{part}:{article}:{row['sourceStart']}:{row['sourceEnd']}:{row['wordOrdinal']}"
        if row['id'] != sha(identity.encode()) or row['id'] in seen:
            raise ValueError('REF_SOURCE_ID')
        seen.add(row['id'])
        matches = list(WORD.finditer(by_article[part][article]['text']))
        i = row['wordOrdinal']
        if (i < 0 or i >= len(matches) or matches[i].group().casefold() != head or
                head not in {m.group().casefold() for m in WORD.finditer(token)} or token.casefold() == head):
            raise ValueError('REF_SOURCE_RELATION')
    paths = [Path(__file__).resolve(), FIXTURE / 'NOTICE.md', FIXTURE / 'contexts.jsonl', FIXTURE / 'receipt.json',
             SOURCE, AUDIT, *(helper_path(name) for name in HELPERS),
             ROOT / 'tools/ci/historical-data-v1/manifest.json',
             ROOT / 'tools/ci/historical-data-v1/files.tar.gz',
             ROOT / 'tools/ci/historical-data-v1/articles.jsonl',
             ROOT / 'tools/ci/historical-data-v1/NOTICE.md']
    return rows, {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}, receipt


def entries():
    rows, bindings, receipt = inputs()
    first = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
        keys=sorted({control.key_for(r, 'regression') for r in rows}),
        surfaceKeys=sorted({control.surface_key('ru', r['typed']) for r in rows}),
        articleKeys=sorted({control.article_key(r) for r in rows}),
        semantics='Full public source tokens behind unknown historical text fragments; not independent data.')
    second = dict(id=ENTRY + '-contexts', usage='historical-context-exclusion', rowCount=len(rows),
        bindings=bindings, keys={'context': sorted(lexical.keys_for(rows, 'context'))}, missingAxes=[],
        notes='Public source-token contexts; no inferred canonical compound family.')
    if len(first['surfaceKeys']) != receipt['counts']['distinctFullForms']:
        raise ValueError('REF_SOURCE_SURFACE_COUNT')
    return first, second


def check():
    first, second = entries()
    a, b = control.load(CONTROL), lexical.load_ledger(LEXICAL)
    if ([e for e in a['entries'] if e['id'] == ENTRY] != [first] or
            [e for e in b['entries'] if e['id'] == ENTRY + '-contexts'] != [second]):
        raise ValueError('REF_SOURCE_DRIFT')
    return first['rowCount']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.check:
        if args.output:
            raise ValueError('REF_SOURCE_SCOPE')
        print(json.dumps({'rows': check(), 'independentQualification': False}))
        return
    if args.output is None:
        raise ValueError('REF_SOURCE_SCOPE')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('REF_SOURCE_OUTPUT')
    old_a, old_b = CONTROL.read_bytes(), LEXICAL.read_bytes()
    first, second = entries()
    receipt = json.loads((FIXTURE / 'receipt.json').read_bytes())
    if receipt.get('controlLedgerSha256') != sha(old_a):
        raise ValueError('REF_SOURCE_CONTROL_DRIFT')
    controls, stored = json.loads(old_a), json.loads(old_b)
    control.validate(controls)
    logical = lexical.validate_ledger(copy.deepcopy(stored))
    if (any(e['id'] == ENTRY for e in controls['entries']) or
            any(e['id'] == ENTRY + '-contexts' for e in logical['entries'])):
        raise ValueError('REF_SOURCE_EXISTS')
    controls['entries'].append(first)
    stored['entries'].append(second)
    control.validate(controls)
    lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes() != old_a or LEXICAL.read_bytes() != old_b or entries() != (first, second):
        raise ValueError('REF_SOURCE_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', controls), ('holdout-ledger.json', stored)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': first['rowCount'], 'independentQualification': False}))


if __name__ == '__main__':
    main()
