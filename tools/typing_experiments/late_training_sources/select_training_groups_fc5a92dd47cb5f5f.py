from pathlib import Path
import collections
import hashlib
import json
import sys

sys.path.insert(0, 'tools/typing_experiments')
from right_context_training_groups import select_groups

root = Path(__file__).parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
manifest = load(root / 'corpus/manifest.json')
assert sha(root / 'corpus/train.jsonl') == manifest['corpusSha256']
assert all(sha(p) == h for p, h in manifest['sourceHashes'].items())
assert sha(root / 'production-pools/observations.jsonl') == load(root / 'production-pools/receipt.json')['outputSha256']
rows = [json.loads(line) for line in (root / 'corpus/train.jsonl').read_text().splitlines()]
observations = [json.loads(line) for line in (root / 'production-pools/observations.jsonl').read_text().splitlines()]
groups, skipped = select_groups(rows, observations)
with (root / 'groups.jsonl').open('x') as stream:
    stream.write(''.join(json.dumps(group, ensure_ascii=False, sort_keys=True) + '\n' for group in groups))
report = dict(groups=len(groups), candidateRows=sum(len(g['candidates']) for g in groups),
              skipped=skipped, scenarioCounts=dict(collections.Counter(g['row']['scenario'] for g in groups)),
              groupsSha256=sha(root / 'groups.jsonl'), observationsSha256=sha(root / 'production-pools/observations.jsonl'),
              corpusManifestSha256=sha(root / 'corpus/manifest.json'),
              sourceHashes=manifest['sourceHashes'] | {str(Path(__file__)): sha(__file__)})
with (root / 'selection.json').open('x') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps(report), flush=True)
