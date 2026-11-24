import sys,json,hashlib,unicodedata,collections,re,struct
from pathlib import Path
import pyarrow.parquet as pq
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as joint
root=Path('build/joint-correction-20261025');work=Path('build/context-ranking-20261025');out=work/'corpus';out.mkdir()
receipt=json.loads((work/'counts-v3/receipt.json').read_text());supported={tuple(json.loads(s)[:2]) for s in (work/'counts-v3/model-counts.jsonl').read_text().splitlines()}
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s}
b=Path('app/src/main/assets/smarttyping/lexicon/ru.morph').read_bytes();width,n,_,pos=struct.unpack_from('<IIII',b,8);prev=b'';families={}
for i in range(n):
 if i%width==0:prev=b''
 pre,size,lemma=struct.unpack_from('<BBI',b,pos);prev=prev[:pre]+b[pos+6:pos+6+size];pos+=6+size
 w=prev.decode()
 if w in known:families[w]=str(lemma) if lemma else 'form:'+w
excluded=set();tails=collections.defaultdict(set)
for name,h in receipt['priorRowBindings'].items():
 p=Path(name);assert joint.common.sha256(p)==h
 for line in p.read_text().splitlines():
  r=json.loads(line)
  if r.get('partition',r.get('split'))=='train':continue
  article=r.get('article',r.get('articleId'))
  if article is not None:excluded.add(str(article))
  prefix=unicodedata.normalize('NFC',r.get('prefix','')).rstrip()
  if len(prefix)>=20:tails[prefix[-20:]].add(prefix[-32:])
pools={p:collections.defaultdict(list) for p in ['calibration','holdout']}
for source in [root/'0018.parquet',root/'0019.parquet']:
 assert joint.common.sha256(source)==receipt['sources'][str(source)]
 for batch in pq.ParquetFile(source).iter_batches(batch_size=64,columns=['id','text']):
  for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
   bucket=hashlib.sha256(('rune-word-context-v1:'+str(article)).encode()).digest()[0]%5
   if bucket<3 or str(article) in excluded:continue
   part='calibration' if bucket==3 else 'holdout';text=unicodedata.normalize('NFC',text or '');matches=list(joint.WORDS.finditer(text))
   def prior(m):
    head=text[max(0,m.start()-160):m.start()].rstrip();return any(head.endswith(t) for t in tails.get(head[-20:],()))
   if any(prior(m) for m in matches):continue
   for ordinal,m in enumerate(matches):
    word=m.group().casefold();family=families.get(word)
    if ordinal<4 or not m.group().islower() or not 3<=len(word)<=12 or family is None:continue
    family_part='calibration' if hashlib.sha256(('rune-word-context-family:'+family).encode()).digest()[0]%2==0 else 'holdout'
    if family_part!=part:continue
    prefix=joint.GENERATOR.bounded_prefix(text[max(0,m.start()-256):m.start()]).rstrip();previous=prefix.split()[-1].casefold() if prefix.split() else ''
    if not re.fullmatch('[а-яё]{1,20}',previous) or (previous,word) not in supported:continue
    identity=hashlib.sha256(('rune-word-context-selection:'+str(article)+word+prefix).encode()).hexdigest();item=dict(word=word,family=family,prefix=prefix,article=str(article),source=source.name,selectionHash=identity)
    pool=pools[part][family]
    if any(x['article']==str(article) for x in pool):continue
    pool.append(item);pool.sort(key=lambda x:x['selectionHash']);del pool[2:]
 print('Scanned',source.name,{p:len(d) for p,d in pools.items()},flush=True)
manifest={'schemaVersion':1,'stage':'frozen-before-calibration-or-holdout-scores','seed':'rune-word-context-v1','wordContextModelSha256':json.loads((work/'counts-v3/model-receipt.json').read_text())['sha256'],'articleBuckets':{'training':[0,1,2],'calibration':[3],'holdout':[4]},'selection':'Supported public word pairs, 120 short and 380 long family keys; unique-lemma IDs with explicit surface-form fallback when lemma is ambiguous. No guarantee that ambiguous surface keys identify distinct lexical lemmas.','partitions':{}}
sets={};articles={}
for part,pool in pools.items():
 rows=[];selected=set()
 for short,quota in [(True,120),(False,380)]:
  eligible=sorted([f for f,items in pool.items() if (len(items[0]['word'])<=4)==short],key=lambda f:hashlib.sha256(('word-context:'+part+f).encode()).hexdigest())
  print(part,'short' if short else 'long','available',len(eligible),flush=True)
  if len(eligible)<quota:raise ValueError('INSUFFICIENT_FAMILY_KEYS')
  for f in eligible[:quota]:
   selected.add(f)
   for item in pool[f][:2 if short else 1]:
    forms=joint.variants(item['word'],known,'word-context:'+item['selectionHash'])[:4]
    for typed,group in forms+[(item['word'],'correct'),('@'+item['word'],'protected')]:
     control=group in ['correct','protected'];rows.append(dict(item,id=f'word-context-{part}-{len(rows):06d}',split=part,language='ru',band='short' if short else 'long',group=group,typed=typed,expectedSpelling=typed if control else item['word'],cohort=group if control else 'typo',noAuto=control))
 p=out/(part+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));sets[part]=selected;articles[part]={r['article'] for r in rows};manifest['partitions'][part]={'rows':len(rows),'familyKeys':len(selected),'articles':len(articles[part]),'sha256':joint.common.sha256(p),'groups':dict(collections.Counter(r['group'] for r in rows))}
assert not sets['calibration']&sets['holdout'] and not articles['calibration']&articles['holdout']
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest['partitions']),flush=True)
