"""Attribute boundary outcomes of disclosed authored deletion phrases."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

import authored_typo_replay as replay
import register_authored_typo_inputs as source


def summarize(cases, observations):
    if len(cases) != len(observations): raise ValueError('TYPO_DIAGNOSTIC_COUNT')
    reasons=Counter(); sources=Counter()
    for (name, phrase, target), row in zip(cases, observations, strict=True):
        if row.get('id') != name or row.get('typed') != phrase: raise ValueError('TYPO_DIAGNOSTIC_IDENTITY')
        stages=row.get('phraseStages')
        if not isinstance(stages,list) or not stages: raise ValueError('TYPO_DIAGNOSTIC_STAGES')
        final=stages[-1];events=final.get('boundaryDiagnostics')
        if not isinstance(events,list) or len(events)!=1: raise ValueError('TYPO_DIAGNOSTIC_EVENT')
        event=events[0];reason=event.get('reason'); origin=event.get('source')
        if not isinstance(reason,str) or not reason or not isinstance(origin,str) or not origin:
            raise ValueError('TYPO_DIAGNOSTIC_EVENT')
        applied=final.get('automaticEdit') is True
        if applied != (reason=='AUTO_REPLACE') or (applied and origin=='NONE') or (not applied and origin!='NONE'):
            raise ValueError('TYPO_DIAGNOSTIC_APPLICATION')
        if applied:
            if final['after'].rstrip().split(' ')[-1]!=target: raise ValueError('TYPO_DIAGNOSTIC_TARGET')
            sources[origin]+=1
        else: reasons[reason]+=1
    return dict(refusals=dict(sorted(reasons.items())),appliedSources=dict(sorted(sources.items())))


def run(java, output):
    previous=os.environ.get('JAVA_TOOL_OPTIONS')
    if previous and 'rune.replay.boundaryDiagnostics' in previous: raise ValueError('TYPO_DIAGNOSTIC_OPTION')
    os.environ['JAVA_TOOL_OPTIONS']=((previous or '')+' -Drune.replay.boundaryDiagnostics=true').strip()
    try: replay.run(java,output)
    finally:
        if previous is None:os.environ.pop('JAVA_TOOL_OPTIONS',None)
        else:os.environ['JAVA_TOOL_OPTIONS']=previous
    output=Path(output);raw=(output/'run-1.jsonl').read_bytes()
    result=summarize(source.cases(),[json.loads(line) for line in raw.splitlines()])
    receipt=dict(scope='disclosed-authored-deletion-boundary-diagnostics',independentQualification=False,
        result=result,resultSha256=hashlib.sha256(raw).hexdigest(),analyzerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'diagnostics.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--java',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.java,args.output)
