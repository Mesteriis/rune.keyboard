from pathlib import Path
import sys,json,hashlib,collections
sys.path.insert(0,'tools/typing_experiments');from right_context_training_groups import select_groups
root=Path('build/right-context-training-v4-20261027');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text())
manifest=load(root/'corpus/manifest.json');assert sha(root/'corpus/train.jsonl')==manifest['corpusSha256'];assert sha('tools/typing_experiments/right_context_role_corpus.py')==manifest['sourceHashes']['tools/typing_experiments/right_context_role_corpus.py']
receipt=load(root/'production-pools/receipt.json');assert sha(root/'queries.tsv')==receipt['inputSha256'];assert sha(root/'production-pools/observations.jsonl')==receipt['outputSha256']
rows=[json.loads(s) for s in (root/'corpus/train.jsonl').read_text().splitlines()];observations=[json.loads(s) for s in (root/'production-pools/observations.jsonl').read_text().splitlines()];groups,skipped=select_groups(rows,observations)
assert sorted({r['family'] for r in rows})==load('build/right-context-training-v3-20261027/frozen-model.json')['trainingFamilies']
with (root/'groups.jsonl').open('x') as f:
 for group in groups:f.write(json.dumps(group,ensure_ascii=False)+'\n')
report=dict(groups=len(groups),candidateRows=sum(len(g['candidates']) for g in groups),skipped=skipped,scenarioCounts=dict(collections.Counter(g['row']['scenario'] for g in groups)),observationsSha256=sha(root/'production-pools/observations.jsonl'),groupsSha256=sha(root/'groups.jsonl'),corpusManifestSha256=sha(root/'corpus/manifest.json'),sourceHashes={p:sha(p) for p in ['tools/typing_experiments/right_context_training_groups.py','tools/typing_experiments/right_context_role_corpus.py','tools/typing_experiments/right_context_role_features.py',__file__]})
(root/'selection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
