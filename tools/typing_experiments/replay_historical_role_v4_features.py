"""Replay the bound historical role-v4 training features; never qualify a model."""
import argparse
from pathlib import Path
import sys,json,hashlib,functools
import numpy as np
sys.path.insert(0,'tools/typing_experiments')
import rank_refinement as rank, neural_refinement as neural
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures,role_revision_features,FEATURES
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
if not __debug__:
 raise RuntimeError('ROLE_REPLAY_REQUIRES_ASSERTIONS')
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
output=args.output.resolve()
if Path.cwd().resolve()!=ROOT or not output.is_relative_to(ROOT/'build') or output.exists():
 raise ValueError('ROLE_REPLAY_OUTPUT_OR_WORKDIR')
p=Path('build/right-context-training-v4-20261027');assets=Path('app/src/main/assets/smarttyping/experiments')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
f=json.loads((p/'frozen-model.json').read_bytes());plan=json.loads((p/'plan.json').read_bytes());assert sha(p/'plan.json')==f['planSha256'] and sha(p/'groups.jsonl')==f['groupsSha256'] and sha(p/'train-vectors.npz')==f['vectorsSha256']
assert all(sha(n)==h for n,h in plan['sourceHashes'].items());assert all(sha(assets/n)==h for n,h in plan['installedAssets'].items())
countfiles=[Path('build/context-ranking-20261025/counts-v3/model-counts.jsonl'),Path('build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl')];assert [sha(q) for q in countfiles]==plan['countsSha256']
lex=PymorphyLexicon(cache_size=16384);assert lex.receipt()==json.loads((p/'morphology-receipt.json').read_bytes())
groups=[json.loads(line) for line in (p/'groups.jsonl').read_text().splitlines()]; saved=np.load(p/'train-vectors.npz',allow_pickle=False);x=saved['features'];assert x.shape==(118635,178) and len(groups)==f['trainingGroups'] and FEATURES==178
tables=[WordContextFeatures.load(q) for q in countfiles];grammar=GrammarContextFeatures(lex);right=RightContextGrammarFeatures(lex);role=RightContextRoleFeatures(lex);character=neural.load_model(assets/'ru-ranking-context.bin')
@functools.lru_cache(maxsize=100000)
def base(context,original,serialized):
 c=json.loads(serialized)
 return tuple(rank.features(context,original,c)+[v for table in tables for v in table.extract(context,original,c['text'])]+[neural.context_score(character,context,c['text'])]+grammar.extract(context,original,c['text']))
index=0;mismatched=0;largest=0.;nonfinite=0
for gid,g in enumerate(groups):
 row=g['row'];context=row['leftContext'][-128:]
 for candidate in g['candidates']:
  prior=base(context,row['original'],json.dumps(candidate,sort_keys=True)); values=np.asarray(role_revision_features(prior,right,role,context,row['rightContext'],row['applied'],candidate['text']),dtype=np.float32)
  assert values.shape==(178,);delta=np.abs(values-x[index]);nonfinite+=int(not np.isfinite(values).all() or not np.isfinite(delta).all());mismatched+=int(not np.array_equal(values,x[index]));largest=max(largest,float(np.max(delta)));index+=1
 if (gid+1)%500==0:print('groups',gid+1,'rows',index,'mismatched',mismatched,flush=True)
assert index==len(x) and all(sha(n)==h for n,h in plan['sourceHashes'].items()) and all(sha(assets/n)==h for n,h in plan['installedAssets'].items()) and [sha(q) for q in countfiles]==plan['countsSha256'] and lex.receipt()==json.loads((p/'morphology-receipt.json').read_bytes())
assert sha(p/'plan.json')==f['planSha256'] and sha(p/'groups.jsonl')==f['groupsSha256'] and sha(p/'train-vectors.npz')==f['vectorsSha256']
out=dict(groups=len(groups),rows=index,features=178,mismatchedRows=mismatched,maxAbsoluteDifference=largest,nonfinite=nonfinite,scope='retained-training-groups',qualification=False)
with output.open('x') as stream:
 stream.write(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+'\n')
print(json.dumps(out),flush=True)
if mismatched or nonfinite:sys.exit(1)
