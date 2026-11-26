"""Bounded upper estimate of hidden target candidates from a product replay."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def measure(rows,observations,identities):
    totals={lang:Counter() for lang in ('ru','en','es')}; count=0; seen=set()
    for row,obs,identity in zip(rows,observations,identities,strict=True):
        if (identity['index']!=count or identity['id']!=obs['id'] or identity['sourceId']!=row['id'] or
            row['id'] in seen or obs['status']!='COMPLETE' or
            any(row[k]!=obs[k] for k in ('language','prefix','typed','split'))):raise ValueError('STRIP_REPLAY_ROW_IDENTITY')
        seen.add(row['id']);count+=1
        if row['cohort']!='typo' or row.get('ambiguous'):continue
        index=row['expectedCandidate']; candidates=row['candidates']
        if type(index)!=int or not 0<=index<len(candidates):raise ValueError('STRIP_LABEL')
        target=candidates[index].strip().casefold()
        if not target:raise ValueError('STRIP_LABEL')
        lang=row['language'];out=totals[lang];out['typoRows']+=1
        view=obs['candidateView']
        if not isinstance(view,dict) or not isinstance(view.get('candidates'),list):raise ValueError('STRIP_VIEW')
        visible={c['text'].casefold() for c in view['candidates'] if c['role']=='CORRECTION'}
        if target in visible:out['targetVisible']+=1
        automatic=obs['actualRequestGeneration'];manual=obs['manualSearchGeneration']
        if automatic is None:out['noCandidateRequest']+=1;continue
        if obs.get('actualOriginal')!=row['typed']:raise ValueError('STRIP_REQUEST_TOKEN_MISMATCH')
        def texts(value):
            if value is None:return []
            return [c['text'].casefold() for c in value['alternatives']]
        # The controller validates and deduplicates by canonical key, not text;
        # retain the complete union to avoid excluding a possible displayed item.
        baseline=texts(automatic);expanded=set(baseline+texts(manual))
        if target not in visible and target in baseline:out['hiddenBaselinePoolUpperBound']+=1
        if target not in visible and target in expanded:out['hiddenExpandedPoolUpperBound']+=1
        if target not in visible and target in expanded and target not in baseline:out['manualOnlyPoolUpperBound']+=1
    if not count:raise ValueError('STRIP_REPLAY_EMPTY')
    return dict(rows=count,language={lang:dict(value) for lang,value in totals.items()})


def run(rows,observations,identities,receipt):
    paths=[Path(p) for p in (rows,observations,identities,receipt)]+[Path(__file__)]
    before=[digest(p) for p in paths]
    meta=json.loads(paths[3].read_text())
    if (meta.get('status')!='COMPLETE' or meta.get('mode')!='current-product' or meta.get('deterministic') is not True
            or meta.get('first',{}).get('observationsSha256')!=before[1]
            or meta.get('hostOnlyIdentitiesSha256')!=before[2]):raise ValueError('STRIP_RECEIPT_IDENTITY')
    row_digest=next((v for k,v in meta['files'].items() if k.endswith('/rows.jsonl') and v==before[0]),None)
    if row_digest!=before[0]:raise ValueError('STRIP_CORPUS_IDENTITY')
    def read(path):
        with path.open(encoding='utf-8') as f:
            for line in f:yield json.loads(line)
    counts=measure(*(read(p) for p in paths[:3]))
    if counts['rows']!=meta['rows']:raise ValueError('STRIP_REPLAY_COUNT')
    if before!=[digest(p) for p in paths]:raise ValueError('STRIP_INPUT_DRIFT')
    return dict(schema=1,purpose='U14_HIDDEN_POOL_UPPER_BOUND_NOT_UI_ACCEPTANCE',counts=counts,
                bindings={'rows':before[0],'observations':before[1],'identities':before[2],
                          'receipt':before[3],'audit':before[4]},
                limitations=['Raw generated pools are not validated or ordered as a hypothetical expanded strip.',
                             'The replay passes manual generation to the controller; it is not an expansion-off comparison.',
                             'Counts are synthetic, case-insensitive, and do not establish user benefit or device acceptance.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','observations','identities','receipt','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('STRIP_OUTPUT_EXISTS')
    report=run(args.rows,args.observations,args.identities,args.receipt)
    args.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report['counts']))


if __name__=='__main__':main()
