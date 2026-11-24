from pathlib import Path
import sys,json,hashlib,bz2,collections,re,unicodedata,base64
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
from conversation_split_checks import target_context_key,check_separation
from grammar_focus_forms import infinitive_contrast
from grammar_revision_scope import InfinitiveRevisionScope
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/grammar-focused-eval-20261026');oldroot=Path('build/conversation-supervised-20261026');parent=Path('build/context-feature-ranker-20261026');plan=json.loads((root/'plan.json').read_text());source=oldroot/'rus_sentences_detailed.tsv.bz2';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(source)==plan['sourceSha256'] and sha('tools/typing_experiments/grammar_focus_forms.py')==plan['formsSha256'] and sha('tools/typing_experiments/grammar_revision_scope.py')==plan['scopeSha256']
cc0=[json.loads(s) for s in (parent/'tatoeba-sentence-splits.jsonl').read_text().splitlines()];cc0ids={s['id'] for s in cc0};blocked_hashes={s['normalizedSha256'] for s in cc0};del cc0
manifest=json.loads((oldroot/'corpus-v2/manifest.json').read_text());prior={Path(p) for p in manifest['exclusions']};prior.update((oldroot/'corpus-v2').glob('*.jsonl'));prior.add(oldroot/'followon-corpus-v2/holdout.jsonl');prior.add(Path('build/joint-correction-20261025/corpus/train.jsonl'))
for name in ['conversation-supervised95-20261026','grammar-context-ranking-20261026','grammar-contrast-training-20261026','grammar-conservative-20261026']:
 prior.update(Path('build',name,'corpus').glob('calibration.jsonl'));prior.update(Path('build',name,'corpus').glob('holdout.jsonl'))
prior.add(Path('build/grammar-contrasts-profiles-20261026/train.jsonl'));contexts=set();blocked_ids=set(cc0ids);bindings={}
for p in sorted(prior):
 bindings[str(p)]=sha(p)
 for line in p.open():
  r=json.loads(line)
  if all(isinstance(r.get(k),str) for k in ['prefix','typed','expectedSpelling']):contexts.add(target_context_key(r))
  article=str(r.get('article',''))
  if article.startswith('tatoeba:'):blocked_ids.add(article.split(':',1)[1])
contrast_rows=[json.loads(line) for line in Path('build/grammar-contrasts-profiles-20261026/train.jsonl').read_text().splitlines()];contrast_forms={form for row in contrast_rows for form in row['contrastCandidates']}
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lemmas=j.morphology(known|contrast_forms);contrast_families={lemmas[w] for w in contrast_forms if w in lemmas}
lexicon=PymorphyLexicon(cache_size=16384);scope=InfinitiveRevisionScope(lexicon);forms_cache={};pools=collections.defaultdict(list);seen=set();scanned=eligible=0;seed=plan['seed'];words=re.compile(r'(?<![\w])[а-яёА-ЯЁ]{4,16}(?![\w])')
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  f=line.rstrip('\n').split('\t');assert len(f)==6 and f[1]=='rus';identity,_,text,owner,added,modified=f;scanned+=1
  if identity in blocked_ids:continue
  text=unicodedata.normalize('NFC',text);sentence_hash=hashlib.sha256(' '.join(text.casefold().split()).encode()).hexdigest()
  if sentence_hash in blocked_hashes or sentence_hash in seen:continue
  seen.add(sentence_hash);candidates=[]
  for match in words.finditer(text):
   word=match.group();family=lemmas.get(word)
   if word not in known or family is None or family in contrast_families or not word.endswith(('ить','иться')):continue
   if word not in forms_cache:forms_cache[word]=infinitive_contrast(word,lexicon)
   forms=forms_cache[word]
   if forms is None:continue
   prefix=j.GENERATOR.bounded_prefix(text[:match.start()]).rstrip()
   if (' '.join(prefix.casefold().split()),word) in contexts or scope.refusal((prefix+' ')[-128:],forms['finite'],word) is not None:continue
   h=hashlib.sha256((seed+identity+word+prefix).encode()).hexdigest()
   candidates.append(dict(forms,family=family,prefix=prefix,article='tatoeba:'+identity,sentenceHash=sentence_hash,owner=owner,sourceModified=modified,selectionHash=h))
  if not candidates:continue
  item=min(candidates,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']];key=(' '.join(item['prefix'].casefold().split()),item['word'])
  duplicate=next((x for x in bucket if (' '.join(x['prefix'].casefold().split()),x['word'])==key),None)
  if duplicate is not None:
   if duplicate['selectionHash']<=item['selectionHash']:continue
   bucket.remove(duplicate)
  bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected={p:[] for p in ['calibration','holdout']}
for item in sorted([item for items in pools.values() for item in items],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((seed+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout'
 if len(selected[part])<plan['contextsPerPart']:selected[part].append(item)
availability=dict(scannedSourceRows=scanned,eligibleSourceSentences=eligible,eligibleFamilies=len(pools),selected={k:len(v) for k,v in selected.items()},familyCounts={k:len({r['family'] for r in v}) for k,v in selected.items()})
(root/'availability.json').write_text(json.dumps(availability,indent=2)+'\n');print(json.dumps(availability),flush=True)
assert all(len(v)==plan['contextsPerPart'] for v in selected.values()),'INSUFFICIENT_PREDECLARED_CONTEXTS'
out=root/'corpus';out.mkdir();parts={};files={};counts={}
for part,items in selected.items():
 rows=[]
 for item in items:
  variants=[(item['typed'],'shared_adjacent',False),(item['word'],'correct',True),(item['finite'],'finite_form_retention',True),('@'+item['word'],'protected',True)]
  for typed,group,control in variants:
   rows.append(dict(item,id=f'focused-infinitive-{part}-{len(rows):06d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
 p=out/(part+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[p.name]=sha(p);parts[part]=rows
 encode=lambda s:base64.b64encode(s.encode()).decode()
 (out/(part+'.tsv')).write_text(''.join('\t'.join([str(i),encode(r['id']),part,'ru',encode(r['prefix']),encode(r['typed'])])+'\n' for i,r in enumerate(rows)))
 counts[part]=dict(rows=len(rows),contexts=len(items),families=len({r['family'] for r in items}))
check_separation(parts,[]);assert not ({r['family'] for r in parts['calibration']}&{r['family'] for r in parts['holdout']})
lock=dict(stage='frozen-before-model-scoring',sourceUrl='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2',sourceLicense='CC-BY-2.0-FR',sourceSha256=sha(source),files=files,counts=counts,planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),exclusionBindings=bindings,excludedContrastFamilies=len(contrast_families),dictionary=lexicon.receipt(),modelCalls=0,qualificationScope=plan['qualificationScope'],limitation='Focused synthetic adjacent corruptions in natural infinitive contexts; no author independence or general natural typing claim')
(out/'manifest.json').write_text(json.dumps(lock,indent=2)+'\n');print('CORPUS_FROZEN',json.dumps(counts),flush=True)
