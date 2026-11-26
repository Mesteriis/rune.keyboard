"""Quarantine complete compound tokens disclosed inside historical neighbor prefixes."""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical
import register_neighbor_history as parent
from audit_wordrank_source_boundaries import TOKEN

ENTRY = 'historical-neighbor-prefix-compounds-v1'
FIXTURE = ROOT / 'tools/typing_experiments/neighbor-prefix-compounds-v1'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
TOKENIZER = ROOT / 'tools/typing_experiments/audit_wordrank_source_boundaries.py'
WORD = re.compile('[а-яё]+')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def frames(rows):
    return sorted({(r['shard'], r['article'], r['prefix']) for r in rows})


def interior_tokens(prefix):
    for match in TOKEN.finditer(prefix):
        start, end = match.span()
        # A dangling hyphen at a boundary can connect to an omitted word.
        if (start == 0 or end == len(prefix) or
                (start == 1 and prefix[0] in '-‐‑–') or
                (end == len(prefix) - 1 and prefix[end] in '-‐‑–')):
            continue
        yield match


def project(rows):
    """Only entire, interior tokens from the disclosed text; no inferred lemmas."""
    result = []
    for shard, article, prefix in frames(rows):
        for match in interior_tokens(prefix):
            start, end = match.span()
            token = match.group()
            heads = WORD.findall(token.casefold())
            if not heads or token.casefold() in heads:
                continue
            identity = json.dumps([shard, article, prefix, start, end], ensure_ascii=False, separators=(',', ':'))
            result.append(dict(id=sha(identity.encode()), article=article, shard=shard,
                frame=prefix, offset=start, language='ru', prefix=prefix[:start].lstrip(),
                typed=token, expectedSpelling=token))
    result.sort(key=lambda row: row['id'])
    if len({row['id'] for row in result}) != len(result):
        raise ValueError('NEIGHBOR_COMPOUND_DUPLICATE')
    return result


def verify_sources(rows, source_texts):
    """Check every captured prefix against its pinned article, including token edges."""
    wanted = frames(rows)
    if set(source_texts) != {(s, a) for s, a, _ in wanted}:
        raise ValueError('NEIGHBOR_COMPOUND_ARTICLES')
    multiple = 0
    for shard, article, prefix in wanted:
        text = unicodedata.normalize('NFC', source_texts[(shard, article)] or '')
        positions = [m.start() for m in re.finditer(re.escape(prefix), text)]
        if not positions:
            raise ValueError('NEIGHBOR_COMPOUND_SOURCE_MISMATCH')
        multiple += len(positions) > 1
        for token in interior_tokens(prefix):
            start, end = token.span()
            for pos in positions:
                actual = TOKEN.match(text, pos + start)
                if (actual is None or actual.group() != token.group() or
                        actual.end() != pos + end):
                    raise ValueError('NEIGHBOR_COMPOUND_SOURCE_BOUNDARY')
    return {'frames': len(wanted), 'articles': len(source_texts), 'multipleMatches': multiple}


def audit(output):
    import pyarrow.parquet as parquet
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_COMPOUND_OUTPUT')
    rows, bindings = parent.inputs()
    control_sha, lexical_sha, analyzer_sha = digest(CONTROL), digest(LEXICAL), digest(Path(__file__))
    tokenizer_sha = digest(TOKENIZER)
    manifest = json.loads((parent.FIXTURE / 'manifest.json').read_bytes())
    sources = defaultdict(set)
    for shard, article, _ in frames(rows):
        sources[shard].add(article)
    texts = {}
    for shard, articles in sorted(sources.items()):
        path = ROOT / f'build/typing-ranker-v2/ru-{shard:04d}.parquet'
        expected = manifest['sources'][str(path.relative_to(ROOT))]
        if path.stat().st_size != expected['bytes'] or digest(path) != expected['sha256']:
            raise ValueError('NEIGHBOR_COMPOUND_SOURCE_IDENTITY')
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
                article = str(article)
                if article in articles:
                    key = (shard, article)
                    if key in texts:
                        raise ValueError('NEIGHBOR_COMPOUND_DUPLICATE_ARTICLE')
                    texts[key] = text
        if digest(path) != expected['sha256']:
            raise ValueError('NEIGHBOR_COMPOUND_SOURCE_DRIFT')
    verified = verify_sources(rows, texts)
    projected = project(rows)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in projected).encode()
    controls = control.load(CONTROL)
    old = {key for entry in controls['entries'] for key in entry.get('surfaceKeys', [])}
    surfaces = {control.surface_key('ru', row['typed']) for row in projected}
    counts = verified | {'occurrences': len(projected), 'forms': len(surfaces), 'newForms': len(surfaces - old)}
    if (parent.inputs() != (rows, bindings) or digest(CONTROL) != control_sha or
            digest(LEXICAL) != lexical_sha or digest(Path(__file__)) != analyzer_sha or
            digest(TOKENIZER) != tokenizer_sha):
        raise ValueError('NEIGHBOR_COMPOUND_INPUT_DRIFT')
    receipt = dict(scope='disclosed-neighbor-prefix-compounds', independentQualification=False,
        counts=counts, contextsSha256=sha(raw), analyzerSha256=analyzer_sha, tokenizerSha256=tokenizer_sha,
        parentBindings=bindings, sourceBindings=manifest['sources'], controlLedgerSha256=control_sha,
        lexicalLedgerSha256=lexical_sha)
    output.mkdir(parents=True, mode=0o700)
    (output / 'contexts.jsonl').write_bytes(raw)
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


