"""Native export plus real published-model calibration on six disclosed rows."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def jsonl(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))


def validate_fixture(fixture):
    if fixture.get('containsPersonalMessages') is not False or len(fixture.get('rows',[]))!=6 or any(
            row.get('split')!='calibration' for row in fixture['rows']):raise ValueError('CALIBRATION_FIXTURE_SCOPE')
    ledger=json.loads((ROOT/'tools/typing_experiments/holdout-ledger.json').read_text())
    for path,key in [('originalManifestPath','originalManifestSha256'),('originalCalibrationPath','originalCalibrationSha256')]:
        if not any(e.get('bindings',{}).get(fixture[path])==fixture[key] for e in ledger['entries']):
            raise ValueError('CALIBRATION_FIXTURE_DISCLOSURE')
    articles={r['article'] for r in fixture['rows']}
    if {a['articleId'] for a in fixture['articleAttribution']}!=articles or any(
            a['historyUrl']!='https://ru.wikipedia.org/w/index.php?curid='+a['articleId']+'&action=history' for a in fixture['articleAttribution']):
        raise ValueError('CALIBRATION_FIXTURE_ATTRIBUTION')


def run(output,java):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_CALIBRATION_SMOKE_OUTPUT')
    output.mkdir(parents=True,exist_ok=False);old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/typing_experiments')]
        import replay_joint_correction as replay
        import calibrate_joint_source as source
        import calibrate_joint_followup as followup
        import joint_calibration_receipt as binding
        from joint_evaluation_smoke import validate_fixture as validate_holdout
        fixture_path=ROOT/'tools/ci/fixtures/joint-calibration-disclosed-rows.json'
        fixture=json.loads(fixture_path.read_text());validate_fixture(fixture)
        held=json.loads((ROOT/'tools/ci/fixtures/joint-editor-disclosed-rows.json').read_text());validate_holdout(held)
        workspace=output/'workspace';corpus=workspace/'corpus';corpus.mkdir(parents=True)
        jsonl(corpus/'calibration.jsonl',fixture['rows']);jsonl(corpus/'holdout.jsonl',held['rows'])
        write(corpus/'manifest.json',dict(fixtureOnly=True,containsPersonalMessages=False,historicalReproduction=True,
            fixturePurpose='controlled reuse of disclosed calibration rows; not original followup or training reproduction',
            files={p.name:sha(p) for p in corpus.iterdir()}))
        assets=ROOT/'app/src/main/assets/smarttyping/experiments'
        packaged=[p for p in assets.iterdir() if p.is_file()]+[ROOT/'tools/typing_experiments/parity.tsv',
            ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/FrozenExperimentAssets.kt']
        before={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        ranker=workspace/'ranker';ranker.mkdir();shutil.copyfile(assets/'ru-joint-ranker.bin',ranker/'joint-ranker.bin')
        meta=json.loads((assets/'joint-correction-provenance.json').read_text())
        parent=dict(fixtureOnly=True,fixturePurpose='copied published model; no training or selection reproduction',
            stage='frozen-before-independent-holdout',modelSha256=sha(ranker/'joint-ranker.bin'),contextSha256=meta['contextSha256'],
            corpusManifestSha256=sha(corpus/'manifest.json'),holdoutSha256=sha(corpus/'holdout.jsonl'))
        write(ranker/'frozen-policy.json',parent)
        cache=ranker/'calibration-scores.json';cache.write_bytes(b'UNUSED_STALE_CACHE_PROBE; not scientific data')
        replay.run(corpus/'calibration.jsonl',output/'export','joint-export',java)
        export=output/'export'
        first=source.run(ranker,export,workspace/'arbitration-v3',True,corpus)
        second=followup.run(workspace,export,workspace/'followup-policy',True,corpus)
        frozen=binding.freeze('source',ranker,corpus,export,ranker/'frozen-policy.json',True)
        inherited=binding.freeze('followup',ranker,corpus,export,workspace/'arbitration-v3/frozen-policy.json',True)
        binding.verify_policy(first,frozen);binding.verify_policy(second,inherited)
        assert first['stage']==second['stage']=='historical-disclosed-calibration'
        assert first['observedCalibrationPassed'] is False and second['observedCalibrationPassed'] is False
        assert not first['independentQualification'] and not second['productionQualified']
        assert cache not in frozen['files'] and first['calibrationSummary']['eligibleGroups']==6
        probes=0;all_files=frozen['files']|inherited['files']
        for path,raw in all_files.items():
            if not path.is_relative_to(output):continue
            path.write_bytes(raw+b' ');snapshot=frozen if path in frozen['files'] else inherited
            try:binding.shared.verify(snapshot)
            except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT';probes+=1
            else:raise AssertionError('calibration input drift accepted')
            finally:path.write_bytes(raw)
        original=source.calibrate;model=ranker/'joint-ranker.bin';raw=model.read_bytes()
        def drift(*args):
            result=original(*args);model.write_bytes(raw+b' ');return result
        with patch.object(source,'calibrate',side_effect=drift):
            try:source.run(ranker,export,workspace/'refused-output',True,corpus)
            except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT'
            else:raise AssertionError('mid-calibration model drift accepted')
        model.write_bytes(raw);assert not (workspace/'refused-output').exists()
        policy_path=workspace/'arbitration-v3/frozen-policy.json';raw=policy_path.read_bytes()
        try:source.run(ranker,export,workspace/'arbitration-v3',True,corpus)
        except ValueError as error:assert str(error)=='FRESH_CALIBRATION_OUTPUT'
        else:raise AssertionError('repeated calibration output accepted')
        assert policy_path.read_bytes()==raw
        assert before=={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        result=dict(scope='actual current native proposals and published-weight scoring; bounded disclosed calibration; no independent qualification',
            rows=6,primary=first['calibrationSummary'],followup=second['calibrationSummary'],
            independentQualification=False,productionQualified=False,oldScoreCacheIgnored=True,
            capturedFiles=len(all_files),isolatedMutationRejections=probes,midCalibrationDriftRejected=True,secondWriteRejected=True,
            packagedFilesUnchanged=True,packagedFileSha256=before,fixtureSha256=sha(fixture_path),driverSha256=sha(Path(__file__)),
            policies={str(p.relative_to(output)):sha(p) for p in (policy_path,workspace/'followup-policy/frozen-policy.json')})
        write(output/'receipt.json',result);return result
    finally:sys.path[:]=old_path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--java',type=Path,required=True)
    a=p.parse_args();result=run(a.output,a.java)
    print(json.dumps({k:result[k] for k in ('rows','isolatedMutationRejections','oldScoreCacheIgnored','packagedFilesUnchanged')}))


if __name__=='__main__':main()
