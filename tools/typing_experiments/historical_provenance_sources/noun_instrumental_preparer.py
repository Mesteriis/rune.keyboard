from pathlib import Path
import sys,json,hashlib,bz2,collections,re,unicodedata,base64
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
from noun_case_focus_forms import accusative_contrast
from grammar_context_features import GrammarContextFeatures,FEATURE_NAMES
from conversation_split_checks import target_context_key
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/noun-case-instrumental-20261026');broad=Path('build/noun-case-broad-v2-20261026');parent=json.loads((broad/'corpus/manifest.json').read_text());source=Path('build/conversation-supervised-20261026/rus_sentences_detailed.tsv.bz2');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split());plan=json.loads((root/'plan.json').read_text())
assert sha(source)==plan['sourceSha256']
prior={Path(p) for p in parent['exclusionBindings']};prior.add(broad/'corpus/broad.jsonl');bindings={};blocked_ids=set();blocked_hashes=set();contexts=set();contrast_forms=set();authored_prefixes=set()
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
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lexicon=PymorphyLexicon(cache_size=16384);grammar=GrammarContextFeatures(lexicon);blocked_families={a.lemma for w in contrast_forms for a in lexicon.analyses(w)};forms={}
for word in sorted(known):
 if not word.endswith(('у','ю')):continue
 contrast=accusative_contrast(word,lexicon)
 if contrast is None:continue
 family=next(iter({a.lemma for a in lexicon.analyses(word)}))
 if family in blocked_families:continue
 forms.setdefault(contrast['instrumental'],[]).append(dict(contrast,family=family))
forms={word:items[0] for word,items in forms.items() if len(items)==1};pools=collections.defaultdict(list);seen=set();scanned=0;eligible=0;words=re.compile(r'(?<![\w])[а-яё]{4,18}(?![\w])');cue=FEATURE_NAMES.index('accusative_object_supported')
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  identity,_,text,owner,added,modified=line.rstrip('\n').split('\t');scanned+=1
  if identity in blocked_ids:continue
  text=unicodedata.normalize('NFC',text);sentence_hash=hashlib.sha256(normalize(text).encode()).hexdigest()
  if sentence_hash in blocked_hashes or sentence_hash in seen:continue
  seen.add(sentence_hash);candidates=[]
  for match in words.finditer(text):
   form=forms.get(match.group())
   if form is None:continue
   prefix=j.GENERATOR.bounded_prefix(text[:match.start()]).rstrip()
   if normalize(prefix) in authored_prefixes or (normalize(prefix),match.group()) in contexts:continue
   if grammar.extract((prefix+' ')[-128:],form['typed'],form['word'])[cue]!=1.:continue
   h=hashlib.sha256((plan['seed']+identity+match.group()+prefix).encode()).hexdigest();candidates.append(dict(form,word=match.group(),accusative=form['word'],prefix=prefix,article='tatoeba:'+identity,sentenceHash=sentence_hash,owner=owner,sourceModified=modified,selectionHash=h))
  if not candidates:continue
  item=min(candidates,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']];key=(normalize(item['prefix']),item['word']);duplicate=next((r for r in bucket if (normalize(r['prefix']),r['word'])==key),None)
  if duplicate is not None:
   if duplicate['selectionHash']<=item['selectionHash']:continue
   bucket.remove(duplicate)
  bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected=sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash'])[:plan['maximumContexts']];assert selected,'NO_INSTRUMENTAL_NEGATIVE_CONTEXTS'
out=root/'corpus';out.mkdir();rows=[]
for item in selected:
 for typed,group,control in [(item['typed'],'shared_equal_cost',False),(item['word'],'correct_instrumental',True),(item['accusative'],'correct_accusative_retention',True),('@'+item['word'],'protected',True)]:
  rows.append(dict(item,id=f'noun-instrumental-{len(rows):06d}',language='ru',split='instrumental',typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
p=out/'instrumental.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));encode=lambda s:base64.b64encode(s.encode()).decode();(out/'instrumental.tsv').write_text(''.join('\t'.join([str(i),encode(r['id']),'instrumental','ru',encode(r['prefix']),encode(r['typed'])])+'\n' for i,r in enumerate(rows)))
assert not ({r['article'].split(':',1)[1] for r in rows}&blocked_ids) and not ({r['sentenceHash'] for r in rows}&blocked_hashes)
receipt=dict(stage='frozen-before-instrumental-projection-scores',purpose='ADDITIONAL_NATURAL_INSTRUMENTAL_REGRESSION_NOT_VOLUME_QUALIFICATION',files={'instrumental.jsonl':sha(p)},counts=dict(scannedSourceRows=scanned,eligibleSentences=eligible,contexts=len(selected),families=len({r['family'] for r in rows}),rows=len(rows),controls=sum(r['noAuto'] for r in rows)),sourceSha256=sha(source),sourceLicense='CC-BY-2.0-FR',planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),exclusionBindings=bindings,sourceSentenceIdOverlap=0,sourceSentenceHashOverlap=0,modelScoresConsumed=False,qualificationLimitation='Additional regression opportunities only; small availability does not establish general precision')
(out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['counts']),flush=True)
