from pathlib import Path
import sys,json,hashlib,bz2,urllib.request,collections,re,unicodedata,base64
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
from conversation_split_checks import target_context_key
oldroot=Path('build/conversation-supervised-20261026');root=Path('build/grammar-contrast-training-20261026');parent=Path('build/context-feature-ranker-20261026');plan=json.loads((root/'plan.json').read_text());out=root/'corpus';out.mkdir()
assert plan['installedModelSha256']==j.common.sha256(Path('app/src/main/assets/smarttyping/experiments/ru-contextual-ranker.bin'))
source=oldroot/'rus_sentences_detailed.tsv.bz2'
assert source.is_file() and source.stat().st_size==23598664
assert j.common.sha256(source)==json.loads(Path('build/grammar-context-ranking-20261026/corpus/manifest.json').read_text())['sourceSha256']
headers={'Last-Modified':'Sat, 24 Oct 2026 06:41:06 GMT','Content-Length':str(source.stat().st_size)}
cc0=[json.loads(s) for s in (parent/'tatoeba-sentence-splits.jsonl').read_text().splitlines()];cc0ids={s['id'] for s in cc0};blocked_hashes={s['normalizedSha256'] for s in cc0};del cc0
manifest=json.loads((oldroot/'corpus-v2/manifest.json').read_text());prior={Path(p) for p in manifest['exclusions']};prior.update((oldroot/'corpus-v2').glob('*.jsonl'));prior.add(oldroot/'followon-corpus-v2/holdout.jsonl');prior.update(Path('build/conversation-supervised95-20261026/corpus').glob('*.jsonl'));prior.add(Path('build/joint-correction-20261025/corpus/train.jsonl'));prior.update(Path('build/grammar-context-ranking-20261026/corpus').glob('*.jsonl'));prior.add(Path('build/grammar-contrasts-20261026/train.jsonl'));contexts=set();blocked_ids=set(cc0ids);bindings={}
for p in sorted(prior):
 bindings[str(p)]=j.common.sha256(p)
 for line in p.read_text().splitlines():
  r=json.loads(line)
  if all(isinstance(r.get(k),str) for k in ['prefix','typed','expectedSpelling']):contexts.add(target_context_key(r))
  article=str(r.get('article',''))
  if article.startswith('tatoeba:'):blocked_ids.add(article.split(':',1)[1])
contrast_rows=[json.loads(line) for line in Path('build/grammar-contrasts-20261026/train.jsonl').read_text().splitlines()];contrast_forms={form for row in contrast_rows for form in row['contrastCandidates']}
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lemmas=j.morphology(known|contrast_forms);contrast_families={lemmas[w] for w in contrast_forms if w in lemmas};pools=collections.defaultdict(list);seen=set();scanned=0;eligibility={};seed='rune-grammar-contrast-independent-20261026-v1';word_re=re.compile(r'(?<![\w])[а-яёА-ЯЁ]{1,20}(?![\w])')
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  f=line.rstrip('\n').split('\t');assert len(f)==6 and f[1]=='rus'
  identity,_,text,owner,added,modified=f;scanned+=1
  if identity in blocked_ids:continue
  text=unicodedata.normalize('NFC',text);normalized=' '.join(text.casefold().split());sentence_hash=hashlib.sha256(normalized.encode()).hexdigest()
  if sentence_hash in blocked_hashes or sentence_hash in seen:continue
  seen.add(sentence_hash);candidates=[]
  for ordinal,m in enumerate(word_re.finditer(text)):
   word=m.group().casefold();family=lemmas.get(word)
   if family in contrast_families:continue
   if ordinal<1 or not m.group().islower() or not 4<=len(word)<=12 or family is None:continue
   if word not in eligibility:eligibility[word]=any(word[:i]+word[i+1:] not in known for i in range(len(word)))
   if not eligibility[word]:continue
   prefix=j.GENERATOR.bounded_prefix(text[:m.start()]).rstrip()
   if (' '.join(prefix.casefold().split()),word) in contexts:continue
   h=hashlib.sha256((seed+identity+word+prefix).encode()).hexdigest()
   candidates.append(dict(word=word,family=family,prefix=prefix,article='tatoeba:'+identity,sentenceHash=sentence_hash,owner=owner,sourceModified=modified,selectionHash=h))
  if not candidates:continue
  if candidates:
   item=min(candidates,key=lambda r:r['selectionHash']);bucket=pools[item['family']]
   key=(' '.join(item['prefix'].casefold().split()),item['word'])
   duplicate=next((x for x in bucket if (' '.join(x['prefix'].casefold().split()),x['word'])==key),None)
   if duplicate is not None:
    if duplicate['selectionHash']<=item['selectionHash']:continue
    bucket.remove(duplicate)
   bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[4:]
  if scanned%100000==0:print('Scanned source rows',scanned,flush=True)
selected={p:[] for p in ['calibration','holdout']}
for item in sorted([item for items in pools.values() for item in items],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((seed+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout'
 if len(selected[part])>=3000:continue
 forms=j.variants(item['word'],known,seed+item['selectionHash']);missing=next((v for v in forms if len(v[0])==len(item['word'])-1),None);other=next((v for v in forms if v!=missing),None)
 if not missing or not other:continue
 item['forms']=[missing,other];selected[part].append(item)
 if all(len(v)==3000 for v in selected.values()):break
from conversation_split_checks import check_separation
parts={};files={};counts={}
for part,items in selected.items():
 assert len(items)==3000
 assert len({(' '.join(r['prefix'].casefold().split()),r['word']) for r in items})==len(items)
 rows=[]
 for item in items:
  forms=item.pop('forms')+[(item['word'],'correct'),('@'+item['word'],'protected')]
  for typed,group in forms:
   control=group in ['correct','protected'];rows.append(dict(item,id=f'supervised95-{part}-{len(rows):06d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
 p=out/(part+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[p.name]=j.common.sha256(p);parts[part]=rows
 def e(x):return base64.b64encode(x.encode()).decode()
 (out/(part+'.tsv')).write_text(''.join('\t'.join([str(i),e(r['id']),part,'ru',e(r['prefix']),e(r['typed'])])+'\n' for i,r in enumerate(rows)))
 counts[part]=dict(rows=len(rows),contexts=len(items),families=len({r['family'] for r in items}))
check_separation(parts,[])
assert not ({r['family'] for r in parts['calibration']}&{r['family'] for r in parts['holdout']})
lock=dict(stage='frozen-before-evaluation-scoring; model-fit-was-already-running',sourceUrl='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2',sourceLicense='CC-BY-2.0-FR',sourceSha256=j.common.sha256(source),sourceRows=scanned,preparerSha256=j.common.sha256(Path(__file__)),files=files,counts=counts,planSha256=j.common.sha256(root/'plan.json'),exclusionBindings=bindings,excludedCc0Ids=len(cc0ids),excludedContrastFamilies=len(contrast_families),limitation='Sentence/prediction-context disjoint; no author-independent or natural phone-typing claim.')
(out/'manifest.json').write_text(json.dumps(lock,indent=2)+'\n');print(json.dumps(counts,indent=2),flush=True)
