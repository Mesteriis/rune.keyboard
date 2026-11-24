"""Compare a disclosed packed-lexicon experiment with the real product baseline."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import historical_model_fixtures
import control_ledger as control
import holdout_ledger as lexical

ARCHIVE='build/typing-word-ranking/data/test-rows.jsonl'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def compare(rows,baseline,candidate):
    counts=Counter();disclosures=set();seen=set()
    for i,(row,old,new) in enumerate(zip(rows,baseline,candidate,strict=True)):
        n=row.get('errorCount');typed=row.get('typed');target=row.get('expectedSpelling');prefix=row.get('prefix');identity=row.get('id')
        if (type(n) is not int or n not in (0,1,2,3) or row.get('cohort')!=('correct' if n==0 else 'typo') or
            row.get('partition')!='test' or row.get('language')!='ru' or not isinstance(identity,str) or not identity or identity in seen or
            not isinstance(typed,str) or not re.fullmatch('[а-яё]+',typed,re.I) or
            not isinstance(target,str) or not re.fullmatch('[а-яё]+',target,re.I) or not isinstance(prefix,str) or
            old.get('id')!=identity or new.get('id')!=f'joint-replay-{i:08d}' or
            any(o.get('status')!='COMPLETE' or o.get('language')!='ru' or o.get('typed')!=typed or o.get('prefix')!=prefix for o in (old,new))):
            raise ValueError('PACKED_WORDRANK_IDENTITY')
        seen.add(identity);group='operations_'+str(n);counts[group+':rows']+=1
        old_before=old.get('beforeBoundary',{}).get('text');new_before=new.get('beforeBoundary',{}).get('text')
        old_after=old.get('afterBoundary',{}).get('text');new_after=new.get('afterBoundary',{}).get('text')
        if any(not isinstance(x,str) for x in (old_before,new_before,old_after,new_after)):
            raise ValueError('PACKED_WORDRANK_EDITOR')
        if old_before!=new_before or not old_before.endswith(typed):
            raise ValueError('PACKED_WORDRANK_INPUT_DIVERGED')
        context=old_before[:-len(typed)];expected=context+target+' '
        if not new_after.startswith(context) or not new_after.endswith(' '):raise ValueError('PACKED_WORDRANK_BOUNDARY')
        actual=new_after[len(context):-1]
        if not re.fullmatch('[а-яё]+',actual,re.I):raise ValueError('PACKED_WORDRANK_OUTPUT')
        article=row.get('articleId')
        if not isinstance(article,str) or not article.isascii() or not article.isdecimal():raise ValueError('PACKED_WORDRANK_ARTICLE')
        disclosures.add((article,context.strip(),actual))
        old_match=old_after==expected;new_match=new_after==expected
        counts[group+':changed']+=old_after!=new_after
        counts[group+':baseline_match']+=old_match;counts[group+':candidate_match']+=new_match
        counts[group+':lost_match']+=old_match and not new_match
        counts[group+':gained_match']+=new_match and not old_match
    if not seen:raise ValueError('PACKED_WORDRANK_EMPTY')
    return dict(sorted(counts.items())),[dict(language='ru',article=a,prefix=p,typed=t,expectedSpelling=t) for a,p,t in sorted(disclosures)]


def run(rows_path,base_path,candidate_path,base_receipt_path,candidate_receipt_path,output):
    paths=list(map(Path,(rows_path,base_path,candidate_path,base_receipt_path,candidate_receipt_path)))
    raw=[p.read_bytes() for p in paths];base=json.loads(raw[3]);candidate=json.loads(raw[4]);_,archive=historical_model_fixtures.verify()
    if (raw[0]!=archive[ARCHIVE] or base.get('status')!='COMPLETE' or base.get('mode')!='current-product' or base.get('exitCode')!=0 or
        base.get('rowsSha256')!=sha(raw[0]) or base.get('observationsSha256')!=sha(raw[1]) or
        candidate.get('purpose')!='PACKED_CANDIDATE_WITH_UNCHANGED_QUALIFICATION_NOT_QUALIFICATION' or
        candidate.get('independentQualification') is not False or candidate.get('exitCode')!=0 or
        candidate.get('rowsSha256')!=sha(raw[0]) or candidate.get('observationsSha256')!=sha(raw[2])):
        raise ValueError('PACKED_WORDRANK_BINDING')
    metrics,values=compare(*(map(json.loads,x.splitlines()) for x in raw[:3]))
    raw_l=(ROOT/'tools/typing_experiments/holdout-ledger.json').read_bytes()
    raw_c=(ROOT/'tools/typing_experiments/control-ledger.json').read_bytes();l=lexical.validate_ledger(json.loads(raw_l));c=control.validate(json.loads(raw_c))
    context={x for e in l['entries'] for x in e['keys'].get('context',[])};surfaces={x for e in c['entries'] for x in e.get('surfaceKeys',[])}
    missing=[v for v in values if not lexical.keys_for([v],'context')<=context or control.surface_key('ru',v['typed']) not in surfaces]
    if any(p.read_bytes()!=v for p,v in zip(paths,raw,strict=True)) or (ROOT/'tools/typing_experiments/control-ledger.json').read_bytes()!=raw_c or (ROOT/'tools/typing_experiments/holdout-ledger.json').read_bytes()!=raw_l:
        raise ValueError('PACKED_WORDRANK_DRIFT')
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('PACKED_WORDRANK_OUTPUT')
    output.mkdir(parents=True,mode=0o700)
    (output/'missing-disclosure.jsonl').write_text(''.join(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n' for v in missing))
    receipt={'scope':'disclosed-historical-packed-candidate-comparison','independentQualification':False,'policyChanged':False,
             'candidateQualificationValid':False,'metrics':metrics,'disclosedOutputs':len(values),'missingDisclosures':len(missing),
             'inputSha256':[sha(x) for x in raw],'lexicalLedgerSha256':sha(raw_l),'controlLedgerSha256':sha(raw_c),
             'missingDisclosureSha256':sha((output/'missing-disclosure.jsonl').read_bytes()),'analyzerSha256':sha(Path(__file__).read_bytes())}
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'metrics':metrics,'missingDisclosures':len(missing)},sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline','candidate','baseline-receipt','candidate-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.rows,a.baseline,a.candidate,a.baseline_receipt,a.candidate_receipt,a.output)
