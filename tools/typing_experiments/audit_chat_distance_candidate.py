"""Screen a distance veto on disclosed replay observations, without modifying policy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(value).hexdigest()


def analyze(rows, observations):
    counts=Counter(); kinds=Counter(); seen=set()
    for row, obs in zip(rows, observations, strict=True):
        identity=row.get('id'); cohort=row.get('cohort')
        if (not isinstance(identity,str) or identity in seen or obs.get('id')!=identity or
            row.get('language')!='ru' or obs.get('language')!='ru' or cohort not in ('correct','typo') or
            not isinstance(row.get('prefix'),str) or row['prefix']!=obs.get('prefix') or
            not isinstance(row.get('expectedSpelling'),str) or not row['expectedSpelling'] or
            row.get('typed')!=obs.get('typed') or obs.get('status')!='COMPLETE'):
            raise ValueError('DISTANCE_SCREEN_IDENTITY')
        seen.add(identity);counts[cohort+':rows']+=1
        edit=obs.get('autoEdit')
        if edit is None:continue
        counts[cohort+':edits']+=1
        selected=obs.get('automaticAdmissionCandidate')
        candidates=edit['correctionGeneration']['alternatives']
        matches=[item for item in candidates if item.get('text')==selected]
        if not matches:
            counts[cohort+':unattributed']+=1
            continue
        if len(matches)!=1:raise ValueError('DISTANCE_SCREEN_DUPLICATE_CANDIDATE')
        candidate=matches[0];distance=candidate.get('unitDistance')
        if (type(distance) is not int or distance<0 or not isinstance(selected,str) or
            edit.get('applied','').strip()!=selected):
            raise ValueError('DISTANCE_SCREEN_CANDIDATE')
        counts[cohort+':attributed']+=1
        if distance<=1:continue
        outcome='expected' if selected==row.get('expectedSpelling') else 'other'
        counts[cohort+':distance_over_one:'+outcome]+=1
        kinds[cohort+':'+str(row.get('edit_kind'))+':'+outcome]+=1
    if not seen:raise ValueError('DISTANCE_SCREEN_EMPTY')
    return {'counts':dict(sorted(counts.items())),'affectedEditKinds':dict(sorted(kinds.items()))}


def run(rows_path, observations_path, replay_receipt_path, output):
    paths=[Path(rows_path),Path(observations_path),Path(replay_receipt_path)]
    raw=[p.read_bytes() for p in paths];receipt=json.loads(raw[2])
    if (receipt.get('mode')!='current-product' or receipt.get('status')!='COMPLETE' or
        receipt.get('exitCode')!=0 or receipt.get('rowsSha256')!=digest(raw[0]) or
        receipt.get('observationsSha256')!=digest(raw[1])):
        raise ValueError('DISTANCE_SCREEN_REPLAY_BINDING')
    data=analyze((json.loads(x) for x in raw[0].splitlines()),(json.loads(x) for x in raw[1].splitlines()))
    if any(p.read_bytes()!=v for p,v in zip(paths,raw,strict=True)):raise ValueError('DISTANCE_SCREEN_INPUT_DRIFT')
    result={'scope':'posthoc-disclosed-single-token-distance-screen','independentQualification':False,
            'policyChanged':False,'sourceLabelsVerified':False,'metrics':data,
            'rowsSha256':digest(raw[0]),'observationsSha256':digest(raw[1]),
            'replayReceiptSha256':digest(raw[2]),'analyzerSha256':digest(Path(__file__).read_bytes())}
    output=Path(output)
    if output.exists():raise ValueError('DISTANCE_SCREEN_OUTPUT_EXISTS')
    output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(data,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows',type=Path,required=True);p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--replay-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.rows,a.observations,a.replay_receipt,a.output)
