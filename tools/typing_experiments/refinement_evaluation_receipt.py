"""Freeze evaluation inputs and data role; this does not qualify model quality."""
import hashlib
import json
from pathlib import Path
import re

import independent_corpus_guard as guard
from public_corpus_preparation_v1 import registry_bindings,registry_bindings_v1

HERE=Path(__file__).resolve().parent


def require(value,code):
    if not value:raise ValueError(code)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def current_registries(historical_reproduction=False):
    bind=registry_bindings_v1 if historical_reproduction else registry_bindings
    return bind((HERE/'holdout-ledger.json').read_bytes(),(HERE/'control-ledger.json').read_bytes())


def legacy_root(project,name):
    project=Path(project).resolve()
    if name=='.':return project
    require(isinstance(name,str) and re.fullmatch('[A-Za-z0-9_./-]+',name) is not None and
            all(part not in ('','.','..') for part in name.split('/')),'EVALUATION_LEGACY_ROOT')
    path=project/name
    require(not path.is_symlink() and path.resolve().is_relative_to(project),'EVALUATION_LEGACY_ROOT')
    return path.resolve()


def capture_legacy(root,read):
    corpus=root/'tools/eval/smart-typing-0.3/qualification-v2/corpus'
    export=root/'build/morphology-public-export-v3'
    expected_path=HERE.parents[1]/'tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json'
    expected=expected_path.read_bytes()
    raw_manifest=read(corpus/'manifest.json','legacy/corpus-manifest',root)
    require(raw_manifest==expected,'EVALUATION_LEGACY_CORPUS_MANIFEST')
    manifest=json.loads(raw_manifest)
    require(manifest.get('containsPersonalMessages') is False,'EVALUATION_LEGACY_PUBLIC_DATA')
    raw_corpus=read(corpus/'spelling-ru.jsonl','legacy/corpus-rows',root)
    require(sha(raw_corpus)==manifest['files']['spelling-ru.jsonl'],'EVALUATION_LEGACY_CORPUS_IDENTITY')
    receipt=json.loads(read(export/'receipt.json','legacy/export-receipt',root))
    require(bool(receipt.get('files')) and bool(receipt.get('sources')),'EVALUATION_LEGACY_EXPORT_SCOPE')
    payloads={}
    for ordinal,(name,digest) in enumerate(sorted(receipt['files'].items())):
        raw=read(Path(name),f'legacy/export-file-{ordinal}',root)
        require(sha(raw)==digest,'EVALUATION_LEGACY_EXPORT_IDENTITY');payloads[Path(name).resolve()]=raw
    for name in ('rows.jsonl','observations.jsonl','source-freeze.json'):
        path=export/name
        require(str(path) in receipt['files'] or any(Path(p).resolve()==path for p in receipt['files']),
                'EVALUATION_LEGACY_EXPORT_MEMBERS')
    verified=0
    for ordinal,(name,digest) in enumerate(sorted(receipt['sources'].items())):
        path=Path(name)
        relative=path.resolve().relative_to(root).as_posix() if path.resolve().is_relative_to(root) else ''
        if (relative.startswith('app/src/main/assets/smarttyping/lexicon/') or
                relative.startswith('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/') or
                relative.startswith('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/') or
                relative=='tools/morphology/ProductionCandidates.kt'):
            require(sha(read(path,f'legacy/generator-{ordinal}',root))==digest,'EVALUATION_LEGACY_GENERATOR_IDENTITY')
            verified+=1
    require(verified>20,'EVALUATION_LEGACY_GENERATOR_SCOPE')
    rows=[json.loads(line) for line in payloads[export/'rows.jsonl'].decode().splitlines()]
    observations=[json.loads(line) for line in payloads[export/'observations.jsonl'].decode().splitlines()]
    source_rows=[json.loads(line) for line in raw_corpus.decode().splitlines()]
    by_id={row['id']:row for row in source_rows}
    require(bool(rows) and len(rows)==len(observations) and len(by_id)==len(source_rows),'EVALUATION_LEGACY_ROW_IDENTITY')
    public=[]
    for ordinal,(row,observation) in enumerate(zip(rows,observations,strict=True)):
        require(type(observation.get('index')) is int and observation['index']==ordinal and
                observation['generation']['original']==row['typed'],
                'EVALUATION_LEGACY_ROW_IDENTITY')
        if row['id'] in by_id:
            require(row==by_id[row['id']],'EVALUATION_LEGACY_ROW_IDENTITY');public.append((row,observation))
    require(bool(public),'EVALUATION_LEGACY_ROW_IDENTITY')
    return dict(corpusManifestSha256=sha(expected),exportRows=len(rows),matchedSourceRows=len(public),
                checkedGeneratorSources=verified),public


