"""Bind current joint editor replay and data roles; disclosed metrics cannot qualify."""
import base64
import json
import math
from pathlib import Path
import sys

import independent_corpus_guard as guard
import refinement_evaluation_receipt as shared

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PIPELINE=ROOT/'tools/eval/smart-typing-0.3/pipeline'
old_path=sys.path[:]
try:
    sys.path.insert(0,str(PIPELINE))
    import evaluate_distance_one_policy as editor
finally:sys.path[:]=old_path
require=shared.require
sha=shared.sha


def editor_metrics(rows,baseline,product):
    result={band:dict(rows=0,inputChanges=0,controlChangesExact=0,prefixChanges=0,undoTextFailures=0,
        undoCaretFailures=0,undoCompositionDifferences=0,expectedCaseOrLayoutMismatches=0,
        baselineControlChangesExact=0,introducedControlChangesExact=0,introducedCaseOrLayoutMismatches=0) for band in ('short','long')}
    for row,left,right in zip(rows,baseline,product,strict=True):
        require(type(row.get('noAuto')) is bool and isinstance(row.get('family'),str) and bool(row['family']),
                'JOINT_ROW_LABEL')
        require(row.get('split')=='holdout' and row.get('language')=='ru','JOINT_HOLDOUT_SCOPE')
        for observed in (left,right):
            require(observed.get('status')=='COMPLETE','JOINT_INCOMPLETE')
            editor.validate_editor(row,observed)
        value=result['short' if len(row['typed'])<=4 else 'long'];value['rows']+=1
        prefix=(row['prefix']+' ' if row['prefix'] else '')
        before=right['beforeBoundary'];after=right['afterBoundary'];undo=right['afterBackspace']
        changed=after['text']!=before['text']+' '
        value['inputChanges']+=left['inputChangedByTyping'] or right['inputChangedByTyping']
        value['controlChangesExact']+=row['noAuto'] and changed
        value['baselineControlChangesExact']+=row['noAuto'] and left['afterBoundary']['text']!=left['beforeBoundary']['text']+' '
        value['introducedControlChangesExact']+=row['noAuto'] and changed and after['text']!=left['afterBoundary']['text']
        value['prefixChanges']+=not after['text'].startswith(prefix)
        value['undoTextFailures']+=changed and undo['text']!=before['text']
        value['undoCaretFailures']+=changed and undo['caret']!=before['caret']
        value['undoCompositionDifferences']+=changed and (undo['composingStart'],undo['composingEnd'])!=(before['composingStart'],before['composingEnd'])
        expected=row.get('expectedSpelling',row['typed'])
        lexical=after['text'].rstrip().split()[-1] if after['text'].split() else ''
        mismatch=changed and lexical.casefold()==expected.casefold() and after['text']!=prefix+expected+' '
        value['expectedCaseOrLayoutMismatches']+=mismatch
        value['introducedCaseOrLayoutMismatches']+=mismatch and after['text']!=left['afterBoundary']['text']
    for value in result.values():
        # Undo's text/caret contract is mandatory. Composition differences are disclosed separately.
        value['passed']=not any(value[key] for key in value if key not in ('rows','undoCompositionDifferences','controlChangesExact','baselineControlChangesExact','expectedCaseOrLayoutMismatches'))
    return result


def thresholds(value):
    result=[]
    for key in ('minimumScore','minimumMargin'):
        number=value.get(key)
        require(type(number) in (int,float) and math.isfinite(number),'JOINT_POLICY_THRESHOLD')
        result.append(float(number))
    return result


