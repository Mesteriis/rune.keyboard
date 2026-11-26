"""Rebuild three historical Side corpora from pinned Wikipedia and registry evidence."""

import argparse
from collections import Counter, defaultdict
import functools
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

from audit_frozen_context_descendants import PREFIX, SPECS, entries_for, folder, verify_variants
from holdout_ledger import keys_for, load_ledger
from import_natural_context_history import GENERATOR_SHA
from recover_available_v6_articles import LEDGER, ROOT, read_lock, sha_file
from recover_legacy_holdout import load_generator
from recover_natural_context_history import verify_shard
from recover_natural_frozen_corpus import digest, encode
from right_context_focus_forms import predicate_contrast, source_surface_refusal
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures, completed_following_words
from right_context_sentence_audit import _source_hash
from right_context_side_forms import grammar_word_sets, non_predicate_contrast
from right_context_training_exclusion import exclude_training_contexts

EVIDENCE = ROOT / 'docs/acceptance/2026-10-27-frozen-context-descendants-evidence.json'
V5_PLAN = ROOT / 'tools/typing_experiments/historical_provenance_sources/v6-inputs/fresh-side-v5-plan.json'
FREQUENCY = ROOT / 'tools/ci/product-replay-v1/sources/ru_50k.txt'
FREQUENCY_SHA = '6095f507cc167488ec66ada5a85ac50433503a08ad24a07c6eabdf54352c4e7f'
GRAMMAR = ROOT / 'app/src/main/assets/smarttyping/experiments/ru-context.gram'
GRAMMAR_SHA = '2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b'
PATTERN = re.compile(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?P<right>[а-яё]{1,32})(?![\w-])')
COPULAS = {'буду', 'будешь', 'будет', 'будем', 'будете', 'будут', 'был', 'была', 'было', 'были'}
GROUPS = ('hard_other_part_negative', 'agreement_role_negative', 'direct_subject_positive',
          'ordinary_other_part_negative')
PARTS = ('calibration', 'holdout')
SHARDS = {'0012.parquet', '0013.parquet', '0014.parquet', '0015.parquet',
          '0016.parquet', '0017.parquet', '0020.parquet'}
SEEDS = {'side': 'right-context-natural-v1-20261027', 'fresh-side-v4': 'right-context-fresh-role-v4-20261027'}


def predicate_pair(word, lexicon, families):
    lexicon._load()
    forms = {form.word for parsed in lexicon._analyzer.parse(word)
             if parsed.normal_form in families for form in parsed.lexeme}
    return predicate_contrast(word, lexicon, forms)


def partition(seed, family):
    return PARTS[hashlib.sha256((seed + ':family:' + family).encode()).digest()[0] % 2]


def row_for(article, source, word, following, prefix, suffix, context_hash, seed, ordinary, features, pair_info):
    families, pure, pair = pair_info(word)
    if not families:
        return None
    partitions = {partition(seed, family) for family in families}
    if len(partitions) != 1:
        return None
    values = dict(zip(FEATURE_NAMES, features.extract(suffix, word), strict=True))
    if (not (values['right_copula_available'] or values['right_subject_available'])
            or not completed_following_words(suffix)):
        return None
    supported = (values['right_copula_number_supported'] or values['right_subject_number_supported']) and not any(
        values[name] for name in ('right_copula_number_conflict', 'right_subject_number_conflict',
                                  'right_copula_gender_conflict', 'right_subject_gender_conflict'))
    if pure:
        if pair is None or (following in COPULAS and supported):
            return None
        group = 'direct_subject_positive' if supported else 'agreement_role_negative'
    else:
        group = 'hard_other_part_negative' if pair else 'ordinary_other_part_negative'
    if pair:
        typed, rival, family = pair['typed'], pair['rival'], pair['family']
    else:
        typed = ordinary(word, seed)
        if typed is None:
            return None
        rival, family = None, families[0]
    selection = digest((seed + ':side:' + article + word + prefix).encode())
    return dict(word=word, typed=typed, rival=rival, family=family, families=families,
                part=partitions.pop(), prefix=prefix, rightContext=suffix, sideGroup=group,
                rightCue='copula' if following in COPULAS else 'subject', article=article, source=source,
                contextHash=context_hash, selectionHash=selection)


