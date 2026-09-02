"""Complete-reference comparison only; bounded failures never compete on their short latencies."""
import collections,csv,hashlib,json,math,pathlib,random,statistics,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];folder=pathlib.Path(sys.argv[1]).resolve();frozen=json.loads((ROOT/'reports/frozen-manifest.json').read_text())
query_meta={(x['language'],x['profile']):x for x in frozen['queries']};groups=collections.defaultdict(list)
def percentile(values,p):
 values=sorted(values);return values[min(len(values)-1,max(0,math.ceil(len(values)*p)-1))]
def basic(values):
 return {k:percentile(values,p) for k,p in [('p50',.5),('p95',.95),('p99',.99),('max',1)]} if values else None
for path in sorted(folder.glob('*.tsv')):
 lines=[line.split('\t')for line in path.read_text().splitlines()]
 meta=next((p for p in lines if p[0]=='META'),None)
 if not meta:continue
 api,lang,form,profile,mode=int(meta[1]),meta[2],meta[3],meta[4],meta[5]
 header=next((p[1:]for p in lines if p[0]=='ROW_HEADER'),None)
 rows=[dict(zip(header,p[1:]))for p in lines if p[0]=='ROW'] if header else []
 done=any(p[0]=='DONE'and p[1]=='PASS' for p in lines)and not any(p[0]in ['FAIL','TIMEOUT']for p in lines)
 fixture=next((p[1]for p in lines if p[0]=='FIXTURE'),None)
 assert fixture==query_meta[lang,profile]['sha256'],'Fixture mismatch'
 expected_ids={q['id']for q in query_meta[lang,profile]['queries']}
 assert all(row['id']in expected_ids for row in rows),'Unexpected query ID'
 reference=[x for x in rows if x['phase']=='reference'];bounded=[x for x in rows if x['phase']=='bounded']
 if done and mode=='full':
  assert len(reference)==len(expected_ids)*3 and len(bounded)==len(expected_ids)*3
  for phase in [reference,bounded]:
   for qid in expected_ids:
    values=[x for x in phase if x['id']==qid];assert len(values)==3 and {x['repeat']for x in values}=={'0','1','2'}
  assert all(x['reason']=='NONE'and x['top7_equal']=='true'and x['expected']==x['returned']for x in reference)
  assert all(int(x['states'])<=8192 and int(x['verified'])<=64 and (x['reason']!='NONE')==(x['prohibits_autoreplace']=='true')for x in bounded)
 memory=[dict(zip(next(p[1:]for p in lines if p[0]=='MEM_HEADER'),p[1:]))for p in lines if p[0]=='MEM']
 loads={p[1]:int(p[2])for p in lines if p[0]=='LOAD'}
 groups[api,lang,profile,mode,form].append({'file':path.name,'pass':done,'rows':rows,'memory':memory,'loads_ns':loads})
assert groups,'No benchmark records found'
expected_dex=hashlib.sha256((ROOT/'bin/benchmark-dex.jar').read_bytes()).hexdigest()
verification=(folder/'verify.tsv').read_text()if(folder/'verify.tsv').exists()else ''
preflight=any(line.startswith('VERIFY\tPASS\t')for line in verification.splitlines())and f'DEX\t{expected_dex}'in verification.splitlines()
summary={'status':'NO_FORMAT_SELECTED','preflight_and_exact_dex_verified':preflight,'fixture_manifest_sha256':hashlib.sha256((ROOT/'reports/frozen-manifest.json').read_bytes()).hexdigest(),'bootstrap':{'replicates':2000,'seed':30902026,'unit':'query/source-word cluster; median of3 measured repeats; paired resampling inside category x frequency-stratum cells; p95 nearest rank'},'comparisons':[],'processes':[]}
for key,processes in groups.items():
 api,lang,profile,mode,form=key
 for p in processes:
  rows=p['rows'];bounded=[r for r in rows if r['phase']=='bounded'];unique=[r for r in bounded if r['repeat']=='0'];first=[r for r in rows if r['phase']=='cold_first']
  summary['processes'].append({'api':api,'language':lang,'profile':profile,'mode':mode,'format':form,'file':p['file'],'pass':p['pass'],'loads_ns':p['loads_ns'],'memory_bytes':p['memory'],'cold_first_topn_ns':[int(r['topn_ns'])for r in first],'bounded_unique':len(unique),'bounded_complete':sum(r['reason']=='NONE'for r in unique),'bounded_reasons':dict(collections.Counter(r['reason']for r in unique)),'bounded_all_latencies_ms_diagnostic_only':basic([int(r['topn_ns'])/1e6 for r in bounded]),'bounded_completed_latencies_ms_not_paired_for_ranking':basic([int(r['topn_ns'])/1e6 for r in bounded if r['reason']=='NONE'])})