def capture_replay(rows_path,rows_raw,rows,path,observations,read,declared,files,project,role):
    directory=path.parent;receipt=json.loads(read(directory/'receipt.json',role+'/receipt',directory))
    require(receipt.get('schemaVersion')==2 and receipt.get('status')=='COMPLETE' and
            type(receipt.get('exitCode')) is int and receipt['exitCode']==0 and
            receipt.get('opaqueControllerIds') is True and receipt.get('inputFieldsSent')==['id','split','language','prefix','typed'],
            'BOUND_JOINT_REPLAY_REQUIRED')
    require(receipt.get('rowsSha256')==sha(rows_raw) and receipt.get('observationsSha256')==sha(files[path]),'JOINT_REPLAY_ROWS')
    require(bool(receipt.get('files')) and bool(receipt.get('outputBindings')),'JOINT_REPLAY_SCOPE')
    for index,(name,digest) in enumerate(sorted(receipt['files'].items())):
        require(sha(declared(name,f'{role}/input-{index}'))==digest,'JOINT_REPLAY_INPUT_IDENTITY')
    mandatory=[project/'tools/typing_experiments/replay_joint_correction.py',rows_path,
               *sorted(p for p in (project/'app/src/main/assets').rglob('*') if p.is_file())]
    require(all(p in files and receipt['files'].get(str(p.relative_to(project)))==sha(files[p]) for p in mandatory),
            'JOINT_REPLAY_RESOURCE_SCOPE')
    require(receipt.get('runnerSha256')==sha(files[mandatory[0]])==sha((HERE/'replay_joint_correction.py').read_bytes()),'JOINT_REPLAY_RUNNER')
    manifest_path=project/'tools/eval/smart-typing-0.3/pipeline/final_product_replay_sources.json'
    require(manifest_path in files,'JOINT_REPLAY_SOURCE_SCOPE')
    declared_sources=json.loads(files[manifest_path])['sources']+[
        'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/TypingDiagnostics.kt',
        'tools/eval/smart-typing-0.3/pipeline/FinalProductSpellingReplay.kt']
    require(all(project/n in files for n in declared_sources) and receipt.get('sources')==
            {n:sha(files[project/n]) for n in declared_sources},'JOINT_REPLAY_SOURCE_SCOPE')
    for index,(name,digest) in enumerate(sorted(receipt['outputBindings'].items())):
        require(Path(name).name==name,'JOINT_REPLAY_OUTPUT_PATH')
        require(sha(read(directory/name,f'{role}/output-{index}',directory))==digest,'JOINT_REPLAY_OUTPUT_IDENTITY')
    for name in ('observations.jsonl','controller-observations.jsonl','inputs.tsv','input-identities.jsonl',
                 'compile.log','final-product-spelling-replay.jar'):
        require(name in receipt['outputBindings'],'JOINT_REPLAY_OUTPUT_SCOPE')
    require(receipt.get('jarSha256')==receipt['outputBindings']['final-product-spelling-replay.jar'],'JOINT_REPLAY_JAR')
    identities=[json.loads(x) for x in files[directory/'input-identities.jsonl'].decode().splitlines()]
    raw_observed=[json.loads(x) for x in files[directory/'controller-observations.jsonl'].decode().splitlines()]
    observed=observations
    require(len(identities)==len(rows)==len(raw_observed),'JOINT_REPLAY_IDENTITY_MAP')
    lines=files[directory/'inputs.tsv'].decode().splitlines();require(len(lines)==len(rows),'JOINT_REPLAY_ENVELOPE')
    enc=lambda value:base64.b64encode(value.encode()).decode('ascii')
    for i,(row,identity,raw,normalized,line) in enumerate(zip(rows,identities,raw_observed,observed,lines,strict=True)):
        opaque=f'joint-replay-{i:08d}'
        require(identity==dict(index=i,id=opaque,sourceId=row['id']) and raw.get('id')==opaque and
                type(raw.get('index')) is int and raw['index']==i and json.dumps(dict(raw,id=row['id']),sort_keys=True,allow_nan=False)==json.dumps(normalized,sort_keys=True,allow_nan=False),
                'JOINT_REPLAY_IDENTITY_MAP')
        require(line=='\t'.join([str(i),enc(opaque),row['split'],row['language'],enc(row['prefix']),enc(row['typed'])]),
                'JOINT_REPLAY_ENVELOPE')
    return receipt


