from pathlib import Path
import sys,json,hashlib,bz2,collections,re,unicodedata,base64,functools
sys.path.insert(0,'tools/typing_experiments')
from right_context_focus_forms import predicate_contrast
from right_context_corpus_separation import exclusion_records
from right_context_grammar_features import RightContextGrammarFeatures,FEATURE_NAMES
import prepare_joint_correction as existing
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-focused-v2-20261027');train=Path('build/right-context-training-20261027');source=Path('build/conversation-supervised-20261026/rus_sentences_detailed.tsv.bz2')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split())
model=load(train/'frozen-model.json');assert sha(train/'experimental-ranker.bin')==model['modelSha256']
prior_manifest=load('build/noun-case-focus-v3-20261026/corpus/manifest.json')
prior={Path(p) for p in prior_manifest['exclusionBindings']}
for name in ['noun-case-focus-v3-20261026','noun-case-broad-v2-20261026','noun-case-instrumental-20261026']:
 prior.update(Path('build',name,'corpus').glob('*.jsonl'))
cc0=Path('build/context-feature-ranker-20261026/tatoeba-sentence-splits.jsonl');prior.add(cc0)
plan=dict(stage='frozen-before-independent-corpus-selection',seed='right-context-natural-v1-20261027',contextsPerPart=400,maximumContextsPerFamily=30,minimumFamiliesPerPart=20,
 sourceSha256=sha(source),modelSha256=model['modelSha256'],formsSha256=sha('tools/typing_experiments/right_context_focus_forms.py'),featureSha256=sha('tools/typing_experiments/right_context_grammar_features.py'),
 exclusionBindings={str(p):sha(p) for p in sorted(prior)},trainingFamilies=model['trainingFamilies'],
 sampling='Source short adjective immediately followed by finite copula; dictionary consensus; one sentence once; family-disjoint calibration/holdout',
 thresholdsRetuned=False,productionActivation=False)
