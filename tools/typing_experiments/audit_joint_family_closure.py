"""Prove dictionary-family coverage of each frozen joint row, including controls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for,load_ledger
from import_joint_history import BASE,MANIFESTS
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]


def audit(root,ledger,lexicon,historical_counts=None):
    root=Path(root);entries={e['id']:e for e in ledger['entries']};counts={};bindings={};all_unresolved=[]
    for corpus,manifest_digest in MANIFESTS.items():
        manifest_path=f'{BASE}/{corpus}/manifest.json'
        if sha(root/manifest_path)!=manifest_digest:raise ValueError('JOINT_FAMILY_MANIFEST')
        manifest=json.loads((root/manifest_path).read_text());bindings[manifest_path]=manifest_digest
        parts=('train','calibration','holdout') if corpus=='corpus' else ('calibration','holdout')
        if set(manifest['files'])!={part+'.jsonl' for part in parts}:raise ValueError('JOINT_FAMILY_SCOPE')
        for part in parts:
            parent=entries.get(f'public-joint-history-{corpus}-{part}')
            family=entries.get(f'public-joint-history-{corpus}-{part}-families')
            window=entries.get(f'public-joint-source-windows-{corpus}-{part}')
            path=f'{BASE}/{corpus}/{part}.jsonl';digest=sha(root/path)
            if not parent or not family or not window or parent['bindings'].get(path)!=digest or window['bindings'].get(path)!=digest or manifest['files'][part+'.jsonl']!=digest:
                raise ValueError('JOINT_FAMILY_BINDING')
            if parent['bindings'].get(manifest_path)!=manifest_digest or window['bindings'].get(manifest_path)!=manifest_digest:
                raise ValueError('JOINT_FAMILY_BINDING')
            rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
            if len(rows)!=parent.get('rowCount') or len(rows)!=manifest['counts'][part]['rows'] or len({r['id'] for r in rows})!=len(rows):raise ValueError('JOINT_FAMILY_COUNT')
            family_keys=set();unresolved=[];protected_ids=set()
            for row in rows:
                word=row.get('word');cohort=row.get('cohort')
                if not isinstance(word,str) or not word or row.get('split')!=part or row.get('language')!='ru':raise ValueError('JOINT_FAMILY_ROW')
                if cohort=='protected':
                    if row.get('typed')!='@'+word or row.get('expectedSpelling')!='@'+word or row.get('noAuto') is not True or row.get('group')!='protected':raise ValueError('JOINT_FAMILY_PROTECTED')
                    protected_ids.add(row['id'])
                elif cohort=='correct':
                    if row.get('typed')!=word or row.get('expectedSpelling')!=word or row.get('noAuto') is not True:raise ValueError('JOINT_FAMILY_CORRECT')
                elif cohort=='typo':
                    if row.get('expectedSpelling')!=word or row.get('noAuto') is not False:raise ValueError('JOINT_FAMILY_TYPO')
                else:raise ValueError('JOINT_FAMILY_COHORT')
                analyses=sorted({a.lemma for a in lexicon.analyses(word)})
                if not analyses:unresolved.append(row['id']);continue
                family_keys.update(keys_for([dict(families=analyses)],'family'))
            declared=set(family['keys'].get('family',[]))
            missing=family_keys-declared
            if unresolved or missing:all_unresolved.append((corpus,part,len(unresolved),len(missing)))
            if historical_counts is not None and set(historical_counts[corpus+'/'+part]['unresolvedRows'])!=protected_ids:
                raise ValueError('JOINT_FAMILY_HISTORICAL_MISMATCH')
            counts[corpus+'/'+part]={'rows':len(rows),'protectedRows':len(protected_ids),'unresolvedRows':len(unresolved),
                'familyKeys':len(family_keys),'missingFamilyKeys':len(missing),'extraExistingKeys':len(declared-family_keys)}
            bindings[path]=digest
    for path,digest in bindings.items():
        if sha(root/path)!=digest:raise ValueError('JOINT_FAMILY_INPUT_DRIFT')
    if all_unresolved:raise ValueError('JOINT_FAMILY_INCOMPLETE')
    return dict(purpose='JOINT_FAMILY_COVERAGE_NOT_QUALIFICATION',counts=counts,inputBindings=bindings,
        dictionary=lexicon.receipt(),modelCalls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ledger',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    raw=args.ledger.read_bytes();ledger=load_ledger(args.ledger)
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    history=ROOT/'docs/acceptance/2026-10-27-joint-history-exclusions-evidence.json'
    history_raw=history.read_bytes();history_counts=json.loads(history_raw)['receipt']['counts']
    receipt=audit(ROOT,ledger,PymorphyLexicon(cache_size=16384),history_counts)
    if args.ledger.read_bytes()!=raw:raise ValueError('JOINT_FAMILY_LEDGER_DRIFT')
    if history.read_bytes()!=history_raw:raise ValueError('JOINT_FAMILY_HISTORY_DRIFT')
    receipt['ledgerSha256']=hashlib.sha256(raw).hexdigest()
    receipt['historicalEvidenceSha256']=hashlib.sha256(history_raw).hexdigest()
    receipt['codeBindings']={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'tools/morphology/ranker.py',ROOT/'tools/typing_experiments/holdout_ledger.py')}
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))

if __name__=='__main__':main()
