from pathlib import Path
import sys,json,hashlib,base64
sys.path.insert(0,'tools/typing_experiments')
from right_context_role_corpus import generate
from right_context_contrast_corpus import PAIRS
from right_context_training_groups import query
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-training-v4-20261027');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
lex=PymorphyLexicon(cache_size=16384);lex._load();paradigms={}
for singular,plural in PAIRS:
 lemmas={a.lemma for a in lex.analyses(singular) if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc'}
 paradigms[singular]=sorted({p.word for parsed in lex._analyzer.parse(singular) if parsed.normal_form in lemmas for p in parsed.lexeme})
rows,skipped=generate(lex,paradigms);corpus=root/'corpus';corpus.mkdir();payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode();(corpus/'train.jsonl').write_bytes(payload)
manifest=dict(purpose='TRAINING_ONLY_NOT_QUALIFICATION',origin='Authored templates and existing 24 training-family dictionary paradigms only',rows=len(rows),families=sorted({r['family'] for r in rows}),skipped=skipped,dictionary=lex.receipt(),corpusSha256=sha(corpus/'train.jsonl'),sourceHashes={p:sha(p) for p in ['tools/typing_experiments/right_context_role_corpus.py','tools/typing_experiments/right_context_role_features.py','tools/typing_experiments/grammar_contrast_corpus.py',__file__]},consumedNaturalHoldoutUsedForTraining=False)
(corpus/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
queries=list({query(r)['id']:query(r) for r in rows}.values());(root/'queries.jsonl').write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in queries));enc=lambda s:base64.b64encode(s.encode()).decode()
(root/'queries.tsv').write_text(''.join('\t'.join([str(i),enc(q['id']),'train','ru',enc(q['prefix']),enc(q['typed'])])+'\n' for i,q in enumerate(queries)))
print(json.dumps(dict(rows=len(rows),queries=len(queries),families=len(manifest['families']),skipped=skipped)),flush=True)
