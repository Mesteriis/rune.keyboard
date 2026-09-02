"""Strict records and paired stratified bootstrap; never selects a format."""
import hashlib,json,math,pathlib,random,statistics,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
FORMATS=('front','trie','delete')
class ValidationFailure(ValueError):
 """Internal static validation code; never an input field or parser exception."""
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,code):
 if not ok:raise ValidationFailure(code)
def parse(text,group,fmt,manifest_sha):
 lines=[x.split('\t') for x in text.splitlines()]
 known={'META','MANIFEST','MEM','OPEN','ROW','DONE'}
 require(all(p[0] in known for p in lines),'UNKNOWN_OR_FAILURE_RECORD')
 def singleton(name):
  found=[p for p in lines if p[0]==name];require(len(found)==1,'SINGLE_'+name);return found[0]
 meta=singleton('META');require(len(meta)==8,'META_COLUMNS')
 require(meta[2:7]==[group['language'],fmt,'277','1','5'] and 30<=int(meta[7])<=600,'META_VALUES')
 require(singleton('MANIFEST')==['MANIFEST',manifest_sha],'MANIFEST_HASH')
 opened=singleton('OPEN');require(len(opened)==2 and int(opened[1])>=0,'OPEN')
 expected={q['id']:q for q in group['queries']};seen={};samples={}
 for p in lines:
  if p[0]!='ROW':continue
  require(len(p)==11,'ROW_COLUMNS')
  phase,qid,rep,cohort,label,wall,cpu,alloc,gc,passed=map(int,p[1:])
  require(qid in expected,'UNKNOWN_ID');q=expected[qid]
  require(cohort==q['cohort'] and label==q['label'] and passed==1,'REFERENCE_LABEL')
  require(wall>=0 and cpu>=-1 and alloc>=-1 and gc>=-1,'METRIC')
  key=(phase,qid,rep);require(key not in seen,'DUPLICATE');seen[key]=(wall,cpu,alloc,gc)
  if phase==5:samples.setdefault(qid,[]).append((wall,cpu,alloc,gc))
 want={(3,group['queries'][0]['id'],0)}|{(4,qid,0) for qid in expected}|{(5,qid,r) for qid in expected for r in range(5)}
 require(set(seen)==want,'MISSING_OR_EXTRA_ROWS')
 mem=[p for p in lines if p[0]=='MEM'];require(len(mem)==6 and {int(p[1]) for p in mem}==set(range(6)),'MEMORY_RECORDS')
 require(all(len(p)==9 and all(int(x)>=-1 for x in p[2:]) for p in mem),'MEMORY_VALUES')
 done=singleton('DONE');require(len(done)==5 and done[:4]==['DONE','PASS','277','1385'],'DONE')
 require(int(done[4])==sum(q['label']==1 for q in group['queries'])*6+int(group['queries'][0]['label']==1),'CONSUMED_RESULT')
 return {'api':int(meta[1]),'open_ns':int(opened[1]),'cold_first_ns':seen[(3,group['queries'][0]['id'],0)][0],'memory':mem,'samples':samples}
def read_all(directory):
 manifest=json.loads((ROOT/'reports/frozen-manifest.json').read_text());mh=sha(ROOT/'reports/frozen-manifest.json')
 verify=(directory/'verify.tsv').read_text().splitlines()
 require(verify==['DEX\t'+sha(ROOT/'bin/benchmark-dex.jar'),'MANIFEST\t'+mh,'VERIFY\tPASS\t'+str(len(manifest['base_assets']))+'\t3'],'PREFLIGHT')
 expected={f'{g["language"]}.{f}.tsv' for g in manifest['groups'] for f in FORMATS}|{'verify.tsv'}
 require({p.name for p in directory.glob('*.tsv')}==expected,'MISSING_OR_EXTRA_PROCESSES')
 parsed={}
 for group in manifest['groups']:
  for fmt in FORMATS:parsed[(group['language'],fmt)]=parse((directory/f'{group["language"]}.{fmt}.tsv').read_text(),group,fmt,mh)
 return manifest,parsed
