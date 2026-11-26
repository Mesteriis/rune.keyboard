"""Freeze retrieval data, generator and scorer inputs; no model qualification."""
import json
import math
from pathlib import Path

import independent_corpus_guard as guard
import refinement_evaluation_receipt as shared
from export_retrieval import support
from word_evaluation_receipt import validate_rows

HERE=Path(__file__).resolve().parent
require=shared.require
sha=shared.sha


def validate_observations(rows,observations):
    support.validate_rows(rows);support.verify_observations(rows,observations);validate_rows(rows)
    for row,observed in zip(rows,observations,strict=True):
        for key in ('generation','manual'):
            generation=observed.get(key)
            if generation is None:
                require(key=='manual','RETRIEVAL_GENERATION');continue
            require(generation.get('original')==row['typed'],'RETRIEVAL_ORIGINAL')
            for count,limit in [('inspectedStates',8192),('verifiedTerminals',64)]:
                require(type(generation.get(count)) is int and 0<=generation[count]<=limit,'SEARCH_BUDGET')
            candidates=generation['alternatives']
            require(len(candidates)<=7 and len({c['canonicalKey'] for c in candidates})==len(candidates),'POOL_BOUND')
        for key in ('generationMs','manualMs'):
            value=observed.get(key)
            require(type(value) in (int,float) and math.isfinite(value) and value>=0,'RETRIEVAL_LATENCY')


