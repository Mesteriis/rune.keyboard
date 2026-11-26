from pathlib import Path
import json,collections,hashlib,struct
root=Path('build/context-ranking-20261025/counts-v3');c=collections.Counter();rows=[]
for line in (root/'word-context-counts.jsonl').read_text().splitlines():
 a,b,n,d=json.loads(line);c.update({k:int(n>=k) for k in [2,3,5,8,10,16]})
 if n>=5:rows.append((a,b,n,d))
print('Pair counts',dict(c));rows.sort(key=lambda r:(-r[2],-r[3],r[0],r[1]));rows=rows[:500000];rows.sort(key=lambda r:(r[0],r[1]));words=sorted({w for r in rows for w in r[:2]});ids={w:i for i,w in enumerate(words)};assert len(words)<=50000
blob=bytearray(b'RWB1'+struct.pack('<III',1,len(words),len(rows)))
for word in words:
 raw=word.encode();blob+=struct.pack('<H',len(raw))+raw
for a,b,n,d in rows:blob+=struct.pack('<HHHH',ids[a],ids[b],min(n,65535),min(d,65535))
p=root/'ru-word-context.bin';p.write_bytes(blob);pins={'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'pairs':len(rows),'vocabulary':len(words),'minimumStoredCount':5,'maximumPairs':500000,'containsPrivateText':False};(root/'model-receipt.json').write_text(json.dumps(pins,indent=2)+'\n');print(pins);print('needed entry',[r for r in rows if r[0]=='нужен' and r[1]=='новый'])
(root/'model-counts.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
