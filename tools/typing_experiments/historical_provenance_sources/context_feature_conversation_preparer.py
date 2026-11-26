from pathlib import Path
import json,sys,hashlib,base64,collections
sys.path.insert(0,'tools/typing_experiments');import prepare_joint_correction as j
root=Path('build/context-feature-ranker-20261026');out=root/'conversation-corpus';out.mkdir()
source=root/'tatoeba-sentence-splits.jsonl';lock=json.loads((root/'tatoeba-source-lock.json').read_text());assert j.common.sha256(source)==lock['sentenceSplitSha256']
known={s.split()[0] for s in Path('build/smart-typing-0.3/corpus-inputs/ru_50k.txt').read_text().splitlines() if s};lemmas=j.morphology(known)
seed='rune-unified-context-conversation-20261026-v1';pools={p:[] for p in ['calibration','holdout']};families={p:set() for p in pools}
for line in source.read_text().splitlines():
 s=json.loads(line);part=s['split']
 if part not in pools:continue
 text=s['text'];eligible=[]
 for index,m in enumerate(j.WORDS.finditer(text)):
  word=m.group().casefold();family=lemmas.get(word)
  if index<1 or not m.group().islower() or len(word)>12 or family is None:continue
  family_part='calibration' if hashlib.sha256((seed+':family:'+family).encode()).digest()[0]%2==0 else 'holdout'
  if family_part!=part:continue
  prefix=j.GENERATOR.bounded_prefix(text[:m.start()]).rstrip()
  identity=hashlib.sha256((seed+s['id']+word+prefix).encode()).hexdigest()
  eligible.append(dict(word=word,family=family,prefix=prefix,article='tatoeba:'+s['id'],sentenceHash=s['normalizedSha256'],selectionHash=identity))
 if eligible:pools[part].append(min(eligible,key=lambda x:x['selectionHash']))
manifest=dict(stage='frozen-before-unified-model-training-and-calibration-scores',sourceSha256=j.common.sha256(source),countsTrainingOnly=True,seed=seed,splitScope='Sentence and target-family disjoint between calibration/holdout; target families may occur in prior ranker training and unsupervised counts. Related sentence templates may span the source splits.',files={},counts={});articles={}
for part,pool in pools.items():
 selected=[];perfamily=collections.Counter()
 for item in sorted(pool,key=lambda x:x['selectionHash']):
  if perfamily[item['family']]>=5:continue
  perfamily[item['family']]+=1;selected.append(item)
  if len(selected)>=600:break
 print(part,'eligible contexts',len(pool),'selected',len(selected),'families',len(perfamily),flush=True)
 assert len(selected)>=400 and len(perfamily)>=100
 rows=[]
 for item in selected:
  variants=j.variants(item['word'],known,seed+item['selectionHash']);missing=next((v for v in variants if len(v[0])==len(item['word'])-1),None);other=next((v for v in variants if v!=missing),None)
  if missing is None or other is None:continue
  for typed,group in [missing,other,(item['word'],'correct'),('@'+item['word'],'protected')]:
   control=group in ['correct','protected'];rows.append(dict(item,id=f'unified-conversation-{part}-{len(rows):05d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],group=group,cohort='correct' if control else 'typo',noAuto=control))
 families[part]={r['family'] for r in rows};articles[part]={r['article'] for r in rows}
 p=out/f'{part}.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));manifest['files'][p.name]=j.common.sha256(p);manifest['counts'][part]=dict(rows=len(rows),families=len(families[part]),sentences=len(articles[part]))
 def e(x):return base64.b64encode(x.encode()).decode()
 (out/f'{part}.tsv').write_text(''.join('\t'.join([str(i),e(r['id']),part,'ru',e(r['prefix']),e(r['typed'])])+'\n' for i,r in enumerate(rows)))
assert not families['calibration']&families['holdout'] and not articles['calibration']&articles['holdout']
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