def article_rows(article, text, source, targets, generator, features, pair_info, ordinary, left_words, right_words):
    text = unicodedata.normalize('NFC', text or '')
    folded = text.lower()
    if len(folded) != len(text):
        return
    for match in PATTERN.finditer(folded):
        word, following = match['word'], match['right']
        if following not in right_words or word not in left_words:
            continue
        start, end = match.span('word')
        prefix = generator.bounded_prefix(text[max(0, match.start() - 256):start]).rstrip(' \t')
        suffix = text[end:end + 128]
        context_hash = _source_hash(prefix, word, suffix)
        sentence, = keys_for([{'contextHash': context_hash}], 'sentence')
        for name, part, keys in targets:
            if sentence not in keys['sentence']:
                continue
            if name == 'fresh-side-v4' and source_surface_refusal(text[start:end], word):
                continue
            context = dict(prefix=prefix, typed=word, expectedSpelling=word)
            if not keys_for([context], 'context') <= keys['context']:
                continue
            row = row_for(article, source, word, following, prefix, suffix, context_hash,
                          SEEDS[name], ordinary, features, pair_info)
            if row and row['part'] == part:
                yield (name, part), row


def capture(source_dir, entries, lexicon, generator, read_batches):
    lock, _ = read_lock()
    frequency = FREQUENCY.read_bytes()
    if digest(frequency) != FREQUENCY_SHA:
        raise ValueError('SIDE_FREQUENCY_DIGEST')
    known = {line.split()[0] for line in frequency.decode().splitlines() if line}
    predicates, nominatives = grammar_word_sets(GRAMMAR.read_bytes(), GRAMMAR_SHA)
    features = RightContextGrammarFeatures(lexicon)
    left_words = predicates | known
    right_words = (nominatives & known) | COPULAS
    article_targets = defaultdict(list)
    for (name, part), entry in entries.items():
        if name in SEEDS:
            keys = {kind: set(values) for kind, values in entry['keys'].items()}
            for key in keys['article']:
                article_targets[key].append((name, part, keys))

    @functools.lru_cache(maxsize=16384)
    def pair_info(word):
        tags = lexicon.analyses(word)
        families = {tag.lemma for tag in tags}
        pure = bool(tags) and all(tag.pos == 'ADJS' for tag in tags)
        if not tags:
            return [], False, None
        pair = predicate_pair(word, lexicon, families) if pure else non_predicate_contrast(word, lexicon, predicates)
        if pair:
            families.add(pair.get('rivalFamily', pair['family']))
        return sorted(families), pure, pair

    @functools.lru_cache(maxsize=16384)
    def ordinary(word, seed):
        return next((variant for variant, _ in generator.safe_typos(word, 'ru', known, seed + ':side:' + word)
                     if 3 <= len(variant) <= 32 and not lexicon.analyses(variant)), None)

    found = defaultdict(dict)
    for shard in lock['shards']:
        code = shard['name']
        if code not in SHARDS:
            continue
        path = source_dir / code
        verify_shard(path, shard)
        source = code if code == '0020.parquet' else 'ru-' + code
        for articles, texts in read_batches(path):
            for article, text in zip(articles, texts, strict=True):
                article = str(article)
                key, = keys_for([{'article': article}], 'article')
                if key not in article_targets:
                    continue
                for scope, row in article_rows(article, text, source, article_targets[key],
                                               generator, features, pair_info, ordinary, left_words, right_words):
                    if key in found[scope] and found[scope][key] != row:
                        raise ValueError('SIDE_DUPLICATE_CAPTURE:' + str(scope))
                    found[scope][key] = row
        verify_shard(path, shard)
        print(code, 'verified', flush=True)
    return found


def variants(part, captures):
    result = []
    for item in captures:
        forms = [(item['typed'], 'typo', False, False, item['rightContext']),
                 (item['typed'], 'unfinished', False, True, ' ' + completed_following_words(item['rightContext'])[0]),
                 (item['word'], 'correct', True, False, item['rightContext']),
                 ('@' + item['word'], 'protected', True, False, item['rightContext'])]
        if item['rival']:
            forms.append((item['rival'], 'correct_rival', True, False, item['rightContext']))
        for typed, group, control, retain, suffix in forms:
            result.append(dict(item, id=f'right-side-{part}-{len(result):06d}', split=part,
                               language='ru', typed=typed, rightContext=suffix, group=group, noAuto=control,
                               retainBaseline=retain, expectedSpelling=typed if control else item['word']))
    return result


def serialize(part, rows):
    return {
        'jsonl': ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode(),
        'tsv': ''.join('\t'.join([str(i), encode(r['id']), part, 'ru', encode(r['prefix']), encode(r['typed'])]) + '\n'
                       for i, r in enumerate(rows)).encode(),
    }


def read_v5_plan():
    raw = V5_PLAN.read_bytes()
    if digest(raw) != SPECS['fresh-side-v5']['planSha256']:
        raise ValueError('SIDE_V5_PLAN_DIGEST')
    return raw, json.loads(raw)


