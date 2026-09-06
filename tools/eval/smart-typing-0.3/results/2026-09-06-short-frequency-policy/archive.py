#!/usr/bin/env python3
"""Archive verified frozen policy evidence; --verify checks stored and decoded bytes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPO = Path('/Users/avm/projects/Personal/rune-keyboard')
RUN = REPO/'build/smart-typing-0.3/short-policy-evaluation-20260906'
DEST = REPO/'tools/eval/smart-typing-0.3/results/2026-09-06-short-frequency-policy'
PIPELINE = REPO/'tools/eval/smart-typing-0.3/pipeline'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def verify(root):
    manifest=json.loads((root/'manifest.json').read_text())
    assert set(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()) == set(manifest['entries']) | {'manifest.json'}
    for name, entry in manifest['entries'].items():
        path=root/name
        assert path.stat().st_size == entry['archivedBytes'] and sha(path)==entry['archivedSha256'],name
        opener=gzip.open if entry['encoding']=='gzip-mtime-zero' else open
        with opener(path,'rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==entry['decodedSha256'],name
        assert entry['decodedSha256']==entry['sourceSha256'],name
        if entry['encoding']=='gzip-mtime-zero':
            with path.open('rb') as stream:
                header=stream.read(10)
            assert header[3]==0 and header[4:8]==b'\0'*4,name
    return {'verifiedEntries':len(manifest['entries']), 'archiveBytes':sum(e['archivedBytes'] for e in manifest['entries'].values())+(root/'manifest.json').stat().st_size,
            'decodedBytes':sum(e['decodedBytes'] for e in manifest['entries'].values()),'manifestSha256':sha(root/'manifest.json')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',type=Path);args=parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify),indent=2));return
    sys.path.insert(0,str(PIPELINE))
    import short_policy_evaluation as policy
    b=policy.base
    export=b.load_export(RUN)
    freeze=b.admit_policy_freeze(RUN,export)
    b.admit_score_stage(RUN,'holdout',export,b.sha256(RUN/'policy-freeze.json'))
    report=json.loads((RUN/'holdout-report.json').read_text())
    assert report['policyFreezeSha256']==b.sha256(RUN/'policy-freeze.json')
    for name,expected in report['artifacts'].items():assert sha(RUN/name)==expected
    for split in ('cal','hold'):
        summary=json.loads((RUN/f'{split}-review-01/summary.json').read_text())
        for key,expected in summary['inputAndToolSha256'].items():assert sha(b.resolve_key(key))==expected,key
    sources=[Path(p) for p in export['commands']['compile'] if p.endswith('.kt')]
    assert len(sources)==41 and sources.count(policy.VARIANT)==1 and policy.ORIGINAL not in sources
    assert not DEST.exists()
    DEST.mkdir(parents=True)
    entries={};excluded={};pending={}
    def add(path, name=None):
        path=path.resolve(strict=True)
        name=name or 'bound/'+b.path_key(path)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert name not in pending or pending[name]==path
        pending[name]=path
    for path in RUN.rglob('*'):
        if not path.is_file():continue
        if path.suffix in ('.jar','.gguf','.apk'):
            excluded[b.path_key(path)]={'sha256':sha(path),'bytes':path.stat().st_size,'reason':'excluded executable/model artifact'}
        else:add(path,'run/'+path.relative_to(RUN).as_posix())
    for key,expected in export['bindings']['files'].items():
        path=b.resolve_key(key)
        assert sha(path)==expected,key
        if not path.is_relative_to(REPO) or path==b.MODEL or path==b.RUNNER or path.suffix in ('.jar','.gguf','.apk','.dylib'):
            excluded[key]={'sha256':expected,'bytes':path.stat().st_size,'reason':'external runtime/toolchain or excluded model/executable'}
        else:add(path)
    for name in ('test_short_policy_evaluation.py','test_final_product_replay.py','original_applicability.py','test_original_applicability.py'):
        add(PIPELINE/name,'tools/'+name)
    reviews=REPO/'.superpowers/sdd/2026-09-02-smart-typing-progress'
    for name in ('task-short-frequency-probe-report.md','task-short-frequency-policy-review.md','task-short-policy-evaluation-report.md','task-short-policy-calibration-review.md','task-short-policy-holdout-review.md'):
        add(reviews/name,'reviews/'+name)
    baseline=REPO/'build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/row-evidence.jsonl'
    assert sha(baseline)=='6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75'
    add(baseline,'baseline/row-evidence.jsonl')
    add(Path(__file__),'archive.py')
    add(Path(__file__).parent/'README.md','README.md')
    for name,path in sorted(pending.items()):
        source_sha=sha(path);length=path.stat().st_size
        compress=length>=32768 and path.suffix in ('.json','.jsonl','.tsv','.log','.md','.txt')
        target=DEST/(name+'.gz' if compress else name)
        target.parent.mkdir(parents=True,exist_ok=True)
        with path.open('rb') as source,target.open('xb') as output:
            if compress:
                with gzip.GzipFile(filename='',fileobj=output,mode='wb',compresslevel=9,mtime=0) as zipped:
                    shutil.copyfileobj(source,zipped)
            else:shutil.copyfileobj(source,output)
        assert sha(path)==source_sha
        entries[target.relative_to(DEST).as_posix()]={'sourcePath':str(path),'sourceSha256':source_sha,
            'encoding':'gzip-mtime-zero' if compress else 'identity','decodedSha256':source_sha,'decodedBytes':length,
            'archivedSha256':sha(target),'archivedBytes':target.stat().st_size}
    b.verify_bound_files(export)
    manifest={'schemaVersion':1,'scope':'immutable revealed-data changed-policy evidence archive',
        'productionPromotionApproved':False,'coefficientsChanged':False,
        'sourceFreezeSha256':sha(RUN/'source-freeze.json'),'policyFreezeSha256':sha(RUN/'policy-freeze.json'),
        'compiledSourceCount':41,'compiledSources':[b.path_key(p) for p in sources],
        'entries':entries,'excludedBoundArtifacts':excluded}
    (DEST/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps(verify(DEST),indent=2))


if __name__=='__main__':main()
