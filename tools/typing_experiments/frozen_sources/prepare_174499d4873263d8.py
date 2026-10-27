from pathlib import Path
import sys,json,hashlib,base64,collections
sys.path.insert(0,'tools/typing_experiments');from right_context_other_part_corpus import generate
from right_context_training_groups import query
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-training-v5-20261027');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text())
lex=PymorphyLexicon(cache_size=16384);new,skipped=generate(lex);old_root=Path('build/right-context-training-v4-20261027');old_manifest=load(old_root/'corpus/manifest.json');old_payload=old_root/'corpus/train.jsonl';assert sha(old_payload)==old_manifest['corpusSha256']
old=[json.loads(s) for s in old_payload.read_text().splitlines()];rows=old+new;assert len(rows)==len({r['id'] for r in rows});corpus=root/'corpus';corpus.mkdir()
(corpus/'train.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
families=sorted({family for r in rows for family in r.get('contrastFamilies',[r['family']])})
manifest=dict(purpose='TRAINING_ONLY_NOT_QUALIFICATION',rows=len(rows),oldRows=len(old),otherPartRows=len(new),families=families,skipped=skipped,dictionary=lex.receipt(),corpusSha256=sha(corpus/'train.jsonl'),oldCorpusSha256=sha(old_payload),sourceHashes={p:sha(p) for p in ['tools/typing_experiments/right_context_other_part_corpus.py','tools/typing_experiments/right_context_role_features.py','tools/typing_experiments/grammar_contrast_corpus.py','tools/typing_experiments/right_context_timeline_calibration.py',__file__]},naturalSentencesOrDisclosedFailuresUsedForTraining=False,scenarioCounts=dict(collections.Counter(r['scenario'] for r in rows)))
(corpus/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');queries=list({query(r)['id']:query(r) for r in rows}.values());(root/'queries.jsonl').write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in queries));enc=lambda s:base64.b64encode(s.encode()).decode()
(root/'queries.tsv').write_text(''.join('\t'.join([str(i),enc(q['id']),'train','ru',enc(q['prefix']),enc(q['typed'])])+'\n' for i,q in enumerate(queries)))
print(json.dumps(dict(rows=len(rows),queries=len(queries),otherPartRows=len(new),families=len(families),skipped=skipped)),flush=True)
