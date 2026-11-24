"""Real numerical retrieval smoke on actual JVM-captured disclosed proposals."""
import argparse
import base64
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def jsonl(path,rows):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))


def run(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_RETRIEVAL_SMOKE_OUTPUT')
    output.mkdir(parents=True,exist_ok=False)
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/typing_experiments')]
        import evaluate_retrieval as evaluation
        import retrieval_evaluation_receipt as binding
        from word_evaluation_smoke import validate_capture
        word_path=ROOT/'tools/ci/fixtures/word-ranking-bounded-capture.json';word=json.loads(word_path.read_text())
        fixture_path=ROOT/'tools/ci/fixtures/retrieval-bounded-capture.json';fixture=json.loads(fixture_path.read_text())
        if fixture['wordCaptureSha256']!=sha(word_path) or fixture.get('containsPersonalMessages') is not False:
            raise ValueError('RETRIEVAL_CAPTURE_ORIGIN')
        validate_capture(word)
        packaged=[p for p in evaluation.ASSETS.iterdir() if p.is_file()]+[
            ROOT/'tools/typing_experiments/parity.tsv',
            ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/FrozenExperimentAssets.kt']
        before={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            directory=Path(folder);sources={}
            import captured_source_identity
            for name,digest in fixture['sourceFiles'].items():
                raw=captured_source_identity.read(ROOT,name,digest)
                target=directory/'source-snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw);sources[str(target)]=digest
            jsonl(directory/'rows.jsonl',word['rows']);jsonl(directory/'observations.jsonl',fixture['observations'])
            (directory/'inputs.tsv').write_text(''.join(f'{i}\t{base64.b64encode(r["typed"].encode()).decode()}\n' for i,r in enumerate(word['rows'])))
            write(directory/'source-freeze.json',sources)
            write(directory/'receipt.json',dict(scope='host-production-manual-retrieval',portableFixture=True,
                fixturePurpose='actual JVM proposals; compiler/runtime evidence retained locally; no new qualification',
                originalExportFiles=fixture['originalExportFiles'],
                sources=sources,files={str(directory/name):sha(directory/name) for name in
                    ('rows.jsonl','observations.jsonl','inputs.tsv','source-freeze.json')}))
            report=evaluation.run(directory,output/'retrieval-report.json',True)
            frozen=binding.freeze(directory,True,ROOT)
            binding.verify_report(report,frozen)
            assert report['evaluationBinding']==frozen['receipt']
            assert report['cohorts']['all']['rows']==3 and report['correctControls']['rows']==1
            assert report['independentQualification'] is False and report['productionQualified'] is False
            mutations=0
            for path,raw in frozen['files'].items():
                # Mutate the isolated source/model snapshots only; never packaged model files.
                if not path.is_relative_to(directory):continue
                path.write_bytes(raw+b' ')
                try:binding.shared.verify(frozen)
                except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT';mutations+=1
                else:raise AssertionError('retrieval input drift accepted')
                finally:path.write_bytes(raw)
            original=evaluation.summarize;path=directory/'rows.jsonl';raw=path.read_bytes()
            def drift(*args):
                result=original(*args);path.write_bytes(raw+b' ');return result
            with patch.object(evaluation,'summarize',side_effect=drift):
                try:evaluation.run(directory,output/'refused-report.json',True)
                except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT'
                else:raise AssertionError('mid-evaluation drift accepted')
            path.write_bytes(raw);assert not (output/'refused-report.json').exists()
            report_bytes=(output/'retrieval-report.json').read_bytes()
            try:evaluation.run(directory,output/'retrieval-report.json',True)
            except ValueError as error:assert str(error)=='FRESH_BUILD_OUTPUT_REQUIRED'
            else:raise AssertionError('second result write accepted')
            assert (output/'retrieval-report.json').read_bytes()==report_bytes
        assert before=={str(p.relative_to(ROOT)):sha(p) for p in packaged}
        result=dict(scope='bounded disclosed current-JVM retrieval; no original historical or independent qualification',
            typoRows=3,controls=1,cohorts=report['cohorts'],independentQualification=False,productionQualified=False,
            capturedFiles=len(frozen['files']),inputBindings=len(frozen['receipt']['inputBindings']),
            isolatedInputMutationRejections=mutations,midEvaluationDriftRejected=True,secondWriteRejected=True,
            modelSnapshotBindings=report['modelHashes'],packagedFilesUnchanged=True,
            packagedFileSha256=before,fixtureSha256=sha(fixture_path),driverSha256=sha(Path(__file__)),
            reportSha256=sha(output/'retrieval-report.json'))
        write(output/'receipt.json',result);return result
    finally:sys.path[:]=old_path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=run(args.output)
    print(json.dumps({key:result[key] for key in ('typoRows','controls','isolatedInputMutationRejections','packagedFilesUnchanged')}))


if __name__=='__main__':main()
