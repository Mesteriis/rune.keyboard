#!/usr/bin/env python3
"""Verify the fixed disclosed corpus/baseline, then run the real two-pass parity gate."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

import generate_product_replay_v1 as corpus
import register_product_replay_v1 as disclosure
import register_historical_replay as history
ROOT=corpus.ROOT
PIPELINE=ROOT/'tools/eval/smart-typing-0.3/pipeline'
sys.path.insert(0,str(PIPELINE))
import replay_projection as projection


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate():
    for name,data in corpus.build().items():
        if (corpus.DATA/name).read_bytes()!=data:raise ValueError('CI_CORPUS_DRIFT:'+name)
    disclosure.check()
    data=corpus.DATA;meta=json.loads((data/'baseline-manifest.json').read_text())
    if (meta.get('schemaVersion')!=1 or meta.get('file')!='baseline.jsonl.gz'
            or meta.get('rows')!=2160 or meta.get('languages')!={'en':720,'ru':720,'es':720}
            or meta.get('modelCalls')!=0 or meta.get('opaqueControllerIds') is not True
            or meta.get('captureTwoPassDeterministic') is not True
            or meta.get('excludedTopLevelFields')!=sorted(projection.TIMING_FIELDS)
            or meta.get('inputManifestSha256')!=sha(data/'manifest.json')
            or meta.get('inputRowsSha256')!=sha(data/'inputs.jsonl')
            or meta.get('fileSha256')!=sha(data/'baseline.jsonl.gz')):
        raise ValueError('CI_BASELINE_MANIFEST')
    acceptance=meta.get('acceptance')
    if (not isinstance(acceptance,str) or not acceptance.startswith('docs/acceptance/')
            or not acceptance.endswith('.md') or '..' in Path(acceptance).parts
            or not (ROOT/acceptance).is_file()
            or not isinstance(meta.get('capturedSourceCommit'),str)
            or re.fullmatch('[0-9a-f]{40}',meta['capturedSourceCommit']) is None
            or not isinstance(meta.get('sourceBindings'),dict) or not meta['sourceBindings']):
        raise ValueError('CI_BASELINE_ACCEPTANCE')
    rows=projection.read_projection(data/'baseline.jsonl.gz')
    if (len(rows)!=meta['rows'] or dict(Counter(row['language'] for row in rows))!=meta['languages']
            or hashlib.sha256(projection.projection_bytes(rows)).hexdigest()!=meta['projectionSha256']):
        raise ValueError('CI_BASELINE_PROJECTION')
    # Source bindings describe the historical capture. Candidate sources may change;
    # their behavior must still pass the actual comparator, never a hash-only waiver.
    return meta


def validate_history():
    history.check()
    data=ROOT/'tools/ci/product-replay-history-v1'
    meta=json.loads((data/'baseline-manifest.json').read_text())
    expected=['tools/eval/smart-typing-0.3/'+name for name in history.FILES]
    if (meta.get('schemaVersion')!=1 or meta.get('file')!='baseline.jsonl.gz'
            or meta.get('inputPaths')!=expected or set(meta.get('inputBindings',{}))!=set(expected)
            or any(sha(ROOT/name)!=meta['inputBindings'][name] for name in expected)
            or meta.get('sourceManifestSha256')!=sha(history.CORPUS/'manifest.json')
            or meta.get('fileSha256')!=sha(data/'baseline.jsonl.gz')
            or meta.get('rows')!=12000 or meta.get('languages')!={'en':4000,'ru':4000,'es':4000}
            or meta.get('excludedTopLevelFields')!=sorted(projection.TIMING_FIELDS)
            or meta.get('modelCalls')!=0 or meta.get('opaqueControllerIds') is not True):
        raise ValueError('CI_HISTORICAL_BASELINE')
    rows=projection.read_projection(data/'baseline.jsonl.gz')
    if (len(rows)!=12000 or dict(Counter(row['language'] for row in rows))!=meta['languages']
            or hashlib.sha256(projection.projection_bytes(rows)).hexdigest()!=meta['projectionSha256']):
        raise ValueError('CI_HISTORICAL_PROJECTION')
    return meta


def run(java,output,historical=False):
    validator=validate_history if historical else validate
    meta=validator()
    data=ROOT/'tools/ci/product-replay-history-v1' if historical else corpus.DATA
    baseline_files=[data/name for name in ('baseline-manifest.json','baseline.jsonl.gz')]
    baseline_files+= [ROOT/path for path in meta['inputPaths']] if historical else [data/name for name in ('inputs.jsonl','manifest.json')]
    before={str(p):sha(p) for p in baseline_files}
    command=[sys.executable,str(PIPELINE/'current_product_replay.py'),'--java',str(java),
        '--baseline',str(data/'baseline.jsonl.gz'),'--output',str(output)]
    for path in ([ROOT/name for name in meta['inputPaths']] if historical else [data/'inputs.jsonl']):
        command+=['--rows',str(path)]
    result=subprocess.run(command,cwd=ROOT)
    if result.returncode:return result.returncode
    receipt=json.loads((output/'receipt.json').read_text())
    if (receipt.get('status')!='COMPLETE' or receipt.get('deterministic') is not True
            or receipt.get('baselineMatches') is not True or receipt.get('rows')!=meta['rows']
            or receipt.get('projectionSha256')!=meta['projectionSha256']):
        raise ValueError('CI_REPLAY_NOT_PROVEN')
    validator()
    if before!={str(p):sha(p) for p in baseline_files}:raise ValueError('CI_BASELINE_CHANGED_DURING_RUN')
    print(json.dumps({'passed':True,'rows':meta['rows'],'projectionSha256':meta['projectionSha256']},sort_keys=True))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    result=run(args.java,output)
    return result if result else run(args.java,output.with_name(output.name+'-historical'),historical=True)


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:print(str(error),file=sys.stderr);sys.exit(1)