def entries():
    rows, parent_bindings = parent.inputs()
    raw = (FIXTURE / 'contexts.jsonl').read_bytes()
    receipt = json.loads((FIXTURE / 'receipt.json').read_bytes())
    manifest = json.loads((parent.FIXTURE / 'manifest.json').read_bytes())
    expected = project(rows)
    projected = [json.loads(line) for line in raw.splitlines()]
    counts = receipt.get('counts', {})
    if (receipt.get('scope') != 'disclosed-neighbor-prefix-compounds' or
            receipt.get('independentQualification') is not False or
            receipt.get('contextsSha256') != sha(raw) or receipt.get('analyzerSha256') != digest(Path(__file__)) or
            receipt.get('tokenizerSha256') != digest(TOKENIZER) or
            receipt.get('parentBindings') != parent_bindings or receipt.get('sourceBindings') != manifest['sources'] or
            projected != expected or counts.get('frames') != len(frames(rows)) or
            counts.get('articles') != len({(r['shard'], r['article']) for r in rows}) or
            counts.get('occurrences') != len(projected)):
        raise ValueError('NEIGHBOR_COMPOUND_BINDING')
    paths = [Path(__file__).resolve(), FIXTURE / 'NOTICE.md', FIXTURE / 'contexts.jsonl', FIXTURE / 'receipt.json',
             TOKENIZER]
    bindings = parent_bindings | {str(path.relative_to(ROOT)): digest(path) for path in paths}
    first = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(projected), bindings=bindings,
        keys=sorted({control.key_for(row, 'regression') for row in projected}),
        surfaceKeys=sorted({control.surface_key('ru', row['typed']) for row in projected}),
        articleKeys=sorted({control.article_key(row) for row in projected}),
        semantics='Complete tokens disclosed in historical prefixes; not independent data.')
    second = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(projected),
        bindings=bindings, keys={'context': sorted(lexical.keys_for(projected, 'context'))}, missingAxes=[],
        notes='Complete tokens disclosed in historical prefixes; no inferred word families.')
    if len(first['surfaceKeys']) != counts.get('forms'):
        raise ValueError('NEIGHBOR_COMPOUND_COUNT')
    return first, second


def check():
    first, second = entries()
    a, b = control.load(CONTROL), lexical.load_ledger(LEXICAL)
    if ([e for e in a['entries'] if e['id'] == ENTRY] != [first] or
            [e for e in b['entries'] if e['id'] == ENTRY+'-contexts'] != [second]):
        raise ValueError('NEIGHBOR_COMPOUND_REGISTRY_DRIFT')
    return first['rowCount']


def register(output):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_COMPOUND_OUTPUT')
    old_a, old_b = CONTROL.read_bytes(), LEXICAL.read_bytes()
    receipt = json.loads((FIXTURE / 'receipt.json').read_bytes())
    if receipt.get('controlLedgerSha256') != sha(old_a) or receipt.get('lexicalLedgerSha256') != sha(old_b):
        raise ValueError('NEIGHBOR_COMPOUND_LEDGER_DRIFT')
    first, second = entries()
    a, b = json.loads(old_a), json.loads(old_b)
    control.validate(a); lexical.validate_ledger(copy.deepcopy(b))
    if any(e['id'] == ENTRY for e in a['entries']) or any(e['id'] == second['id'] for e in b['entries']):
        raise ValueError('NEIGHBOR_COMPOUND_EXISTS')
    a['entries'].append(first); b['entries'].append(second)
    control.validate(a); lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes() != old_a or LEXICAL.read_bytes() != old_b or entries() != (first, second):
        raise ValueError('NEIGHBOR_COMPOUND_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', a), ('holdout-ledger.json', b)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': first['rowCount'], 'independentQualification': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--audit', type=Path); group.add_argument('--register', type=Path)
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.audit: audit(args.audit)
    elif args.register: register(args.register)
    else: print(json.dumps({'rows': check(), 'independentQualification': False}))
