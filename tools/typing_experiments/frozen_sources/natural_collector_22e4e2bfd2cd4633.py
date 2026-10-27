from pathlib import Path
import sys,json,hashlib,collections,re,unicodedata,functools
import pyarrow.parquet as parquet
import pyarrow; pyarrow.set_cpu_count(2)
sys.path.insert(0,'tools/typing_experiments')
from right_context_focus_forms import predicate_contrast
from right_context_corpus_separation import exclusion_records
from right_context_grammar_features import RightContextGrammarFeatures,FEATURE_NAMES
import prepare_joint_correction as existing
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-wiki0014-20261027');source=Path('build/typing-ranker-v2/ru-0014.parquet')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split())
lock=load('build/typing-ranker-v2/external-holdout-v9-ru0014/manifest.json');item=lock['source'];entry={'lfs':{'oid':item['sha256']},'size':item['bytes']}
assert sha(source)==entry['lfs']['oid'] and source.stat().st_size==entry['size']
previous=load('build/right-context-focused-v2-20261027/plan.json');frozen=load('build/right-context-training-20261027/frozen-model.json')
assert sha('build/right-context-training-20261027/experimental-ranker.bin')==frozen['modelSha256']
plan=dict(stage='source-availability-before-scoring',parentNaturalPlanSha256=sha('build/right-context-focused-v2-20261027/plan.json'),seed=previous['seed'],contextsPerPart=previous['contextsPerPart'],minimumFamiliesPerPart=previous['minimumFamiliesPerPart'],maximumContextsPerFamily=previous['maximumContextsPerFamily'],sourceSha256=sha(source),sourceLockSha256=sha('build/typing-ranker-v2/external-holdout-v9-ru0014/manifest.json'),modelSha256=frozen['modelSha256'],exclusionBindings=previous['exclusionBindings'],thresholdChanges=False,modelCalls=0)
with (root/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
blocked_articles=set();blocked_forms=set()
for name,digest in plan['exclusionBindings'].items():
 path=Path(name);assert sha(path)==digest
 for row in exclusion_records(path):
  article=str(row.get('article',''))
  if article.isdigit():blocked_articles.add(article)
  if row.get('purpose')=='AUTHORED_CONTRAST_TRAINING_ONLY':blocked_forms.update(row['contrastCandidates'])
lex=PymorphyLexicon(cache_size=16384);features=RightContextGrammarFeatures(lex)
blocked=set(frozen['trainingFamilies'])|{a.lemma for word in blocked_forms for a in lex.analyses(word)}
for row in load('tools/typing_experiments/fixtures/conversation_supervised_false_proposals_20261026.json')['cases']:
 for key in ['expectedSpelling','rejectedProposal']:blocked.update(a.lemma for a in lex.analyses(row[key]))
@functools.lru_cache(maxsize=8192)
def forms(word):
 tags=lex.analyses(word)
 if not tags or any(a.pos!='ADJS' or a.lemma in blocked for a in tags):return None
 lex._load();paradigm={p.word for parsed in lex._analyzer.parse(word) for p in parsed.lexeme if parsed.normal_form in {a.lemma for a in tags}}
 return predicate_contrast(word,lex,paradigm)
pattern=re.compile(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?:буду|будешь|будет|будем|будете|будут|был|была|было|были)(?=[ \t.,!?;:]|$)')
pools=collections.defaultdict(list);seen=set();scanned=eligible=0
for batch in parquet.ParquetFile(source).iter_batches(batch_size=64,columns=['id','text']):
 for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
  article=str(article);scanned+=1
  if article in blocked_articles:continue
  text=unicodedata.normalize('NFC',text or '');folded=text.lower()
  if len(folded)!=len(text):continue
  items=[]
  for match in pattern.finditer(folded):
   pair=forms(match['word'])
   if pair is None:continue
   prefix=existing.GENERATOR.bounded_prefix(text[max(0,match.start('word')-256):match.start('word')]).rstrip(' \t')
   suffix=text[match.end('word'):match.end('word')+128]
   target=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['word'])));rival=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['rival'])))
   if target['right_copula_number_supported']!=1 or target['right_copula_number_conflict'] or rival['right_copula_number_conflict']!=1:continue
   context_hash=hashlib.sha256(normalize(prefix+' '+pair['word']+suffix).encode()).hexdigest()
   if context_hash in seen:continue
   seen.add(context_hash);h=hashlib.sha256((plan['seed']+':wiki:'+article+pair['word']+prefix).encode()).hexdigest()
   items.append(dict(pair,prefix=prefix,rightContext=suffix,article=article,source='ru-0014.parquet',contextHash=context_hash,selectionHash=h))
  if not items:continue
  item=min(items,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']]
  bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
selected={part:[] for part in ['calibration','holdout']}
for item in sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((plan['seed']+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout'
 selected[part].append(item)
with (root/'contexts.unqualified.jsonl').open('x') as out:
 for part,items in selected.items():
  for item in items:out.write(json.dumps(dict(item,provisionalSplit=part),ensure_ascii=False)+'\n')
report=dict(stage='availability-only-not-qualified',scannedArticles=scanned,eligibleArticles=eligible,eligibleFamilies=len(pools),selected={k:len(v) for k,v in selected.items()},families={k:len({r['family'] for r in v}) for k,v in selected.items()},sourceSha256=sha(source),modelCalls=0,blockedPriorArticles=len(blocked_articles),candidateContextsSha256=sha(root/'contexts.unqualified.jsonl'),preparerSha256=sha(__file__),readyForOriginalNaturalGate=all(len(v)>=plan['contextsPerPart'] and len({r['family'] for r in v})>=plan['minimumFamiliesPerPart'] for v in selected.values()))
(root/'availability.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
