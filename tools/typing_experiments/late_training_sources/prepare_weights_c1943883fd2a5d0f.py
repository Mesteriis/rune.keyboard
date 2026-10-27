from pathlib import Path
import collections,hashlib,json,sys
import numpy as np
sys.path.insert(0,'tools/typing_experiments')
from right_context_training_weights import strong_supervision_weight
root=Path(__file__).parent
inputs=Path('build/right-context-oblique-v12-inputs-20261027')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prepared=json.loads((inputs/'feature-preparation.json').read_text())
assert sha(inputs/'groups.jsonl')==prepared['groupsSha256']
assert sha(inputs/'train-group-weights.npy')==prepared['weightsSha256']
groups=[json.loads(line) for line in (inputs/'groups.jsonl').read_text().splitlines()]
old=np.load(inputs/'train-group-weights.npy');weights=np.empty_like(old)
counts=collections.Counter();sums=collections.defaultdict(lambda:dict(previous=0.,updated=0.))
offset=0
for group in groups:
 row=group['row'];n=len(group['candidates'])
 previous=3. if row['kind']=='unknown_original' and row['applied']!=row['original'] and row['expectedApplied']!=row['applied'] else 1.
 assert np.all(old[offset:offset+n]==previous)
 updated=strong_supervision_weight(row);weights[offset:offset+n]=updated
 intent=row['kind']
 if intent=='unknown_original':
  intent='raw_acquisition' if row['applied']==row['original'] else 'retain_correct_applied' if row['expectedApplied']==row['applied'] else 'repair_wrong_applied'
 counts[intent]+=1;sums[intent]['previous']+=previous;sums[intent]['updated']+=updated
 if previous!=updated:counts['changedGroups']+=1
 offset+=n
assert offset==len(old)==503679 and counts['changedGroups']==9146
assert all(sums[intent]['updated']==13719 for intent in ('raw_acquisition','retain_correct_applied','repair_wrong_applied'))
assert np.isfinite(weights).all() and np.all((weights==1.)|(weights==3.))
np.save(root/'balanced-group-weights.npy',weights)
report=dict(purpose='WEIGHT_ONLY_ABLATION_NO_DATA_FEATURE_LABEL_CHANGES',policy='symmetric-strong-intents-v1',
 groups=len(groups),candidateRows=len(old),counts=dict(counts),groupWeightSums=dict(sums),
 groupsSha256=sha(inputs/'groups.jsonl'),previousWeightsSha256=sha(inputs/'train-group-weights.npy'),weightsSha256=sha(root/'balanced-group-weights.npy'),
 previousVectorsSha256=sha(inputs/'train-vectors.npz'),
 sourceHashes={str(p):sha(p) for p in [Path(__file__),Path('tools/typing_experiments/right_context_training_weights.py')]})
(root/'weight-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'sourceHashes'}}))
