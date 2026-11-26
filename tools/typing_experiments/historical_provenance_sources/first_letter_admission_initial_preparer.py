import sys,json,struct,hashlib
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'tools/typing_experiments')
import prepare_joint_correction as j
import pyarrow.parquet as pq
root=Path('build/joint-correction-20261025'); out=Path('build/first-letter-admission')
blob=Path('app/src/main/assets/smarttyping/lexicon/ru.morph').read_bytes()
width,count,_,pos=struct.unpack_from('<IIII',blob,8); prev=b''; ambiguous=set()
for i in range(count):
 if i%width==0:prev=b''
 prefix,size,lemma=struct.unpack_from('<BBI',blob,pos);prev=prev[:prefix]+blob[pos+6:pos+6+size];pos+=6+size
 if lemma==0:ambiguous.add(prev.decode())
known={x.split()[0] for x in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines()}
wanted={w for w in ambiguous&known if 5<=len(w)<=20}
excluded_articles=set();excluded_words=set()
for folder in ['corpus','followup-corpus','followup-corpus-v3']:
 for p in (root/folder).glob('*.jsonl'):
  for line in p.read_text().splitlines():
   r=json.loads(line);excluded_articles.add(r['article']);excluded_words.add(r['word'])
pool=defaultdict(list)
for batch in pq.ParquetFile(root/'0020.parquet').iter_batches(batch_size=128,columns=['id','text']):
 for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
  if str(article) in excluded_articles:continue
  for m in j.WORDS.finditer(text or ''):
   word=m.group().casefold()
   if word not in wanted or word in excluded_words:continue
   prefix=j.GENERATOR.bounded_prefix(text[max(0,m.start()-256):m.start()]).rstrip()
   if not prefix:continue
   key=hashlib.sha256(('ambiguous-v1:'+str(article)+word+prefix).encode()).hexdigest()
   item=dict(word=word,family='surface:'+word,prefix=prefix,article=str(article),source='0020.parquet',selectionHash=key)
   pool[item['family']].append(item);pool[item['family']].sort(key=lambda x:x['selectionHash']);del pool[item['family']][1:]
rows=j.rows_from_pool(pool,'holdout',known)
path=out/'holdout.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
manifest=dict(stage='frozen-before-admission-rule-replay',rows=len(rows),surfaceFamilies=len(pool),rowsSha256=hashlib.sha256(path.read_bytes()).hexdigest(),protocol='Existing scores and margins unchanged. Only long ambiguous morphology winners, complete unique distance-one local winner and complete joint comparison. New-replacement precision >=99%, at least 100 correct and 20 surface families; zero control changes, correct-to-wrong, prefix or Undo failures. Surface-disjoint only: ambiguous lemma IDs unavailable. Excluded all prior selected articles and words. No fitting on results.',model=j.common.sha256(Path('app/src/main/assets/smarttyping/experiments/ru-joint-ranker.bin')),source=j.common.sha256(root/'0020.parquet'))
(out/'frozen-protocol.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
