"""Bounded real word-ranking comparison of disclosed rows; never training acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import refinement_evaluation_smoke as refinement
import captured_source_identity


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def jsonl(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))


def validate_capture(fixture):
    import historical_model_fixtures as originals
    _,payloads=originals.read_bundle()
    prefix='build/typing-word-ranking/data/'
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    if fixture.get('containsPersonalMessages') is not False or fixture.get('sourceManifestSha256')!=digest(payloads[prefix+'manifest.json']):
        raise ValueError('WORD_CAPTURE_ORIGIN')
    manifest=json.loads(payloads[prefix+'manifest.json'])
    rows={r['id']:r for r in (json.loads(x) for x in payloads[prefix+'test-rows.jsonl'].decode().splitlines())}
    if (fixture.get('sourceSha256')!=manifest['sourceSha256'] or len(fixture['rows'])!=4 or
            {r['errorCount'] for r in fixture['rows']}!={0,1,2,3} or
            any(row!=rows.get(row['id']) for row in fixture['rows'])):
        raise ValueError('WORD_CAPTURE_ORIGIN')
    texts=[json.loads(x) for x in payloads[prefix+'test-text.jsonl'].decode().splitlines()]
    if not any(fixture['text']==(t|{'text':t['text'][:100]}) for t in texts):
        raise ValueError('WORD_CAPTURE_ORIGIN')


def copy_regression(previous,destination):
    for old,new in [('data','data'),('verified-observations','observations'),('candidates-v2','candidates-v2')]:
        shutil.copytree(previous/old,destination/new,dirs_exist_ok=True)
    receipt_path=destination/'candidates-v2/receipt.json';receipt=json.loads(receipt_path.read_text())
    receipt['files']={str(destination/Path(p).relative_to(previous)):sha(destination/Path(p).relative_to(previous))
                      for p in receipt['files']}
    write(receipt_path,receipt)
    path=destination/'observations/manifest.json';meta=json.loads(path.read_text())
    meta.update(dataManifest=str(destination/'data/manifest.json'),dataManifestSha256=sha(destination/'data/manifest.json'),
                exportReceipt=str(receipt_path),exportReceiptSha256=sha(receipt_path));write(path,meta)


def compare_fixture(repo,project,legacy,previous,output):
    import evaluate_word_ranking as evaluation
    import word_evaluation_receipt as binding
    import word_ranking as training
    import rank_refinement as rank
    import neural_refinement as neural
    fixture_path=repo/'tools/ci/fixtures/word-ranking-bounded-capture.json'
    fixture=json.loads(fixture_path.read_text());validate_capture(fixture)
    source=project/'build/word-ranking-fixture';source.mkdir()
    # Narrow the old dev set using its actual retained rows and observations.
    path=previous/'verified-observations/dev.jsonl'
    observed=[json.loads(x) for x in path.read_text().splitlines()][:4]
    jsonl(path,observed);jsonl(previous/'data/dev-rows.jsonl',[o['row'] for o in observed])
    meta_path=previous/'data/manifest.json';meta=json.loads(meta_path.read_text())
    meta['files']['dev-rows.jsonl']=sha(previous/'data/dev-rows.jsonl');write(meta_path,meta)
    path=previous/'verified-observations/manifest.json';meta=json.loads(path.read_text())
    meta.update(dataManifestSha256=sha(meta_path));meta['partitions']['dev']=sha(previous/'verified-observations/dev.jsonl');write(path,meta)
    copy_regression(previous,project/'build/typing-extra-epochs')
    for name in ('data','observations','candidates','training'):(source/name).mkdir()
    sources={}
    for name,digest in fixture['sourceFiles'].items():
        raw=captured_source_identity.read(repo,name,digest)
        target=source/'source-snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw);sources[str(target)]=digest
    jsonl(source/'candidates/rows.jsonl',fixture['rows'])
    jsonl(source/'candidates/observations.jsonl',fixture['observations'])
    receipt=dict(scope='portable derivative of actual JVM capture; compiler/runtime evidence retained locally',
        files={str(p):sha(p) for p in (source/'candidates').iterdir()},sources=sources,
        originalExportFiles=fixture['originalExportFiles'],fixtureSha256=sha(fixture_path))
    write(source/'candidates/receipt.json',receipt)
    for part in ('train','dev','test'):
        jsonl(source/f'data/{part}-rows.jsonl',fixture['rows'] if part=='test' else [])
        jsonl(source/f'data/{part}-text.jsonl',[fixture['text']] if part=='test' else [])
        jsonl(source/f'observations/{part}.jsonl',
              [dict(row=r,observation=o) for r,o in zip(fixture['rows'],fixture['observations'],strict=True)] if part=='test' else [])
    manifest=dict(containsPersonalMessages=False,historicalReproduction=True,sourceSha256=fixture['sourceSha256'],
        fixtureOnly=True,fixturePurpose='CONTROLLED_DISCLOSED_WORD_SUBSET_NOT_ORIGINAL_TRAINING_OR_SELECTION',
        files={p.name:sha(p) for p in (source/'data').iterdir()})
    write(source/'data/manifest.json',manifest)
    write(source/'observations/manifest.json',dict(dataManifest=str(source/'data/manifest.json'),
        dataManifestSha256=sha(source/'data/manifest.json'),exportReceipt=str(source/'candidates/receipt.json'),
        exportReceiptSha256=sha(source/'candidates/receipt.json'),
        partitions={part:sha(source/f'observations/{part}.jsonl') for part in ('train','dev','test')}))
    assets=project/'app/src/main/assets/smarttyping/experiments'
    shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin',assets/'ru-ranker.bin')
    for name in ('original.bin','fixture.bin'):
        shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin',source/'training'/name)
    network=neural.load_model(source/'training/original.bin')
    groups=[(o['row'],o['observation']['generation']['alternatives'],None) for o in observed]
    trees=rank.scores(assets/'ru-ranker.bin',groups)
    packed,_=training.pack(observed,trees);values=training.context_values(network,packed)
    summary=training.summarize(packed,values)
    model=dict(sha256=sha(source/'training/original.bin'),oldDev=summary,
               newDev=training.summarize([],[]))
    selection=dict(selected='fixture',selectedPath=str(source/'training/fixture.bin'),
        selectedSha256=sha(source/'training/fixture.bin'),originalSha256=sha(source/'training/original.bin'),
        rankerSha256=sha(assets/'ru-ranker.bin'),selectionFrozenBeforeTest=True,testAccess=False,fixtureOnly=True)
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),
                     ('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        payload=dict(fixtureOnly=True,testAccess=False)
        if name=='dev-report.json':payload.update(planSha256=selection['planSha256'],models={'original':model,'fixture':model})
        if name=='dev-scores.json':payload.update(
            oldDev=dict(rowIds=[o['row']['id'] for o in observed],models={'original':values,'fixture':values}),
            newDev=dict(rowIds=[],models={'original':[],'fixture':[]}))
        write(source/'training'/name,payload);selection[key]=sha(source/'training'/name)
    write(source/'training/selection.json',selection)
    with patch.object(evaluation,'ROOT',project):report=evaluation.run(source,True,legacy,4)
    frozen=binding.freeze(source,True,project,legacy,4);binding.shared.verify_report(report,frozen)
    assert report['accepted'] is False and report['independentDataEvaluation'] is False
    assert {k:v['totalTypoRows'] for k,v in report['fresh'].items()}==dict(all=3,single=1,hard=2,double=1,triple=1)
    assert report['correctControls']['rows']==1
    assert all(v['models']['before']==v['models']['after'] for v in report['fresh'].values())
    mutations=0
    for path,raw in frozen['files'].items():
        path.write_bytes(raw+b' ')
        try:binding.shared.verify(frozen)
        except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT';mutations+=1
        else:raise AssertionError('word input drift accepted')
        finally:path.write_bytes(raw)
    # The writer refuses a second result without overwriting the first.
    report_bytes=(source/'evaluation.json').read_bytes()
    with patch.object(evaluation,'ROOT',project):
        try:evaluation.run(source,True,legacy,4)
        except ValueError as error:assert str(error)=='EVALUATION_ALREADY_REVEALED'
        else:raise AssertionError('second test disclosure accepted')
    assert (source/'evaluation.json').read_bytes()==report_bytes
    Path(output).write_bytes(report_bytes)
    return dict(scope='controlled disclosed word comparison; real JVM-captured proposals; no training reproduction',
        mainRows=4,typoRows=3,controls=1,oldDevRows=len(observed),
        previousRows=report['exposedRegressions']['previous']['rowsWithAlternatives'],
        extraRows=report['exposedRegressions']['extraEpochs']['rowsWithAlternatives'],
        legacyRows=report['exposedRegressions']['legacy']['rowsWithAlternatives'],
        accepted=report['accepted'],observedGatePassed=report['observedGatePassed'],
        inputMutationRejections=mutations,capturedFiles=len(frozen['files']),secondDisclosureRejected=True,reportSha256=sha(Path(output)),
        fixtureSha256=sha(fixture_path),receiptInputs=len(frozen['receipt']['inputBindings']))


def run(output):
    return refinement.run(output,lambda repo,project,legacy,previous:
        compare_fixture(repo,project,legacy,previous,Path(output).resolve()/'word-ranking-report.json'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.output)['extraComparison']))


if __name__=='__main__':main()
