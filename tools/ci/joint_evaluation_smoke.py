"""Compile actual joint replay, then exercise disclosed evaluation and drift refusal."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')


def validate_fixture(fixture):
    if fixture.get('containsPersonalMessages') is not False or len(fixture.get('rows',[]))!=4:
        raise ValueError('JOINT_FIXTURE_SCOPE')
    ledger=json.loads((ROOT/'tools/typing_experiments/holdout-ledger.json').read_text())
    for path,key in [('originalManifestPath','originalManifestSha256'),('originalHoldoutPath','originalHoldoutSha256')]:
        if not any(e.get('bindings',{}).get(fixture[path])==fixture[key] for e in ledger['entries']):
            raise ValueError('JOINT_FIXTURE_DISCLOSURE')
    articles={r['article'] for r in fixture['rows']}
    if {r['articleId'] for r in fixture['articleAttribution']}!=articles or any(
        r['historyUrl']!='https://ru.wikipedia.org/w/index.php?curid='+r['articleId']+'&action=history' for r in fixture['articleAttribution']):
        raise ValueError('JOINT_FIXTURE_ATTRIBUTION')


def run(output,java):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_JOINT_SMOKE_OUTPUT')
    output.mkdir(parents=True,exist_ok=False)
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/typing_experiments')]
        import replay_joint_correction as replay
        import evaluate_joint_product as main
        import evaluate_joint_followup as followup
        import joint_evaluation_receipt as binding
        fixture_path=ROOT/'tools/ci/fixtures/joint-editor-disclosed-rows.json';fixture=json.loads(fixture_path.read_text());validate_fixture(fixture)
        rows=output/'rows.jsonl';rows.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in fixture['rows']))
        assets=ROOT/'app/src/main/assets/smarttyping/experiments'
        packaged=list(assets.iterdir())+[ROOT/'tools/typing_experiments/parity.tsv',
            ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/FrozenExperimentAssets.kt']
        packaged=[p for p in packaged if p.is_file()];before={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        meta=json.loads((assets/'joint-correction-provenance.json').read_text())
        policy=dict(fixtureOnly=True,fixturePurpose='controlled four-row disclosed replay; copied packaged thresholds; no training or selection reproduction',
            stage='frozen-before-independent-holdout',holdoutSha256=sha(rows),modelSha256=meta['model']['sha256'],
            contextSha256=meta['contextSha256'],thresholds=dict(short=meta['short']['thresholds'],long=meta['long']['thresholds']))
        policy_path=output/'policy.json';write(policy_path,policy)
        for mode,name in [('joint-primary-only','baseline'),('joint-production','product')]:
            receipt=replay.run(rows,output/name,mode,java)
            assert receipt['status']=='COMPLETE' and receipt['opaqueControllerIds'] is True
        baseline=output/'baseline/observations.jsonl';product=output/'product/observations.jsonl'
        report=main.run(rows,baseline,product,policy_path,output/'main-report.json',True)
        second=followup.run(rows,baseline,product,policy_path,output/'followup-report.json',True)
        frozen=binding.freeze(rows,baseline,product,policy_path,True)
        binding.verify_report(report,frozen);binding.verify_report(second,frozen)
        assert report['passed'] is False and second['passed'] is False
        mutations=0
        for path,raw in frozen['files'].items():
            if not path.is_relative_to(output):continue
            path.write_bytes(raw+b' ')
            try:binding.shared.verify(frozen)
            except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT';mutations+=1
            else:raise AssertionError('joint replay drift accepted')
            finally:path.write_bytes(raw)
        original=main.evaluate;raw=baseline.read_bytes()
        def drift(*args):
            result=original(*args);baseline.write_bytes(raw+b' ');return result
        with patch.object(main,'evaluate',side_effect=drift):
            try:main.run(rows,baseline,product,policy_path,output/'refused-report.json',True)
            except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT'
            else:raise AssertionError('mid-evaluation drift accepted')
        baseline.write_bytes(raw);assert not (output/'refused-report.json').exists()
        raw=(output/'main-report.json').read_bytes()
        try:main.run(rows,baseline,product,policy_path,output/'main-report.json',True)
        except ValueError as error:assert str(error)=='FRESH_JOINT_OUTPUT'
        else:raise AssertionError('second report write accepted')
        assert (output/'main-report.json').read_bytes()==raw
        assert before=={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        result=dict(scope='actual current joint controller replay on disclosed original rows; no independent model qualification',
            rows=4,passed=False,independentDataEvaluation=False,opaqueControllerIds=True,
            capturedFiles=len(frozen['files']),namedInputs=len(frozen['receipt']['inputBindings']),
            isolatedMutationRejections=mutations,midEvaluationDriftRejected=True,secondWriteRejected=True,
            editorIntegrity=report['editorIntegrity'],metrics=report['metrics'],packagedFilesUnchanged=True,
            packagedFileSha256=before,fixtureSha256=sha(fixture_path),driverSha256=sha(Path(__file__)),
            reports={name:sha(output/name) for name in ('main-report.json','followup-report.json')})
        write(output/'receipt.json',result);return result
    finally:sys.path[:]=old_path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--java',type=Path,required=True)
    a=p.parse_args();result=run(a.output,a.java)
    print(json.dumps({k:result[k] for k in ('rows','isolatedMutationRejections','packagedFilesUnchanged','passed')}))


if __name__=='__main__':main()
