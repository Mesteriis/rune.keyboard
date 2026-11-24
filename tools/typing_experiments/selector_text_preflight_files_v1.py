"""Bind a diagnostic text preflight to a public source lock and exact input bytes.

No result grants corpus publication, source-label qualification, or independent
holdout status. Historical collectors and their archived guards stay unchanged.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

import control_ledger
import holdout_ledger
import independent_corpus_guard as guard
from joint_exclusion_inputs import source_context_hash
import prepare_external_spelling_holdout as selector
import selector_text_preflight_v1 as text_preflight
from audit_selector_text_exposure import PARTS, WORD

ROOT = Path(__file__).resolve().parents[2]
SOURCE_LOCK = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
LEXICAL = Path(__file__).with_name('holdout-ledger.json')
CONTROLS = Path(__file__).with_name('control-ledger.json')
HELPERS = ('selector_text_preflight_files_v1.py', 'selector_text_preflight_v1.py',
           'audit_selector_text_exposure.py', 'independent_corpus_guard.py',
           'control_ledger.py', 'holdout_ledger.py', 'source_identities.py',
           'conversation_split_checks.py', 'joint_exclusion_inputs.py',
           'public_corpus_preparation_v1.py', 'english_family_keys.py',
           'recover_legacy_families.py', 'prepare_external_spelling_holdout.py',
           'right_context_sentence_audit.py', 'right_context_grammar_features.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def attest_word_rows(parts, sources, lexicon, generator):
    """Match rows to decoded article text; caller must trust the decoder."""
    counts = Counter()
    for part in PARTS:
        for row in parts[part]:
            counts['rows'] += 1
            if (not isinstance(row, dict) or row.get('partition') != part or row.get('language') != 'ru' or
                    not isinstance(row.get('articleId'), str) or not row['articleId'].isascii() or
                    not row['articleId'].isdecimal() or row.get('article') != row['articleId'] or
                    row.get('sourceRepository') not in (None, 'wikimedia/wikipedia') or
                    not isinstance(row.get('expectedSpelling'), str) or not row['expectedSpelling'] or
                    not isinstance(row.get('prefix'), str) or not row['prefix'] or
                    not isinstance(row.get('contextHash'), str) or not isinstance(row.get('sourceSegmentHash'), str)):
                counts['invalidIdentity'] += 1
                continue
            article = sources.get(row['articleId'])
            if not isinstance(article, str):
                counts['missingArticle'] += 1
                continue
            text = unicodedata.normalize('NFC', article)
            matches = 0
            for sentence, start in guard.selector_segments(text):
                for match in WORD.finditer(sentence):
                    if (match.group() != row['expectedSpelling'] or
                            sentence[max(0, match.start()-128):match.start()].lstrip() != row['prefix'] or
                            not guard.whole_selector_token(text, sentence, start, match, {})):
                        continue
                    absolute = WORD.match(text, start + match.start())
                    if (absolute is not None and absolute.group() == match.group() and
                            not text_preflight.source_fragment(text, absolute.start(), absolute.end()) and
                            holdout_ledger.source_segment_hash(sentence) == row['sourceSegmentHash'] and
                            source_context_hash(text, absolute, generator) == row['contextHash']):
                        matches += 1
            if matches != 1:
                counts['unmatchedSource' if matches == 0 else 'ambiguousSource'] += 1
                continue
            families = sorted({analysis.lemma for analysis in lexicon.analyses(row['expectedSpelling'])})
            if not families or row.get('families') != families:
                counts['dictionaryMismatch'] += 1
                continue
            counts['verified'] += 1
    return {name: counts[name] for name in ('rows', 'verified', 'invalidIdentity', 'missingArticle',
                                             'unmatchedSource', 'ambiguousSource', 'dictionaryMismatch')}


def assess_files(data, source, lock_path, lexical_path, controls_path, lexicon, read_batches):
    data, source = Path(data), Path(source)
    input_paths = {'source-lock.json':Path(lock_path), 'lexical-ledger.json':Path(lexical_path),
                   'control-ledger.json':Path(controls_path), 'manifest.json':data/'manifest.json'}
    for part in PARTS:
        for kind in ('text', 'rows'):
            name = f'{part}-{kind}.jsonl'
            input_paths[name] = data/name
    captured = {name:path.read_bytes() for name,path in input_paths.items()}
    lock = json.loads(captured['source-lock.json'])['wikipediaContext']['files']['ru-0007.parquet']
    digest = file_sha(source)
    if source.stat().st_size != lock['bytes'] or digest != lock['sha256']:
        raise ValueError('TEXT_PREFLIGHT_SOURCE_IDENTITY')
    manifest = json.loads(captured['manifest.json'])
    if manifest.get('containsPersonalMessages') is not False or manifest.get('sourceSha256') != digest:
        raise ValueError('TEXT_PREFLIGHT_MANIFEST')
    for part in PARTS:
        for kind in ('text', 'rows'):
            name = f'{part}-{kind}.jsonl'
            if manifest.get('files', {}).get(name) != sha(captured[name]):
                raise ValueError('TEXT_PREFLIGHT_INPUT_IDENTITY')
    texts = {part:[json.loads(line) for line in captured[f'{part}-text.jsonl'].splitlines()] for part in PARTS}
    rows = {part:[json.loads(line) for line in captured[f'{part}-rows.jsonl'].splitlines()] for part in PARTS}
    text_articles = {row['articleId'] for records in texts.values() for row in records}
    row_articles = {row['articleId'] for records in rows.values() for row in records
                    if isinstance(row, dict) and isinstance(row.get('articleId'), str)
                    and row['articleId'].isascii() and row['articleId'].isdecimal()}
    wanted = text_articles | row_articles
    sources = {}
    helper_paths = {name:Path(__file__).with_name(name) for name in HELPERS}
    helper_paths['ranker.py'] = ROOT/'tools/morphology/ranker.py'
    helper_paths['qualification-v2/generate_corpus.py'] = selector.GENERATOR
    for name in ('ewt_surface_exclusions_v1.py', 'ewt-surface-exclusions-v1.json', 'import_english_ewt_exposure.py',
                 'public_sources/ud-ewt-2.18/source-lock.json'):
        helper_paths[name] = Path(__file__).parent/name
    helpers = {name:file_sha(path) for name,path in helper_paths.items()}
    dictionary_bytes = json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':'),
                                  allow_nan=False).encode()
    for articles, values in read_batches(source):
        for article, value in zip(articles, values, strict=True):
            article = str(article)
            if article in wanted:
                if article in sources:
                    raise ValueError('TEXT_PREFLIGHT_DUPLICATE_SOURCE')
                sources[article] = value
    if not text_articles <= set(sources):
        raise ValueError('TEXT_PREFLIGHT_MISSING_SOURCE')
    lexical = holdout_ledger.validate_ledger(json.loads(captured['lexical-ledger.json']))
    controls = control_ledger.validate(json.loads(captured['control-ledger.json']))
    report = text_preflight.assess(texts, rows, sources, lexicon, lexical, controls)
    word_attestation = attest_word_rows(rows, sources, lexicon, selector.load_generator()) if row_articles else {
        'rows': sum(len(rows[part]) for part in PARTS), 'verified': 0, 'invalidIdentity': sum(len(rows[part]) for part in PARTS),
        'missingArticle': 0, 'unmatchedSource': 0, 'ambiguousSource': 0, 'dictionaryMismatch': 0}
    report['wordRowSourceAttestation'] = word_attestation
    if word_attestation['verified'] != word_attestation['rows'] and report['status'] == 'BLOCKED_COVERAGE':
        report['status'] = 'BLOCKED_TEXT_IDENTITIES'
    if (source.stat().st_size != lock['bytes'] or file_sha(source) != digest or
            any(path.read_bytes() != captured[name] for name,path in input_paths.items()) or
            any(file_sha(path) != helpers[name] for name,path in helper_paths.items()) or
            json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':'),
                       allow_nan=False).encode() != dictionary_bytes):
        raise ValueError('TEXT_PREFLIGHT_INPUT_DRIFT')
    report['sourceIdentityVerified'] = True
    report['sourceDecoderAttested'] = False
    report['bindings'] = {'sourceSha256':digest, 'inputs':{name:sha(raw) for name,raw in captured.items()},
                          'helpers':helpers, 'dictionary':json.loads(dictionary_bytes)}
    report['scope'] = 'source-lock-bound-diagnostic-not-admission'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    import pyarrow.parquet as parquet
    sys.path.insert(0, str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    def read_batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id','text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()
    report = assess_files(args.data, args.source, SOURCE_LOCK, LEXICAL, CONTROLS,
                          PymorphyLexicon(cache_size=16384), read_batches)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