for api,lang,profile,mode in sorted({k[:4]for k in groups}):
 if mode!='full':continue
 comparison={'api':api,'language':lang,'profile':profile,'ready':False,'formats':{},'paired_p95_delta_ms':{}}
 for form in ['front','trie','delete']:
  candidates=groups.get((api,lang,profile,mode,form),[])
  if len(candidates)!=1 or not candidates[0]['pass']:comparison['formats'][form]={'status':'MISSING_OR_INCOMPLETE'}
  else:comparison['formats'][form]={'status':'PASS'}
 if all(v['status']=='PASS'for v in comparison['formats'].values()):
  qmeta=query_meta[lang,profile]['queries'];cells=collections.defaultdict(list)
  for q in qmeta:cells[q['category'],q['stratum']].append(q['id'])
  medians={};allocations={}
  for form in ['front','trie','delete']:
   rs=[r for r in groups[api,lang,profile,mode,form][0]['rows']if r['phase']=='reference']
   medians[form]={q['id']:statistics.median(int(r['topn_ns'])/1e6 for r in rs if r['id']==q['id'])for q in qmeta}
   alloc=[int(r['allocated_bytes'])for r in rs if int(r['allocated_bytes'])>=0]
   comparison['formats'][form].update({'completed_queries':len(qmeta),'completed_measured_runs':len(rs),'full_reference_topn_ms':basic(list(medians[form].values())),'reference_allocated_bytes':basic(alloc),'reference_cpu_ms':basic([int(r['cpu_ns'])/1e6 for r in rs]),'reference_gc_count':basic([int(r['gc_count'])for r in rs if int(r['gc_count'])>=0])})
  rng=random.Random(30902026);bootstrap={form:[]for form in medians}
  for _ in range(2000):
   sample=[rng.choice(ids)for ids in cells.values()for _ in ids]
   for form in medians:bootstrap[form].append(percentile([medians[form][qid]for qid in sample],.95))
  for form in medians:comparison['formats'][form]['p95_bootstrap_95ci_ms']=[percentile(bootstrap[form],.025),percentile(bootstrap[form],.975)]
  for a,b in [('front','trie'),('delete','trie'),('delete','front')]:
   delta=[x-y for x,y in zip(bootstrap[a],bootstrap[b])];comparison['paired_p95_delta_ms'][a+' minus '+b]=[percentile(delta,.025),percentile(delta,.975)]
  comparison['ready']=api==26 and profile=='development'and preflight
  comparison['interpretation']='Completed reference comparison; capped feasibility reported separately. Synthetic development profile, not natural typing or energy evidence.'
 summary['comparisons'].append(comparison)
ready=[c for c in summary['comparisons']if c['ready']]
summary['api26_full_three_language_comparison_ready']=len(ready)==3 and {c['language']for c in ready}=={'en','es','ru'}
summary['cold_summaries']=[]
for key,processes in groups.items():
 api,lang,profile,mode,form=key
 if mode!='cold':continue
 passed=[p for p in processes if p['pass']]
 first=[int(r['topn_ns'])/1e6 for p in passed for r in p['rows']if r['phase']=='cold_first']
 memory={}
 for stage in ['boot','frequency_loaded','index_opened','first_query']:
  values=[m for p in passed for m in p['memory']if m['stage']==stage]
  memory[stage]={metric:basic([int(m[metric])for m in values if int(m[metric])>=0])for metric in ['heap_used','heap_committed','native_allocated','pss','private_dirty','rss','peak_rss']}
 summary['cold_summaries'].append({'api':api,'language':lang,'format':form,'fresh_processes':len(processes),'passed':len(passed),'three_process_preset_complete':len(passed)==3,'index_open_ms':basic([p['loads_ns']['index']/1e6 for p in passed]),'frequency_load_ms':basic([p['loads_ns']['frequency']/1e6 for p in passed]),'first_query_ms':basic(first),'memory_bytes':memory,'scope':'Three fresh processes at most; OS caches unknown and preflight-warmed. Quantiles describe these observations, not reliable cold p95 population estimates.'})
summary['apk_measurement']='apk-assets.json; actual aapt2 + zipalign fixtures with common storage policy'
output=ROOT/'reports'/('summary-'+folder.name+'.json');output.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'summary':str(output),'api26_full_three_language_comparison_ready':summary['api26_full_three_language_comparison_ready'],'processes':len(summary['processes']),'all_processes_pass':all(p['pass']for p in summary['processes'])}))
