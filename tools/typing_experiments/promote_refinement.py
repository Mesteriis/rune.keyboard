#!/usr/bin/env python3
"""Promote the already-selected/evaluated public experiment; never choose on test results."""
from pathlib import Path
import json
import math
import rank_refinement as rank
import neural_refinement as neural
ROOT=rank.ROOT
OUT=ROOT/'build/typing-refinement'
ASSETS=ROOT/'app/src/main/assets/smarttyping/experiments'

def main():
    selection=json.loads((OUT/'selection.json').read_text());evaluation=json.loads((OUT/'test-report.json').read_text())
    assert evaluation['selectionSha256']==rank.sha(OUT/'selection.json')
    assert selection['selectionFrozenBeforeTest'] and selection['blendGain']==1
    source_tree=OUT/'ranker'/f"{selection['ranker']}.bin"
    source_network=OUT/'neural'/f"{selection['neural']}.bin"
    assert rank.sha(source_tree)==selection['rankerSha256'] and rank.sha(source_network)==selection['neuralSha256']
    assert source_tree.read_bytes()[:4]==b'RET2' and neural.load_model(source_network).window==48
    old=neural.load_model(ASSETS/'ru-context.bin')
    legacy=json.loads((Path(__file__).parent/'baseline/provenance.json').read_text())
    assert rank.sha(ASSETS/'ru-context.bin')==legacy['assetSha256']['ru-context.bin']
    (ASSETS/'ru-ranker.bin').write_bytes(source_tree.read_bytes())
    (ASSETS/'ru-ranking-context.bin').write_bytes(source_network.read_bytes())
    identities={p.name:{'bytes':p.stat().st_size,'sha256':rank.sha(p)} for p in [ASSETS/'ru-ranker.bin',ASSETS/'ru-context.bin',ASSETS/'ru-ranking-context.bin']}
    lines=['package io.github.mesteriis.rune.keyboard.smarttyping.experiments','','/** Frozen public-only experiment assets; see tools/typing_experiments/README.md. */','internal object FrozenExperimentAssets {']
    for key,name in [('RANK','ru-ranker.bin'),('CONTEXT','ru-context.bin'),('RANKING_CONTEXT','ru-ranking-context.bin')]:
        lines.extend([f'    const val {key}_BYTES = {identities[name]["bytes"]}',f'    const val {key}_SHA256 = "{identities[name]["sha256"]}"'])
    (ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/FrozenExperimentAssets.kt').write_text('\n'.join(lines+['}','']))
    network=neural.load_model(source_network);tree=source_tree.read_bytes();fixtures=[]
    for context,word in [('это','слово'),('мы идем','домой'),('привет','мир'),('','я')]:
        candidate=dict(text=word,unitDistance=1,frequencyRank=300,editCost=1.,isFallback=False);original=word+'а'
        score=.8*math.tanh(rank.tree_score(tree,rank.features(context,original,candidate))/4)
        letters=neural.probabilities(old,context+' '+word)[1:];letters/=letters.sum()
        fixtures.append('\t'.join([context,original,word,str(score),str(neural.context_score(network,context,word)),','.join(map(str,letters))]))
    (Path(__file__).parent/'parity.tsv').write_text('\n'.join(fixtures)+'\n')
    manifest=json.loads((OUT/'data/manifest.json').read_text())
    rank.write(ASSETS/'provenance.json',{'schemaVersion':2,'experimental':True,'productionQualified':False,'privateDataUsed':False,
        'assets':identities,'source':{k:manifest[k] for k in ['sourceRepository','sourceRevision','sourcePath','sourceSha256','license','frequencySha256']},
        'data':{p:{k:v for k,v in counts.items() if k!='articles'} for p,counts in manifest['partitions'].items()},
        'dataFileSha256':manifest['files'],'selected':selection,'evaluation':evaluation,
        'baselineTapModel':'Unchanged REC1 asset; provenance in tools/typing_experiments/baseline/provenance.json',
        'runtime':'RET2 95 features 128 depth-5 numeric symmetric trees; REC2 48-character 48-hidden; no Android ML framework',
        'scope':'Reorders manual alternatives only. Original and automatic-edit policy unchanged. Russian only. Both independent controls default off.',
        'trainingScripts':{p.name:rank.sha(p) for p in Path(__file__).parent.glob('*refinement.py')}})
if __name__=='__main__':main()
