from pathlib import Path
import sys,json,hashlib,bz2,collections,re,unicodedata,base64
sys.path.insert(0,'tools/typing_experiments')
import prepare_joint_correction as j
from conversation_split_checks import target_context_key,check_separation
from noun_case_focus_forms import accusative_contrast
from grammar_context_features import GrammarContextFeatures,FEATURE_NAMES
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/noun-case-focus-v3-20261026');train=Path('build/noun-case-training-20261026');source=Path('build/conversation-supervised-20261026/rus_sentences_detailed.tsv.bz2');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();plan=json.loads((root/'plan.json').read_text())
assert sha(source)==plan['sourceSha256'] and sha('tools/typing_experiments/noun_case_focus_forms.py')==plan['formsSha256']
assert sha('tools/typing_experiments/grammar_context_features.py')==plan['grammarSha256']
parent=Path('build/grammar-focused-eval-20261026/corpus/manifest.json');parentManifest=json.loads(parent.read_text());prior={Path(p) for p in parentManifest['exclusionBindings']}
for name in ['grammar-focused-eval-20261026','grammar-revision-broad-20261026','grammar-profile-training-20261026']:
 prior.update(Path('build',name,'corpus').glob('*.jsonl'))
prior.add(train/'corpus/train.jsonl');prior.add(Path('build/grammar-contrasts-profiles-20261026/train.jsonl'))
cc0=Path('build/context-feature-ranker-20261026/tatoeba-sentence-splits.jsonl');cc0rows=[json.loads(s) for s in cc0.read_text().splitlines()]
blocked_ids={str(s['id']) for s in cc0rows};blocked_hashes={s['normalizedSha256'] for s in cc0rows};del cc0rows
contexts=set();bindings={str(cc0):sha(cc0)};contrast_forms=set();authored_prefixes=set()
normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split())
for path in sorted(prior):
 bindings[str(path)]=sha(path)
 for line in path.open():
  r=json.loads(line)
  if all(isinstance(r.get(k),str) for k in ['prefix','typed','expectedSpelling']):contexts.add(target_context_key(r))
  if r.get('purpose')=='AUTHORED_CONTRAST_TRAINING_ONLY':
   contrast_forms.update(r['contrastCandidates']);authored_prefixes.add(normalize(r['prefix']))
  article=str(r.get('article',r.get('sourceSentence','')))
  if article.startswith('tatoeba:'):blocked_ids.add(article.split(':',1)[1])
  if isinstance(r.get('sentenceHash'),str):blocked_hashes.add(r['sentenceHash'])
