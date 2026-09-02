import sys,array,hashlib,json,mmap,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[1]
def emit(path,data):
 if '--check' in sys.argv:assert path.read_bytes()==data, str(path)
 else:path.write_bytes(data)
manifest=[]
for lang in ('en','es','ru'):
 lengths=array.array('B',(len(w.rstrip('\n')) for w in (ROOT.parent/'lexicon-prototype/outputs'/f'{lang}.words.txt').open()))
 f=(ROOT/'assets'/f'{lang}.trie').open('rb');b=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);nodes=struct.unpack_from('<I',b,8)[0]
 data=bytearray([33,0])*nodes
 for n in range(nodes-1,-1,-1):
  child=struct.unpack_from('<I',b,16+n*16+4)[0];terminal=struct.unpack_from('<I',b,16+n*16+12)[0]
  lo=hi=lengths[terminal-1] if terminal else 0
  if not terminal:lo=33
  while child:
   lo=min(lo,data[child*2]);hi=max(hi,data[child*2+1]);child=struct.unpack_from('<I',b,16+child*16+8)[0]
  assert 1<=lo<=hi<=32
  data[n*2]=lo;data[n*2+1]=hi
 b.close();f.close()
 out=ROOT/'assets'/f'{lang}.trie.lengths';emit(out,struct.pack('<4sIII',b'LEN1',1,nodes,0)+data)
 base=1
 while base<len(lengths):base*=2
 data=bytearray([33,0])*(2*base)
 for i,l in enumerate(lengths):data[(base+i)*2]=data[(base+i)*2+1]=l
 for i in range(base-1,0,-1):data[2*i]=min(data[4*i],data[4*i+2]);data[2*i+1]=max(data[4*i+1],data[4*i+3])
 out=ROOT/'assets'/f'{lang}.front.lengths';emit(out,struct.pack('<4sIII',b'LEN1',2,len(lengths),base)+data)
 for kind in ('front','trie'):
  p=ROOT/'assets'/f'{lang}.{kind}.lengths';manifest.append({'language':lang,'format':kind,'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 print(lang,'length metadata complete',flush=True)
if '--check' not in sys.argv:(ROOT/'development/reports/length-assets.json').write_text(json.dumps(manifest,indent=2)+'\n')
else:(ROOT/'development/reports/length-reproducibility.json').write_text(json.dumps({'all_six_metadata_assets_byte_identical':True})+'\n')
