import pathlib,json,hashlib,subprocess,base64,os,shutil,difflib
R=pathlib.Path.cwd(); O=R/'build/smart-typing-0.3/retrieval-probe-20260906'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x): (O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
commands=[]
def run(c,n,timeout=180):
 commands.append(c); save('commands.json',commands)
 with (O/(n+'.stdout')).open('w') as out,(O/(n+'.stderr')).open('w') as err:
  p=subprocess.run(c,stdout=out,stderr=err,timeout=timeout)
 assert p.returncode==0,(n,p.returncode)
P=R/'app/src/main/java/io/github/mesteriis/rune/keyboard'
paths=['ime/model/KeyboardState.kt']+['smarttyping/correction/'+s+'.kt' for s in ('TokenUnicode','ProtectedTokenPolicy','CasePattern','KeyboardDistance','WeightedDamerauLevenshtein')]+['smarttyping/lexicon/'+s+'.kt' for s in ('LanguageRouter','CandidateLexicon','CanonicalCaseLexicon','CandidateGenerator','PackedCandidateLexicon','PackedLexiconData','PackedLexiconManifest','FrozenPackedLexicons','TopCandidateSelection','PackedTopSeven','PrefixDistance')]
sources=[P/p for p in paths]+[R/'tools/eval/smart-typing-0.3/pipeline/CandidateExport.kt']
manifest=json.loads((R/'tools/lexicon/smart-typing-0.3/weighted-qualification/manifests/reproduction-toolchain.json').read_text()); jars=[]
for item in manifest['jars']:
 found=list((pathlib.Path.home()/'.gradle/caches/modules-2/files-2.1'/item['group']/item['artifact']/item['version']).glob('*/*.jar'))
 assert len(found)==1 and sha(found[0])==item['sha256']; jars+=found
java='/opt/homebrew/opt/openjdk@17/bin/java'; run([java,'-version'],'java-version')
rows=[]
for l in (R/'build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/rows.jsonl').open():
 r=json.loads(l)
 if r['split']!='calibration': continue
 rows.append(r)
assert len(rows)==6000
(O/'calibration.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
named=[r for r in rows if r['typed'] in ['автокрекция','correcion','teh']]
assert len(named)==3
for name,rr in [('named',named),('calibration',rows)]:
 (O/(name+'.tsv')).write_text(''.join(str(i)+'\t'+r['language']+'\t'+base64.b64encode(r['typed'].encode()).decode()+'\n' for i,r in enumerate(rr)))
asset=R/'app/src/main/assets/smarttyping/lexicon'
assets=[asset/(lang+suffix) for lang in ['en','ru','es'] for suffix in ['.trie','.trie.lengths']]+[asset/'frequency'/(lang+'.ranks') for lang in ['en','ru','es']]
save('inputs-manifest.json',{'head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'source':{str(p):sha(p) for p in sources},'toolchain':{str(p):sha(p) for p in jars},'assets':{str(p):sha(p) for p in assets},'calibration':sha(O/'calibration.jsonl'),'probe':sha(O/'probe.py'),'initial-discovery-failures':['Missing top-seven/probe.py','Missing pipeline parent export_candidates.py','System java_home could not locate Java; using pinned Homebrew Java17','Android Studio Java path absent']})
for variant in ['baseline','deeper']:
 d=O/variant; d.mkdir(exist_ok=True); copied=[]
 for p in sources:
  q=d/'sources'/p.relative_to(R); q.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,q); copied.append(q)
  if variant=='deeper' and p.name=='PackedTopSeven.kt':
   old=q.read_text(); before='return a < b // queue scheduling only, never a certificate tie-break'; after='return if (depth[a] != depth[b]) depth[a] > depth[b] else a < b // queue scheduling only, never a certificate tie-break'
   assert old.count(before)==1; q.write_text(old.replace(before,after)); (O/'variant.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),q.read_text().splitlines(True),fromfile='baseline/PackedTopSeven.kt',tofile='deeper/PackedTopSeven.kt')))
 save(variant+'-sources.json',{str(p):sha(p) for p in copied})
 run([java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,jars)),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','17','-classpath',os.pathsep.join(map(str,jars[1:3])),'-d',str(d/'generator.jar'),*map(str,copied)],variant+'-compile')
 run([java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,[d/'generator.jar',*jars[1:3]])),'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport',str(O/'named.tsv'),str(asset),str(asset/'frequency'),'3'],variant+'-named')
print('Named runs ready')