def v5_manifest(plan_bytes, plan, files, counts, audits):
    manifest = dict(stage='frozen-before-any-model-scoring', files=files, counts=counts,
                    exclusionAudits=audits, planSha256=digest(plan_bytes),
                    sourceManifestSha256=plan['sourceManifestSha256'],
                    trainingCorpusManifestSha256=plan['trainingCorpusManifestSha256'],
                    familyArticleContextSeparation=True, excludedAdditionalTrainingFamilies=True,
                    modelScoresUsed=False, modelBindingRequiredBeforeScoring=True)
    raw = (json.dumps(manifest, indent=2) + '\n').encode()
    if digest(raw) != SPECS['fresh-side-v5']['manifestSha256']:
        raise ValueError('SIDE_V5_MANIFEST_DIGEST')
    return raw


def recover(source_dir, lexicon, generator, read_batches):
    evidence = json.loads(EVIDENCE.read_bytes())['receipt']
    names = (*SEEDS, 'fresh-side-v5')
    indexed = {e['id']: e for e in load_ledger(LEDGER)['entries']}
    entries = {(n, p): indexed[PREFIX + n + '-' + p] for n in names for p in PARTS}
    plan_bytes, plan = read_v5_plan()
    if sha_file(ROOT / 'tools/typing_experiments/right_context_training_exclusion.py') != plan['filterSourceSha256']:
        raise ValueError('SIDE_V5_FILTER_DIGEST')
    found = capture(source_dir, entries, lexicon, generator, read_batches)
    payloads, stats, parent_rows = {}, {}, {}
    v5_counts, v5_audits, v5_files = {}, {}, {}
    for name in names:
        for part in PARTS:
            entry = entries[name, part]
            if name == 'fresh-side-v5':
                rows, v5_audits[part] = exclude_training_contexts(parent_rows[part], plan['excludedFamilies'])
            else:
                relevant = found[name, part]
                missing = set(entry['keys']['article']) - set(relevant)
                if missing:
                    raise ValueError(f'SIDE_MISSING_CAPTURES:{name}:{part}:{len(missing)}')
                order = sorted(relevant.values(), key=lambda r: (GROUPS.index(r['sideGroup']), r['selectionHash']))
                rows = variants(part, order)
                if name == 'fresh-side-v4':
                    parent_rows[part] = rows
            frames = verify_variants(rows)
            verified, facts = entries_for(name, part, rows, frames, lexicon, entry['bindings'])
            if len(verified) != 1 or verified[0]['keys'] != entry['keys'] or len(rows) != entry['rowCount']:
                raise ValueError(f'SIDE_REGISTRY_MISMATCH:{name}:{part}')
            stats[name + '-' + part] = dict(rows=len(rows), contexts=len(frames))
            if name == 'fresh-side-v5':
                v5_counts[part] = dict(rows=len(rows), contexts=len(frames),
                    groups=dict(Counter(r['sideGroup'] for r in frames)),
                    families=len({family for row in frames for family in row['families']}),
                    controls=sum(row['noAuto'] for row in rows),
                    unfinishedControls=sum(row['retainBaseline'] for row in rows))
            for suffix, raw in serialize(part, rows).items():
                path = f'{folder(name)}/corpus/{part}.{suffix}'
                if digest(raw) != entry['bindings'][path] or digest(raw) != evidence['bindings'][path]:
                    raise ValueError(f'SIDE_ORIGINAL_DIGEST:{name}:{part}:{suffix}')
                payloads[Path(path).relative_to('build')] = raw
                if name == 'fresh-side-v5':
                    v5_files[f'{part}.{suffix}'] = digest(raw)
            print(name, part, len(rows), 'exact rows', flush=True)
    base = Path(folder('fresh-side-v5')).relative_to('build')
    payloads[base / 'plan.json'] = plan_bytes
    payloads[base / 'corpus/manifest.json'] = v5_manifest(plan_bytes, plan, v5_files, v5_counts, v5_audits)
    return payloads, stats, v5_audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'build') or output.exists():
        parser.error('output must be a new directory inside the repository build directory')

    import pyarrow.parquet as parquet

    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon

    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()

    lexicon = PymorphyLexicon(cache_size=16384)
    payloads, stats, audits = recover(args.source_dir, lexicon, load_generator(GENERATOR_SHA), batches)
    output.mkdir(parents=True, exist_ok=False)
    for path, raw in payloads.items():
        destination = output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    _, lock_bytes = read_lock()
    report = dict(schema=1, modelCalls=0, independentQualification=False,
                  sourceLockSha256=digest(lock_bytes), ledgerSha256=sha_file(LEDGER),
                  evidenceSha256=sha_file(EVIDENCE), recoverySourceSha256=sha_file(__file__),
                  stats=stats, freshSideV5Exclusions=audits,
                  files={str(path): digest(raw) for path, raw in payloads.items()})
    (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
