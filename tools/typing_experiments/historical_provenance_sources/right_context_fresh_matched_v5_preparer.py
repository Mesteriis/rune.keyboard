from pathlib import Path
import sys,json,hashlib,collections,re,unicodedata,functools,base64
import pyarrow;pyarrow.set_cpu_count(2)
import pyarrow.parquet as parquet
sys.path.insert(0,'tools/typing_experiments')
from right_context_focus_forms import predicate_contrast,source_surface_refusal
from right_context_corpus_separation import exclusion_records
from right_context_grammar_features import RightContextGrammarFeatures,FEATURE_NAMES
import prepare_joint_correction as existing
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-fresh-matched-v5-20261027');train=Path('build/right-context-training-v5-20261027');side=Path('build/right-context-fresh-side-v5-20261027');base=Path('build/right-context-fresh-side-v4-20261027')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text());normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split())
parent=load(base/'plan.json');source_bindings=dict(parent['sourceBindings'])
for item in load('build/joint-correction-20261025/public-source-lock.json')['files']:source_bindings['build/joint-correction-20261025/'+Path(item['path']).name]=item['lfs']['oid']
source_bindings['build/typing-ranker-v2/ru-0011.parquet']=load('build/typing-ranker-v2/external-holdout-v6-ru0011/manifest.json')['source']['sha256']
training=load(train/'corpus/manifest.json');blocked=set(load(base/'corpus/manifest.json')['excludedFamilies'])|set(training['families']);bindings=dict(parent['exclusionBindings'])
for part in ['calibration','holdout']:bindings[str(side/'corpus'/(part+'.jsonl'))]=sha(side/'corpus'/(part+'.jsonl'))
plan=dict(stage='frozen-before-fresh-matched-corpus-collection',seed=parent['seed'],contextsPerPart=400,maximumContextsPerFamily=30,minimumFamiliesPerPart=20,excludedFamilies=sorted(blocked),exclusionBindings=bindings,sourceContextBindings=parent['sourceContextBindings'],sourceBindings=source_bindings,trainingCorpusManifestSha256=sha(train/'corpus/manifest.json'),surfaceGuardSha256=sha('tools/typing_experiments/right_context_focus_forms.py'),scriptSha256=sha(__file__),modelCalls=0,sideCalibrationAlreadyScored=True,reason='Restore the separately required following-copula cohort alongside role/other-part cohorts; no threshold or count gate relaxed')
with (root/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
for p,h in source_bindings.items():assert sha(p)==h
blocked_articles=set()
for name,h in bindings.items():
 assert sha(name)==h
 for r in exclusion_records(Path(name)):
  article=str(r.get('article',''))
  if article.isdigit():blocked_articles.add(article)
for name,h in plan['sourceContextBindings'].items():
 assert sha(name)==h
 for r in exclusion_records(Path(name)):blocked_articles.add(str(r['article']))
lex=PymorphyLexicon(cache_size=16384);features=RightContextGrammarFeatures(lex)
@functools.lru_cache(maxsize=8192)
def forms(word):
 tags=lex.analyses(word)
 if not tags or any(a.pos!='ADJS' or a.lemma in blocked for a in tags):return None
 lex._load();paradigm={p.word for parsed in lex._analyzer.parse(word) for p in parsed.lexeme if parsed.normal_form in {a.lemma for a in tags}}
 return predicate_contrast(word,lex,paradigm)
pattern=re.compile(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?:буду|будешь|будет|будем|будете|будут|был|была|было|были)(?=[ \t.,!?;:]|$)')
pools=collections.defaultdict(list);seen=set();scanned=eligible=0
for source in map(Path,source_bindings):
 for batch in parquet.ParquetFile(source).iter_batches(batch_size=64,columns=['id','text']):
  for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
   article=str(article);scanned+=1
   if article in blocked_articles:continue
   text=unicodedata.normalize('NFC',text or '');folded=text.lower()
   if len(text)!=len(folded):continue
   items=[]
   for match in pattern.finditer(folded):
    if source_surface_refusal(text[match.start('word'):match.end('word')],match['word']):continue
    pair=forms(match['word'])
    if pair is None:continue
    prefix=existing.GENERATOR.bounded_prefix(text[max(0,match.start('word')-256):match.start('word')]).rstrip(' \t');suffix=text[match.end('word'):match.end('word')+128]
    target=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['word'])));rival=dict(zip(FEATURE_NAMES,features.extract(suffix,pair['rival'])))
    if target['right_copula_number_supported']!=1 or target['right_copula_number_conflict'] or rival['right_copula_number_conflict']!=1:continue
    key=hashlib.sha256(normalize(prefix+' '+pair['word']+suffix).encode()).hexdigest()
    if key in seen:continue
    seen.add(key);selection=hashlib.sha256((plan['seed']+':fresh-matched:'+article+pair['word']+prefix).encode()).hexdigest()
    items.append(dict(pair,families=[pair['family']],prefix=prefix,rightContext=suffix,article=article,source=source.name,contextHash=key,selectionHash=selection,sideGroup='matched_copula_positive'))
   if not items:continue
   item=min(items,key=lambda r:r['selectionHash']);eligible+=1;bucket=pools[item['family']];bucket.append(item);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
 print('SOURCE_COLLECTED',source.name,'articles',scanned,'eligible',eligible,flush=True)