# Resolve all prior sentence IDs to full normalized hashes, blocking duplicate text under new IDs.
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  f=line.rstrip('\n').split('\t');assert len(f)==6 and f[1]=='rus'
  if f[0] in blocked_ids:blocked_hashes.add(hashlib.sha256(normalize(f[2]).encode()).hexdigest())
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s}
lexicon=PymorphyLexicon(cache_size=16384);grammar=GrammarContextFeatures(lexicon);blocked_families={a.lemma for w in contrast_forms for a in lexicon.analyses(w)}
disclosed=Path('tools/typing_experiments/fixtures/conversation_supervised_false_proposals_20261026.json');bindings[str(disclosed)]=sha(disclosed)
disclosed_forms={r[k] for r in json.loads(disclosed.read_text())['cases'] for k in ['expectedSpelling','rejectedProposal']}
disclosed_families={a.lemma for w in disclosed_forms for a in lexicon.analyses(w)};blocked_families.update(disclosed_families)
forms_cache={};pools=collections.defaultdict(list);seen=set();scanned=eligible=0;words=re.compile(r'(?<![\w])[а-яё]{4,16}(?![\w])');cue=FEATURE_NAMES.index('accusative_object_supported')
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  f=line.rstrip('\n').split('\t');identity,_,text,owner,added,modified=f;scanned+=1
  if identity in blocked_ids:continue
  text=unicodedata.normalize('NFC',text);sentence_hash=hashlib.sha256(normalize(text).encode()).hexdigest()
  if sentence_hash in blocked_hashes or sentence_hash in seen:continue
  seen.add(sentence_hash);candidates=[]
  for match in words.finditer(text):
   word=match.group()
   if word not in known or not word.endswith(('у','ю')):continue
   if word not in forms_cache:forms_cache[word]=accusative_contrast(word,lexicon)
   forms=forms_cache[word]
   if forms is None:continue
   family=next(iter({a.lemma for a in lexicon.analyses(word)}))
   if family in blocked_families:continue
   prefix=j.GENERATOR.bounded_prefix(text[:match.start()]).rstrip()
   if normalize(prefix) in authored_prefixes or (normalize(prefix),word) in contexts:continue
   if grammar.extract((prefix+' ')[-128:],'',word)[cue]!=1.:continue
   h=hashlib.sha256((plan['seed']+identity+word+prefix).encode()).hexdigest()
   candidates.append(dict(forms,family=family,prefix=prefix,article='tatoeba:'+identity,sentenceHash=sentence_hash,owner=owner,sourceModified=modified,selectionHash=h))
  if not candidates:continue
  item=min(candidates,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']];key=(normalize(item['prefix']),item['word'])
  duplicate=next((x for x in bucket if (normalize(x['prefix']),x['word'])==key),None)
  if duplicate is not None:
   if duplicate['selectionHash']<=item['selectionHash']:continue
   bucket.remove(duplicate)
  bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected={p:[] for p in ['calibration','holdout']}
for item in sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((plan['seed']+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout'
 if len(selected[part])<plan['contextsPerPart']:selected[part].append(item)
availability=dict(scannedSourceRows=scanned,eligibleSourceSentences=eligible,eligibleFamilies=len(pools),selected={k:len(v) for k,v in selected.items()},familyCounts={k:len({r['family'] for r in v}) for k,v in selected.items()})
(root/'availability.json').write_text(json.dumps(availability,indent=2)+'\n');print(json.dumps(availability),flush=True)
assert all(len(v)==plan['contextsPerPart'] for v in selected.values()),'INSUFFICIENT_PREDECLARED_CONTEXTS'
assert all(len({r['family'] for r in v})>=100 for v in selected.values()),'INSUFFICIENT_FAMILY_DIVERSITY'
out=root/'corpus';out.mkdir();parts={};files={};counts={}
for part,items in selected.items():
 rows=[]
 for item in items:
  for typed,group,control in [(item['typed'],'shared_equal_cost',False),(item['word'],'correct',True),(item['instrumental'],'instrumental_retention',True),('@'+item['word'],'protected',True)]:
   rows.append(dict(item,id=f'focused-noun-case-{part}-{len(rows):06d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
 p=out/(part+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[p.name]=sha(p);parts[part]=rows
 encode=lambda s:base64.b64encode(s.encode()).decode();(out/(part+'.tsv')).write_text(''.join('\t'.join([str(i),encode(r['id']),part,'ru',encode(r['prefix']),encode(r['typed'])])+'\n' for i,r in enumerate(rows)))
 counts[part]=dict(rows=len(rows),contexts=len(items),families=len({r['family'] for r in items}))
check_separation(parts,[]);assert not ({r['family'] for r in parts['calibration']}&{r['family'] for r in parts['holdout']})
lock=dict(stage='frozen-before-model-scoring',sourceSha256=sha(source),sourceUrl='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2',sourceLicense='CC-BY-2.0-FR',files=files,counts=counts,planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),exclusionBindings=bindings,excludedContrastFamilies=len(blocked_families),excludedDisclosedFamilies=sorted(disclosed_families),excludedAuthoredContexts=len(authored_prefixes),blockedPriorSentenceIds=len(blocked_ids),blockedNormalizedSentenceHashes=len(blocked_hashes),dictionary=lexicon.receipt(),modelCalls=0,limitations=['Natural public contexts with synthetic equal-cost corruptions, not natural human typing','Calibration/holdout family and sentence separation, not contributor independence'])
(out/'manifest.json').write_text(json.dumps(lock,indent=2)+'\n');print('CORPUS_FROZEN',json.dumps(counts),flush=True)
