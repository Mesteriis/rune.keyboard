"""Aggregate non-text EWT replay diagnostics after context registration."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

import ewt_product_replay as replay
import register_ewt_product_candidates as candidates
import register_ewt_product_contexts as contexts

ROOT=Path(__file__).resolve().parents[2]
SOURCES={'NONE','CANONICAL_CASE'}
REASONS={'ORIGINAL_VALID','SERVICE_REFUSED','NOT_QUALIFIED','LOCAL_SEARCH_EMPTY','INELIGIBLE','NO_RANKING','WINNER_AMBIGUOUS','AUTO_REPLACE'}


def diagnostic_counts(labels,observed):
    if len(labels)!=len(observed):raise ValueError('EWT_REPORT_ALIGNMENT')
    counts={}
    for label,row in zip(labels,observed,strict=True):
        kind=label.get('kind');events=row.get('boundaryDiagnostics')
        if kind not in ('annotated','unannotated-unknown') or not isinstance(events,list) or len(events)!=1:
            raise ValueError('EWT_REPORT_DIAGNOSTIC')
        event=events[0]
        if not isinstance(event,dict) or event.get('source') not in SOURCES or event.get('reason') not in REASONS:
            raise ValueError('EWT_REPORT_DIAGNOSTIC')
        c=counts.setdefault(kind,Counter());c[event['source']+':'+event['reason']]+=1
    return {kind:dict(sorted(value.items())) for kind,value in sorted(counts.items())}


def run(data,run):
    ledger_raw=candidates.LEDGER.read_bytes();ledger=candidates.control.validate(json.loads(ledger_raw))
    for module in (contexts,candidates):
        expected=module.entry()
        if [e for e in ledger['entries'] if e['id']==module.ENTRY]!=[expected]:raise ValueError('EWT_REPORT_EXCLUSIONS')
    summary=replay.summarize(data,run)
    fixture=json.loads(candidates.FIXTURE.read_bytes())
    if fixture.get('projectionSha256')!=summary['projectionSha256'] or fixture.get('rows')!=summary['rows']:
        raise ValueError('EWT_REPORT_PROJECTION_DRIFT')
    label_path=data/'labels.jsonl';projection_path=run/'projection.jsonl';manifest_path=data/'manifest.json'
    label_raw=label_path.read_bytes();projection_raw=projection_path.read_bytes();manifest_raw=manifest_path.read_bytes()
    manifest=json.loads(manifest_raw)
    if (replay.model.sha(label_raw)!=manifest.get('labelSha256') or
            replay.model.sha(projection_raw)!=summary['projectionSha256'] or
            replay.model.sha(manifest_raw)!=summary['preparationManifestSha256']):raise ValueError('EWT_REPORT_INPUT_DRIFT')
    labels=[json.loads(x) for x in label_raw.splitlines()]
    observed=[json.loads(x) for x in projection_raw.splitlines()]
    counts=diagnostic_counts(labels,observed)
    if (candidates.LEDGER.read_bytes()!=ledger_raw or label_path.read_bytes()!=label_raw or
            projection_path.read_bytes()!=projection_raw or manifest_path.read_bytes()!=manifest_raw):
        raise ValueError('EWT_REPORT_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-current-product-report-not-qualification',summary=summary,
        boundaryDiagnostics=counts,caseOnlyChanges=fixture['caseOnlyChanges'],otherChanges=fixture['otherChanges'],
        inputContexts=len(contexts.entry()['keys']),candidateContexts=len(candidates.entry()['keys']),
        registrySha256=replay.model.sha(ledger_raw),analyzerSha256=replay.model.sha(Path(__file__).read_bytes()),
        labelsQualified=False,independentQualification=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data','replay','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();os.umask(0o077);out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('EWT_REPORT_OUTPUT')
    result=run(args.data,args.replay)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result['boundaryDiagnostics'],sort_keys=True))


if __name__=='__main__':main()
