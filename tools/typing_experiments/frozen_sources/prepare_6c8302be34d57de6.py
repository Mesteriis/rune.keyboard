from pathlib import Path
import base64
import collections
import hashlib
import json
import sys

sys.path.insert(0, 'tools/typing_experiments')
sys.path.insert(0, 'tools/morphology')
from ranker import PymorphyLexicon
from right_context_instrumental_corpus import generate, PAIRS
from right_context_training_groups import query

root = Path(__file__).parent
parent = Path('build/right-context-training-v7-20261027')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
old_manifest = load(parent / 'corpus/manifest.json')
assert sha(parent / 'corpus/train.jsonl') == old_manifest['corpusSha256']
assert all(sha(p) == h for p, h in old_manifest['sourceHashes'].items())
lexicon = PymorphyLexicon(cache_size=16384)
assert lexicon.receipt() == load(parent / 'morphology-receipt.json')
lexicon._load()
paradigms = {}
for _, noun, _ in PAIRS:
    lemmas = {a.lemma for a in lexicon.analyses(noun) if a.pos == 'NOUN' and a.case == 'nomn'}
    paradigms[noun] = sorted({p.word for parsed in lexicon._analyzer.parse(noun)
                             if parsed.normal_form in lemmas for p in parsed.lexeme})
new, skipped = generate(lexicon, paradigms)
old = [json.loads(line) for line in (parent / 'corpus/train.jsonl').read_text().splitlines()]
rows = new
assert len(rows) == len({row['id'] for row in rows})
families = sorted({f for row in rows for f in row.get('contrastFamilies', [row['family']])})
new_families = sorted(set(families) - set(old_manifest['families']))
assert set(new_families) == {'ум', 'бог', 'беда', 'боль'}
(root / 'corpus').mkdir()
with (root / 'corpus/train.jsonl').open('x') as stream:
    stream.write(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows))
sources = [Path('tools/typing_experiments/right_context_instrumental_corpus.py'),
           Path('tools/typing_experiments/prepare_word_ranking.py'),
           Path('tools/typing_experiments/prepare_refinement.py'),
           Path('tools/typing_experiments/right_context_left_sequence_features.py'),
           Path('tools/typing_experiments/right_context_applied_corpus.py'),
           Path('tools/typing_experiments/right_context_applied_features.py'),
           Path('tools/typing_experiments/grammar_contrast_corpus.py'),
           Path('tools/typing_experiments/right_context_training_groups.py'), Path(__file__)]
manifest = dict(purpose='AUTHORED_INPUT_PREPARATION_NOT_A_TRAINED_MODEL', rows=len(rows), oldRowsIncluded=0,
                instrumentalRows=len(new), newlySupervisedFamilies=new_families, families=families, skipped=skipped,
                noNaturalFailuresUsedForSupervision=True, dictionary=lexicon.receipt(),
                oldCorpusSha256=sha(parent / 'corpus/train.jsonl'), corpusSha256=sha(root / 'corpus/train.jsonl'),
                sourceHashes={str(p): sha(p) for p in sources},
                scenarioCounts=dict(collections.Counter(row['scenario'] for row in rows)))
with (root / 'corpus/manifest.json').open('x') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
queries = list({query(row)['id']: query(row) for row in rows}.values())
with (root / 'queries.jsonl').open('x') as stream:
    stream.write(''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in queries))
enc = lambda s: base64.b64encode(s.encode()).decode()
with (root / 'queries.tsv').open('x') as stream:
    stream.write(''.join('\t'.join([str(i), enc(q['id']), 'train', 'ru', enc(q['prefix']), enc(q['typed'])]) + '\n' for i, q in enumerate(queries)))
print(json.dumps(dict(rows=len(rows), newRows=len(new), families=len(families), queries=len(queries), skipped=skipped)), flush=True)
