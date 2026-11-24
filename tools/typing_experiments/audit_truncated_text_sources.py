#!/usr/bin/env python3
"""Recover full public source tokens behind truncated disclosed fragments."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import historical_data_fixtures as historical_data
import historical_model_fixtures as historical_model
import control_ledger as control
from holdout_ledger import keys_for, load_ledger
from audit_selector_text_exposure import WORD
from audit_wordrank_source_boundaries import TOKEN
from independent_corpus_guard import selector_segments
from ranker import PymorphyLexicon

PARTS = ('train', 'dev', 'test')
CORPORA = {'word': 'build/typing-word-ranking/data', 'refinement': 'typing-refinement/data',
           'epoch': 'typing-extra-epochs/data'}
HELPERS = ('tools/typing_experiments/audit_selector_text_exposure.py',
           'tools/typing_experiments/audit_wordrank_source_boundaries.py',
           'tools/typing_experiments/independent_corpus_guard.py',
           'tools/typing_experiments/control_ledger.py', 'tools/typing_experiments/holdout_ledger.py',
           'tools/typing_experiments/source_identities.py', 'tools/morphology/ranker.py',
           'tools/ci/historical_data_fixtures.py', 'tools/ci/historical_model_fixtures.py',
           'tools/ci/historical_model_sources.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def derive(corpora, sources, lexicon):
    if set(corpora) != set(CORPORA):
        raise ValueError('TRUNCATED_CORPORA')
    rows = []
    for name in CORPORA:
        if set(corpora[name]) != set(PARTS):
            raise ValueError('TRUNCATED_PARTITIONS')
        for part in PARTS:
            seen = set()
            for record in corpora[name][part]:
                if (not isinstance(record, dict) or set(record) != {'articleId', 'text'} or
                        not isinstance(record['articleId'], str) or record['articleId'] in seen or
                        not isinstance(record['text'], str) or not record['text'] or record['articleId'] not in sources):
                    raise ValueError('TRUNCATED_RECORD')
                article, fragment = record['articleId'], record['text']
                seen.add(article)
                source = unicodedata.normalize('NFC', sources[article] or '')
                original = list(WORD.finditer(source))
                clean = ' '.join(WORD.findall(source.lower()))
                if not clean.startswith(fragment) or [m.group().lower() for m in original] != WORD.findall(source.lower()):
                    raise ValueError('TRUNCATED_SOURCE_MISMATCH')
                if not (len(fragment) < len(clean) and fragment[-1].isalpha() and clean[len(fragment)].isalpha()):
                    continue
                words = list(WORD.finditer(fragment))
                if not words or words[-1].end() != len(fragment) or len(words) > len(original):
                    raise ValueError('TRUNCATED_WORD_MAPPING')
                ordinal = len(words) - 1
                partial, head = words[-1].group(), original[ordinal].group()
                if not head.lower().startswith(partial) or len(head.lower()) <= len(partial):
                    raise ValueError('TRUNCATED_WORD_MAPPING')
                tokens = list(TOKEN.finditer(source))
                index = bisect.bisect_right([m.start() for m in tokens], original[ordinal].start()) - 1
                if index < 0 or tokens[index].end() < original[ordinal].end():
                    raise ValueError('TRUNCATED_TOKEN_MAPPING')
                token = tokens[index]
                segments = list(selector_segments(source))
                segment_index = bisect.bisect_right([start for _, start in segments], token.start()) - 1
                if segment_index < 0:
                    raise ValueError('TRUNCATED_SEGMENT')
                segment, start = segments[segment_index]
                offset = token.start() - start
                if offset < 0 or segment[offset:offset + len(token.group())] != token.group():
                    raise ValueError('TRUNCATED_SEGMENT')
                families = sorted({a.lemma for a in lexicon.analyses(head.casefold())})
                identity = f'{name}:{part}:{article}:{token.start()}:{token.end()}:{ordinal}'
                rows.append(dict(id=sha(identity.encode()), corpus=name, partition=part, language='ru',
                    article=article, prefix=segment[max(0, offset-128):offset].lstrip(),
                    typed=token.group(), expectedSpelling=token.group(), head=head.casefold(),
                    partial=partial, wordOrdinal=ordinal, sourceStart=token.start(), sourceEnd=token.end(),
                    families=families))
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('TRUNCATED_DUPLICATE')
    return sorted(rows, key=lambda r:r['id'])


def run(parquet, output):
    import pyarrow.parquet as pq
    parquet, output = Path(parquet), Path(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'):
        raise ValueError('TRUNCATED_OUTPUT')
    lock_path = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
    control_path = ROOT / 'tools/typing_experiments/control-ledger.json'
    lexical_path = ROOT / 'tools/typing_experiments/holdout-ledger.json'
    inputs = {str(p.relative_to(ROOT)): p.read_bytes() for p in (lock_path, control_path, lexical_path, Path(__file__).resolve())}
    helpers = {name: sha((ROOT / name).read_bytes()) for name in HELPERS}
    lock = json.loads(inputs[str(lock_path.relative_to(ROOT))]); expected = lock['wikipediaContext']['files']['ru-0007.parquet']
    with parquet.open('rb') as f:
        source_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    if source_sha != expected['sha256'] or parquet.stat().st_size != expected['bytes']:
        raise ValueError('TRUNCATED_SOURCE_IDENTITY')
    _, model = historical_model.verify(); data = historical_data.verify()
    archives = {'word': model, 'refinement': data, 'epoch': data}
    names = {name:{p:f'{folder}/{p}-text.jsonl' for p in PARTS} for name,folder in CORPORA.items()}
    corpora = {name:{p:[json.loads(line) for line in archives[name][names[name][p]].splitlines()] for p in PARTS} for name in CORPORA}
    wanted = {r['articleId'] for parts in corpora.values() for records in parts.values() for r in records}
    sources = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for ident, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            ident = str(ident)
            if ident in wanted:
                if ident in sources:
                    raise ValueError('TRUNCATED_DUPLICATE_SOURCE')
                sources[ident] = text
    if set(sources) != wanted:
        raise ValueError('TRUNCATED_MISSING_SOURCE')
    dictionary = PymorphyLexicon(cache_size=16384); dictionary_receipt = dictionary.receipt()
    rows = derive(corpora, sources, dictionary)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()
    controls = control.validate(json.loads(inputs[str(control_path.relative_to(ROOT))]))
    lexical = load_ledger(lexical_path)
    old_surfaces = {v for e in controls['entries'] for v in e.get('surfaceKeys', [])}
    old_families = {v for e in lexical['entries'] for v in e['keys'].get('family', [])}
    surfaces = {control.surface_key('ru', r['typed']) for r in rows}
    families = keys_for([r for r in rows if r['families']], 'family')
    counts = dict(rows=len(rows), forms=len(surfaces), newForms=len(surfaces-old_surfaces),
                  families=len(families), newFamilies=len(families-old_families),
                  unknownRows=sum(not r['families'] for r in rows),
                  corpusRows={name:sum(r['corpus']==name for r in rows) for name in CORPORA})
    _, model_after = historical_model.verify(); data_after = historical_data.verify()
    with parquet.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != source_sha:
            raise ValueError('TRUNCATED_SOURCE_DRIFT')
    if (dictionary.receipt() != dictionary_receipt or
        any((ROOT / name).read_bytes() != raw_bytes for name, raw_bytes in inputs.items()) or
        any(sha((ROOT / name).read_bytes()) != digest for name,digest in helpers.items()) or
        any((model_after if name == 'word' else data_after)[names[name][p]] != archives[name][names[name][p]]
            for name in CORPORA for p in PARTS)):
        raise ValueError('TRUNCATED_INPUT_DRIFT')
    receipt = dict(scope='disclosed-historical-truncated-source-boundary', independentQualification=False,
        sourceSha256=source_sha, sourceLockSha256=sha(inputs[str(lock_path.relative_to(ROOT))]),
        controlLedgerSha256=sha(inputs[str(control_path.relative_to(ROOT))]),
        lexicalLedgerSha256=sha(inputs[str(lexical_path.relative_to(ROOT))]),
        analyzerSha256=sha(inputs[str(Path(__file__).resolve().relative_to(ROOT))]), helperSha256=helpers,
        archiveTextSha256={name:{p:sha(archives[name][names[name][p]]) for p in PARTS} for name in CORPORA},
        dictionary=dictionary_receipt, contextsSha256=sha(raw), counts=counts)
    output.mkdir(parents=True, mode=0o700)
    (output/'contexts.jsonl').write_bytes(raw)
    (output/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    return counts


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', required=True, type=Path); parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args(); print(json.dumps(run(args.parquet, args.output), sort_keys=True))