def freeze(rows_path,baseline_path,product_path,policy_path,historical_reproduction=False,
           project_root=ROOT,short_policy_path=None,corpus_manifest_path=None):
    snapshot=guard.begin(historical_reproduction);project=Path(project_root).resolve()
    files={};boundaries={};bindings={}
    def read(path,key,boundary):
        path=Path(path)
        require(path.is_absolute() and not path.is_symlink() and path.resolve().is_relative_to(boundary),'EVALUATION_INPUT_PATH')
        raw=path.read_bytes();files[path]=raw;boundaries[path]=boundary;bindings[key]=sha(raw);return raw
    def resolve(name):return Path(name) if Path(name).is_absolute() else project/name
    def declared(name,key):
        path=resolve(name);return read(path,key,project if path.resolve().is_relative_to(project) else path.parent.resolve())
    paths=[Path(p).resolve() for p in (rows_path,baseline_path,product_path,policy_path)]
    rows_raw,baseline_raw,product_raw,policy_raw=[read(p,n,project/'build') for p,n in zip(paths,('rows','baseline','product','policy'),strict=True)]
    rows=[json.loads(x) for x in rows_raw.decode().splitlines()]
    baseline=[json.loads(x) for x in baseline_raw.decode().splitlines()]
    product=[json.loads(x) for x in product_raw.decode().splitlines()];policy=json.loads(policy_raw)
    require(bool(rows) and len({r['id'] for r in rows})==len(rows) and
            [r['id'] for r in rows]==[r['id'] for r in baseline]==[r['id'] for r in product],'IDENTITY')
    require((policy.get('stage')=='frozen-before-independent-holdout' or
             historical_reproduction and policy.get('stage')=='historical-disclosed-calibration') and policy.get('holdoutSha256')==sha(rows_raw),
            'FROZEN_HOLDOUT_IDENTITY')
    receipts={}
    for role,path in [('baseline',paths[1]),('product',paths[2])]:
        receipts[role]=capture_replay(paths[0],rows_raw,rows,path,baseline if role=='baseline' else product,
            read,declared,files,project,role)
    short_policy=None
    if short_policy_path is not None:
        short_policy=json.loads(read(Path(short_policy_path).resolve(),'short-policy',project/'build'))
        require(policy.get('shortPolicySha256')==sha(files[Path(short_policy_path).resolve()]),'JOINT_SHORT_POLICY_IDENTITY')
    spec=policy['thresholds'];short=spec.get('short') or (short_policy or {}).get('thresholds',{}).get('short')
    require(short is not None,'JOINT_SHORT_POLICY_REQUIRED')
    long=spec.get('long',{})
    acquisition=spec.get('acquisition') or long.get('acquisition') or long
    retention=spec.get('retention') or long.get('retention') or acquisition
    expected=thresholds(short)+thresholds(acquisition)+thresholds(retention)
    receipt=receipts['product'];assets=project/'app/src/main/assets/smarttyping/experiments'
    if receipt['mode']=='joint-ready':
        config_hash=receipt.get('configSha256');configs=[raw for path,raw in files.items() if sha(raw)==config_hash]
        require(bool(config_hash) and bool(configs),'JOINT_CONFIG_BINDING')
        config=configs[0].decode().strip().split('\t');require(len(config) in (6,8),'JOINT_CONFIG_BINDING')
        require(config[1]==policy['modelSha256'] and sha(files[Path(config[0]).resolve()])==policy['modelSha256'],'JOINT_POLICY_MODEL')
        actual=list(map(float,config[2:]));actual=actual+actual[-2:] if len(actual)==4 else actual
    elif receipt['mode']=='joint-production':
        meta=json.loads(read(assets/'joint-correction-provenance.json','execution/packaged-policy',project))
        require(sha(files[assets/'ru-joint-ranker.bin'])==policy['modelSha256']==meta['model']['sha256'],'JOINT_POLICY_MODEL')
        actual=thresholds(meta['short']['thresholds'])+thresholds(meta['long']['thresholds']['acquisition'])+thresholds(meta['long']['thresholds']['retention'])
    else:raise ValueError('JOINT_POLICY_MODE')
    require(actual==expected,'JOINT_POLICY_THRESHOLDS')
    require(sha(files[assets/'ru-ranking-context.bin'])==policy['contextSha256'],'JOINT_POLICY_CONTEXT')
    if corpus_manifest_path is not None:
        path=Path(corpus_manifest_path).resolve();raw=read(path,'corpus/manifest',project/'build');manifest=json.loads(raw)
        require(sha(raw)==policy.get('corpusManifestSha256',policy.get('corpusSha256')),'JOINT_CORPUS_MANIFEST')
        for name,digest in manifest['files'].items():
            require(Path(name).name==name,'JOINT_CORPUS_PATH')
            require(sha(read(path.parent/name,'corpus/'+name,path.parent))==digest,'JOINT_CORPUS_IDENTITY')
        require(manifest['files'].get('holdout.jsonl')==sha(rows_raw),'JOINT_CORPUS_ROWS_IDENTITY')
        if snapshot is not None:
            require(manifest.get('containsPersonalMessages') is False and manifest.get('historicalReproduction') is False and
                    manifest.get('registryBindings')==snapshot['registryBindings'],'EVALUATION_REGISTRY_BINDING')
    else:require(historical_reproduction,'JOINT_CORPUS_MANIFEST_REQUIRED')
    role=guard.finish(snapshot,rows);registries=shared.current_registries(historical_reproduction)
    if snapshot is not None:require(registries==snapshot['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    code={str((HERE/n).relative_to(ROOT)):sha((HERE/n).read_bytes()) for n in (
        'joint_evaluation_receipt.py','evaluate_joint_product.py','evaluate_joint_followup.py','replay_joint_correction.py',
        'refinement_evaluation_receipt.py','independent_corpus_guard.py','public_corpus_preparation_v1.py')}
    for name in ('evaluate_distance_one_policy.py','final_product_replay.py'):
        code[str((PIPELINE/name).relative_to(ROOT))]=sha((PIPELINE/name).read_bytes())
    integrity=editor_metrics(rows,baseline,product)
    receipt=dict(schema='rune-joint-evaluation-v1',historicalReproduction=historical_reproduction,
        independentDataEvaluation=not historical_reproduction,corpusRole=role['scope'],
        inputBindings=bindings,sourceBindings=code,registryBindings=registries,
        executionThresholds=actual,policySha256=sha(policy_raw),rowsSha256=sha(rows_raw))
    return dict(files=files,boundaries=boundaries,receipt=receipt,rows=rows,baseline=baseline,product=product,editorIntegrity=integrity)


