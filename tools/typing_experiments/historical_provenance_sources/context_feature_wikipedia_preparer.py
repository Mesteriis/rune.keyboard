from pathlib import Path
import sys,json,hashlib,re,unicodedata,collections,base64
import pyarrow.parquet as pq
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
root=Path('build/context-feature-ranker-20261026');out=root/'corpus';out.mkdir(exist_ok=True);assert not list(out.iterdir())
source=Path('build/joint-correction-20261025/0020.parquet');lock=json.loads(Path('build/joint-correction-20261025/followup-source-lock.json').read_text());entry=next(x for x in lock['files'] if x['path'].endswith('0020.parquet'));assert j.common.sha256(source)==entry['lfs']['oid'] and source.stat().st_size==entry['size']
freq=Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt');assert j.common.sha256(freq)==j.common.FREQUENCY_SHA256
known={s.split()[0] for s in freq.read_text().splitlines() if re.fullmatch('[а-яё]{3,12}',s.split()[0])};lemmas=j.morphology(known)
prior=set(Path(x) for x in json.loads(Path('build/context-ranking-20261025/counts-v3/receipt.json').read_text())['priorRowBindings'])
for folder in [Path('build/joint-correction-20261025'),Path('build/context-ranking-20261025')]:
 for directory in folder.glob('*corpus*'):
  if directory.is_dir():prior.update(directory.glob('*.jsonl'))
prior.add(Path('build/joint-correction-20261025/corpus/train.jsonl'))
articles=set();families=set();tails=set();bindings={}
for path in sorted(prior):
 if not path.is_file():continue
 bindings[str(path)]=j.common.sha256(path)
 for line in path.read_text().splitlines():
  r=json.loads(line);a=r.get('article',r.get('articleId'))
  if a is not None:articles.add(str(a))
  word=next((r[k] for k in ['word','expectedSpelling','expectedCandidate','typed'] if isinstance(r.get(k),str)), '').casefold()
  if word in lemmas:families.add(lemmas[word])
  f=r.get('family')
  if f:families.add(str(f))
  prefix=unicodedata.normalize('NFC',r.get('prefix','')).rstrip()
  if len(prefix)>=32:tails.add(prefix[-32:])
seed='rune-context-feature-probe-20261026-v1'
def partition(namespace,value):return 'calibration' if hashlib.sha256((seed+namespace+value).encode()).digest()[0]<128 else 'holdout'
pools={k:{} for k in ['calibration','holdout']}
for batch in pq.ParquetFile(source).iter_batches(batch_size=128,columns=['id','text']):
 for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
  article=str(article)
  if article in articles:continue
  part=partition(':article:',article);text=unicodedata.normalize('NFC',text or '')
  for ordinal,m in enumerate(j.WORDS.finditer(text)):
   word=m.group().casefold();family=lemmas.get(word)
   if ordinal<4 or not m.group().islower() or family is None or family in families or partition(':family:',family)!=part:continue
   prefix=j.GENERATOR.bounded_prefix(text[max(0,m.start()-256):m.start()]).rstrip()
   if not prefix or prefix[-32:] in tails:continue
   identity=hashlib.sha256((seed+article+word+prefix).encode()).hexdigest()
   old=pools[part].get(family)
   if old is None or identity<old['selectionHash']:pools[part][family]=dict(word=word,family=family,prefix=prefix,article=article,source=source.name,selectionHash=identity)
print('Available fresh families:',{k:len(v) for k,v in pools.items()},flush=True)
sets={};article_sets={};files={};counts={}
for part,quota in [('calibration',600),('holdout',1000)]:
 selected=sorted(pools[part].values(),key=lambda r:r['selectionHash'])[:quota];assert len(selected)==quota
 rows=[]
 for item in selected:
  word=item['word'];salt=seed+item['selectionHash'];variants=j.variants(word,known,salt)
  missing=[x for x in variants if len(x[0])==len(word)-1][:2]
  other=[x for x in variants if x not in missing][:2]
  for typed,group in missing+other+[(word,'correct'),('@'+word,'protected')]:
   control=group in ['correct','protected'];rows.append(dict(item,id=f'context-feature-{part}-{len(rows):05d}',split=part,language='ru',typed=typed,expectedSpelling=typed if control else word,group=group,cohort='correct' if control else 'typo',noAuto=control))
 sets[part]={r['family'] for r in rows};article_sets[part]={r['article'] for r in rows}
 path=out/f'{part}.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[path.name]=j.common.sha256(path);counts[part]=dict(rows=len(rows),families=len(sets[part]),groups=dict(collections.Counter(r['group'] for r in rows)))
 def enc(x):return base64.b64encode(x.encode()).decode()
 (out/f'{part}.tsv').write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)))
assert not sets['calibration']&sets['holdout'] and not article_sets['calibration']&article_sets['holdout']
manifest=dict(stage='frozen-before-model-training-and-calibration-scores',seed=seed,sourceSha256=j.common.sha256(source),priorRows=bindings,excludedArticles=len(articles),excludedLemmaOrFamilyKeys=len(families),excludedPrefixTails=len(tails),files=files,counts=counts,limits='Ranker-label lemma/article disjoint; public unsupervised pretraining may contain these words. Heldout source0020 is absent from context-count sources.')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(counts),flush=True)