def capture_dataset(source,observations,read,project,prefix=''):
    source=Path(source).resolve()
    def local(name):return read(source/name,prefix+name,source)
    raw_manifest=local('data/manifest.json');manifest=json.loads(raw_manifest)
    require(manifest.get('containsPersonalMessages') is False,'EVALUATION_PUBLIC_DATA')
    data={}
    for name,digest in manifest['files'].items():
        require(isinstance(name,str) and re.fullmatch('[A-Za-z0-9_-]+\\.jsonl',name) is not None,'EVALUATION_DATA_PATH')
        raw=local('data/'+name);require(sha(raw)==digest,'EVALUATION_DATA_IDENTITY');data[name]=raw
    require({'test-rows.jsonl','test-text.jsonl'}<=set(data),'EVALUATION_TEST_INPUTS')
    raw_observations=local(observations+'/test.jsonl')
    observed_binding=json.loads(local(observations+'/manifest.json'))
    require(observed_binding['dataManifestSha256']==sha(raw_manifest) and
            Path(observed_binding['dataManifest']).resolve()==source/'data/manifest.json' and
            observed_binding['partitions']['test']==sha(raw_observations),'EVALUATION_OBSERVATION_BINDING')
    rows=[json.loads(line) for line in data['test-rows.jsonl'].decode().splitlines()]
    observed=[json.loads(line) for line in raw_observations.decode().splitlines()]
    require(bool(rows) and len(rows)==len(observed) and len({r['id'] for r in rows})==len(rows),
            'EVALUATION_ROW_IDENTITY')
    for row,observation in zip(rows,observed,strict=True):
        require(observation.get('row')==row and row.get('partition')=='test' and
                observation['observation']['generation']['original']==row['typed'],'EVALUATION_ROW_IDENTITY')
    export_path=Path(observed_binding['exportReceipt'])
    raw_export=read(export_path,prefix+'export/receipt',source)
    require(sha(raw_export)==observed_binding['exportReceiptSha256'],'EVALUATION_EXPORT_BINDING')
    export=json.loads(raw_export)
    require(bool(export.get('files')) and bool(export.get('sources')),'EVALUATION_EXPORT_SCOPE')
    for ordinal,(name,digest) in enumerate(sorted(export['files'].items())):
        require(sha(read(Path(name),prefix+f'export/file-{ordinal}',source))==digest,'EVALUATION_EXPORT_IDENTITY')
    for ordinal,(name,digest) in enumerate(sorted(export['sources'].items())):
        if '/smarttyping/lexicon/' in name or '/smarttyping/correction/' in name or name.endswith('/ProductionCandidates.kt'):
            require(sha(read(Path(name),prefix+f'export/source-{ordinal}',project))==digest,'EVALUATION_GENERATOR_IDENTITY')
    return manifest,raw_manifest,data,raw_observations


