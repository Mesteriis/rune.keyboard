"""Analyze a disclosed historical multi-operation set and a bound product replay."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import historical_model_fixtures
import audit_chat_distance_candidate as base

ARCHIVE_PATH='build/typing-word-ranking/data/test-rows.jsonl'


def analyze(rows, observations):
    counts=Counter();seen=set()
    for row, obs in zip(rows, observations, strict=True):
        rid=row.get('id');errors=row.get('errorCount');cohort=row.get('cohort')
        if (not isinstance(rid,str) or not rid or rid in seen or obs.get('id')!=rid or
            row.get('language')!='ru' or obs.get('language')!='ru' or row.get('partition')!='test' or
            type(errors) is not int or errors not in (0,1,2,3) or
            cohort!=('correct' if errors==0 else 'typo') or
            not isinstance(row.get('prefix'),str) or row['prefix']!=obs.get('prefix') or
            not isinstance(row.get('expectedSpelling'),str) or not row['expectedSpelling'] or
            not isinstance(row.get('typed'),str) or not row['typed'] or
            row['typed']!=obs.get('typed') or obs.get('status')!='COMPLETE'):
            raise ValueError('WORD_DISTANCE_IDENTITY')
        seen.add(rid);group='operations_'+str(errors);counts[group+':rows']+=1
        expected_input=(row['prefix']+' ' if row['prefix'] else '')+row['typed']
        before=obs.get('beforeBoundary',{}).get('text')
        if (not isinstance(before,str) or not before.endswith(row['typed']) or type(obs.get('inputChangedByTyping')) is not bool or
            obs.get('inputExpected')!=expected_input or obs.get('inputChangedByTyping')!=(before!=expected_input)):
            raise ValueError('WORD_DISTANCE_EDITOR_INPUT')
        if before!=expected_input:counts[group+':input_changed_by_typing']+=1
        expected=before[:-len(row['typed'])]+row['expectedSpelling']+' '
        after=obs.get('afterBoundary',{}).get('text')
        if not isinstance(after,str):raise ValueError('WORD_DISTANCE_EDITOR_OUTPUT')
        edit=obs.get('autoEdit')
        if edit is None:continue
        counts[group+':automatic']+=1
        exact=after==expected
        if exact:counts[group+':automatic_expected']+=1
        if obs.get('restoredBeforeBoundaryExactly') is not True:raise ValueError('WORD_DISTANCE_UNDO')
        selected=obs.get('automaticAdmissionCandidate')
        matches=[v for v in edit['correctionGeneration']['alternatives'] if v.get('text')==selected]
        if not matches:
            counts[group+':unattributed']+=1
            continue
        if (len(matches)!=1 or not isinstance(selected,str) or not selected or not isinstance(edit.get('applied'),str) or
            type(matches[0].get('unitDistance')) is not int or matches[0]['unitDistance']<0 or
            not edit.get('applied','').endswith(selected+' ')):
            raise ValueError('WORD_DISTANCE_CANDIDATE')
        if matches[0]['unitDistance']>1:
            counts[group+':distance_over_one']+=1
            if exact:counts[group+':distance_over_one_expected']+=1
    if not seen:raise ValueError('WORD_DISTANCE_EMPTY')
    return dict(sorted(counts.items()))


def run(rows_path, observation_path, receipt_path, output):
    paths=list(map(Path,(rows_path,observation_path,receipt_path)))
    raw=[p.read_bytes() for p in paths];r=json.loads(raw[2]);_,archive=historical_model_fixtures.verify()
    if raw[0]!=archive[ARCHIVE_PATH]:raise ValueError('WORD_DISTANCE_ARCHIVE')
    if (r.get('mode')!='current-product' or r.get('status')!='COMPLETE' or r.get('exitCode')!=0 or
        r.get('rowsSha256')!=base.digest(raw[0]) or r.get('observationsSha256')!=base.digest(raw[1])):
        raise ValueError('WORD_DISTANCE_REPLAY_BINDING')
    result=analyze((json.loads(x) for x in raw[0].splitlines()),(json.loads(x) for x in raw[1].splitlines()))
    if any(p.read_bytes()!=v for p,v in zip(paths,raw,strict=True)):raise ValueError('WORD_DISTANCE_INPUT_DRIFT')
    receipt={'scope':'disclosed-historical-multi-operation-recorded-choice-screen',
             'independentQualification':False,'policyChanged':False,'sourceLabelsVerified':False,
             'metrics':result,'rowsSha256':base.digest(raw[0]),'observationsSha256':base.digest(raw[1]),
             'replayReceiptSha256':base.digest(raw[2]),'analyzerSha256':base.digest(Path(__file__).read_bytes())}
    output=Path(output)
    if output.exists():raise ValueError('WORD_DISTANCE_OUTPUT_EXISTS')
    output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','observations','replay-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.rows,a.observations,a.replay_receipt,a.output)
