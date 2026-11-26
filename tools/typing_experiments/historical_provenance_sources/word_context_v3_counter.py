import sys,json,hashlib,re,collections,unicodedata
from pathlib import Path
import pyarrow.parquet as pq
sys.path.insert(0,'tools/typing_experiments');import prepare_external_spelling_holdout as c
root=Path('build/joint-correction-20261025');work=Path('build/context-ranking-20261025');out=work/'counts-v3';out.mkdir()
files={}
for folder in Path('build/typing-ranker-v2').glob('external-holdout-v*-ru*'):
 p=folder/'manifest.json'
 if not p.exists():continue
 v=json.loads(p.read_text()).get('source',{})
 if v.get('repository')=='https://huggingface.co/datasets/wikimedia/wikipedia' and 'sha256' in v:
  name=Path(v['path']).stem;files[Path('build/typing-ranker-v2')/('ru-'+name+'.parquet')]=v['sha256']
for e in json.loads((root/'public-source-lock.json').read_text())['files']:files[root/Path(e['path']).name]=e['lfs']['oid']
assert len(files)==9
for p,h in files.items():assert c.sha256(p)==h
freq=Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt');assert c.sha256(freq)==c.FREQUENCY_SHA256
known={s.split()[0] for s in freq.read_text().splitlines() if s and re.fullmatch('[а-яё]{1,20}',s.split()[0])}
excluded=set();tails=collections.defaultdict(set);bindings={}
paths=set(Path('build/typing-ranker-v2').rglob('*rows.jsonl'))
for folder in [root/'corpus',root/'followup-corpus',root/'followup-corpus-v3',Path('build/diagnostic-rare-ranking/fresh-corpus')]:
 paths.update(p for p in folder.glob('*.jsonl') if p.stem in ['calibration','holdout'])
for p in sorted(paths):
 bindings[str(p)]=c.sha256(p)
 for line in p.read_text().splitlines():
  r=json.loads(line)
  if r.get('partition',r.get('split'))=='train':continue
  article=r.get('article',r.get('articleId'))
  if article is not None:excluded.add(str(article))
  prefix=unicodedata.normalize('NFC',r.get('prefix','')).rstrip()
  if len(prefix)>=20:tails[min(32,len(prefix))].add(prefix[-32:])
tail_index=collections.defaultdict(set)
for endings in tails.values():
 for ending in endings:tail_index[ending[-20:]].add(ending)
words=re.compile('[а-яёА-ЯЁ]+');counts=collections.Counter();docs=collections.Counter();articles=0;tokens=0;overlap=0
for source,digest in sorted(files.items()):
 for batch in pq.ParquetFile(source).iter_batches(batch_size=64,columns=['id','text']):
  for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
   if str(article) in excluded or hashlib.sha256(('rune-word-context-v1:'+str(article)).encode()).digest()[0]%5>=3:continue
   text=unicodedata.normalize('NFC',text or '');matches=list(words.finditer(text))
   def observed_before(m):
    head=text[max(0,m.start()-160):m.start()].rstrip()
    return any(head.endswith(ending) for ending in tail_index.get(head[-20:],()))
   if any(observed_before(m) for m in matches):overlap+=1;continue
   articles+=1;seen=set();previous=None;end=0
   for m in matches:
    word=m.group().casefold();gap=text[end:m.start()];end=m.end()
    if previous and word in known and previous in known and 3<=len(word)<=20 and gap.isspace():
     pair=(previous,word);counts[pair]+=1;seen.add(pair);tokens+=1
    previous=word
   docs.update(seen)
 print(source.name,'articles',articles,'pairs',len(counts),flush=True)
selected={a:(n,docs[a]) for a,n in counts.items() if n>=2 and docs[a]>=2}
p=out/'word-context-counts.jsonl';p.write_text(''.join(json.dumps([*pair,*selected[pair]],ensure_ascii=False)+'\n' for pair in sorted(selected)))
(out/'receipt.json').write_text(json.dumps({'sources':{str(p):h for p,h in files.items()},'frequencySha256':c.sha256(freq),'excludedArticleIds':len(excluded),'excludedTailOverlaps':overlap,'priorRowBindings':bindings,'articles':articles,'tokens':tokens,'pairs':len(selected),'seed':'rune-word-context-v1','trainArticleBuckets':[0,1,2],'countsSha256':c.sha256(p)},indent=2)+'\n')
for prefix in ['нужен','с','о','мой','для']:
 print(prefix,[(word,counts[(prefix,word)],docs[(prefix,word)]) for word in ['новый','новой','ной','нова','ново']],flush=True)
print('Done',articles,tokens,len(selected),flush=True)