assert plan['sourceSha256']=='3993a545d85db1e60a9423c0165a909c0d52beba85070883adf93cf5abe3db5f'
with (root/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
blocked_ids=set();blocked_hashes=set();blocked_forms=set();bindings=plan['exclusionBindings']
for path in sorted(prior):
 for row in exclusion_records(path):
  if path==cc0:
   blocked_ids.add(str(row['id']));blocked_hashes.add(row['normalizedSha256']);continue
  sentence=str(row.get('article',row.get('sourceSentence','')))
  if sentence.startswith('tatoeba:'):blocked_ids.add(sentence.split(':',1)[1])
  if isinstance(row.get('sentenceHash'),str):blocked_hashes.add(row['sentenceHash'])
  if row.get('purpose')=='AUTHORED_CONTRAST_TRAINING_ONLY':blocked_forms.update(row['contrastCandidates'])
lex=PymorphyLexicon(cache_size=16384);features=RightContextGrammarFeatures(lex)
blocked_families=set(plan['trainingFamilies'])|{a.lemma for word in blocked_forms for a in lex.analyses(word)}
disclosed=Path('tools/typing_experiments/fixtures/conversation_supervised_false_proposals_20261026.json')
for row in load(disclosed)['cases']:
 for key in ['expectedSpelling','rejectedProposal']:blocked_families.update(a.lemma for a in lex.analyses(row[key]))
# Resolve excluded IDs to normalized full-sentence hashes, not just exact identifiers.
with bz2.open(source,'rt',encoding='utf-8') as stream:
 for line in stream:
  fields=line.rstrip('\n').split('\t')
  if fields[0] in blocked_ids:blocked_hashes.add(hashlib.sha256(normalize(fields[2]).encode()).hexdigest())
@functools.lru_cache(maxsize=8192)
def forms(word):
 tags=lex.analyses(word)
 if not tags or any(a.pos!='ADJS' for a in tags) or any(a.lemma in blocked_families for a in tags):return None
 lex._load();paradigm={p.word for parsed in lex._analyzer.parse(word) for p in parsed.lexeme if parsed.normal_form in {a.lemma for a in tags}}
 return predicate_contrast(word,lex,paradigm)
pattern=re.compile(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?P<copula>буду|будешь|будет|будем|будете|будут|был|была|было|были)(?=[ \t.,!?;:]|$)')
pools=collections.defaultdict(list);seen=set();scanned=eligible=0
for line in bz2.open(source,'rt',encoding='utf-8'):
 identity,language,text,owner,added,modified=line.rstrip('\n').split('\t');scanned+=1;assert language=='rus'
 if identity in blocked_ids:continue
 text=unicodedata.normalize('NFC',text);normalized_hash=hashlib.sha256(normalize(text).encode()).hexdigest()
 if normalized_hash in blocked_hashes or normalized_hash in seen:continue
 seen.add(normalized_hash);items=[]
 if len(text.lower())!=len(text):continue
 for match in pattern.finditer(text.lower()):
  pair=forms(match['word'])
  if pair is None:continue
  prefix=existing.GENERATOR.bounded_prefix(text[:match.start('word')]).rstrip(' \t')
  suffix=text[match.end('word'):][:128]
  target=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['word'])))
  rival=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['rival'])))
  if target['right_copula_number_supported']!=1 or target['right_copula_number_conflict'] or rival['right_copula_number_conflict']!=1:continue
  choiceHash=hashlib.sha256((plan['seed']+identity+pair['word']+prefix).encode()).hexdigest()
  items.append(dict(pair,prefix=prefix,rightContext=suffix,article='tatoeba:'+identity,sentenceHash=normalized_hash,sourceContributor=owner,sourceModified=modified,selectionHash=choiceHash))
 if not items:continue
 item=min(items,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']]
 signature=lambda r:(normalize(r['prefix']),r['word'],normalize(r['rightContext']))
 old=next((r for r in bucket if signature(r)==signature(item)),None)
 if old is not None:
  if old['selectionHash']<=item['selectionHash']:continue
  bucket.remove(old)
 bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected={part:[] for part in ['calibration','holdout']}
for item in sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((plan['seed']+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout'
 if len(selected[part])<plan['contextsPerPart']:selected[part].append(item)
availability=dict(scannedSourceRows=scanned,eligibleSourceSentences=eligible,eligibleFamilies=len(pools),selected={k:len(v) for k,v in selected.items()},families={k:len({r['family'] for r in v}) for k,v in selected.items()},blockedPriorSentenceIds=len(blocked_ids),blockedSentenceHashes=len(blocked_hashes))
(root/'availability.json').write_text(json.dumps(availability,indent=2)+'\n');print(json.dumps(availability),flush=True)
assert all(len(v)==plan['contextsPerPart'] and len({r['family'] for r in v})>=plan['minimumFamiliesPerPart'] for v in selected.values()),'INSUFFICIENT_PREDECLARED_NATURAL_CONTEXTS'
out=root/'corpus';out.mkdir();parts={};files={}
for part,items in selected.items():
 rows=[]
 for item in items:
  for typed,kind,control in [(item['typed'],'typo',False),(item['word'],'correct',True),(item['rival'],'correct_rival',True),('@'+item['word'],'protected',True)]:
   rows.append(dict(item,id=f'right-natural-{part}-{len(rows):06d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],noAuto=control,cohort='correct' if control else 'typo',group=kind))
 parts[part]=rows;path=out/(part+'.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[path.name]=sha(path)
 enc=lambda s:base64.b64encode(s.encode()).decode()
 (out/(part+'.tsv')).write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)))
assert not ({r['family'] for r in parts['calibration']}&{r['family'] for r in parts['holdout']})
assert not ({r['sentenceHash'] for r in parts['calibration']}&{r['sentenceHash'] for r in parts['holdout']})
manifest=dict(stage='frozen-before-calibration-and-holdout-scoring',files=files,counts={k:len(v) for k,v in parts.items()},modelSha256=model['modelSha256'],planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),sourceSha256=sha(source),sourceLicense='CC-BY-2.0-FR',sourceUrl='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2',exclusionBindings=bindings,excludedFamilies=sorted(blocked_families),blockedPriorSentenceIds=len(blocked_ids),blockedSentenceHashes=len(blocked_hashes),dictionary=lex.receipt(),modelCalls=0,limitations=['Natural source text with synthetic shared corruptions; not human typing','Family and normalized-sentence separation; not author independence'])
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('CORPUS_FROZEN',flush=True)
