"""Bounded disclosed-data evaluation/export smoke; never an independent qualification."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]


def run(output,extra_check=None):
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):
        raise ValueError('FRESH_EVALUATION_SMOKE_OUTPUT')
    out.mkdir(parents=True,exist_ok=False)
    repo=ROOT
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(repo/'tools/ci'),str(repo/'tools/typing_experiments')]
        import historical_model_fixtures as fixtures
        import evaluate_refinement as evaluation
        import rank_refinement as rank
        import promote_refinement as promotion
        import refinement_evaluation_receipt as binding
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        packaged=[p for p in promotion.ASSETS.iterdir() if p.is_file()]+[repo/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/FrozenExperimentAssets.kt',repo/'tools/typing_experiments/parity.tsv']
        before={str(p.relative_to(repo)):sha(p) for p in packaged}
        with fixtures.workspace('refinement') as project,fixtures.workspace('baseline',parent=project/'build') as baseline_root,contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(rank,'ROOT',project));stack.enter_context(patch.object(evaluation,'ROOT',project))
            stack.enter_context(patch.object(promotion,'ROOT',project.resolve()));stack.enter_context(patch.object(promotion,'ASSETS',project/'app/src/main/assets/smarttyping/experiments'))
            source=project/'build/typing-refinement'
            promotion.ASSETS.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-context.bin',promotion.ASSETS/'ru-context.bin')
            rows=[json.loads(line) for line in (source/'data/test-rows.jsonl').read_text().splitlines()]
            observed=[json.loads(line) for line in (source/'verified-observations/test.jsonl').read_text().splitlines()]
            pairs=[(r,o) for r,o in zip(rows,observed,strict=True) if o['observation']['generation']['alternatives']][:4]
            assert len(pairs)==4
            (source/'data/test-rows.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r,_ in pairs))
            (source/'verified-observations/test.jsonl').write_text(''.join(json.dumps(o,ensure_ascii=False)+'\n' for _,o in pairs))
            text=json.loads((source/'data/test-text.jsonl').read_text().splitlines()[0]);text['text']=text['text'][:100]
            (source/'data/test-text.jsonl').write_text(json.dumps(text,ensure_ascii=False)+'\n')
            manifest=json.loads((source/'data/manifest.json').read_text())
            for name in ('test-rows.jsonl','test-text.jsonl'):manifest['files'][name]=sha(source/'data'/name)
            manifest['partitions']['test']['rows']=4;manifest['partitions']['test']['characters']=len(text['text'])
            manifest['fixturePurpose']='BOUNDED_DISCLOSED_SUBSET_NOT_ORIGINAL_QUALIFICATION'
            (source/'data/manifest.json').write_text(json.dumps(manifest,sort_keys=True)+'\n')
            meta=json.loads((source/'verified-observations/manifest.json').read_text())
            meta['dataManifestSha256']=sha(source/'data/manifest.json');meta['partitions']['test']=sha(source/'verified-observations/test.jsonl')
            (source/'verified-observations/manifest.json').write_text(json.dumps(meta,sort_keys=True)+'\n')
            (source/'neural').mkdir(exist_ok=True)
            shutil.copyfile(repo/'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin',source/'neural/fixture.bin')
            (project/'tools/typing_experiments/baseline').mkdir(parents=True,exist_ok=True)
            shutil.copyfile(repo/'tools/typing_experiments/baseline/ru-ranker.bin',project/'tools/typing_experiments/baseline/ru-ranker.bin')
            selection=dict(ranker='pairwise',neural='fixture',rankerSha256=sha(source/'ranker/pairwise.bin'),neuralSha256=sha(source/'neural/fixture.bin'),blendGain=1,selectionFrozenBeforeTest=True,fixtureOnly=True)
            (source/'selection.json').write_text(json.dumps(selection,sort_keys=True)+'\n')
            report=evaluation.run(source,True,baseline_root,4)
            assert report['independentDataEvaluation'] is False and report['rowsWithAlternatives']==4
            assert report['evaluationBinding']['legacyRegressionBound'] is True
            assert report['exposedV1Regression']['rowsWithAlternatives']==4
            frozen=binding.freeze(source,True,project,(project/'tools/typing_experiments/baseline/ru-ranker.bin',promotion.ASSETS/'ru-context.bin'),baseline_root,4)
            binding.verify_report(report,frozen)
            request=promotion.prepare_request(source,project/'build/review-export',True)
            legacy_observations=baseline_root/'build/morphology-public-export-v3/observations.jsonl'
            original_legacy=legacy_observations.read_bytes();legacy_observations.write_bytes(original_legacy+b' ')
            try:promotion.verify_request(request)
            except ValueError as error:assert str(error)=='EVALUATION_INPUT_DRIFT'
            else:raise AssertionError('legacy drift accepted')
            legacy_observations.write_bytes(original_legacy)
            provenance=promotion.promote(source,project/'build/review-export',True)
            assert provenance['productionQualified'] is False
            for p in (project/'build/review-export').iterdir():
                destination=out/'bounded-review-export';destination.mkdir(exist_ok=True);shutil.copyfile(p,destination/p.name)
            shutil.copyfile(source/'test-report.json',out/'bounded-test-report.json')
            tampered=dict(report);tampered['characters']+=1
            try:binding.verify_report(tampered,frozen)
            except ValueError as error:assert str(error)=='EVALUATION_REPORT_PAYLOAD'
            else:raise AssertionError('tampered metric accepted')
            result=dict(scope='bounded-disclosed-real-driver-replay-not-original-qualification',mainRows=4,legacyRows=4,characters=len(text['text']),independentDataEvaluation=False,legacyRegressionBound=True,legacyBinding=report['evaluationBinding']['legacyRegressionBinding'],legacyInputMutationRejected=True,reportSha256=sha(out/'bounded-test-report.json'),exportFiles={p.name:sha(p) for p in (out/'bounded-review-export').iterdir()},metricMutationRejected=True)
            if extra_check is not None:result['extraComparison']=extra_check(repo,project,baseline_root,source)
        assert before=={str(p.relative_to(repo)):sha(p) for p in packaged}
        result['packagedFilesUnchanged']=True;result['packagedFileSha256']=before
        result['driverSha256']=sha(Path(__file__))
        (out/'bounded-replay-receipt.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        return result
    finally:
        sys.path[:]=old_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=run(args.output)
    print(json.dumps(dict(mainRows=result['mainRows'],legacyRows=result['legacyRows'],
                         packagedFilesUnchanged=result['packagedFilesUnchanged'])))


if __name__=='__main__':main()
