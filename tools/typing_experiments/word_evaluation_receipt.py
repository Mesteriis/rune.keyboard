"""Bind word-ranking comparison inputs; a disclosed replay cannot qualify a model."""
import json
import math
from pathlib import Path

import independent_corpus_guard as guard
import refinement_evaluation_receipt as shared
from extra_epoch_evaluation_receipt import finish_report
from prepare_word_ranking import distance

HERE=Path(__file__).resolve().parent
require=shared.require
sha=shared.sha


def validate_rows(rows):
    for row in rows:
        count=row.get('errorCount')
        require(type(count) is int,'WORD_ERROR_COUNT')
        if row.get('cohort')=='correct':
            require(count==0 and row.get('noAuto') is True and row['typed']==row['expectedSpelling'],
                    'CORRECT_CONTROL_MUTATED')
        else:
            require(row.get('cohort')=='typo' and row.get('noAuto') is False and
                    1<=count<=3 and row['typed']!=row['expectedSpelling'],'WORD_TYPO_COHORT')
            require(distance(row['typed'],row['expectedSpelling'])==count,'WORD_EDIT_DISTANCE')


def capture_dev(root,directory,dataset,read,prefix):
    raw=read(root/directory/'dev.jsonl',prefix+'dev-observations',root)
    meta=json.loads(read(root/directory/'manifest.json',prefix+'dev-manifest',root))
    require(sha(raw)==meta['partitions']['dev'],'WORD_DEV_OBSERVATIONS')
    rows=[json.loads(line) for line in dataset[2]['dev-rows.jsonl'].decode().splitlines()]
    observations=[json.loads(line) for line in raw.decode().splitlines()]
    require(len(rows)==len(observations) and len({r['id'] for r in rows})==len(rows),'WORD_DEV_ROW_IDENTITY')
    for row,observed in zip(rows,observations,strict=True):
        require(observed.get('row')==row and row.get('partition')=='dev' and
                observed['observation']['generation']['original']==row['typed'],'WORD_DEV_ROW_IDENTITY')
    return observations


def validate_dev(selection,report,scores,groups):
    require(report.get('testAccess') is False,'WORD_DEV_TEST_ACCESS')
    require(report.get('planSha256')==selection['planSha256'],'WORD_DEV_PLAN')
    for key,observed in groups.items():
        rows=[o['row'] for o in observed]
        require(scores[key]['rowIds']==[r['id'] for r in rows],'WORD_DEV_SCORE_ROWS')
        typo=sum(r['cohort']=='typo' and not r['noAuto'] for r in rows)
        for name in {'original',selection['selected']}:
            summary=report['models'][name][key]
            require(type(summary.get('typoRows')) is int and summary['typoRows']==typo and
                    type(summary.get('controls')) is int and summary['controls']==len(rows)-typo,
                    'WORD_DEV_DENOMINATOR')
            for count in ('expectedAvailable','combinedTop1','neuralTop1'):
                require(type(summary.get(count)) is int and 0<=summary[count]<=typo,'WORD_DEV_COUNT')
            require(summary['combinedTop1']<=summary['expectedAvailable'] and
                    summary['neuralTop1']<=summary['expectedAvailable'],'WORD_DEV_COUNT')
            values=scores[key]['models'][name]
            require(len(values)==len(observed) and all(len(v)==len(o['observation']['generation']['alternatives'])
                    for v,o in zip(values,observed,strict=True)),'WORD_DEV_SCORE_SHAPE')
            require(all(type(x) in (int,float) and math.isfinite(x) for v in values for x in v),
                    'WORD_DEV_SCORE_FINITE')
    for name,key in [('original','originalSha256'),(selection['selected'],'selectedSha256')]:
        require(report['models'][name]['sha256']==selection[key],'WORD_DEV_MODEL_IDENTITY')


