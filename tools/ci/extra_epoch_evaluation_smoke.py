"""Controlled disclosed-input epoch comparison smoke, not a training reproduction."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import refinement_evaluation_smoke as refinement


def compare_fixture(repo,project,legacy,previous,report_output=None):
    import evaluate_extra_epochs as evaluation
    import extra_epoch_evaluation_receipt as binding
    epoch=project/'build/extra-epoch-fixture';epoch.mkdir()
    for old,new in [('data','data'),('verified-observations','observations'),('candidates-v2','candidates-v2')]:
        shutil.copytree(previous/old,epoch/new)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest_path=epoch/'data/manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest['fixturePurpose']='CONTROLLED_DISCLOSED_REFINEMENT_SUBSET_NOT_ORIGINAL_EPOCH_TEST'
    manifest_path.write_text(json.dumps(manifest,sort_keys=True)+'\n')
    receipt_path=epoch/'candidates-v2/receipt.json';receipt=json.loads(receipt_path.read_text())
    receipt['files']={str(epoch/Path(name).relative_to(previous)):sha(epoch/Path(name).relative_to(previous))
                      for name in receipt['files']}
    receipt_path.write_text(json.dumps(receipt,sort_keys=True)+'\n')
    observed_path=epoch/'observations/manifest.json';observed=json.loads(observed_path.read_text())
    observed.update(dataManifest=str(manifest_path),dataManifestSha256=sha(manifest_path),
                    exportReceipt=str(receipt_path),exportReceiptSha256=sha(receipt_path))
    observed_path.write_text(json.dumps(observed,sort_keys=True)+'\n')
    assets=project/'app/src/main/assets/smarttyping/experiments'
    shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin',assets/'ru-ranker.bin')
    training=epoch/'training';training.mkdir()
    for name in ('original.bin','fixture.bin'):
        shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin',training/name)
    selection=dict(selected='fixture',selectedPath=str(training/'fixture.bin'),
        selectedSha256=sha(training/'fixture.bin'),originalSha256=sha(training/'original.bin'),
        rankerSha256=sha(assets/'ru-ranker.bin'),observationsSha256=sha(previous/'verified-observations/dev.jsonl'),
        selectionFrozenBeforeTest=True,testAccess=False,devTop1Before=0,devTop1After=0,fixtureOnly=True)
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),
                     ('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        payload={'fixtureOnly':True}
        if name=='dev-report.json':payload['models']={'original':{'devCE':1.0},'fixture':{'devCE':1.0}}
        (training/name).write_text(json.dumps(payload,sort_keys=True)+'\n');selection[key]=sha(training/name)
    (training/'selection.json').write_text(json.dumps(selection,sort_keys=True)+'\n')
    with patch.object(evaluation,'ROOT',project):
        report=evaluation.run(epoch,True,legacy,4)
    assert report['accepted'] is False and report['independentDataEvaluation'] is False
    assert report['fresh']['models']['before']==report['fresh']['models']['after']
    frozen=binding.freeze(epoch,True,project,legacy,4)
    binding.shared.verify_report(report,frozen)
    if report_output is not None:Path(report_output).write_bytes((epoch/'evaluation.json').read_bytes())
    path=previous/'verified-observations/dev.jsonl';raw=path.read_bytes();path.write_bytes(raw+b' ')
    try:binding.shared.verify(frozen)
    except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT'
    else:raise AssertionError('dev input drift accepted')
    path.write_bytes(raw)
    result=dict(scope='controlled-bound-input-comparison-not-original-epoch-qualification',
        mainRows=report['fresh']['rowsWithAlternatives'],previousRows=report['exposedPrevious']['rowsWithAlternatives'],
        legacyRows=report['exposedLegacy']['rowsWithAlternatives'],accepted=report['accepted'],
        observedGatePassed=report['observedGatePassed'],devInputMutationRejected=True,
        reportSha256=sha(epoch/'evaluation.json'),receiptInputs=len(frozen['receipt']['inputBindings']))
    return result


def run(output):
    def check(repo,project,legacy,previous):
        return compare_fixture(repo,project,legacy,previous,Path(output).resolve()/'extra-epoch-report.json')
    return refinement.run(output,check)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=run(args.output)
    print(json.dumps(result['extraComparison']))


if __name__=='__main__':main()