def freeze(directory,historical_reproduction=False,project_root=None,manifest_path=None,selection_path=None):
    snapshot=guard.begin(historical_reproduction)
    project=Path(project_root).resolve() if project_root else HERE.parents[1]
    directory=Path(directory).resolve()
    require(directory.is_relative_to(project/'build'),'RETRIEVAL_EVALUATION_ROOT')
    require((manifest_path is None)==(selection_path is None),'FRESH_BINDINGS_REQUIRED')
    require(historical_reproduction or manifest_path is not None,'FRESH_BINDINGS_REQUIRED')
    files={};boundaries={};bindings={}
    def read(path,key,boundary):
        path=Path(path)
        require(path.is_absolute() and not path.is_symlink() and path.resolve().is_relative_to(boundary),'EVALUATION_INPUT_PATH')
        raw=path.read_bytes();files[path]=raw;boundaries[path]=boundary;bindings[key]=sha(raw);return raw
    def declared(path,key):
        path=Path(path)
        # Real exporter receipts also bind compiler/SDK files outside the project.
        # They are hashed as data; no command from a receipt is executed.
        boundary=project if path.resolve().is_relative_to(project) else path.parent.resolve()
        return read(path,key,boundary)
    raw_receipt=read(directory/'receipt.json','export/receipt',directory);export=json.loads(raw_receipt)
    require(export.get('scope')=='host-production-manual-retrieval','EXPORT_SCOPE')
    require(bool(export.get('files')) and bool(export.get('sources')),'EMPTY_BINDINGS')
    for ordinal,(name,digest) in enumerate(sorted(export['files'].items())):
        require(sha(read(Path(name),f'export/file-{ordinal}',directory))==digest,'BOUND_FILE_CHANGED')
    for name in ('rows.jsonl','observations.jsonl','source-freeze.json','inputs.tsv'):
        raw=files.get(directory/name)
        require(raw is not None and export['files'].get(str(directory/name))==sha(raw),'CONSUMED_FILE_BINDING')
    require(json.loads(files[directory/'source-freeze.json'])==export['sources'],'RETRIEVAL_SOURCE_FREEZE')
    for ordinal,(name,digest) in enumerate(sorted(export['sources'].items())):
        require(sha(declared(name,f'export/source-{ordinal}'))==digest,'BOUND_FILE_CHANGED')
    rows=[json.loads(line) for line in files[directory/'rows.jsonl'].decode().splitlines()]
    observations=[json.loads(line) for line in files[directory/'observations.jsonl'].decode().splitlines()]
    validate_observations(rows,observations)
    selection_hash=None;manifest_hash=None
    if manifest_path is not None:
        manifest_path=Path(manifest_path).resolve();selection_path=Path(selection_path).resolve()
        raw_manifest=read(manifest_path,'fresh/manifest',project/'build');manifest=json.loads(raw_manifest)
        raw_selection=read(selection_path,'fresh/selection',project/'build');selection=json.loads(raw_selection)
        require(selection.get('frozenBeforeFreshEvaluation') is True,'FROZEN_SELECTION_REQUIRED')
        require(bool(selection.get('files')),'EMPTY_BINDINGS')
        for ordinal,(name,digest) in enumerate(sorted(selection['files'].items())):
            require(sha(declared(name,f'selection/file-{ordinal}'))==digest,'BOUND_FILE_CHANGED')
        require(selection['freshManifestSha256']==sha(raw_manifest),'FRESH_MANIFEST_IDENTITY')
        require(manifest.get('containsPersonalMessages') is False,'PUBLIC_DATA_REQUIRED')
        for name,digest in manifest['files'].items():
            require(isinstance(name,str) and Path(name).name==name and name.endswith('.jsonl'),'RETRIEVAL_DATA_PATH')
            require(sha(read(manifest_path.parent/name,'fresh/data/'+name,manifest_path.parent))==digest,'FRESH_ROWS_IDENTITY')
        raw_rows=files[manifest_path.parent/'test-rows.jsonl']
        require([json.loads(x) for x in raw_rows.decode().splitlines()]==rows,'FRESH_ROWS_IDENTITY')
        lock=json.loads(read(project/'tools/model/rune-text-0.2/source-lock.json','public-source-lock',project))
        require(manifest['sourceSha256']==lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'],'PUBLIC_SOURCE_IDENTITY')
        require({str(r['articleId']) for r in rows}<=set(manifest['articles']),'FRESH_ARTICLES')
        if snapshot is not None:
            require(manifest.get('historicalReproduction') is False and manifest.get('registryBindings')==snapshot['registryBindings'],
                    'EVALUATION_REGISTRY_BINDING')
        selection_hash=sha(raw_selection);manifest_hash=sha(raw_manifest)
    role=guard.finish(snapshot,rows)
    assets=project/'app/src/main/assets/smarttyping/experiments'
    model_hashes={}
    for name in ('ru-ranker.bin','ru-ranking-context.bin'):
        model_hashes[name]=sha(read(assets/name,'models/'+name,project))
    registries=shared.current_registries(historical_reproduction)
    if snapshot is not None:require(registries==snapshot['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    code={str((HERE/name).relative_to(HERE.parents[1])):sha((HERE/name).read_bytes()) for name in (
        'retrieval_evaluation_receipt.py','evaluate_retrieval.py','export_retrieval.py','word_evaluation_receipt.py',
        'prepare_word_ranking.py',
        'refinement_evaluation_receipt.py','rank_refinement.py','neural_refinement.py','train.py',
        'independent_corpus_guard.py','public_corpus_preparation_v1.py','promote_refinement.py')}
    code['tools/morphology/evaluate.py']=sha((HERE.parents[1]/'tools/morphology/evaluate.py').read_bytes())
    receipt=dict(schema='rune-retrieval-evaluation-v1',historicalReproduction=historical_reproduction,
        independentQualification=False,productionQualified=False,corpusRole=role['scope'],
        exportReceiptSha256=sha(raw_receipt),selectionSha256=selection_hash,dataManifestSha256=manifest_hash,
        inputBindings=bindings,sourceBindings=code,registryBindings=registries,modelHashes=model_hashes)
    return dict(source=directory,files=files,boundaries=boundaries,receipt=receipt,rows=rows,
                observations=observations,assets=assets)


def finish_report(frozen,result):
    result.update(evaluationBinding=frozen['receipt'],historicalReproduction=frozen['receipt']['historicalReproduction'],
        independentQualification=False,productionQualified=False,corpusRole=frozen['receipt']['corpusRole'])
    shared.verify(frozen);result['reportPayloadSha256']=shared.seal(result);return result


def verify_report(report,frozen):
    require(report.get('evaluationBinding')==frozen['receipt'],'EVALUATION_RECEIPT_MISMATCH')
    for key in ('historicalReproduction','independentQualification','productionQualified','corpusRole','modelHashes'):
        require(type(report.get(key)) is type(frozen['receipt'][key]) and report.get(key)==frozen['receipt'][key],
                'EVALUATION_REPORT_ROLE')
    require(report.get('reportPayloadSha256')==shared.seal(report),'EVALUATION_REPORT_PAYLOAD')
