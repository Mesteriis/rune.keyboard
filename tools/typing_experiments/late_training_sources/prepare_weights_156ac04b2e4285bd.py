from pathlib import Path
import collections,hashlib,json,math,sys
import numpy as np
sys.path[:0]=['tools/typing_experiments','tools/morphology']
from ranker import PymorphyLexicon
from right_context_signature_weights import TargetSignatureWeights,MAX_FACTOR
root=Path(__file__).parent
inputs=Path('build/right-context-oblique-v12-inputs-20261027')
previous=Path('build/right-context-symmetric-residual-v13-20261027')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prepared=json.loads((inputs/'feature-preparation.json').read_text())
frozen=json.loads((previous/'frozen-model.json').read_text())
assert sha(inputs/'groups.jsonl')==prepared['groupsSha256']==sha(previous/'groups.jsonl')
assert sha(previous/'train-group-weights.npy')==frozen['weightsSha256']
assert sha(inputs/'train-vectors.npz')==prepared['vectorsSha256']==sha(previous/'train-vectors.npz')
groups=[json.loads(line) for line in (inputs/'groups.jsonl').read_text().splitlines()]
rows=[g['row'] for g in groups]
lex=PymorphyLexicon(cache_size=16384)
assert lex.receipt()==json.loads((previous/'morphology-receipt.json').read_text())
policy=TargetSignatureWeights.fit(rows,lex)
old=np.load(previous/'train-group-weights.npy');weights=np.empty_like(old)
counts=collections.Counter();sums=collections.defaultdict(lambda:dict(previous=0.,updatedFloat32=0.))
strong_weights=[];offset=0
for group in groups:
 row=group['row'];n=len(group['candidates']);previous_weight=3. if row['kind']=='unknown_original' else 1.
 assert np.all(old[offset:offset+n]==previous_weight)
 updated=policy.weight(row,lex);weights[offset:offset+n]=updated
 intent=row['kind']
 if intent=='unknown_original':
  intent='raw_acquisition' if row['applied']==row['original'] else 'retain_correct_applied' if row['expectedApplied']==row['applied'] else 'repair_wrong_applied'
  strong_weights.append(updated)
 else:assert updated==1.
 counts[intent]+=1;sums[intent]['previous']+=previous_weight;sums[intent]['updatedFloat32']+=float(weights[offset])
 counts['changedGroups']+=int(float(weights[offset])!=previous_weight)
 offset+=n
assert offset==len(old)==503679 and counts['changedGroups']==13719
assert math.isclose(math.fsum(strong_weights),41157.,abs_tol=1e-9)
assert all(abs(sums[intent]['updatedFloat32']-13719.)<.01 for intent in ('raw_acquisition','retain_correct_applied','repair_wrong_applied'))
assert np.isfinite(weights).all() and np.all(weights>0) and np.max(weights)<=24.
np.save(root/'balanced-group-weights.npy',weights)
report=dict(purpose='WEIGHT_ONLY_TARGET_SIGNATURE_ABLATION',policy='target-pos-signature-sqrt-cap8-v1',
 maxUnnormalizedFactor=MAX_FACTOR,normalization=policy.normalization,
 signatures=[dict(parts=key,groups=count,unnormalizedFactor=factor,weight=3*factor/policy.normalization) for key,count,factor in policy.entries],
 groups=len(groups),candidateRows=len(old),counts=dict(counts),groupWeightSums=dict(sums),strongGroupWeightSumBeforeFloat32=math.fsum(strong_weights),
 groupsSha256=sha(inputs/'groups.jsonl'),previousWeightsSha256=sha(previous/'train-group-weights.npy'),weightsSha256=sha(root/'balanced-group-weights.npy'),
 previousVectorsSha256=sha(inputs/'train-vectors.npz'),dictionary=lex.receipt(),
 sourceHashes={str(p):sha(p) for p in [Path(__file__),Path('tools/typing_experiments/right_context_training_weights.py'),Path('tools/typing_experiments/right_context_signature_weights.py')]})
(root/'weight-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'sourceHashes','dictionary'}}))
