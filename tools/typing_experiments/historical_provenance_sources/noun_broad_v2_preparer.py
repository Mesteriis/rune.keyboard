from pathlib import Path
import sys,json,hashlib,bz2,collections,re,unicodedata,base64
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
from conversation_split_checks import target_context_key
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/noun-case-broad-v2-20261026');focus=Path('build/noun-case-focus-v3-20261026');parent=json.loads((focus/'corpus/manifest.json').read_text());source=Path('build/conversation-supervised-20261026/rus_sentences_detailed.tsv.bz2');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split());plan=json.loads((root/'plan.json').read_text())
assert sha(source)==parent['sourceSha256']==plan['sourceSha256']
prior={Path(p) for p in parent['exclusionBindings']};prior.update((focus/'corpus').glob('*.jsonl'));bindings={};blocked_ids=set();blocked_hashes=set();contexts=set();contrast_forms=set();authored_prefixes=set()
for path in sorted(prior):
 bindings[str(path)]=sha(path);records=json.loads(path.read_text())['cases'] if path.suffix=='.json' else (json.loads(line) for line in path.open())
 for r in records:
  if all(isinstance(r.get(k),str) for k in ['prefix','typed','expectedSpelling']):contexts.add(target_context_key(r))
  article=str(r.get('article',r.get('sourceSentence','')))
  if article.startswith('tatoeba:'):blocked_ids.add(article.split(':',1)[1])
  if path.name=='tatoeba-sentence-splits.jsonl':blocked_ids.add(str(r['id']))
  for key in ['normalizedSha256','sentenceHash']:
   if isinstance(r.get(key),str):blocked_hashes.add(r[key])
  if r.get('purpose')=='AUTHORED_CONTRAST_TRAINING_ONLY':contrast_forms.update(r['contrastCandidates']);authored_prefixes.add(normalize(r['prefix']))
  if 'rejectedProposal' in r:contrast_forms.update([r['rejectedProposal'],r['expectedSpelling']])
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  f=line.rstrip('\n').split('\t');assert len(f)==6 and f[1]=='rus'
  if f[0] in blocked_ids:blocked_hashes.add(hashlib.sha256(normalize(f[2]).encode()).hexdigest())
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lemmas=j.morphology(known|contrast_forms);blocked_families={lemmas[w] for w in contrast_forms if w in lemmas};assert blocked_families and all(f.isdecimal() for f in blocked_families)
pools=collections.defaultdict(list);seen=set();scanned=0;word_re=re.compile(r'(?<![\w])[а-яёА-ЯЁ]{1,20}(?![\w])');eligibility={}
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  identity,_,text,owner,added,modified=line.rstrip('\n').split('\t');scanned+=1
  if identity in blocked_ids:continue
  text=unicodedata.normalize('NFC',text);sentence_hash=hashlib.sha256(normalize(text).encode()).hexdigest()
  if sentence_hash in blocked_hashes or sentence_hash in seen:continue
  seen.add(sentence_hash);candidates=[]
  for ordinal,match in enumerate(word_re.finditer(text)):
   word=match.group();family=lemmas.get(word)
   if ordinal<1 or not word.islower() or not 4<=len(word)<=12 or family is None or family in blocked_families:continue
   if word not in eligibility:eligibility[word]=any(word[:i]+word[i+1:] not in known for i in range(len(word)))
   if not eligibility[word]:continue
   prefix=j.GENERATOR.bounded_prefix(text[:match.start()]).rstrip()
   if normalize(prefix) in authored_prefixes or (normalize(prefix),word) in contexts:continue
   h=hashlib.sha256((plan['seed']+identity+word+prefix).encode()).hexdigest();candidates.append(dict(word=word,family=family,prefix=prefix,article='tatoeba:'+identity,sentenceHash=sentence_hash,owner=owner,sourceModified=modified,selectionHash=h))
  if not candidates:continue
  item=min(candidates,key=lambda r:r['selectionHash']);bucket=pools[item['family']];key=(normalize(item['prefix']),item['word']);duplicate=next((r for r in bucket if (normalize(r['prefix']),r['word'])==key),None)
  if duplicate is not None:
   if duplicate['selectionHash']<=item['selectionHash']:continue
   bucket.remove(duplicate)
  bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected=[]
for item in sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash']):
 forms=j.variants(item['word'],known,plan['seed']+item['selectionHash']);missing=next((v for v in forms if len(v[0])==len(item['word'])-1),None);other=next((v for v in forms if v!=missing),None)
 if not missing or not other:continue
 item['forms']=[missing,other];selected.append(item)
 if len(selected)==plan['contexts']:break
assert len(selected)==plan['contexts'] and len({r['family'] for r in selected})>=750
assert not ({r['family'] for r in selected}&blocked_families)
out=root/'corpus';out.mkdir();rows=[]
for item in selected:
 forms=item.pop('forms')+[(item['word'],'correct'),('@'+item['word'],'protected')]
 for typed,group in forms:
  control=group in ['correct','protected'];rows.append(dict(item,id=f'noun-broad-holdout-{len(rows):06d}',language='ru',split='broad',typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
p=out/'broad.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));encode=lambda s:base64.b64encode(s.encode()).decode();(out/'broad.tsv').write_text(''.join('\t'.join([str(i),encode(r['id']),'broad','ru',encode(r['prefix']),encode(r['typed'])])+'\n' for i,r in enumerate(rows)))
assert not ({r['article'].split(':',1)[1] for r in rows}&blocked_ids) and not ({r['sentenceHash'] for r in rows}&blocked_hashes) and not ({(normalize(r['prefix']),r['word']) for r in rows}&contexts)
receipt=dict(stage='frozen-before-broad-model-scoring',files={'broad.jsonl':sha(p)},counts=dict(contexts=len(selected),rows=len(rows),families=len({r['family'] for r in rows}),controls=sum(r['noAuto'] for r in rows)),sourceSha256=sha(source),sourceLicense='CC-BY-2.0-FR',planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),exclusionBindings=bindings,excludedTrainingAndDisclosedFamilies=len(blocked_families),selectedFamilyOverlap=0,sourceSentenceHashOverlap=0,sourceSentenceIdOverlap=0,targetContextOverlap=0,modelScoresConsumed=False,limitations=['Natural public contexts with synthetic spelling corruptions; not natural human typing or contributor independence'])
(out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['counts']),flush=True)
