"""Predeclared finite controls. Independent edit graph + preserved source-only reference."""
from pathlib import Path
import heapq,itertools,json,hashlib,importlib.util
import argparse
B=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
C=p.parse_args().output;C.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('reference',B/'reference.py');ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def words(alphabet,n):return ['']+[''.join(w) for k in range(1,n+1) for w in itertools.product(alphabet,repeat=k)]
def graph(source,alphabet,weighted):
 best={source:0};pending=[(0,source)]
 while pending:
  cost,w=heapq.heappop(pending)
  if best[w]!=cost:continue
  edges=[]
  for i,c in enumerate(w):
   edges.append((w[:i]+w[i+1:],4))
   for other in alphabet:
    if other!=c:
     adjacent=frozenset((c,other)) in [frozenset('as'),frozenset('sd'),frozenset('aw')]
     edges.append((w[:i]+other+w[i+1:],3 if weighted and adjacent else 4))
   if i+1<len(w) and c!=w[i+1]:edges.append((w[:i]+w[i+1]+c+w[i+2:],5 if weighted else 4))
  if len(w)<4:
   for i in range(len(w)+1):
    for c in alphabet:edges.append((w[:i]+c+w[i:],4))
  for nxt,weight in edges:
   nc=cost+weight
   if nc<best.get(nxt,10**9):best[nxt]=nc;heapq.heappush(pending,(nc,nxt))
 return best
bounds=[];groups=[];requests=[];cid=0
for alphabet in ('asd','adw'):
 ws=words(alphabet,3)
 for source in ws:
  u=graph(source,alphabet,False);w=graph(source,alphabet,True)
  for target in ws:bounds.append([ref.hex_units(source),ref.hex_units(target),0,u[target]//4,w[target]])
 dictionaries={0:{w:1 for i,w in enumerate(ws[1:]) if i%3==0},2:{w:1 for i,w in enumerate(ws[1:]) if i%3==1}}
 for q in ws[1:]:groups.append(dictionaries);requests.append((cid,q,0));cid+=1
for source,target,lang in [('ca','abc',0),('a cat','an act',0),('aabb','abab',0),('aaabb','abbbb',0),('𐐨a','a𐐨',0),('е','ё',1),('n','ñ',2),('café','cafe',2),('a'*32,'a'*31+'b',0)]:
 bounds.append([ref.hex_units(source),ref.hex_units(target),lang,ref.distance(source,target,ref.LANGS[lang],False)//4,ref.distance(source,target,ref.LANGS[lang])])
manual=[
 ('l',0,{0:{'ñ':1,'a':2,'b':3,'c':4,'d':5,'e':6},2:{'k':1,'p':2,'ñ':3}}),
 ('İ',0,{0:{'in':1,'it':1},2:{'ib':1}}),
 ('Sßab',0,{0:{'ßab':1,'ssab':1},2:{'ssab':1}}),
 ('S'+'a'*31,0,{0:{'ß'+'a'*31:1,'x'+'a'*31:2},2:{'z':1}}),
 ('елка',1,{1:{'ёлка':1,'елька':2}}),
 ('nino',2,{2:{'niño':1,'nina':2},0:{'nine':1}}),
 ('piñ',0,{2:{'piña':1}}),
 ('cafe\u0301s',2,{2:{'café':1,'cafésa':2}}),
 ('S',0,{0:{'ſ':1,'ß':2},2:{'s':1}}),
 ('S',0,{0:{'ſ':1,'ß':2},2:{'z':1}}),
 ('𐐨a',0,{0:{'a':1},2:{'b':1}}),
 ('a/b',0,{0:{'ab':1},2:{'b':1}}),
 ('ABC',0,{0:{'ab':1},2:{'b':1}}),
 ('catt',0,{0:{'cat':1},2:{'catt':1}}),
 ('zzzz',0,{0:{'a':1},2:{'b':1}}),
 ('a'*33,0,{0:{'a':1},2:{'b':1}}),
]
for q,active,d in manual:groups.append(d);requests.append((cid,q,active));cid+=1
dictrows=[];expected=[];inputrows=[]
for (cid,query,active),dictionaries in zip(requests,groups):
 reason=ref.protection(query);routes=ref.routes(query,active);key=ref.folded(query);case=ref.pattern(query)
 valid=any(key in dictionaries.get(lang,{}) for lang in routes)
 status=1 if reason>=0 else 2 if valid else 0
 raw=[]
 for lang,dictionary in dictionaries.items():
  for word,rank in dictionary.items():dictrows.append([cid,lang,ref.hex_units(word),rank])
 if status==0:
  for ri,lang in enumerate(routes):
   for word,rank in dictionaries.get(lang,{}).items():
    unit=ref.distance(key,word,ref.LANGS[lang],False)//4
    if not 1<=unit<=(1 if len(key)<5 else 2):continue
    display=ref.preserve(word,case);displaykey=ref.folded(display) if display is not None else ''
    raw.append({'terminal':word,'display':display or '', 'key':displaykey,'language':lang,'frequency':rank,'prior':4 if ri==0 else 1,'fallback':int(ri>0),'unit':unit,'quarters':ref.distance(key,word,ref.LANGS[lang]),'repeats':ref.repeats(key,word),'length':abs(len(key)-len(word)),'case':case,'admitted':display is not None and displaykey!=key})
 selected=ref.select(raw)
 inputrows.append([cid,ref.hex_units(query),active,status,reason,len(selected)])
 for pos,c in enumerate(selected):expected.append([cid,pos,c['language'],ref.hex_units(c['terminal']),ref.hex_units(c['display']),ref.hex_units(c['key']),c['frequency'],c['prior'],c['fallback'],c['unit'],c['quarters'],c['repeats'],c['length'],c['case']])
for name,rows in [('bounds.tsv',bounds),('dictionaries.tsv',dictrows),('requests.tsv',inputrows),('expected.tsv',expected)]:
 p=C/name;assert not p.exists();p.write_text(''.join('\t'.join(map(str,r))+'\n' for r in rows))
(C/'MANIFEST.json').write_text(json.dumps({'schema':1,'requests':len(requests),'bound_pairs':len(bounds),'source':'two finite edit-graph alphabets plus predeclared Unicode/route/case controls','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in C.glob('*.tsv')}},indent=2)+'\n')
print('CONTROL_FIXTURES',len(requests),'BOUND_PAIRS',len(bounds))
