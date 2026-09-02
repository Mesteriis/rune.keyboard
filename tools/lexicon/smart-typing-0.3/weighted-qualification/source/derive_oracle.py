"""Prepare all expected output from frozen sources before production generator runs."""
from pathlib import Path
import argparse,hashlib,json,subprocess,shutil,sys
sys.dont_write_bytecode=True
import reference as ref
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def emit(p,v):p.write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n')
def derive(base: Path, wordforms: Path, manifest: Path, cpp: Path, compiler: str | None):
 lock=json.loads((base/'fixtures/input-lock.json').read_text());assert sha(base/'fixtures/inputs.json')==lock['inputs_sha256']
 inputs=json.loads((base/'fixtures/inputs.json').read_text());frozen=json.loads((manifest).read_text())
 assert sha(manifest)=='ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48'
 for item in frozen['languages']:assert sha(wordforms/f'{item["language"]}.words.txt')==item['canonical_keys']['sha256']
 for item in frozen['frequency']:assert sha(wordforms/'frequency'/f'{item["language"]}.tsv')==item['data']['sha256']
 neighbors={lang:{} for lang in ref.LANGS};provenance={}
 for lang in ('en','es','ru'):
  f=base/'fixtures'/f'{lang}.development.tsv'
  origin=next(x for x in lock['origins'] if x['path'].endswith(f'/{lang}.development.tsv'))
  assert sha(f)==origin['sha256']
  for line in f.read_text().splitlines():
   _,key,_,_,_,words=line.split('\t');neighbors[lang][key]=words.split(',') if words else []
  provenance[lang]={'inherited_sha256':sha(f)}
 wanted={lang:set() for lang in ref.LANGS}
 for row in inputs:
  row['protected']=ref.protection(row['query']);row['routes']=[] if row['cancellation'] else ref.routes(row['query'],row['active'])
  row['key']=ref.folded(row['query']) if row['protected']<0 else ''
  row['case']=ref.pattern(row['query']) if row['protected']<0 else -1
  for language in row['routes']:wanted[ref.LANGS[language]].add(row['key'])
 # Membership uses independent complete canonical wordlist streaming.
 membership={lang:set() for lang in ref.LANGS}
 for lang in ref.LANGS:
  with (wordforms/f'{lang}.words.txt').open() as stream:
   for line in stream:
    word=line.rstrip('\n')
    if word in wanted[lang]:membership[lang].add(word)
 for row in inputs:
  row['present_routes']=[language for language in row['routes'] if row['key'] in membership[ref.LANGS[language]]]
  row['expected_completion']=5 if row['cancellation'] else 1 if row['protected']>=0 else 2 if row['present_routes'] else 0
 missing={lang:set() for lang in ref.LANGS}
 for row in inputs:
  if row['expected_completion']!=0:continue
  for language in row['routes']:
   lang=ref.LANGS[language]
   if row['key'] not in neighbors[lang]:missing[lang].add(row['key'])
 assert sha(cpp)=='a9a689eb7b11f9c03a92ae2dd8f086e645ec2fbc23fd02f3d673cbb2b865f6f0'
 plan={'inputs_sha256':lock['inputs_sha256'],'missing_queries':{k:len(v) for k,v in missing.items()},
       'cpp_source_sha256':sha(cpp),'source_manifest_sha256':sha(manifest),
       'selection':'Source-only membership before scans; reuse matching-language frozen neighborhoods, fill only missing route/query pairs. No production reader executed.'}
 for lang in ref.LANGS:
  path=base/'oracle'/f'{lang}.missing.queries.txt';content=''.join(q+'\n' for q in sorted(missing[lang]))
  if path.exists():assert path.read_text()==content
  else:path.write_text(content)
  plan[lang+'_queries_sha256']=sha(path)
 if (base/'oracle/scan-plan.json').exists():assert json.loads((base/'oracle/scan-plan.json').read_text())==plan
 else:emit(base/'oracle/scan-plan.json',plan)
 emit(base/'fixtures/source-routes.json',inputs)
 print('ORACLE_PLAN',plan['missing_queries'],flush=True)
 binary=base/'bin/unit_oracle'
 if compiler is not None:subprocess.run([compiler,'-O2','-std=c++17',str(cpp),'-o',str(binary)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
 for lang in ref.LANGS:
  target=base/'oracle'/f'{lang}.missing.neighbors.tsv'
  if compiler is not None:
   result=subprocess.run([str(binary),str(wordforms/f'{lang}.words.txt'),str(base/'oracle'/f'{lang}.missing.queries.txt'),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=900)
   if result.returncode:raise RuntimeError('UNIT_ORACLE_FAILED')
  lines=target.read_text().splitlines();assert len(lines)==len(missing[lang])
  for line,query in zip(lines,sorted(missing[lang])):
   columns=line.split('\t');assert columns[0]==query;assert columns[1:]==sorted(set(columns[1:]));neighbors[lang][query]=columns[1:]
  provenance[lang]['new_query_sha256']=sha(base/'oracle'/f'{lang}.missing.queries.txt');provenance[lang]['new_neighborhood_sha256']=sha(target)
  print('ORACLE_COMPLETE',lang,len(lines),flush=True)
 frequencies={}
 for lang in ref.LANGS:
  lines=(wordforms/'frequency'/f'{lang}.tsv').read_text().splitlines()[1:]
  frequencies[lang]={p[0]:int(p[1]) for line in lines if (p:=line.split('\t'))}
 required={lang:set() for lang in ref.LANGS}
 for row in inputs:
  if row['expected_completion']==0:
   for language in row['routes']:
    lang=ref.LANGS[language];required[lang].update(neighbors[lang][row['key']])
 ordinals={lang:{} for lang in ref.LANGS}
 for lang in ref.LANGS:
  with (wordforms/f'{lang}.words.txt').open() as stream:
   for ordinal,line in enumerate(stream,1):
    word=line.rstrip('\n')
    if word in required[lang]:ordinals[lang][word]=ordinal
  assert len(ordinals[lang])==len(required[lang])
 expected=[];candidate_rows=[];input_rows=[]
 for row in inputs:
  key=row['key'];all_candidates=[]
  if row['expected_completion']==0:
   for route_index,language in enumerate(row['routes']):
    lang=ref.LANGS[language]
    for terminal in neighbors[lang][key]:
     unit=ref.distance(key,terminal,lang,False)//4;assert 1<=unit<=(1 if len(key)<5 else 2)
     display=ref.preserve(terminal,row['case']);display_key=ref.folded(display) if display is not None else ''
     c={'terminal':terminal,'ordinal':ordinals[lang][terminal],'language':language,'fallback':int(route_index>0),
        'prior':4 if route_index==0 else 1,'frequency':frequencies[lang].get(terminal,2147483647),
        'unit':unit,'quarters':ref.distance(key,terminal,lang),'repeats':ref.repeats(key,terminal),
        'length_difference':abs(len(key)-len(terminal)),'case':row['case'],'display':display or '',
        'key':display_key,'admitted':display is not None and display_key!=key}
     all_candidates.append(c)
     candidate_rows.append('\t'.join(map(str,[row['id'],language,c['ordinal'],ref.hex_units(terminal),ref.hex_units(c['display']),ref.hex_units(c['key']),c['fallback'],c['prior'],c['frequency'],c['unit'],c['quarters'],c['repeats'],c['length_difference'],c['case'],int(c['admitted'])])))
  result={'id':row['id'],'completion':row['expected_completion'],'protected':row['protected'],'routes':row['routes'],
          'present_routes':row['present_routes'],'all_candidates':all_candidates,'best':ref.select(all_candidates)}
  expected.append(result)
  input_rows.append('\t'.join(map(str,[row['id'],row['group'],row['active'],int(row['cancellation']),ref.hex_units(row['query'])])))
 emit(base/'fixtures/expected.json',expected)
 (base/'fixtures/inputs.tsv').write_text('\n'.join(input_rows)+'\n');(base/'fixtures/candidates.tsv').write_text('\n'.join(candidate_rows)+'\n')
 emit(base/'oracle/provenance.json',{'schema':1,'groups':provenance,'unit_cpp_sha256':sha(cpp),'unit_binary_sha256':sha(binary) if compiler is not None else None,
      'reference_source_sha256':sha(Path(ref.__file__)),'plan_sha256':sha(base/'oracle/scan-plan.json'),
      'expected_sha256':sha(base/'fixtures/expected.json'),'inputs_tsv_sha256':sha(base/'fixtures/inputs.tsv'),'candidates_tsv_sha256':sha(base/'fixtures/candidates.tsv'),
      'full_candidate_records':len(candidate_rows),'expected_completed_requests':sum(x['completion']==0 for x in expected),'production_not_executed':True})
 print('EXPECTED_FROZEN',len(expected),'FULL_CANDIDATES',len(candidate_rows),flush=True)
if __name__=='__main__':raise SystemExit('USE_QUALIFY_COMMAND')
