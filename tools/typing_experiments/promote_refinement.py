#!/usr/bin/env python3
"""Package a source-bound evaluation, or export disclosed artifacts for review only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import independent_corpus_guard as registry_guard
import refinement_evaluation_receipt as evaluation_receipt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/typing-refinement'
ASSETS=ROOT/'app/src/main/assets/smarttyping/experiments'


def require(condition,code):
    if not condition:raise ValueError(code)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def validate_tree(raw,expected_features):
    # Match ObliviousTreeRanker.decode bounds without its optional host libraries.
    require(20<=len(raw)<=65536 and raw[:4]==b'RET2','PROMOTION_TREE_FORMAT')
    valid=lambda value:math.isfinite(value) and abs(value)<=32
    try:
        features,count,scale,bias=struct.unpack_from('<IIff',raw,4)
        require(features==expected_features and 1<=count<=128 and valid(scale) and valid(bias),
                'PROMOTION_TREE_STRUCTURE')
        offset=20
        for _ in range(count):
            depth,=struct.unpack_from('<I',raw,offset);offset+=4
            require(1<=depth<=6,'PROMOTION_TREE_STRUCTURE')
            for _ in range(depth):
                index,border=struct.unpack_from('<If',raw,offset);offset+=8
                require(index<features and valid(border),'PROMOTION_TREE_STRUCTURE')
            leaves=struct.unpack_from('<'+'f'*(1<<depth),raw,offset);offset+=4*(1<<depth)
            require(all(valid(value) for value in leaves),'PROMOTION_TREE_STRUCTURE')
        require(offset==len(raw),'PROMOTION_TREE_STRUCTURE')
    except struct.error as error:raise ValueError('PROMOTION_TREE_STRUCTURE') from error


def prepare_request(source=OUT,output=None,historical_reproduction=False):
    snapshot=registry_guard.begin(historical_reproduction)
    source=Path(source).resolve()
    require(source.is_relative_to(ROOT/'build'),'PROMOTION_SOURCE_ROOT')
    if historical_reproduction:
        require(output is not None,'HISTORICAL_REVIEW_OUTPUT_REQUIRED')
        output=Path(output)
        require(not output.is_symlink() and not output.exists() and
                output.resolve().is_relative_to(ROOT/'build'),'FRESH_REVIEW_OUTPUT_REQUIRED')
        output=output.resolve()
    else:
        require(output is None,'PACKAGED_PROMOTION_OUTPUT_FIXED')
        output=ASSETS

    inputs={}
    def read(name):
        path=source/name
        require(not path.is_symlink() and path.resolve().is_relative_to(source),'PROMOTION_INPUT_PATH')
        raw=path.read_bytes();inputs[name]=raw
        return raw

    selection_raw=read('selection.json');selection=json.loads(selection_raw)
    evaluation=json.loads(read('test-report.json'));manifest_raw=read('data/manifest.json')
    manifest=json.loads(manifest_raw)
    require(evaluation.get('selectionSha256')==sha(selection_raw),'PROMOTION_SELECTION_BINDING')
    require(selection.get('selectionFrozenBeforeTest') is True and
            type(selection.get('blendGain')) in (int,float) and selection['blendGain']==1,
            'PROMOTION_FROZEN_SELECTION')
    require(manifest.get('containsPersonalMessages') is False,'PROMOTION_PUBLIC_DATA')
    if not historical_reproduction:
        require(evaluation.get('dataManifestSha256')==sha(manifest_raw) and
                evaluation.get('independentDataEvaluation') is True and
                evaluation.get('evaluationBinding',{}).get('legacyRegressionBound') is True,
                'PROMOTION_INDEPENDENT_DATA_REQUIRED')
        require(manifest.get('historicalReproduction') is False and
                manifest.get('registryBindings')==snapshot['registryBindings'],'PROMOTION_REGISTRY_BINDING')
        rows=[]
        for part in ('train','dev','test'):
            name=part+'-rows.jsonl';raw=read('data/'+name)
            require(sha(raw)==manifest['files'].get(name),'PROMOTION_ROW_IDENTITY')
            rows.extend(json.loads(line) for line in raw.decode().splitlines())
        registry_guard.finish(snapshot,rows)
    elif 'dataManifestSha256' in evaluation:
        require(evaluation['dataManifestSha256']==sha(manifest_raw),'PROMOTION_DATA_BINDING')
    frozen_evaluation=None
    if not historical_reproduction or 'evaluationBinding' in evaluation:
        baseline_tree=ROOT/'tools/typing_experiments/baseline/ru-ranker.bin'
        recorded=evaluation.get('evaluationBinding',{})
        legacy=evaluation_receipt.legacy_root(ROOT,recorded['legacyRoot']) if recorded.get('legacyRoot') is not None else None
        frozen_evaluation=evaluation_receipt.freeze(source,historical_reproduction,ROOT,
            (baseline_tree,ASSETS/'ru-context.bin'),legacy,recorded.get('legacyRowLimit'))
        evaluation_receipt.verify_report(evaluation,frozen_evaluation)
    blobs={}
    for key,directory in [('ranker','ranker'),('neural','neural')]:
        name=selection.get(key)
        require(isinstance(name,str) and re.fullmatch('[A-Za-z0-9_-]+',name) is not None,'PROMOTION_MODEL_NAME')
        raw=read(directory+'/'+name+'.bin')
        require(sha(raw)==selection.get(key+'Sha256'),'PROMOTION_MODEL_IDENTITY')
        blobs[key]=raw
    require(blobs['ranker'][:4]==b'RET2','PROMOTION_TREE_FORMAT')
    return dict(source=source,output=output,selection=selection,evaluation=evaluation,manifest=manifest,
                dataManifestSha256=sha(manifest_raw),blobs=blobs,inputs=inputs,
                historicalReproduction=historical_reproduction,registrySnapshot=snapshot,
                frozenEvaluation=frozen_evaluation)


def verify_request(request):
    if request['frozenEvaluation'] is not None:evaluation_receipt.verify(request['frozenEvaluation'])
    for name,raw in request['inputs'].items():
        path=request['source']/name
        require(not path.is_symlink() and path.resolve().is_relative_to(request['source']) and
                path.read_bytes()==raw,'PROMOTION_INPUT_DRIFT')
    if request['registrySnapshot'] is not None:
        current=registry_guard.begin(False)
        require(current['registryBindings']==request['registrySnapshot']['registryBindings'],
                'PROMOTION_REGISTRY_DRIFT')


def promote(source=OUT,output=None,historical_reproduction=False):
    request=prepare_request(source,output,historical_reproduction)
    # Heavy libraries are unnecessary for default refusal or receipt validation.
    import rank_refinement as rank
    import neural_refinement as neural
    validate_tree(request['blobs']['ranker'],rank.FEATURES)
    selection=request['selection'];evaluation=request['evaluation'];manifest=request['manifest']
    source_tree=request['source']/'ranker'/f"{selection['ranker']}.bin"
    source_network=request['source']/'neural'/f"{selection['neural']}.bin"
    network=neural.load_model(source_network)
    require(network.window==48,'PROMOTION_NETWORK_WINDOW')
    old_raw=(ASSETS/'ru-context.bin').read_bytes()
    legacy=json.loads((Path(__file__).parent/'baseline/provenance.json').read_text())
    require(sha(old_raw)==legacy['assetSha256']['ru-context.bin'],'PROMOTION_BASELINE_IDENTITY')
    old=neural.load_model(ASSETS/'ru-context.bin')
    payloads={'ru-ranker.bin':request['blobs']['ranker'],'ru-ranking-context.bin':request['blobs']['neural'],
              'ru-context.bin':old_raw}
    identities={name:dict(bytes=len(raw),sha256=sha(raw)) for name,raw in payloads.items()}
    lines=['package io.github.mesteriis.rune.keyboard.smarttyping.experiments','',
           '/** Frozen public-only experiment assets; see tools/typing_experiments/README.md. */',
           'internal object FrozenExperimentAssets {']
    for key,name in [('RANK','ru-ranker.bin'),('CONTEXT','ru-context.bin'),('RANKING_CONTEXT','ru-ranking-context.bin')]:
        lines.extend([f'    const val {key}_BYTES = {identities[name]["bytes"]}',
                      f'    const val {key}_SHA256 = "{identities[name]["sha256"]}"'])
    fixtures=[]
    for context,word in [('это','слово'),('мы идем','домой'),('привет','мир'),('','я')]:
        candidate=dict(text=word,unitDistance=1,frequencyRank=300,editCost=1.,isFallback=False);original=word+'а'
        score=.8*math.tanh(rank.tree_score(request['blobs']['ranker'],rank.features(context,original,candidate))/4)
        letters=neural.probabilities(old,context+' '+word)[1:];total=float(letters.sum())
        require(math.isfinite(total) and total>0,'PROMOTION_PARITY_FINITE')
        letters/=total;context_score=neural.context_score(network,context,word)
        require(all(math.isfinite(float(value)) for value in [score,context_score,*letters]),'PROMOTION_PARITY_FINITE')
        fixtures.append('\t'.join([context,original,word,str(score),str(context_score),','.join(map(str,letters))]))
    provenance={'schemaVersion':2,'experimental':True,'productionQualified':False,'privateDataUsed':False,
        'assets':identities,'source':{k:manifest[k] for k in ['sourceRepository','sourceRevision','sourcePath','sourceSha256','license','frequencySha256']},
        'data':{p:{k:v for k,v in counts.items() if k!='articles'} for p,counts in manifest['partitions'].items()},
        'dataFileSha256':manifest['files'],'dataManifestSha256':request['dataManifestSha256'],
        'selected':selection,'evaluation':evaluation,'historicalReproduction':historical_reproduction,
        'baselineTapModel':'Unchanged REC1 asset; provenance in tools/typing_experiments/baseline/provenance.json',
        'runtime':'RET2 95 features 128 depth-5 numeric symmetric trees; REC2 48-character 48-hidden; no Android ML framework',
        'independentQualification':False,'scope':'Historical review export only; no APK mutation.' if historical_reproduction else 'Experimental manual ranking; no automatic-edit qualification.',
        'trainingScripts':{p.name:rank.sha(p) for p in Path(__file__).parent.glob('*refinement.py')}}
    payloads['FrozenExperimentAssets.kt']='\n'.join(lines+['}','']).encode()
    payloads['parity.tsv']=('\n'.join(fixtures)+'\n').encode()
    payloads['provenance.json']=(json.dumps(provenance,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    # Recheck source artifacts before the first mutation; failed parity leaves no output.
    verify_request(request)
    require((ASSETS/'ru-context.bin').read_bytes()==old_raw,'PROMOTION_BASELINE_DRIFT')
    if historical_reproduction:
        request['output'].mkdir(parents=True,exist_ok=False)
    for name,raw in payloads.items():
        target=request['output']/name
        if not historical_reproduction:
            if name=='FrozenExperimentAssets.kt':target=ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments'/name
            if name=='parity.tsv':target=Path(__file__).parent/name
        target.write_bytes(raw)
    return provenance


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=OUT)
    parser.add_argument('--historical-reproduction',action='store_true')
    parser.add_argument('--output',type=Path,help='Fresh build directory, required for historical review export.')
    args=parser.parse_args()
    promote(args.source_root,args.output,args.historical_reproduction)


if __name__=='__main__':main()
