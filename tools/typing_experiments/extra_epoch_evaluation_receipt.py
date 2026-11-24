"""Freeze additional-epoch comparison inputs; disclosed replay cannot grant acceptance."""
import json
import math
from pathlib import Path

import independent_corpus_guard as guard
import refinement_evaluation_receipt as shared

HERE=Path(__file__).resolve().parent
require=shared.require
sha=shared.sha


def validate_dev_metrics(selection,report,rows):
    for key in ('devTop1Before','devTop1After'):
        require(type(selection.get(key)) is int and 0<=selection[key]<=rows,'EPOCH_DEV_COUNT')
    for name in ('original',selection['selected']):
        value=report['models'][name]['devCE']
        require(type(value) in (int,float) and math.isfinite(value) and value>=0,'EPOCH_DEV_CROSS_ENTROPY')


def freeze(source,historical_reproduction=False,project_root=None,legacy=None,regression_row_limit=None):
    snapshot=guard.begin(historical_reproduction)
    source=Path(source).resolve();project=Path(project_root).resolve() if project_root else HERE.parents[1]
    require(source.is_relative_to(project/'build'),'EPOCH_EVALUATION_ROOT')
    require(regression_row_limit is None or (historical_reproduction and
            type(regression_row_limit) is int and regression_row_limit>0),'EPOCH_REGRESSION_LIMIT')
    files={};boundaries={};bindings={}
    def read(path,key,boundary):
        path=Path(path)
        require(not path.is_symlink() and path.resolve().is_relative_to(boundary),'EVALUATION_INPUT_PATH')
        raw=path.read_bytes();files[path]=raw;boundaries[path]=boundary;bindings[key]=sha(raw);return raw
    def local(name):return read(source/name,name,source)
    raw_selection=local('training/selection.json');selection=json.loads(raw_selection)
    require(selection.get('selectionFrozenBeforeTest') is True and selection.get('testAccess') is False,
            'FROZEN_DEV_SELECTION_REQUIRED')
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),
                     ('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        require(sha(local('training/'+name))==selection.get(key),'SELECTION_BINDING')
    selected=Path(selection['selectedPath'])
    selected_raw=read(selected,'models/selected',source/'training')
    original_raw=local('training/original.bin')
    ranker=project/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin'
    ranker_raw=read(ranker,'models/ranker',project)
    for raw,key in [(selected_raw,'selectedSha256'),(original_raw,'originalSha256'),(ranker_raw,'rankerSha256')]:
        require(sha(raw)==selection.get(key),'MODEL_IDENTITY')
    primary=shared.capture_dataset(source,'observations',read,project,'main/')
    previous_root=project/'build/typing-refinement'
    previous=shared.capture_dataset(previous_root,'verified-observations',read,project,'previous/')
    dev_observations=read(previous_root/'verified-observations/dev.jsonl','selection/dev-observations',previous_root)
    require(sha(dev_observations)==selection.get('observationsSha256'),'EPOCH_DEV_OBSERVATIONS')
    dev_report=json.loads(local('training/dev-report.json'))
    validate_dev_metrics(selection,dev_report,len(previous[2]['dev-rows.jsonl'].decode().splitlines()))
    legacy=project if legacy is None else Path(legacy).resolve()
    require(legacy.is_relative_to(project),'EVALUATION_LEGACY_ROOT')
    locator='.' if legacy==project else legacy.relative_to(project).as_posix()
    legacy_binding,legacy_rows=shared.capture_legacy(shared.legacy_root(project,locator),read)
    if snapshot is not None:
        manifest,_,data,_=primary
        require(manifest.get('historicalReproduction') is False and
                manifest.get('registryBindings')==snapshot['registryBindings'],'EVALUATION_REGISTRY_BINDING')
        require({'train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl'}<=set(data),'EVALUATION_SPLIT_INPUTS')
        rows=[json.loads(line) for name,raw in data.items() if name in
              ('train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl') for line in raw.decode().splitlines()]
        guard.finish(snapshot,rows)
    registries=shared.current_registries(historical_reproduction)
    if snapshot is not None:require(registries==snapshot['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    code={str((HERE/name).relative_to(HERE.parents[1])):sha((HERE/name).read_bytes()) for name in (
        'extra_epoch_evaluation_receipt.py','evaluate_extra_epochs.py','extra_epochs.py',
        'refinement_evaluation_receipt.py','rank_refinement.py','neural_refinement.py','train.py')}
    code['tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json']=legacy_binding['corpusManifestSha256']
    receipt=dict(schema='rune-extra-epoch-evaluation-v1',historicalReproduction=historical_reproduction,
        independentDataEvaluation=not historical_reproduction,selectionSha256=sha(raw_selection),
        dataManifestSha256=sha(primary[1]),observationsSha256=sha(primary[3]),inputBindings=bindings,
        sourceBindings=code,registryBindings=registries,legacyRoot=locator,
        legacyRegressionBinding=legacy_binding,regressionRowLimit=regression_row_limit)
    return dict(source=source,files=files,boundaries=boundaries,receipt=receipt,selection=selection,
                manifest=primary[0],legacyRows=legacy_rows,selected=selected,original=source/'training/original.bin',
                ranker=ranker,previous=previous_root)


def finish_report(frozen,result,observed_gate):
    require(type(observed_gate) is bool,'EPOCH_OBSERVED_GATE_BOOLEAN')
    result.update(historicalReproduction=frozen['receipt']['historicalReproduction'],
        independentDataEvaluation=frozen['receipt']['independentDataEvaluation'],
        dataManifestSha256=frozen['receipt']['dataManifestSha256'],
        selectionSha256=frozen['receipt']['selectionSha256'],
        observationsSha256=frozen['receipt']['observationsSha256'],
        observedGatePassed=observed_gate,
        accepted=observed_gate and frozen['receipt']['independentDataEvaluation'],
        evaluationBinding=frozen['receipt'])
    shared.verify(frozen)
    result['reportPayloadSha256']=shared.seal(result)
    return result