def freeze(source,historical_reproduction=False,project_root=None,legacy=None,regression_row_limit=None):
    snapshot=guard.begin(historical_reproduction)
    project=Path(project_root).resolve() if project_root else HERE.parents[1]
    source=Path(source).resolve()
    require(source.is_relative_to(project/'build'),'WORD_EVALUATION_ROOT')
    require(regression_row_limit is None or (historical_reproduction and
            type(regression_row_limit) is int and regression_row_limit>0),'WORD_REGRESSION_LIMIT')
    files={};boundaries={};bindings={}
    def read(path,key,boundary):
        path=Path(path)
        require(not path.is_symlink() and path.resolve().is_relative_to(boundary),'EVALUATION_INPUT_PATH')
        raw=path.read_bytes();files[path]=raw;boundaries[path]=boundary;bindings[key]=sha(raw);return raw
    def local(name):return read(source/name,name,source)
    raw_selection=local('training/selection.json');selection=json.loads(raw_selection)
    require(selection.get('selectionFrozenBeforeTest') is True and selection.get('testAccess') is False,
            'FROZEN_DEV_SELECTION_REQUIRED')
    supporting={}
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),
                     ('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        raw=local('training/'+name);require(sha(raw)==selection.get(key),'SELECTION_BINDING')
        supporting[name]=json.loads(raw)
    selected=Path(selection['selectedPath']);selected_raw=read(selected,'models/selected',source/'training')
    original_raw=local('training/original.bin')
    ranker=project/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin'
    ranker_raw=read(ranker,'models/ranker',project)
    for raw,key in [(selected_raw,'selectedSha256'),(original_raw,'originalSha256'),(ranker_raw,'rankerSha256')]:
        require(sha(raw)==selection.get(key),'MODEL_IDENTITY')
    def dataset(root,directory,prefix):
        graph=shared.capture_dataset(root,directory,read,project,prefix)
        observed=json.loads(files[root/directory/'manifest.json'])
        export=json.loads(files[Path(observed['exportReceipt'])])
        # Bind every declared project dependency, including experiment policies.
        # Historical external toolchains are metadata, not executable fixtures.
        for ordinal,(name,digest) in enumerate(sorted(export['sources'].items())):
            path=Path(name)
            if path.resolve().is_relative_to(project) and '.external' not in path.parts:
                require(sha(read(path,prefix+f'export/project-source-{ordinal}',project))==digest,
                        'EVALUATION_PROJECT_SOURCE_IDENTITY')
        return graph
    primary=dataset(source,'observations','main/')
    rows=[json.loads(line) for line in primary[2]['test-rows.jsonl'].decode().splitlines()]
    validate_rows(rows)
    previous_root=project/'build/typing-refinement';extra_root=project/'build/typing-extra-epochs'
    previous=dataset(previous_root,'verified-observations','previous/')
    dataset(extra_root,'observations','extra/')
    groups={'newDev':capture_dev(source,'observations',primary,read,'selection/new/'),
            'oldDev':capture_dev(previous_root,'verified-observations',previous,read,'selection/old/')}
    validate_dev(selection,supporting['dev-report.json'],supporting['dev-scores.json'],groups)
    read(project/'tools/model/rune-text-0.2/source-lock.json','public-source-lock',project)
    legacy=project if legacy is None else Path(legacy).resolve()
    require(legacy.is_relative_to(project),'EVALUATION_LEGACY_ROOT')
    locator='.' if legacy==project else legacy.relative_to(project).as_posix()
    legacy_binding,legacy_rows=shared.capture_legacy(shared.legacy_root(project,locator),read)
    if snapshot is not None:
        manifest,_,data,_=primary
        require(manifest.get('historicalReproduction') is False and
                manifest.get('registryBindings')==snapshot['registryBindings'],'EVALUATION_REGISTRY_BINDING')
        require({'train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl'}<=set(data),'EVALUATION_SPLIT_INPUTS')
        all_rows=[json.loads(line) for name,raw in data.items() if name in
            ('train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl') for line in raw.decode().splitlines()]
        guard.finish(snapshot,all_rows)
    registries=shared.current_registries(historical_reproduction)
    if snapshot is not None:require(registries==snapshot['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    code={str((HERE/name).relative_to(HERE.parents[1])):sha((HERE/name).read_bytes()) for name in (
        'word_evaluation_receipt.py','evaluate_word_ranking.py','word_ranking.py','prepare_word_ranking.py',
        'extra_epoch_evaluation_receipt.py','evaluate_extra_epochs.py','refinement_evaluation_receipt.py',
        'rank_refinement.py','neural_refinement.py','train.py','independent_corpus_guard.py',
        'public_corpus_preparation_v1.py','promote_refinement.py')}
    code['tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json']=legacy_binding['corpusManifestSha256']
    receipt=dict(schema='rune-word-ranking-evaluation-v1',historicalReproduction=historical_reproduction,
        independentDataEvaluation=not historical_reproduction,selectionSha256=sha(raw_selection),
        dataManifestSha256=sha(primary[1]),observationsSha256=sha(primary[3]),inputBindings=bindings,
        sourceBindings=code,registryBindings=registries,legacyRoot=locator,
        legacyRegressionBinding=legacy_binding,regressionRowLimit=regression_row_limit)
    return dict(source=source,files=files,boundaries=boundaries,receipt=receipt,selection=selection,
        manifest=primary[0],rows=rows,legacyRows=legacy_rows,selected=selected,
        original=source/'training/original.bin',ranker=ranker,previous=previous_root,extra=extra_root)