def finish_report(frozen,result,observed_gate):
    require(type(observed_gate) is bool,'JOINT_GATE_BOOLEAN')
    numerical=observed_gate;observed_gate=observed_gate and all(v['passed'] for v in frozen['editorIntegrity'].values())
    result.update(numericalGatePassed=numerical,historicalReproduction=frozen['receipt']['historicalReproduction'],
        independentDataEvaluation=frozen['receipt']['independentDataEvaluation'],corpusRole=frozen['receipt']['corpusRole'],
        observedGatePassed=observed_gate,passed=observed_gate and frozen['receipt']['independentDataEvaluation'],
        editorIntegrity=frozen['editorIntegrity'],evaluationBinding=frozen['receipt'])
    shared.verify(frozen);result['reportPayloadSha256']=shared.seal(result);return result


def verify_report(report,frozen):
    require(report.get('evaluationBinding')==frozen['receipt'],'EVALUATION_RECEIPT_MISMATCH')
    for key in ('historicalReproduction','independentDataEvaluation','corpusRole'):
        require(type(report.get(key)) is type(frozen['receipt'][key]) and report.get(key)==frozen['receipt'][key],
                'EVALUATION_REPORT_ROLE')
    require(report.get('reportPayloadSha256')==shared.seal(report),'EVALUATION_REPORT_PAYLOAD')
