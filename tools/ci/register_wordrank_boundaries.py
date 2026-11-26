"""Quarantine full source tokens behind disclosed historical fragments."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/typing_experiments'),str(ROOT/'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical
import historical_model_fixtures as fixtures

ENTRY='historical-wordrank-source-boundaries-v1'
FIXTURE=ROOT/'tools/typing_experiments/wordrank-boundary-origin-v1/contexts.jsonl'
RECEIPT=ROOT/'docs/acceptance/2026-10-29-q6-wordrank-boundaries.json'
SOURCE=ROOT/'tools/model/rune-text-0.2/source-lock.json'
AUDIT=ROOT/'tools/typing_experiments/audit_wordrank_source_boundaries.py'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
ARCHIVE='build/typing-word-ranking/data/all-rows.jsonl'


def sha(data):return hashlib.sha256(data).hexdigest()


def inputs():
    raw=FIXTURE.read_bytes();receipt=json.loads(RECEIPT.read_bytes());lock=SOURCE.read_bytes();_,archive=fixtures.verify()
    rows=[json.loads(line) for line in raw.splitlines()];original=[json.loads(line) for line in archive[ARCHIVE].splitlines()]
    counts=receipt.get('counts',{})
    if (not rows or receipt.get('scope')!='disclosed-historical-source-boundary-audit' or
        receipt.get('independentQualification') is not False or receipt.get('contextsSha256')!=sha(raw) or
        receipt.get('archiveRowsSha256')!=sha(archive[ARCHIVE]) or receipt.get('sourceLockSha256')!=sha(lock) or
        receipt.get('sourceSha256')!=json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
        receipt.get('analyzerSha256')!=sha(AUDIT.read_bytes()) or
        counts.get('hyphenRows',0)+counts.get('alphanumericRows',0)!=len(rows)):
        raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_BINDING')
    by_id={r['id']:r for r in original}
    if len(by_id)!=len(original) or len({r.get('id') for r in rows})!=len(rows):raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_IDS')
    for row in rows:
        parent=by_id.get(row.get('id'));token=row.get('typed');head=row.get('head');kind=row.get('boundaryKind')
        if (parent is None or row.get('article')!=parent.get('articleId') or row.get('prefix')!=parent.get('prefix','').strip() or
            head!=parent.get('expectedSpelling') or row.get('language')!='ru' or not isinstance(token,str) or
            row.get('expectedSpelling')!=token or not isinstance(head,str) or not token.startswith(head) or len(token)<=len(head) or
            kind not in ('hyphen','alphanumeric') or
            (kind=='hyphen' and token[len(head)] not in '-‐‑–') or
            (kind=='alphanumeric' and not token[len(head)].isalnum())):
            raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_SOURCE')
    paths=[Path(__file__).resolve(),FIXTURE,FIXTURE.with_name('NOTICE.md'),RECEIPT,SOURCE,AUDIT,
           ROOT/'tools/ci/historical-model-fixtures-v1/manifest.json',ROOT/'tools/ci/historical-model-fixtures-v1/files.tar.gz']
    return rows,{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def entries():
    rows,bindings=inputs()
    first=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(rows),bindings=bindings,
        keys=sorted({control.key_for(r,'regression') for r in rows}),
        surfaceKeys=sorted({control.surface_key('ru',r['typed']) for r in rows}),
        articleKeys=sorted({control.article_key(r) for r in rows}),
        semantics='Complete public source tokens for disclosed historical Cyrillic target fragments; not independent data.')
    second=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(rows),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(rows,'context'))},missingAxes=[],
        notes='Complete source-token contexts; no inferred canonical compound family.')
    return first,second


def check():
    first,second=entries();a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL)
    if [e for e in a['entries'] if e['id']==ENTRY]!=[first] or [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[second]:
        raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_DRIFT')
    return len(inputs()[0])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check:
        if a.output:raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_SCOPE')
        print(json.dumps({'rows':check(),'independentQualification':False}));return
    if a.output is None:raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_SCOPE')
    output=a.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_OUTPUT')
    old_a=CONTROL.read_bytes();old_b=LEXICAL.read_bytes();first,second=entries();bound=first['bindings']
    controls=json.loads(old_a);stored=json.loads(old_b);control.validate(controls);logical=lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id']==ENTRY for e in controls['entries']) or any(e['id']==ENTRY+'-contexts' for e in logical['entries']):raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_EXISTS')
    controls['entries'].append(first);stored['entries'].append(second);control.validate(controls);lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes()!=old_a or LEXICAL.read_bytes()!=old_b or inputs()[1]!=bound:raise ValueError('SOURCE_BOUNDARY_DISCLOSURE_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'rows':len(inputs()[0]),'independentQualification':False}))


if __name__=='__main__':main()
