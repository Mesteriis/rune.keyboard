from pathlib import Path
import base64
import collections
import hashlib
import json
import sys

sys.path.insert(0, 'tools/typing_experiments')
sys.path.insert(0, 'tools/morphology')
from ranker import PymorphyLexicon
from right_context_continuation_corpus import generate
from right_context_training_groups import query

root = Path(__file__).parent
parent = Path('build/right-context-training-v6-20261027')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
manifest = load(parent / 'corpus/manifest.json')
assert sha(parent / 'corpus/train.jsonl') == manifest['corpusSha256']
lexicon = PymorphyLexicon(cache_size=16384)
assert lexicon.receipt() == load(parent / 'morphology-receipt.json')
old = [json.loads(line) for line in (parent / 'corpus/train.jsonl').read_text().splitlines()]
rows = generate(old, lexicon)
assert len(rows) == len({row['id'] for row in rows})
families = sorted({f for row in rows for f in row.get('contrastFamilies', [row['family']])})
assert families == load(parent / 'frozen-model.json')['trainingFamilies']
(root / 'corpus').mkdir()
with (root / 'corpus/train.jsonl').open('x') as stream:
    stream.write(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows))
sources = ['tools/typing_experiments/right_context_continuation_corpus.py',
           'tools/typing_experiments/right_context_continuation_features.py',
           'tools/typing_experiments/right_context_training_groups.py', str(Path(__file__))]
report = dict(purpose='TRAINING_ONLY_NOT_QUALIFICATION', rows=len(rows), parentRows=len(old),
              families=families, parentCorpusSha256=sha(parent / 'corpus/train.jsonl'),
              corpusSha256=sha(root / 'corpus/train.jsonl'), dictionary=lexicon.receipt(),
              naturalSentencesOrDisclosedFailuresUsedForTraining=False,
              sourceHashes={p: sha(p) for p in sources},
              scenarioCounts=dict(collections.Counter(row['scenario'] for row in rows)))
with (root / 'corpus/manifest.json').open('x') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
queries = list({query(row)['id']: query(row) for row in rows}.values())
with (root / 'queries.jsonl').open('x') as stream:
    stream.write(''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in queries))
enc = lambda s: base64.b64encode(s.encode()).decode()
with (root / 'queries.tsv').open('x') as stream:
    stream.write(''.join('\t'.join([str(i), enc(q['id']), 'train', 'ru', enc(q['prefix']), enc(q['typed'])]) + '\n' for i, q in enumerate(queries)))
print(json.dumps(dict(rows=len(rows), queries=len(queries), families=len(families), scenarios=report['scenarioCounts'])), flush=True)