selected={part:[] for part in ['calibration','holdout']}
for item in sorted([r for bucket in pools.values() for r in bucket],key=lambda r:r['selectionHash']):
 part='calibration' if hashlib.sha256((plan['seed']+':family:'+item['family']).encode()).digest()[0]%2==0 else 'holdout';selected[part].append(item)
availability=dict(scannedArticles=scanned,eligibleArticles=eligible,available={part:dict(contexts=len(items),families=len({r['family'] for r in items})) for part,items in selected.items()})
(root/'availability.json').write_text(json.dumps(availability,indent=2)+'\n')
with (root/'contexts.unqualified.jsonl').open('x') as f:
 for part,items in selected.items():
  for item in items:f.write(json.dumps(dict(item,provisionalSplit=part),ensure_ascii=False)+'\n')
assert all(len(items)>=plan['contextsPerPart'] and len({r['family'] for r in items[:plan['contextsPerPart']]})>=plan['minimumFamiliesPerPart'] for items in selected.values()),'INSUFFICIENT_FRESH_MATCHED_COHORT'
out=root/'corpus';out.mkdir();files={};counts={}
for part,items in selected.items():
 rows=[]
 for item in items[:plan['contextsPerPart']]:
  for typed,kind,control in [(item['typed'],'typo',False),(item['word'],'correct',True),(item['rival'],'correct_rival',True),('@'+item['word'],'protected',True)]:
   rows.append(dict(item,id=f'fresh-matched-{part}-{len(rows):06d}',split=part,language='ru',typed=typed,group=kind,noAuto=control,retainBaseline=False,expectedSpelling=typed if control else item['word']))
 path=out/(part+'.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[path.name]=sha(path);enc=lambda s:base64.b64encode(s.encode()).decode();tsv=out/(part+'.tsv');tsv.write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)));files[tsv.name]=sha(tsv)
 counts[part]=dict(rows=len(rows),contexts=plan['contextsPerPart'],families=len({r['family'] for r in rows}),controls=sum(r['noAuto'] for r in rows))
(out/'manifest.json').write_text(json.dumps(dict(stage='frozen-before-model-scoring',files=files,counts=counts,planSha256=sha(root/'plan.json'),trainingCorpusManifestSha256=sha(train/'corpus/manifest.json'),sourceBindings=source_bindings,familySplitSeed=plan['seed'],articleSeparatedFromSide=True),indent=2)+'\n');print('MATCHED_CORPUS_FROZEN',json.dumps(counts),flush=True)