def freeze(source,historical_reproduction=False,project_root=None,additional_paths=(),legacy=None,legacy_row_limit=None):
    snapshot=guard.begin(historical_reproduction)
    source=Path(source).resolve();project=Path(project_root).resolve() if project_root else source
    files={};bindings={};boundaries={}

    def read(path,key,boundary):
        path=Path(path)
        require(not path.is_symlink() and path.resolve().is_relative_to(boundary),'EVALUATION_INPUT_PATH')
        raw=path.read_bytes();files[path]=raw;boundaries[path]=boundary;bindings[key]=sha(raw)
        return raw

    def local(name):return read(source/name,name,source)

    raw_selection=local('selection.json');selection=json.loads(raw_selection)
    require(selection.get('selectionFrozenBeforeTest') is True and
            type(selection.get('blendGain')) in (int,float) and selection['blendGain']==1,'EVALUATION_SELECTION')
    manifest,raw_manifest,data,raw_observations=capture_dataset(source,'verified-observations',read,project)
    for key in ('ranker','neural'):
        name=selection.get(key)
        require(isinstance(name,str) and re.fullmatch('[A-Za-z0-9_-]+',name) is not None,'EVALUATION_MODEL_PATH')
        require(sha(local(key+'/'+name+'.bin'))==selection.get(key+'Sha256'),'EVALUATION_MODEL_IDENTITY')
    for ordinal,path in enumerate(additional_paths):
        read(Path(path),f'baseline/{ordinal}',project)
    require(legacy_row_limit is None or (historical_reproduction and type(legacy_row_limit) is int and
            legacy_row_limit>0),'EVALUATION_LEGACY_LIMIT')
    require(legacy_row_limit is None or legacy is not None,'EVALUATION_LEGACY_LIMIT')
    legacy_name=None;legacy_binding=None;legacy_rows=[]
    if legacy is not None:
        legacy=Path(legacy).resolve()
        require(legacy.is_relative_to(project),'EVALUATION_LEGACY_ROOT')
        legacy_name='.' if legacy==project else legacy.relative_to(project).as_posix()
        legacy_binding,legacy_rows=capture_legacy(legacy_root(project,legacy_name),read)
    if snapshot is not None:
        require({'train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl'}<=set(data),'EVALUATION_SPLIT_INPUTS')
        require(manifest.get('historicalReproduction') is False and
                manifest.get('registryBindings')==snapshot['registryBindings'],'EVALUATION_REGISTRY_BINDING')
        all_rows=[json.loads(line) for name,raw in data.items() if name in
                  ('train-rows.jsonl','dev-rows.jsonl','test-rows.jsonl') for line in raw.decode().splitlines()]
        guard.finish(snapshot,all_rows)
    registries=current_registries(historical_reproduction)
    if snapshot is not None:
        require(registries==snapshot['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    code={str((HERE/name).relative_to(HERE.parents[1])):sha((HERE/name).read_bytes()) for name in (
        'refinement_evaluation_receipt.py','evaluate_refinement.py','rank_refinement.py','neural_refinement.py','train.py')}
    if legacy_binding is not None:
        code['tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json']=legacy_binding['corpusManifestSha256']
    receipt=dict(schema='rune-refinement-evaluation-v2',historicalReproduction=historical_reproduction,
        independentDataEvaluation=not historical_reproduction,dataManifestSha256=sha(raw_manifest),
        selectionSha256=sha(raw_selection),observationsSha256=sha(raw_observations),
        inputBindings=bindings,registryBindings=registries,sourceBindings=code,
        legacyRoot=legacy_name,legacyRegressionBound=legacy_binding is not None,
        legacyRegressionBinding=legacy_binding,legacyRowLimit=legacy_row_limit)
    return dict(source=source,files=files,boundaries=boundaries,receipt=receipt,selection=selection,
                manifest=manifest,legacyRows=legacy_rows)


def verify(frozen):
    for path,raw in frozen['files'].items():
        require(not path.is_symlink() and path.resolve().is_relative_to(frozen['boundaries'][path]) and
                path.read_bytes()==raw,'EVALUATION_INPUT_DRIFT')
    require(current_registries(frozen['receipt']['historicalReproduction'])==frozen['receipt']['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    for name,digest in frozen['receipt']['sourceBindings'].items():
        require(sha((HERE.parents[1]/name).read_bytes())==digest,'EVALUATION_SOURCE_DRIFT')


def seal(report):
    payload={key:value for key,value in report.items() if key!='reportPayloadSha256'}
    return sha(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def verify_report(report,frozen):
    require(report.get('evaluationBinding')==frozen['receipt'],'EVALUATION_RECEIPT_MISMATCH')
    for key in ('dataManifestSha256','selectionSha256','observationsSha256',
                'historicalReproduction','independentDataEvaluation'):
        require(type(report.get(key)) is type(frozen['receipt'][key]) and
                report.get(key)==frozen['receipt'][key],'EVALUATION_REPORT_ROLE')
    require(report.get('reportPayloadSha256')==seal(report),'EVALUATION_REPORT_PAYLOAD')
