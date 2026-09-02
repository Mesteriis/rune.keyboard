"""Full-neighborhood/weighted/route/case/partial-output contracts; numeric reports only."""
from pathlib import Path
import collections,hashlib,json,sys
sys.dont_write_bytecode=True
import reference as ref
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(condition,code,rid,failures):
 if not condition:failures.append({'id':rid,'code':code})
def main(base: Path):
 inputs=json.loads((base/'fixtures/source-routes.json').read_text());expected=json.loads((base/'fixtures/expected.json').read_text());provenance=json.loads((base/'oracle/provenance.json').read_text())
 assert sha(base/'fixtures/expected.json')==provenance['expected_sha256']
 rows=[]
 for line in (base/'reports/actual.tsv').read_text().splitlines():
  values=line.split('\t');assert all(x.lstrip('-').isascii() and x.lstrip('-').isdecimal() for x in values)
  row=list(map(int,values));assert row[0]==1;rows.append(row)
 failures=[];width={0:5,1:13,2:17,3:6,4:7,5:9,6:3}
 assert all(r[1] in width and len(r)==width[r[1]] for r in rows)
 assert rows[-1]==[1,6,len(inputs)]
 loads=[r for r in rows if r[1]==0];assert [r[2] for r in loads]==[0,1,2]
 queries=[r for r in rows if r[1]==1];assert [r[2] for r in queries]==list(range(len(inputs)))
 other=collections.defaultdict(list)
 for r in rows:
  if r[1] in (2,3,4,5):assert 0<=r[2]<len(inputs);other[r[2]].append(r)
 results=[]
 for item,want,q in zip(inputs,expected,queries):
  rid=item['id'];events=other[rid];a=[x for x in events if x[1]==2];e=[x for x in events if x[1]==3];s=[x for x in events if x[1]==4];v=[x for x in events if x[1]==5]
  raw={(c['language'],c['ordinal']):c for c in want['all_candidates']}
  actual=[];verified=[]
  check(q[3:5]==[item['group'],item['active']],1,rid,failures)
  check(q[8]==1 and 0<=q[9]<=8192 and 0<=q[10]<=64 and q[12]==len(a)<=7,2,rid,failures)
  check([x[3] for x in a]==list(range(len(a))),3,rid,failures)
  check([x[3] for x in v]==list(range(len(v))),4,rid,failures)
  for x in v:
   key=(x[4],x[5]);check(key in raw,5,rid,failures)
   check(x[7] in (0,1) and x[8] in (0,1),6,rid,failures)
   if key in raw:check(x[6]==raw[key]['frequency'],7,rid,failures)
   if x[7]==1 and key in raw:verified.append(raw[key])
  check(len(verified)==q[10] and len({(x['language'],x['ordinal']) for x in verified})==len(verified),8,rid,failures)
  for x in a:
   c=raw.get((x[4],x[5]));check(c is not None and c['admitted'],9,rid,failures)
   if c is None:continue
   fields=[c['fallback'],c['prior'],c['frequency'],c['unit'],c['quarters'],c['repeats'],c['repeats'],c['length_difference'],c['case'],1,1]
   check(x[6:]==fields,10,rid,failures);actual.append(c)
  check(sum(x['fallback'] for x in actual)<=2 and len({x['key'] for x in actual})==len(actual),11,rid,failures)
  check(actual==ref.select(verified),12,rid,failures)
  check(q[9]==sum(x[5] for x in e)+sum(x[5] for x in s) and q[10]==sum(x[6] for x in s),13,rid,failures)
  if want['completion'] in (1,5):
   check(q[5]==want['completion'] and not a and not events and q[6]==0 and q[7]==1 and q[9:11]==[0,0],14,rid,failures)
   check(q[11]==(-1 if want['completion']==5 else want['protected']),15,rid,failures)
  else:
   checked_routes=[]
   for language in want['routes']:
    checked_routes.append(language)
    if language in want['present_routes']:break
   check([x[3] for x in e]==checked_routes,16,rid,failures)
   check(all(x[4]==(0 if x[3] in want['present_routes'] else 1) for x in e),17,rid,failures)
   check(q[11]==-1,18,rid,failures)
   if want['completion']==2:
    check(q[5]==2 and q[6]==1 and q[7]==1 and not a and not s and not v and q[10]==0,19,rid,failures)
   else:
    check(q[5] in (0,3,4) and q[6]==0 and q[7]==int(q[5]!=0),20,rid,failures)
    check([x[3] for x in s]==want['routes'][:len(s)] and len(s)>=1,21,rid,failures)
    if q[5]==0:
     check([x[3] for x in s]==want['routes'] and all(x[4]==0 for x in s),22,rid,failures)
     check({(x['language'],x['ordinal']) for x in verified}==set(raw),23,rid,failures)
     check(actual==want['best'],24,rid,failures)
    else:
     check(s[-1][4]==1 and (q[9]==8192 if q[5]==3 else q[10]==64),25,rid,failures)
  best_ids={(c['language'],c['ordinal']) for c in want['best']};actual_ids={(c['language'],c['ordinal']) for c in actual}
  source=item.get('source_word');eligible_source=any(c['terminal']==source and c['admitted'] for c in raw.values()) if source else False
  results.append({'id':rid,'group':item['group'],'active':item['active'],'expected_completion':want['completion'],'completion':q[5],
   'states':q[9],'verified':q[10],'candidate_count':len(a),'full_neighborhood_count':len(raw),'oracle_top7_count':len(best_ids),
   'oracle_top7_retained':len(best_ids&actual_ids),'full_top7_equal':int(actual==want['best']),
   'eligible_source':int(eligible_source),'source_returned':int(any(c['terminal']==source for c in actual)) if source else 0,
   'primary_exact_hit':int(q[5]==2 and len(e)==1),'fallback_exact_hit':int(q[5]==2 and len(e)==2),
   'fallback_returned':sum(c['fallback'] for c in actual),'duplicates_collapsed_full':len([c for c in raw.values() if c['admitted']])-len({c['key'] for c in raw.values() if c['admitted']})})
 groups=[]
 for group in (0,1):
  for active in (0,1,2):
   rs=[x for x in results if x['group']==group and x['active']==active]
   if not rs:continue
   retrieval=[x for x in rs if x['expected_completion']==0];incomplete=[x for x in retrieval if x['completion'] in (3,4)]
   groups.append({'group':group,'active':active,'requests':len(rs),'statuses':dict(collections.Counter(x['completion'] for x in rs)),
      'retrieval_requests':len(retrieval),'complete_retrieval':sum(x['completion']==0 for x in retrieval),
      'states_exhausted':sum(x['completion']==3 for x in retrieval),'verified_exhausted':sum(x['completion']==4 for x in retrieval),
      'oracle_top7_retained':sum(x['oracle_top7_retained'] for x in retrieval),'oracle_top7_total':sum(x['oracle_top7_count'] for x in retrieval),
      'incomplete_but_equal_top7':sum(x['full_top7_equal'] for x in incomplete),
      'eligible_source':sum(x['eligible_source'] for x in retrieval),'source_returned':sum(x['source_returned'] for x in retrieval),
      'primary_exact_hits':sum(x['primary_exact_hit'] for x in rs),'fallback_exact_hits':sum(x['fallback_exact_hit'] for x in rs),
      'fallback_returned':sum(x['fallback_returned'] for x in retrieval),'full_display_duplicates':sum(x['duplicates_collapsed_full'] for x in retrieval)})
 summary={'schema':1,'validation_pass':not failures,'requests':len(inputs),'independent_full_candidate_records':sum(len(x['all_candidates']) for x in expected),
          'violations':failures,'groups':groups,'actual_sha256':sha(base/'reports/actual.tsv'),'expected_sha256':sha(base/'fixtures/expected.json'),
          'no_device_or_energy_measurement':True,'no_quality_holdout_or_calibration':True,'caps_unchanged':True}
 (base/'reports/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 keys=list(results[0]);(base/'reports/per-query.tsv').write_text('\t'.join(keys)+'\n'+'\n'.join('\t'.join(str(x[k]) for k in keys) for x in results)+'\n')
 print('CONTRACT_RESULT',int(not failures),'REQUESTS',len(inputs),'VIOLATIONS',len(failures))
 for x in groups:print('GROUP',x['group'],x['active'],'REQUESTS',x['requests'],'COMPLETE',x['complete_retrieval'],'STATES',x['states_exhausted'],'VERIFIED',x['verified_exhausted'],'TOP7',x['oracle_top7_retained'],x['oracle_top7_total'],'VALID',x['primary_exact_hits'],x['fallback_exact_hits'])
 return int(bool(failures))
if __name__=='__main__':raise SystemExit('USE_QUALIFY_COMMAND')