def p95(values):return sorted(values)[math.ceil(len(values)*.95)-1]
def ci(values):
 s=sorted(values);return [s[int(.025*(len(s)-1))],s[int(.975*(len(s)-1))]]
def summarize(manifest,data):
 out={'validation':'PASS','api26_ready':all(p['api']==26 for p in data.values()),'processes':9,'measured_exact_comparisons':12465,'manifest_sha256':sha(ROOT/'reports/frozen-manifest.json'),'dex_sha256':sha(ROOT/'bin/benchmark-dex.jar'),'bootstrap':{'samples':2000,'seed':30902026,'paired':True,'stratification':'category x stratum within reported cohort/label'},'groups':[]}
 for group in manifest['groups']:
  lang=group['language']
  pools={'development':[q for q in group['queries'] if q['cohort']==0], 'control_present':[q for q in group['queries'] if q['cohort']==1], 'control_absent':[q for q in group['queries'] if q['cohort']==2], 'control_empty':[q for q in group['queries'] if q['cohort']==3]}
  for label in (0,1):pools['development_'+('present' if label else 'absent')]=[q for q in group['queries'] if q['cohort']==0 and q['label']==label]
  for name,queries in pools.items():
   if not queries:
    out['groups'].append({'language':lang,'pool':name,'queries':0,'status':'EMPTY_PREDECLARED_LABEL_POOL'});continue
   med={fmt:{q['id']:statistics.median(data[lang,fmt]['samples'][q['id']][i][0] for i in range(5)) for q in queries} for fmt in FORMATS}
   strata={}
   for q in queries:strata.setdefault((q['category'],q['stratum']),[]).append(q['id'])
   boot={fmt:[] for fmt in FORMATS};diff={pair:[] for pair in [('front','trie'),('delete','trie'),('delete','front')]}
   rng=random.Random(30902026)
   for _ in range(2000):
    ids=[rng.choice(cell) for cell in strata.values() for _ in cell]
    vals={fmt:p95([med[fmt][i] for i in ids]) for fmt in FORMATS}
    for fmt in FORMATS:boot[fmt].append(vals[fmt])
    for pair in diff:diff[pair].append(vals[pair[0]]-vals[pair[1]])
   records={}
   for fmt in FORMATS:
    extra={}
    for col,title in [(1,'cpu_ns'),(2,'allocated_bytes'),(3,'gc_count')]:
     repeats=[[s[col] for s in data[lang,fmt]['samples'][q['id']]] for q in queries]
     # Missing repetitions cannot disappear inside a nonnegative median.
     extra[title+'_p95']=None if any(v<0 for values in repeats for v in values) else p95([statistics.median(values) for values in repeats])
    records[fmt]={'wall_ns_p95':p95(list(med[fmt].values())),'wall_ns_p95_ci95':ci(boot[fmt]),**extra}
   out['groups'].append({'language':lang,'pool':name,'queries':len(queries),'formats':records,'paired_p95_difference_ns_ci95':{'-'.join(p):ci(v) for p,v in diff.items()}})
 out['process_observations']=[{'language':lang,'format':fmt,**{k:v for k,v in rec.items() if k!='samples'}} for (lang,fmt),rec in data.items()]
 return out
if __name__=='__main__':
 try:
  require(len(sys.argv)==3,'ARGS');m,d=read_all(pathlib.Path(sys.argv[1]));out=summarize(m,d)
  dest=pathlib.Path(sys.argv[2]).resolve();require(dest.is_relative_to(ROOT),'OUTPUT_SCOPE');dest.write_text(json.dumps(out,indent=2)+'\n')
  print('PASS complete exact records; API26 readiness='+str(out['api26_ready']))
 except Exception as e:
  print('FAIL '+(str(e) if isinstance(e,ValidationFailure) else type(e).__name__));sys.exit(2)
