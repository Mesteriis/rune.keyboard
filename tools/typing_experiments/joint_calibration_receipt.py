"""Bind calibration inputs and data role; never promote disclosed calibration."""
import hashlib
import json
import math
from pathlib import Path

import independent_corpus_guard as guard
import refinement_evaluation_receipt as shared
import joint_evaluation_receipt as editor_binding
from holdout_ledger import keys_for

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
require=shared.require
sha=shared.sha


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_rows(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def inputs(project):
    frozen=dict(files={},boundaries={},bindings={})
    def read(path,key,boundary):
        path=Path(path)
        require(path.is_absolute() and not path.is_symlink() and path.resolve().is_relative_to(boundary),'CALIBRATION_INPUT_PATH')
        raw=path.read_bytes()
        require(path not in frozen['files'] or frozen['files'][path]==raw,'CALIBRATION_CAPTURE_DRIFT')
        frozen['files'][path]=raw;frozen['boundaries'][path]=boundary;frozen['bindings'][key]=sha(raw);return raw
    def declared(name,key):
        path=Path(name) if Path(name).is_absolute() else project/name
        return read(path,key,project if path.resolve().is_relative_to(project) else path.parent.resolve())
    return frozen,read,declared


def code_bindings():
    names=('joint_calibration_receipt.py','calibrate_joint_source.py','calibrate_joint_followup.py','calibrate_joint_rescue.py',
        'joint_evaluation_receipt.py','replay_joint_correction.py','train_joint_correction.py','rank_refinement.py','train.py',
        'neural_refinement.py','abstaining_ranker.py','refinement_evaluation_receipt.py','independent_corpus_guard.py',
        'public_corpus_preparation_v1.py','requirements.txt','promote_refinement.py')
    result={str((HERE/n).relative_to(ROOT)):file_hash(HERE/n) for n in names}
    for n in ('evaluate_distance_one_policy.py','final_product_replay.py'):
        p=editor_binding.PIPELINE/n;result[str(p.relative_to(ROOT))]=file_hash(p)
    return result


def receipt(frozen,kind,historical,role,extra=None):
    registries=shared.current_registries(historical)
    if not historical:require(registries==role['registryBindings'],'EVALUATION_REGISTRY_DRIFT')
    frozen['receipt']=dict(schema='rune-joint-calibration-v1',kind=kind,historicalReproduction=historical,
        independentQualification=False,productionQualified=False,corpusRole=role['scope'],
        inputBindings=frozen['bindings'],registryBindings=registries,sourceBindings=code_bindings(),**(extra or {}))
    return frozen


def freeze_training(corpus,train_export,calibration_export,snapshot,project_root=ROOT):
    """Bind independent training inputs and real replay before model fitting."""
    require(snapshot is not None,'TRAINING_REGISTRY_REQUIRED')
    project=Path(project_root).resolve()
    corpus,train_export,calibration_export=[Path(p).resolve() for p in (corpus,train_export,calibration_export)]
    frozen,read,declared=inputs(project)
    raw_manifest=read(corpus/'manifest.json','corpus/manifest',project/'build')
    manifest=json.loads(raw_manifest)
    require(manifest.get('containsPersonalMessages') is False and manifest.get('historicalReproduction') is False and
            manifest.get('registryBindings')==snapshot['registryBindings'],'TRAINING_REGISTRY_BINDING')
    require({'train.jsonl','calibration.jsonl','holdout.jsonl'}<=set(manifest.get('files',{})),'TRAINING_CORPUS_SCOPE')
    for name,digest in manifest['files'].items():
        require(Path(name).name==name and name.endswith('.jsonl'),'TRAINING_CORPUS_PATH')
        require(sha(read(corpus/name,'corpus/'+name,corpus))==digest,'TRAINING_CORPUS_IDENTITY')
    partitions={};observations={}
    for part,export in (('train',train_export),('calibration',calibration_export)):
        rows_path=corpus/(part+'.jsonl');raw=frozen['files'][rows_path]
        rows=[json.loads(x) for x in raw.decode().splitlines()]
        require(bool(rows) and len({r['id'] for r in rows})==len(rows),'TRAINING_ROW_IDENTITY')
        require(all(r.get('split')==part and r.get('language')=='ru' and type(r.get('noAuto')) is bool and
                    isinstance(r.get('family'),str) and bool(r['family']) for r in rows),'TRAINING_ROW_SCOPE')
        observed_path=export/'observations.jsonl'
        observed=[json.loads(x) for x in read(observed_path,part+'/observations',project/'build').decode().splitlines()]
        require([r['id'] for r in rows]==[o.get('id') for o in observed],'TRAINING_ROW_IDENTITY')
        replay=editor_binding.capture_replay(rows_path,raw,rows,observed_path,observed,read,declared,frozen['files'],project,part+'/replay')
        require(replay.get('mode')=='joint-export','TRAINING_REPLAY_MODE')
        for row,observation in zip(rows,observed,strict=True):editor_binding.editor.validate_editor(row,observation)
        partitions[part]=rows;observations[part]=observed
    for axis in ('article','sentence','context','family'):
        require(not (keys_for(partitions['train'],axis)&keys_for(partitions['calibration'],axis)),
                'TRAINING_PARTITION_OVERLAP')
    combined=partitions['train']+partitions['calibration']
    require(len({r['id'] for r in combined})==len(combined),'TRAINING_ROW_IDENTITY')
    role=guard.finish(snapshot,combined)
    receipt(frozen,'training',False,role,dict(corpusManifestSha256=sha(raw_manifest),
        holdoutSha256=manifest['files']['holdout.jsonl']))
    context=project/'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin'
    read(context,'model/context',project)
    frozen.update(partitions=partitions,observations=observations,manifest=manifest,context=context)
    shared.verify(frozen)
    return frozen


def freeze(kind,ranker,corpus,export,parent_policy,historical_reproduction=False,project_root=ROOT):
    snapshot=guard.begin(historical_reproduction);project=Path(project_root).resolve()
    require(kind in ('source','followup'),'CALIBRATION_KIND')
    ranker,corpus,export,parent_policy=[Path(p).resolve() for p in (ranker,corpus,export,parent_policy)]
    frozen,read,declared=inputs(project)
    raw_manifest=read(corpus/'manifest.json','corpus/manifest',project/'build');manifest=json.loads(raw_manifest)
    require({'calibration.jsonl','holdout.jsonl'}<=set(manifest['files']),'CALIBRATION_CORPUS_SCOPE')
    for name,digest in manifest['files'].items():
        require(Path(name).name==name and name.endswith('.jsonl'),'CALIBRATION_CORPUS_PATH')
        require(sha(read(corpus/name,'corpus/'+name,corpus))==digest,'CALIBRATION_CORPUS_IDENTITY')
    raw_rows=frozen['files'][corpus/'calibration.jsonl'];rows=[json.loads(x) for x in raw_rows.decode().splitlines()]
    require(bool(rows) and len({r['id'] for r in rows})==len(rows),'CALIBRATION_ROW_IDENTITY')
    for row in rows:
        require(row.get('split')=='calibration' and row.get('language')=='ru' and type(row.get('noAuto')) is bool and
                isinstance(row.get('family'),str) and bool(row['family']),'CALIBRATION_ROW_SCOPE')
    raw_parent=read(parent_policy,'parent/policy',project/'build');parent=json.loads(raw_parent)
    if 'calibrationBinding' in parent:verify_policy(parent)
    model=ranker/'joint-ranker.bin';context=project/'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin'
    require(sha(read(model,'model/ranker',project/'build'))==parent['modelSha256'],'CALIBRATION_MODEL_IDENTITY')
    require(sha(read(context,'model/context',project))==parent['contextSha256'],'CALIBRATION_CONTEXT_IDENTITY')
    if kind=='source':
        require(parent.get('corpusManifestSha256')==sha(raw_manifest) and
                parent.get('holdoutSha256')==manifest['files']['holdout.jsonl'],'CALIBRATION_PARENT_CORPUS')
    observed_path=export/'observations.jsonl';observed_raw=read(observed_path,'observations',project/'build')
    observations=[json.loads(x) for x in observed_raw.decode().splitlines()]
    require([r['id'] for r in rows]==[o.get('id') for o in observations],'CALIBRATION_ROW_IDENTITY')
    capture=editor_binding.capture_replay(corpus/'calibration.jsonl',raw_rows,rows,observed_path,observations,
        read,declared,frozen['files'],project,'calibration-replay')
    require(capture.get('mode')=='joint-export','CALIBRATION_REPLAY_MODE')
    for row,observed in zip(rows,observations,strict=True):editor_binding.editor.validate_editor(row,observed)
    if snapshot is not None:
        require(manifest.get('containsPersonalMessages') is False and manifest.get('historicalReproduction') is False and
                manifest.get('registryBindings')==snapshot['registryBindings'],'CALIBRATION_REGISTRY_BINDING')
    role=guard.finish(snapshot,rows)
    receipt(frozen,kind,historical_reproduction,role,dict(corpusManifestSha256=sha(raw_manifest),
        calibrationRowsSha256=sha(raw_rows),holdoutSha256=manifest['files']['holdout.jsonl'],
        parentPolicySha256=sha(raw_parent),scoring='recomputed from bound current observations and weights',
        parentTrainingRequalified=False))
    frozen.update(rows=rows,observations=observations,parent=parent,model=model,context=context,manifest=manifest)
    return frozen


def validate_scores(records,rows,observations):
    by_id={r['id']:r for r in rows};by_obs={o['id']:o for o in observations}
    require(bool(records) and len({r['id'] for r in records})==len(records),'CALIBRATION_SCORE_IDS')
    for record in records:
        require(record['id'] in by_id and record['id'] in by_obs,'CALIBRATION_SCORE_IDS')
        row=by_id[record['id']];observed=by_obs[record['id']]
        require(record.get('original')==row['typed'].casefold() and record.get('expected')==row.get('expectedSpelling',row['typed']).casefold() and
                record.get('family')==row['family'] and type(record.get('control')) is bool and record['control']==row['noAuto'] and
                record.get('band')==('short' if len(row['typed'])<=4 else 'long') and
                record.get('baseline')==observed['afterBoundary']['text'].rstrip().split()[-1].casefold(),'CALIBRATION_SCORE_ROW')
        pool=observed['jointSearch']['alternatives'];scores=record['scores']
        require(len(scores)==len(pool)+1 and len(scores)>=2,'CALIBRATION_SCORE_POOL')
        require(all(type(x) in (int,float) and math.isfinite(x) for x in scores),'CALIBRATION_SCORE_FINITE')
        order=sorted(range(len(scores)),key=lambda i:(-scores[i],i))
        require(all(type(record.get(key)) in (int,float) and math.isfinite(record[key]) for key in ('topScore','margin')) and
                record['topScore']==scores[order[0]] and record['margin']==scores[order[0]]-scores[order[1]],'CALIBRATION_SCORE_SUMMARY')


def seal_policy(frozen,policy,observed):
    require(type(observed) is bool,'CALIBRATION_GATE_BOOLEAN')
    policy.update(stage='historical-disclosed-calibration' if frozen['receipt']['historicalReproduction'] else 'frozen-before-independent-holdout',
        historicalReproduction=frozen['receipt']['historicalReproduction'],corpusRole=frozen['receipt']['corpusRole'],
        independentQualification=False,productionQualified=False,observedCalibrationPassed=observed,
        calibrationBinding=frozen['receipt'])
    shared.verify(frozen);policy['policyPayloadSha256']=shared.seal({k:v for k,v in policy.items() if k!='policyPayloadSha256'});return policy


def publish(frozen,output,policy,records,config=None):
    output=Path(output).resolve();project=ROOT
    require(output.is_relative_to(project/'build') and not output.exists() and not output.is_symlink(),'FRESH_CALIBRATION_OUTPUT')
    payloads={'frozen-policy.json':json.dumps(policy,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',
              'calibration-scores.json':json.dumps(records,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'}
    if config is not None:payloads['config.tsv']=config
    shared.verify(frozen);output.mkdir(parents=True,exist_ok=False)
    for name,text in payloads.items():
        with (output/name).open('x',encoding='utf-8') as stream:stream.write(text)


def verify_policy(policy,frozen=None):
    if frozen is not None:require(policy.get('calibrationBinding')==frozen['receipt'],'CALIBRATION_RECEIPT_MISMATCH')
    receipt=policy['calibrationBinding']
    for key in ('historicalReproduction','corpusRole','independentQualification','productionQualified'):
        require(type(policy.get(key)) is type(receipt[key]) and policy.get(key)==receipt[key],'CALIBRATION_POLICY_ROLE')
    require(policy.get('policyPayloadSha256')==shared.seal({k:v for k,v in policy.items() if k!='policyPayloadSha256'}),
            'CALIBRATION_POLICY_PAYLOAD')


def freeze_rescue(root,work,pins,model_pin,historical_reproduction=False,project_root=ROOT):
    guard.begin(historical_reproduction)
    require(historical_reproduction,'PINNED_RESCUE_IS_DISCLOSED_ONLY')
    project=Path(project_root).resolve();root=Path(root).resolve();work=Path(work).resolve()
    frozen,read,_=inputs(project)
    for name,digest in pins.items():require(sha(read(root/name,'pinned/'+name,project/'build'))==digest,'PUBLIC_CALIBRATION_IDENTITY')
    assets=project/'app/src/main/assets/smarttyping/experiments'
    provenance=json.loads(read(assets/'joint-rescue-provenance.json','reference/provenance',project))
    raw_policy=read(assets/'ru-joint-rescue-policy.json','reference/policy',project);published=json.loads(raw_policy)
    require(sha(raw_policy)==provenance['policy']['sha256'],'RESCUE_REFERENCE_POLICY')
    model=work/'rescue-model/ranker.bin';raw_model=read(model,'model/ranker',project/'build')
    require(sha(raw_model)==model_pin==published['modelSha256']==provenance['model']['sha256'],'MODEL_IDENTITY')
    for name,key in [('calibration-scores.json','secondaryCalibrationScoresSha256'),('receipt.json','trainingReceiptSha256')]:
        require(sha(read(work/'rescue-model'/name,'secondary/'+name,project/'build'))==published[key],'RESCUE_SECONDARY_IDENTITY')
    raw_holdout=read(work/'fresh-corpus/holdout.jsonl','corpus/holdout-hash-only',project/'build')
    require(sha(raw_holdout)==published['holdoutSha256'],'RESCUE_HOLDOUT_IDENTITY')
    morph=read(project/'app/src/main/assets/smarttyping/lexicon/ru.morph','model/morphology',project)
    # These legacy receipt bytes are historical references; their generator runtime is not requalified.
    read(root/'followup-calibration-export-v2/receipt.json','historical/export-receipt',project/'build')
    rows=[json.loads(x) for x in frozen['files'][root/'followup-corpus/calibration.jsonl'].decode().splitlines()]
    observed=[json.loads(x) for x in frozen['files'][root/'followup-calibration-export-v2/observations.jsonl'].decode().splitlines()]
    primary=json.loads(frozen['files'][root/'followup-policy-v2/calibration-scores.json'])
    secondary=json.loads(frozen['files'][work/'rescue-model/calibration-scores.json'])
    require(len({r['id'] for r in rows})==len(rows) and [r['id'] for r in rows]==[o['id'] for o in observed],
            'CALIBRATION_ROW_IDENTITY')
    validate_scores(primary,rows,observed);validate_scores(secondary,rows,observed)
    require([r['id'] for r in primary]==[r['id'] for r in secondary],'RESCUE_SCORE_IDS')
    role=guard.finish(None,rows)
    receipt(frozen,'rescue',True,role,dict(scoring='exact packaged-policy-pinned historical score vectors',
        originalGeneratorRuntimeVerified=False,parentTrainingRequalified=False,
        morphologySha256=sha(morph),holdoutSha256=sha(raw_holdout)))
    frozen.update(rows=rows,observations=observed,primary=primary,secondary=secondary,morphology=morph,published=published)
    return frozen
