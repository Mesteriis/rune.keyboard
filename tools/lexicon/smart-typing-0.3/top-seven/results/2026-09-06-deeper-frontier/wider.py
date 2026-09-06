import pathlib,json,subprocess,hashlib,base64,collections
O=pathlib.Path.cwd()/'build/smart-typing-0.3/retrieval-probe-20260906'
commands=json.loads((O/'commands.json').read_text())
for v in ['baseline','deeper']:
 c=next(c for c in commands if any('/'+v+'/generator.jar' in s for s in c) and 'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport' in c)
 c=[s.replace('/named.tsv','/calibration.tsv') for s in c]
 with (O/(v+'-calibration.stdout')).open('w') as out,(O/(v+'-calibration.stderr')).open('w') as err:
  p=subprocess.run(c,stdout=out,stderr=err,timeout=900)
 commands.append(c); (O/'commands.json').write_text(json.dumps(commands,indent=2)+'\n'); assert p.returncode==0
 print(v+' done',flush=True)
rows=[json.loads(l) for l in (O/'calibration.jsonl').read_text().splitlines()]
def parse(v):
 rr=[]
 for l in (O/(v+'-calibration.stdout')).read_text().splitlines():
  f=l.split('\t')
  if f[0]=='R':
   assert int(f[1])==len(rr)
   rr.append(dict(completion=f[2],valid=f[3],veto=f[4],states=int(f[5]),terminals=int(f[6]),protected=f[7],count=int(f[8]),candidates=[]))
  else:
   rr[-1]['candidates'].append([base64.b64decode(s).decode() for s in f[3:6]]+f[6:])
 assert len(rr)==6000
 for r in rr: assert r['states']<=8192 and r['terminals']<=64 and len(r['candidates'])==r['count']<=3
 return rr
b,d=parse('baseline'),parse('deeper')
summary={'rows':6000,'baseline_completions':dict(collections.Counter(r['completion'] for r in b)),'deeper_completions':dict(collections.Counter(r['completion'] for r in d)),'previous_complete':sum(r['completion']=='COMPLETE' for r in b),'previous_complete_output_differences':[],'newly_complete':[],'newly_incomplete':[],'candidate_changed':0,'target_recall':{},'limits_preserved':True}
with (O/'comparison.jsonl').open('w') as out:
 for r,x,y in zip(rows,b,d):
  if x['completion']=='COMPLETE' and x['candidates']!=y['candidates']:summary['previous_complete_output_differences'].append(r['id'])
  if x['completion']!='COMPLETE' and y['completion']=='COMPLETE':summary['newly_complete'].append(r['id'])
  if x['completion']=='COMPLETE' and y['completion']!='COMPLETE':summary['newly_incomplete'].append(r['id'])
  summary['candidate_changed']+=x['candidates']!=y['candidates']
  target=r.get('expectedSpelling') or (r['candidates'][r['expectedCandidate']].strip() if r['expectedCandidate']>0 else None)
  if target:
   cohort=summary['target_recall'].setdefault('expected_nonoriginal',dict(rows=0,before=0,after=0,gained=[],lost=[])); cohort['rows']+=1
   bx=target in [c[0] for c in x['candidates']];dy=target in [c[0] for c in y['candidates']];cohort['before']+=bx;cohort['after']+=dy
   if dy and not bx:cohort['gained'].append(r['id'])
   if bx and not dy:cohort['lost'].append(r['id'])
  out.write(json.dumps(dict(id=r['id'],typed=r['typed'],target=target,before=x,after=y),ensure_ascii=False)+'\n')
for v,rr in [('baseline',b),('deeper',d)]: summary[v+'_counts']={'states_sum':sum(r['states'] for r in rr),'terminals_sum':sum(r['terminals'] for r in rr),'states_max':max(r['states'] for r in rr),'terminals_max':max(r['terminals'] for r in rr)}
(O/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
