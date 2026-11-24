"""Recover the seven historical Wikipedia context pools into local build output."""

import argparse
import functools
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

from holdout_ledger import keys_for, load_ledger
from import_natural_context_history import GENERATOR_SHA, PREFIX, entries_for
from recover_available_v6_articles import LEDGER, ROOT, read_lock, sha_file
from recover_legacy_holdout import load_generator
from right_context_focus_forms import predicate_contrast
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures
from right_context_sentence_audit import _source_hash

SEED = 'right-context-natural-v1-20261027'
PATTERN = re.compile(
    r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+'
    r'(?:буду|будешь|будет|будем|будете|будут|был|была|было|были)(?=[ \t.,!?;:]|$)'
)
EVIDENCE = ROOT / 'docs/acceptance/2026-10-27-natural-context-history-evidence.json'


def find_forms(word, lexicon):
    tags = lexicon.analyses(word)
    if not tags or any(tag.pos != 'ADJS' for tag in tags):
        return None
    lexicon._load()
    lemmas = {tag.lemma for tag in tags}
    paradigm = {form.word for parsed in lexicon._analyzer.parse(word)
                if parsed.normal_form in lemmas for form in parsed.lexeme}
    return predicate_contrast(word, lexicon, paradigm)


def capture_article(article, text, source, keys, generator, forms, features):
    text = unicodedata.normalize('NFC', text or '')
    folded = text.lower()
    matches = {}
    if len(folded) != len(text):
        return matches
    for match in PATTERN.finditer(folded):
        word = match['word']
        start, end = match.span('word')
        prefix = generator.bounded_prefix(text[max(0, start - 256):start]).rstrip(' \t')
        suffix = text[end:end + 128]
        context_hash = _source_hash(prefix, word, suffix)
        if not keys_for([{'contextHash': context_hash}], 'sentence') <= keys['sentence']:
            continue
        context = dict(prefix=prefix, typed=word, expectedSpelling=word)
        if not keys_for([context], 'context') <= keys['context']:
            continue
        pair = forms(word)
        if pair is None:
            continue
        target = dict(zip(FEATURE_NAMES, features.extract(suffix, word), strict=True))
        rival = dict(zip(FEATURE_NAMES, features.extract(suffix, pair['rival']), strict=True))
        if (target['right_copula_number_supported'] != 1 or target['right_copula_number_conflict']
                or rival['right_copula_number_conflict'] != 1):
            continue
        selection = hashlib.sha256((SEED + ':wiki:' + article + word + prefix).encode()).hexdigest()
        family = hashlib.sha256((SEED + ':family:' + pair['family']).encode()).digest()[0]
        row = dict(pair, prefix=prefix, rightContext=suffix, article=article, source=source,
                   contextHash=context_hash, selectionHash=selection,
                   provisionalSplit='holdout' if family % 2 else 'calibration')
        # The original collector emitted the first identical normalized context.
        matches.setdefault(context_hash, row)
    return matches


def verify_shard(path, shard):
    if path.stat().st_size != shard['bytes'] or sha_file(path) != shard['sha256']:
        raise ValueError('NATURAL_CONTEXT_SHARD_IDENTITY:' + path.name)


def recover_pool(path, shard, entry, historical, lexicon, generator, read_batches):
    verify_shard(path, shard)
    name = entry['id'].removeprefix(PREFIX)
    row_path = f'build/{name}/contexts.unqualified.jsonl'
    source_path, = (path for path in entry['bindings'] if path.endswith('.parquet'))
    if (entry['bindings'][row_path] != historical[row_path]
            or entry['bindings'][source_path] != historical[source_path]
            or historical[source_path] != shard['sha256']
            or Path(source_path).name.removeprefix('ru-') != shard['name']):
        raise ValueError('NATURAL_CONTEXT_ORIGINAL_BINDINGS:' + name)

    keys = {axis: set(values) for axis, values in entry['keys'].items()}
    forms = functools.lru_cache(maxsize=8192)(lambda word: find_forms(word, lexicon))
    features = RightContextGrammarFeatures(lexicon)
    captures = {}
    for articles, texts in read_batches(path):
        for article, text in zip(articles, texts, strict=True):
            article = str(article)
            key, = keys_for([{'article': article}], 'article')
            if key not in keys['article']:
                continue
            choices = capture_article(article, text, Path(source_path).name, keys,
                                      generator, forms, features)
            if key in captures or len(choices) != 1:
                raise ValueError('NATURAL_CONTEXT_AMBIGUOUS_CAPTURE:' + name)
            captures[key], = choices.values()
    verify_shard(path, shard)
    if set(captures) != keys['article']:
        raise ValueError('NATURAL_CONTEXT_MISSING_ARTICLE:' + name)

    rows = sorted(captures.values(), key=lambda row: (row['provisionalSplit'], row['selectionHash']))
    recovered, facts = entries_for(name, rows, lexicon, entry['bindings'])
    if len(recovered) != 1 or recovered[0]['keys'] != entry['keys'] or len(rows) != entry['rowCount']:
        raise ValueError('NATURAL_CONTEXT_REGISTRY_MISMATCH:' + name)
    raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    if hashlib.sha256(raw).hexdigest() != historical[row_path]:
        raise ValueError('NATURAL_CONTEXT_ORIGINAL_ROW_DIGEST:' + name)
    return raw, facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'build') or output.exists():
        parser.error('output must be a new directory inside the repository build directory')

    import pyarrow
    import pyarrow.parquet as parquet

    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon

    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()

    evidence = json.loads(EVIDENCE.read_bytes())['receipt']
    lock, lock_bytes = read_lock()
    shards = {s['name']: s for s in lock['shards']}
    ledger = load_ledger(LEDGER)
    generator = load_generator(GENERATOR_SHA)
    lexicon = PymorphyLexicon(cache_size=16384)
    recovered = {}
    for entry in ledger['entries']:
        if not entry['id'].startswith(PREFIX):
            continue
        pool = entry['id'].removeprefix(PREFIX)
        source, = (p for p in entry['bindings'] if p.endswith('.parquet'))
        shard = shards[Path(source).name.removeprefix('ru-')]
        raw, facts = recover_pool(args.source_dir / shard['name'], shard, entry,
                                  evidence['bindings'], lexicon, generator, batches)
        if facts != evidence['counts'][pool]:
            raise ValueError('NATURAL_CONTEXT_ORIGINAL_COUNTS:' + pool)
        recovered[pool] = (raw, facts, shard['name'])

    if set(recovered) != set(evidence['counts']):
        raise ValueError('NATURAL_CONTEXT_POOL_COVERAGE')
    report = dict(schema=1, sourceLockSha256=hashlib.sha256(lock_bytes).hexdigest(),
                  ledgerSha256=sha_file(LEDGER), originalEvidenceSha256=sha_file(EVIDENCE),
                  recoverySourceSha256=sha_file(__file__), pyarrowVersion=pyarrow.__version__,
                  dictionary=lexicon.receipt(), modelCalls=0, independentQualification=False, pools={})
    output.mkdir(parents=True, exist_ok=False)
    for pool, (raw, facts, shard) in sorted(recovered.items()):
        filename = pool + '.jsonl'
        (output / filename).write_bytes(raw)
        report['pools'][pool] = dict(facts, shard=shard, sha256=hashlib.sha256(raw).hexdigest())
    (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(sum(facts['rows'] for _, facts, _ in recovered.values()), 'exact historical rows')


if __name__ == '__main__':
    main()
