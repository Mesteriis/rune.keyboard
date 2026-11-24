from pathlib import Path
import sys,json,hashlib,base64,collections
sys.path.insert(0,'tools/typing_experiments');from right_context_grammar_features import completed_following_words
from right_context_sentence_audit import audit_new_sentences
from right_context_corpus_separation import exclusion_records
root=Path('build/right-context-available-calibration-v6-20261027');parent=Path('build/right-context-sentence-pairs-v2-v6-20261027');load=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();plan=load(parent/'plan.json');frozen=load('build/right-context-training-v6-20261027/frozen-model.json');items=list(map(json.loads,(parent/'contexts.unqualified.jsonl').read_text().splitlines()))
freeze=dict(stage='available-record-calibration-diagnostic-only',fullCohortGatePassed=False,failedAvailabilitySha256=sha(parent/'availability.json'),parentPlanSha256=sha(parent/'plan.json'),recordsSha256=sha(parent/'contexts.unqualified.jsonl'),modelSha256=frozen['modelSha256'],scriptSha256=sha(__file__),auditSourceSha256=sha('tools/typing_experiments/right_context_sentence_audit.py'),qualificationRequirementsChanged=False,holdoutScoringAllowed=False,modelCalls=0)
with (root/'plan.json').open('x') as f:json.dump(freeze,f,indent=2)
prior=[];bindings=dict(plan['exclusionBindings'])|dict(plan['sourceContextBindings'])|dict(plan['additionalArticleBindings'])
for p,h in bindings.items():
 assert sha(p)==h
 prior.extend(exclusion_records(Path(p)))
parts={part:[] for part in ['calibration','holdout']}
for item in items:
 rows=parts[item['part']]
 variants=[(item['typed'],'typo',False,False,item['rightContext']),(item['typed'],'unfinished',False,True,' '+completed_following_words(item['rightContext'])[0]),(item['word'],'correct',True,False,item['rightContext']),('@'+item['word'],'protected',True,False,item['rightContext'])]
 if item['rival']:variants.append((item['rival'],'correct_rival',True,False,item['rightContext']))
 for typed,group,control,retain,suffix in variants:
  rows.append(dict(item,id=f'available-v6-{item["part"]}-{len(rows):06d}',split=item['part'],language='ru',typed=typed,group=group,noAuto=control,retainBaseline=retain,rightContext=suffix,expectedSpelling=typed if control else item['word']))
audit=audit_new_sentences(parts,prior,frozen['trainingFamilies'],seed=plan['seed']);(root/'identity-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
assert audit['passed'],'AVAILABLE_SENTENCE_IDENTITY_AUDIT_FAILED'
out=root/'corpus';out.mkdir();files={};counts={}
for part,rows in parts.items():
 p=out/(part+'.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[p.name]=sha(p);enc=lambda s:base64.b64encode(s.encode()).decode();t=out/(part+'.tsv');t.write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)));files[t.name]=sha(t)
 counts[part]=dict(rows=len(rows),contexts=len({r['contextHash'] for r in rows}),controls=sum(r['noAuto'] for r in rows),unfinishedControls=sum(r['retainBaseline'] for r in rows),groups=dict(collections.Counter(r['sideGroup'] for r in rows if r['group']=='typo')))
manifest=dict(stage='available-record-calibration-diagnostic-only',files=files,counts=counts,fullCohortGatePassed=False,identityAuditSha256=sha(root/'identity-audit.json'),planSha256=sha(root/'plan.json'),modelSha256=frozen['modelSha256'],holdoutScoringAllowed=False,modelCalls=0)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(counts),flush=True)
