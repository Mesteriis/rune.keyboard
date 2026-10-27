from pathlib import Path
import sys,json,hashlib,collections,re,unicodedata,functools,base64
import pyarrow;pyarrow.set_cpu_count(2)
import pyarrow.parquet as parquet
sys.path.insert(0,'tools/typing_experiments')
from right_context_corpus_separation import exclusion_records
from right_context_side_forms import grammar_word_sets,non_predicate_contrast
from right_context_focus_forms import predicate_contrast,source_surface_refusal
from right_context_grammar_features import RightContextGrammarFeatures,FEATURE_NAMES,completed_following_words
import prepare_joint_correction as existing
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-fresh-side-v4-20261027');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text());normalize=lambda s:' '.join(unicodedata.normalize('NFC',s).casefold().split())
model=load('build/right-context-training-v4-20261027/frozen-model.json');assert sha('build/right-context-training-v4-20261027/experimental-ranker.bin')==model['modelSha256']
parents=[Path('build/right-context-wikipedia-20261027')]+[Path('build/right-context-wiki'+s+'-20261027') for s in ['0012','0013','0014','0015','0016','0017']]
sources=[Path('build/joint-correction-20261025/0020.parquet')]+[Path('build/typing-ranker-v2/ru-'+s+'.parquet') for s in ['0012','0013','0014','0015','0016','0017']]
seed='right-context-fresh-role-v4-20261027';bindings=dict(load(parents[0]/'plan.json')['exclusionBindings']);bindings.update({str(Path(base)/'corpus'/(part+'.jsonl')):sha(Path(base)/'corpus'/(part+'.jsonl')) for base in ['build/right-context-natural-frozen-20261027','build/right-context-side-20261027'] for part in ['calibration','holdout']});grammar=Path('app/src/main/assets/smarttyping/experiments/ru-context.gram');grammarHash='2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b'
plan=dict(stage='frozen-before-side-corpus-selection-and-model-scoring',seed=seed,modelSha256=model['modelSha256'],trainingPlanSha256=sha('build/right-context-training-v4-20261027/plan.json'),surfaceGuardSha256=sha('tools/typing_experiments/right_context_focus_forms.py'),excludedPreviouslyDisclosedFamilies=True,grammarSha256=grammarHash,sourceBindings={str(p):load(parent/'availability.json')['sourceSha256'] for p,parent in zip(sources,parents)},exclusionBindings=bindings,sourceContextBindings={str(parent/'contexts.unqualified.jsonl'):sha(parent/'contexts.unqualified.jsonl') for parent in parents},maximumContextsPerFamilyWithinGroupAndPart=20,maximumContextsPerFamily=20,maximumContextsPerGroupAndPart=400,minimumNegativeContextsPerPart=300,minimumPositiveSubjectContextsPerPart=100,minimumFamiliesPerPart=20,modelCalls=0,scopeTypes=['direct_subject_positive','agreement_role_negative','hard_other_part_negative','ordinary_other_part_negative'],formsSha256=sha('tools/typing_experiments/right_context_side_forms.py'),originalVetoEnvironment='Public-only synthetic evaluation',modelScoresMayAffectSelection=False)
with (root/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
for p,h in plan['sourceBindings'].items():assert sha(p)==h
predicates,nominatives=grammar_word_sets(grammar.read_bytes(),grammarHash)
frequency=Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt');assert sha(frequency)=='6095f507cc167488ec66ada5a85ac50433503a08ad24a07c6eabdf54352c4e7f';known={line.split()[0] for line in frequency.read_text().splitlines() if line}
blocked_articles=set();blocked_forms=set();disclosed_families=set()
for name,h in bindings.items():
 assert sha(name)==h
 for row in exclusion_records(Path(name)):
  disclosed_families.update(row.get('families',[]));disclosed_families.update([row['family']] if row.get('family') else []);article=str(row.get('article',''))
  if article.isdigit():blocked_articles.add(article)
  if row.get('purpose')=='AUTHORED_CONTRAST_TRAINING_ONLY':blocked_forms.update(row['contrastCandidates'])
for parent in parents:
 for line in (parent/'contexts.unqualified.jsonl').open():blocked_articles.add(json.loads(line)['article'])
lex=PymorphyLexicon(cache_size=16384);features=RightContextGrammarFeatures(lex);blocked_families=disclosed_families|set(model['trainingFamilies'])|{a.lemma for w in blocked_forms for a in lex.analyses(w)}
for row in load('tools/typing_experiments/fixtures/conversation_supervised_false_proposals_20261026.json')['cases']:
 for key in ['expectedSpelling','rejectedProposal']:blocked_families.update(a.lemma for a in lex.analyses(row[key]))
copulas={'буду','будешь','будет','будем','будете','будут','был','была','было','были'}
right_words=(nominatives & known)|copulas
part_for=lambda family:'calibration' if hashlib.sha256((seed+':family:'+family).encode()).digest()[0]%2==0 else 'holdout'
@functools.lru_cache(maxsize=16384)
def info(word):
 tags=lex.analyses(word)
 if not tags:return None
 families={a.lemma for a in tags}
 if families & blocked_families or len({part_for(f) for f in families})!=1:return None
 pure=all(a.pos=='ADJS' for a in tags)
 pair=None
 if pure:
  lex._load();forms={p.word for parsed in lex._analyzer.parse(word) for p in parsed.lexeme if parsed.normal_form in families};pair=predicate_contrast(word,lex,forms)
 else:pair=non_predicate_contrast(word,lex,predicates)
 if pair:
  families|={pair.get('rivalFamily',pair['family'])}
  if families & blocked_families or len({part_for(f) for f in families})!=1:return None
 return dict(tags=tags,families=sorted(families),part=part_for(next(iter(families))),pure=pure,pair=pair)
@functools.lru_cache(maxsize=16384)
def ordinary(word):
 for typed,kind in existing.GENERATOR.safe_typos(word,'ru',known,seed+':side:'+word):
  if 3<=len(typed)<=32 and not lex.analyses(typed):return typed
 return None
pattern=re.compile(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?P<right>[а-яё]{1,32})(?![\w-])')
pools=collections.defaultdict(list);seen=set();scanned=eligible=0
priority={'hard_other_part_negative':0,'agreement_role_negative':1,'direct_subject_positive':2,'ordinary_other_part_negative':3}
for source in sources:
 for batch in parquet.ParquetFile(source).iter_batches(batch_size=64,columns=['id','text']):
  for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
   article=str(article);scanned+=1
   if article in blocked_articles:continue
   text=unicodedata.normalize('NFC',text or '');folded=text.lower()
   if len(text)!=len(folded):continue
   choices=[]
   for match in pattern.finditer(folded):
    word=match['word'];following=match['right']
    if source_surface_refusal(text[match.start('word'):match.end('word')],word):continue
    if following not in right_words or word not in known and word not in predicates:continue
    item=info(word)
    if item is None:continue
    prefix=existing.GENERATOR.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip(' \t');suffix=text[match.end('word'):match.end('word')+128]
    values=dict(zip(FEATURE_NAMES,features.extract(suffix,word)))
    if not (values['right_copula_available'] or values['right_subject_available']) or not completed_following_words(suffix):continue
    supported=(values['right_copula_number_supported'] or values['right_subject_number_supported']) and not any(values[k] for k in ['right_copula_number_conflict','right_subject_number_conflict','right_copula_gender_conflict','right_subject_gender_conflict'])
    pair=item['pair']
    if item['pure']:
     if pair is None:continue
     if following in copulas and supported:continue
     group='direct_subject_positive' if supported else 'agreement_role_negative'
    else:group='hard_other_part_negative' if pair else 'ordinary_other_part_negative'
    typed=pair['typed'] if pair else ordinary(word)
    if typed is None:continue
    key=hashlib.sha256(normalize(prefix+' '+word+suffix).encode()).hexdigest()
    if key in seen:continue
    seen.add(key);selection=hashlib.sha256((seed+':side:'+article+word+prefix).encode()).hexdigest()
    choices.append(dict(word=word,typed=typed,rival=pair['rival'] if pair else None,family=pair['family'] if pair else item['families'][0],families=item['families'],part=item['part'],prefix=prefix,rightContext=suffix,sideGroup=group,rightCue='copula' if following in copulas else 'subject',article=article,source=source.name,contextHash=key,selectionHash=selection))
   if not choices:continue
   candidate=min(choices,key=lambda r:(priority[r['sideGroup']],r['selectionHash']));eligible+=1
   bucket=pools[candidate['part'],candidate['sideGroup'],candidate['family']];bucket.append(candidate);bucket.sort(key=lambda r:r['selectionHash']);del bucket[plan['maximumContextsPerFamily']:]
 print('SOURCE_COLLECTED',source.name,'articles',scanned,'eligible',eligible,flush=True)
selected={part:[] for part in ['calibration','holdout']}
for part in selected:
 for group in priority:
  candidates=sorted([r for (p,g,f),items in pools.items() if p==part and g==group for r in items],key=lambda r:r['selectionHash'])
  selected[part].extend(candidates[:plan['maximumContextsPerGroupAndPart']])
availability=dict(scannedArticles=scanned,eligibleArticles=eligible,grammarPredicates=len(predicates),grammarNominatives=len(nominatives),blockedArticles=len(blocked_articles),parts={part:dict(contexts=len(items),groups=dict(collections.Counter(r['sideGroup'] for r in items)),families=len({f for r in items for f in r['families']}),cueTypes=dict(collections.Counter(r['rightCue'] for r in items))) for part,items in selected.items()})
(root/'availability.json').write_text(json.dumps(availability,indent=2)+'\n');print(json.dumps(availability),flush=True)
with (root/'contexts.unqualified.jsonl').open('x') as out:
 for items in selected.values():
  for r in items:out.write(json.dumps(r,ensure_ascii=False)+'\n')
assert all(sum(r['sideGroup']!='direct_subject_positive' for r in items)>=plan['minimumNegativeContextsPerPart'] and sum(r['sideGroup']=='direct_subject_positive' for r in items)>=plan['minimumPositiveSubjectContextsPerPart'] and len({f for r in items for f in r['families']})>=plan['minimumFamiliesPerPart'] for items in selected.values()),'INSUFFICIENT_SIDE_COHORT'
assert not ({f for r in selected['calibration'] for f in r['families']}&{f for r in selected['holdout'] for f in r['families']})
assert not ({r['article'] for r in selected['calibration']}&{r['article'] for r in selected['holdout']})
assert not ({r['contextHash'] for r in selected['calibration']}&{r['contextHash'] for r in selected['holdout']})
out=root/'corpus';out.mkdir();files={};counts={}
for part,items in selected.items():
 rows=[]
 for item in items:
  variants=[(item['typed'],'typo',False,False,item['rightContext']),(item['typed'],'unfinished',False,True,' '+completed_following_words(item['rightContext'])[0]),(item['word'],'correct',True,False,item['rightContext']),('@'+item['word'],'protected',True,False,item['rightContext'])]
  if item['rival']:variants.append((item['rival'],'correct_rival',True,False,item['rightContext']))
  for typed,group,control,retain,suffix in variants:
   rows.append(dict(item,id=f'right-side-{part}-{len(rows):06d}',split=part,language='ru',typed=typed,rightContext=suffix,group=group,noAuto=control,retainBaseline=retain,expectedSpelling=typed if control else item['word']))
 path=out/(part+'.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[path.name]=sha(path)
 enc=lambda s:base64.b64encode(s.encode()).decode();tsv=out/(part+'.tsv');tsv.write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)));files[tsv.name]=sha(tsv)
 counts[part]=dict(rows=len(rows),contexts=len(items),controls=sum(r['noAuto'] for r in rows),unfinishedControls=sum(r['retainBaseline'] for r in rows),groups=availability['parts'][part]['groups'])
manifest=dict(stage='frozen-before-side-calibration-and-holdout-scoring',files=files,counts=counts,planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),modelSha256=model['modelSha256'],sourceLicense=['CC-BY-SA-3.0','GFDL-1.3'],sourceBindings=plan['sourceBindings'],excludedFamilies=sorted(blocked_families),exclusionBindings=bindings,familyArticleAndContextSeparation=True,modelCalls=0,limitations=['Natural public contexts with synthetic corruptions; not observed human typing','Role-negative labels restore the printed source form; semantic ambiguity requires separate review','Nonoverlapping word pairs and adversarial-priority sampling; not a natural error-rate estimate'])
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('SIDE_CORPUS_FROZEN',json.dumps(counts),flush=True)
