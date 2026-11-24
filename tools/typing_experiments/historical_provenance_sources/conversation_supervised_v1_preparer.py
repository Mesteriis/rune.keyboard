from pathlib import Path
import sys,json,hashlib,collections,base64
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
from conversation_split_checks import check_separation,target_context_key,context_key
root=Path('build/conversation-supervised-20261026');parent=Path('build/context-feature-ranker-20261026');out=root/'corpus';out.mkdir()
source=parent/'tatoeba-sentence-splits.jsonl';lock=json.loads((parent/'tatoeba-source-lock.json').read_text());assert j.common.sha256(source)==lock['sentenceSplitSha256']
prior_paths=[parent/'corpus'/f'{p}.jsonl' for p in ['calibration','holdout']]+[parent/'conversation-corpus'/f'{p}.jsonl' for p in ['calibration','holdout']]+[parent/'authored.jsonl',Path('tools/typing_experiments/fixtures/context_ranker_regressions_20261026.jsonl')]
# Include the previously disclosed correction qualifications for exclusion, never training.
prior_paths += [Path(p) for p in json.loads((parent/'corpus/manifest.json').read_text())['priorRows'] if not p.endswith('/train.jsonl')]
disclosed=[];bindings={}
for p in sorted(set(prior_paths)):
 bindings[str(p)]=j.common.sha256(p)
 for line in p.read_text().splitlines():
  r=json.loads(line)
  if all(isinstance(r.get(k),str) for k in ['prefix','typed','expectedSpelling']):disclosed.append(r)
blocked_sentences={r['article'] for r in disclosed if r.get('article')};blocked_contexts={target_context_key(r) for r in disclosed}
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lemmas=j.morphology(known)
seed='rune-supervised-conversation-20261026-v1';family_seed='rune-unified-context-conversation-20261026-v1';rivals={'стол','стал','стул','будет','будут','будки'}
pools={p:[] for p in ['train','calibration','holdout']}
for line in source.read_text().splitlines():
 s=json.loads(line);part=s['split'];article='tatoeba:'+s['id']
 if article in blocked_sentences:continue
 eligible=[]
 for index,m in enumerate(j.WORDS.finditer(s['text'])):
  word=m.group().casefold();family=lemmas.get(word)
  if index<1 or not m.group().islower() or len(word)>12 or family is None:continue
  if part!='train':
   expected='calibration' if hashlib.sha256((family_seed+':family:'+family).encode()).digest()[0]%2==0 else 'holdout'
   if part!=expected:continue
  prefix=j.GENERATOR.bounded_prefix(s['text'][:m.start()]).rstrip()
  if ( ' '.join(prefix.casefold().split()),word) in blocked_contexts:continue
  h=hashlib.sha256((seed+s['id']+word+prefix).encode()).hexdigest()
  eligible.append(dict(word=word,family=family,prefix=prefix,article=article,sentenceHash=s['normalizedSha256'],selectionHash=h))
 if eligible:pools[part].append(min(eligible,key=lambda r:(r['word'] not in rivals,r['selectionHash'])) if part=='train' else min(eligible,key=lambda r:r['selectionHash']))
rows_by_part={};manifest=dict(stage='frozen-before-supervised-training',seed=seed,sourceSha256=j.common.sha256(source),sourceLockSha256=j.common.sha256(parent/'tatoeba-source-lock.json'),exclusions=bindings,excludedSentenceIds=len(blocked_sentences),excludedTargetContexts=len(blocked_contexts),builderSha256=j.common.sha256(Path(__file__)),guardSha256=j.common.sha256(Path('tools/typing_experiments/conversation_split_checks.py')),files={},counts={},modelPlan=dict(wikiFoundationGroups='all non-overlapping original train groups',maxFreshTrainGroups=6000,maxCorrectRetentionGroups=1000,trees=128,depth=5,learningRate=.05,seed=25102026,contextScoring='108-feature unified tree; character model frozen, no additive bonus',gate='calibration>=100 new correct and >=99.5%; independent>=100 and >=99%; zero old-correct losses or control changes; positive net correct; runtime qualification separate'))
for part,pool in pools.items():
 cap=4000 if part=='train' else 1000;per_family=collections.Counter();selected=[]
 for item in sorted(pool,key=lambda r:(r['word'] not in rivals if part=='train' else False,r['selectionHash'])):
  if per_family[item['family']]>= (12 if part=='train' else 10):continue
  per_family[item['family']]+=1;selected.append(item)
  if len(selected)>=cap:break
 rows=[]
 for item in selected:
  forms=j.variants(item['word'],known,seed+item['selectionHash']);missing=[x for x in forms if len(x[0])==len(item['word'])-1][:2 if part=='train' else 1]
  others=[x for x in forms if x not in missing][:2 if part=='train' else 1]
  if not missing or not others:continue
  for typed,group in missing+others+[(item['word'],'correct'),('@'+item['word'],'protected')]:
   control=group in ['correct','protected'];r=dict(item,id=f'convo-supervised-{part}-{len(rows):05d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],cohort='correct' if control else 'typo',noAuto=control,group=group)
   if target_context_key(r) not in blocked_contexts:rows.append(r)
 rows_by_part[part]=rows;assert len({r['article'] for r in rows})>= (1000 if part=='train' else 400)
 p=out/f'{part}.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));manifest['files'][p.name]=j.common.sha256(p)
 manifest['counts'][part]=dict(rows=len(rows),sentences=len({r['article'] for r in rows}),families=len({r['family'] for r in rows}),groups=dict(collections.Counter(r['group'] for r in rows)),naturalRivalTargetRows=sum(r['word'] in rivals for r in rows))
 def e(x):return base64.b64encode(x.encode()).decode()
 (out/f'{part}.tsv').write_text(''.join('\t'.join([str(i),e(r['id']),part,'ru',e(r['prefix']),e(r['typed'])])+'\n' for i,r in enumerate(rows)))
check_separation(rows_by_part,disclosed)
assert not {r['family'] for r in rows_by_part['calibration']}&{r['family'] for r in rows_by_part['holdout']}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest['counts']),flush=True)
