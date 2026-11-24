"""Quarantine an authenticated suspended compound from disclosed retrieval data.

The local snapshot identifies source bytes but does not qualify a corpus or
infer a complete audio compound. --verify-parquet independently checks the
snapshot against the hash-locked public shard; it needs the pinned PyArrow.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/typing_experiments'), str(ROOT / 'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical
import register_retrieval_history as parent
from independent_corpus_guard import selector_segments
from source_identities import unsupported_surface_key

FIXTURE = ROOT / 'tools/typing_experiments/retrieval-suspended-source-v1'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
LOCK = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
UNRESOLVED = ROOT / 'tools/typing_experiments/retrieval-boundary-origin-v1/unresolved.json'
ENTRY = 'historical-retrieval-suspended-source-v1'
ROW_ID = 'retrieval-0b33fc8fd3060a72f19480bf'
ARTICLE = '3089989'
ARTICLE_SHA256 = 'ad02c5743093de5e1d2abc976d45471a0b69c594d96f481cd9d5dc9cc3d082e7'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parent_row():
    rows, _, _ = parent.inputs()
    found = [r for r in rows if r.get('id') == ROW_ID]
    if len(found) != 1 or found[0].get('articleId') != ARTICLE or found[0].get('expectedSpelling') != 'аудио':
        raise ValueError('SUSPENDED_SOURCE_PARENT')
    return found[0]


def project(row, article):
    phrase = row['prefix'] + 'аудио- и видеофайлов'
    if article.count(phrase) != 1:
        raise ValueError('SUSPENDED_SOURCE_BOUNDARY')
    start = article.index(phrase) + len(row['prefix'])
    expected = [('аудио-', start), ('видеофайлов', start + len('аудио- и '))]
    segments = list(selector_segments(article))
    result = []
    for word, offset in expected:
        matches = [(segment, base) for segment, base in segments if base <= offset < base + len(segment)]
        if len(matches) != 1 or article[offset:offset + len(word)] != word:
            raise ValueError('SUSPENDED_SOURCE_SEGMENT')
        segment, base = matches[0]
        relative = offset - base
        if segment[relative:relative + len(word)] != word:
            raise ValueError('SUSPENDED_SOURCE_SEGMENT')
        prefix = segment[max(0, relative - 128):relative].lstrip()
        if not prefix:
            raise ValueError('SUSPENDED_SOURCE_SEGMENT')
        result.append(dict(language='ru', article=ARTICLE, prefix=prefix, typed=word, expectedSpelling=word))
    return result


def article_from_batches(batches):
    found = []
    for ids, texts in batches:
        if len(ids) != len(texts):
            raise ValueError('SUSPENDED_SOURCE_ARTICLE')
        for article, text in zip(ids, texts, strict=True):
            if article == ARTICLE:
                if not isinstance(text, str):
                    raise ValueError('SUSPENDED_SOURCE_ARTICLE')
                found.append(unicodedata.normalize('NFC', text))
    if len(found) != 1 or sha(found[0].encode()) != ARTICLE_SHA256:
        raise ValueError('SUSPENDED_SOURCE_ARTICLE')
    return found[0]


def article_snapshot():
    raw = (FIXTURE / 'article.json').read_bytes()
    try:
        text = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('SUSPENDED_SOURCE_ARTICLE_IDENTITY') from None
    if (not isinstance(text, str) or sha(text.encode()) != ARTICLE_SHA256 or
            raw != (json.dumps(text, ensure_ascii=False) + '\n').encode()):
        raise ValueError('SUSPENDED_SOURCE_ARTICLE_IDENTITY')
    return text


def inputs():
    source = article_snapshot()
    unresolved = json.loads(UNRESOLVED.read_bytes())
    if unresolved != [dict(id=ROW_ID, reason='SOURCE_BOUNDARY_COMPOUND')]:
        raise ValueError('SUSPENDED_SOURCE_UNRESOLVED')
    row = parent_row()
    _, _, parent_bindings = parent.inputs()
    rows = project(row, source)
    paths = [Path(__file__).resolve(), FIXTURE / 'article.json', FIXTURE / 'NOTICE.md', LOCK, UNRESOLVED,
             *(ROOT / 'tools/typing_experiments' / name for name in (
                 'independent_corpus_guard.py', 'holdout_ledger.py', 'control_ledger.py',
                 'conversation_split_checks.py', 'source_identities.py'))]
    return rows, parent_bindings | {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def entries():
    rows, bindings = inputs()
    first = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
                 keys=sorted({control.key_for(r, 'regression') for r in rows}),
                 surfaceKeys=sorted({control.surface_key('ru', r['typed']) for r in rows}),
                 articleKeys=sorted({control.article_key(r) for r in rows}),
                 semantics='Observed suspended-hyphen source and following surface; no inferred completion.')
    second = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(rows),
                  bindings=bindings, keys={'context': sorted(lexical.keys_for(rows, 'context'))},
                  missingAxes=[], unsupportedSurfaceKeys=[unsupported_surface_key('видеофайлов')],
                  notes='Exact disclosed surfaces and contexts; no compound lemma inferred.')
    return first, second


def check():
    first, second = entries()
    a, b = control.load(CONTROL), lexical.load_ledger(LEXICAL)
    if ([e for e in a['entries'] if e['id'] == ENTRY] != [first] or
            [e for e in b['entries'] if e['id'] == second['id']] != [second]):
        raise ValueError('SUSPENDED_SOURCE_REGISTRY_DRIFT')
    return len(inputs()[0])


def verify_parquet(path):
    from selector_text_preflight_files_v2 import read_source_batches, decoder_identity
    lock_raw = LOCK.read_bytes()
    spec = json.loads(lock_raw)['wikipediaContext']['files']['ru-0007.parquet']
    path = Path(path).resolve(strict=True)
    def file_sha():
        with path.open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    if path.stat().st_size != spec['bytes'] or file_sha() != spec['sha256']:
        raise ValueError('SUSPENDED_SOURCE_SHARD')
    identity = decoder_identity()
    found = article_from_batches(read_source_batches(path))
    if found != article_snapshot():
        raise ValueError('SUSPENDED_SOURCE_ARTICLE_IDENTITY')
    if LOCK.read_bytes() != lock_raw or file_sha() != spec['sha256'] or decoder_identity() != identity:
        raise ValueError('SUSPENDED_SOURCE_DRIFT')
    return len(inputs()[0])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--output', type=Path)
    group.add_argument('--verify-parquet', type=Path)
    args = p.parse_args()
    if args.check:
        print(json.dumps({'rows': check(), 'independentQualification': False})); return
    if args.verify_parquet:
        print(json.dumps({'sourceVerifiedRows': verify_parquet(args.verify_parquet), 'independentQualification': False})); return
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('SUSPENDED_SOURCE_OUTPUT')
    old_a, old_b = CONTROL.read_bytes(), LEXICAL.read_bytes()
    first, second = entries()
    controls, stored = json.loads(old_a), json.loads(old_b)
    control.validate(controls); lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id'] == ENTRY for e in controls['entries']) or any(e['id'] == second['id'] for e in stored['entries']):
        raise ValueError('SUSPENDED_SOURCE_EXISTS')
    controls['entries'].append(first); stored['entries'].append(second)
    control.validate(controls); lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes() != old_a or LEXICAL.read_bytes() != old_b or entries() != (first, second):
        raise ValueError('SUSPENDED_SOURCE_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', controls), ('holdout-ledger.json', stored)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': len(inputs()[0]), 'independentQualification': False}))


if __name__ == '__main__':
    main()
