"""Portable, isolated fixtures for the three original historical test modules."""
from contextlib import contextmanager
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

import historical_data_fixtures as core
import historical_model_sources as sources

ROOT = sources.ROOT
DATA = Path(__file__).with_name('historical-model-fixtures-v1')
ARCHIVE_SHA256 = '8c2e7bcf8906651185683220c32ac4a245c576f852416b77a365f1e95ce90ec2'
ENTRY = 'public-word-ranking-contexts-v1'
MODEL_PINS = {
    'build/typing-experiments/catboost-reference.cbm': 'f79649eab727b90ae6da22e8c873a12d2f8ac9c72c0e5db6cda68a8660a25891',
    'build/typing-refinement/ranker/pairwise.cbm': '2970cbe699916c45b516e3fc42fc08eda443adc8c425869b5eb82a20c1ee5d23',
    'build/typing-refinement/ranker/pairwise.bin': 'f3ac83997946b97b57f410f0955a9a479a72453f4c68ed4f473c1afded583648',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bundle(data=DATA):
    meta = json.loads((data / 'manifest.json').read_text())
    raw = (data / 'files.tar.gz').read_bytes()
    if (meta.get('schemaVersion') != 1 or meta.get('purpose') != 'ORIGINAL_HISTORICAL_TEST_FIXTURES' or
            digest(raw) != ARCHIVE_SHA256 or meta.get('archiveSha256') != ARCHIVE_SHA256 or
            meta.get('sourceIndexSha256') != sources.sha(sources.DATA / 'manifest.json') or
            meta.get('coreManifestSha256') != sources.sha(core.DATA / 'manifest.json') or
            meta.get('articleAttributionSha256') != sources.sha(data / 'articles.jsonl') or
            meta.get('noticeSha256') != sources.sha(data / 'NOTICE.md')):
        raise ValueError('MODEL_FIXTURE_ARCHIVE_IDENTITY')
    expected_repository = {
        'app/src/main/assets/smarttyping/experiments/ru-context.bin',
        'tools/model/rune-text-0.2/source-lock.json',
        'tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json',
    }
    if set(meta.get('repositoryFiles', {})) != expected_repository:
        raise ValueError('MODEL_FIXTURE_REPOSITORY_SCOPE')
    payloads = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as bundle:
        for member in bundle:
            name = sources.relative(member.name)
            if (not member.isfile() or name in payloads or name not in meta['files'] or
                    member.size != meta['files'][name]['bytes'] or member.size < 0):
                raise ValueError('MODEL_FIXTURE_ARCHIVE_MEMBER')
            total += member.size
            if total > 64 * 1024 * 1024:
                raise ValueError('MODEL_FIXTURE_ARCHIVE_LIMIT')
            content = bundle.extractfile(member).read(member.size + 1)
            if len(content) != member.size or digest(content) != meta['files'][name]['sha256']:
                raise ValueError('MODEL_FIXTURE_PAYLOAD_IDENTITY')
            payloads[name] = content
    if set(payloads) != set(meta['files']):
        raise ValueError('MODEL_FIXTURE_ARCHIVE_INCOMPLETE')
    for name, expected in {
        'tools/typing_experiments/baseline/ru-ranker.bin': 'bc7542fa35ab615718ee636bd530868441101a4cb89d86aef26b3af1038d8c43',
        'app/src/main/assets/smarttyping/experiments/ru-context.bin': 'c97774d38d35393cbe0e99ea4271e40409fbdce0c08cc21fda5f3f7bf4fd006b',
    }.items():
        if (ROOT / name).is_symlink() or sources.sha(ROOT / name) != expected:
            raise ValueError('MODEL_FIXTURE_REPOSITORY_REFERENCE')
    for name, expected in MODEL_PINS.items():
        if digest(payloads[name]) != expected:
            raise ValueError('MODEL_FIXTURE_REFERENCE_IDENTITY')
    word = 'build/typing-word-ranking/data/'
    if digest(payloads[word + 'manifest.json']) != sources.WORD_SHA:
        raise ValueError('MODEL_FIXTURE_WORD_MANIFEST')
    manifest = json.loads(payloads[word + 'manifest.json'])
    for name, expected in manifest['files'].items():
        sources.relative(name)
        if '/' in name or digest(payloads[word + name]) != expected:
            raise ValueError('MODEL_FIXTURE_WORD_DATA')
    articles = {a for part in manifest['partitions'].values() for a in part['articles']}
    credit = [json.loads(line) for line in (data / 'articles.jsonl').read_text().splitlines()]
    if (len(credit) != len(articles) or {r['articleId'] for r in credit} != articles or
            any(not r.get('title') or r['historyUrl'] !=
                'https://ru.wikipedia.org/w/index.php?curid=' + r['articleId'] + '&action=history' for r in credit)):
        raise ValueError('MODEL_FIXTURE_ATTRIBUTION')
    for name, record in meta['files'].items():
        if record['mode'] not in ('raw', 'template') or not set(record['profiles']) <= {'baseline', 'refinement', 'word'}:
            raise ValueError('MODEL_FIXTURE_SCHEMA')
        if record['mode'] == 'raw' and record['originalSha256'] != record['sha256']:
            raise ValueError('MODEL_FIXTURE_RAW_CHANGED')
    return meta, payloads


def context_entry(data=DATA, payloads=None):
    if payloads is None:
        _, payloads = read_bundle(data)
    rows = []
    for part in ('train', 'dev', 'test'):
        rows.extend(json.loads(line) for line in payloads['build/typing-word-ranking/data/' + part + '-rows.jsonl'].splitlines())
    return {'id': ENTRY, 'usage': 'historical-context-exclusion', 'rowCount': len(rows),
        'bindings': {str((data / n).relative_to(ROOT)): sources.sha(data / n)
                     for n in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md')},
        'keys': {'context': sorted(sources.keys_for(rows, 'context'))},
        'missingAxes': [], 'parentEntries': [sources.ENTRY],
        'notes': 'Complete target-context addendum for the original 9000-row word-ranking corpus; '
                 'parent retains its original article-only scope. No canonical-family or full-source-sentence claim.'}


def verify(data=DATA):
    meta, payloads = read_bundle(data)
    sources.audit()
    ledger = sources.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
    if [e for e in ledger['entries'] if e['id'] == ENTRY] != [context_entry(data, payloads)]:
        raise ValueError('MODEL_FIXTURE_CONTEXT_EXCLUSION')
    return meta, payloads


def _write(root, name, raw):
    path = root / sources.relative(name)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError('MODEL_FIXTURE_PATH_COLLISION')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


@contextmanager
def workspace(profile):
    if profile not in ('baseline', 'refinement', 'word'):
        raise ValueError('MODEL_FIXTURE_PROFILE')
    meta, payloads = verify()
    original_data = core.verify()
    with tempfile.TemporaryDirectory(prefix='rune-historical-') as folder:
        root = Path(folder)
        if profile in ('refinement', 'word'):
            for name, raw in original_data.items():
                _write(root, 'build/' + name, raw)
        for name, record in meta['files'].items():
            if profile not in record['profiles']:
                continue
            raw = payloads[name]
            if record['mode'] == 'template':
                raw = raw.decode().replace('$ROOT', str(root)).replace('$EXTERNAL', str(root / '.external')).encode()
            _write(root, name, raw)
        if profile in ('baseline', 'refinement'):
            graph = json.loads((sources.DATA / 'manifest.json').read_text())
            export = 'morphology-public-export-v3' if profile == 'baseline' else 'typing-refinement/candidates-v2'
            records = {(r['path'], r['sha256']): r for r in graph['sources']}
            for name, expected in graph['exports'][export]['sources'].items():
                record = records[name, expected]
                if record['origin'] == 'repository':
                    raw = (ROOT / name).read_bytes()
                elif record['origin'] == 'archived-git':
                    raw = (sources.DATA / record['file']).read_bytes()
                else:
                    raw = b''.join(original_data['typing-refinement/data/' + p + '-rows.jsonl'] for p in ('train', 'dev', 'test'))
                if digest(raw) != expected:
                    raise ValueError('MODEL_FIXTURE_SOURCE_IDENTITY')
                _write(root, name, raw)
            receipt_path = root / 'build' / export / 'receipt.json'
            receipt = json.loads(receipt_path.read_text())
            for name in receipt['files']:
                path = Path(name)
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError('MODEL_FIXTURE_RECEIPT_PATH')
                receipt['files'][name] = sources.sha(path)
            receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        for name, record in meta['repositoryFiles'].items():
            sources.relative(name)
            if profile in record['profiles']:
                raw = (ROOT / name).read_bytes()
                if digest(raw) != record['sha256']:
                    raise ValueError('MODEL_FIXTURE_REPOSITORY_IDENTITY')
                _write(root, name, raw)
        if profile == 'refinement':
            path = root / 'build/typing-refinement/verified-observations/manifest.json'
            binding = json.loads(path.read_text())
            binding['exportReceiptSha256'] = sources.sha(root / 'build/typing-refinement/candidates-v2/receipt.json')
            path.write_text(json.dumps(binding, sort_keys=True, indent=2) + '\n')
        yield root


def register(output):
    _, payloads = read_bundle()
    ledger = copy.deepcopy(sources.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json'))
    if any(e['id'] == ENTRY for e in ledger['entries']):
        raise ValueError('MODEL_FIXTURE_ALREADY_REGISTERED')
    ledger['entries'].append(context_entry(payloads=payloads))
    ledger['coverage']['pending'] = [text.replace(
        'Original word-ranking text exposure now has permanent article exclusions; canonical families, target contexts and full source sentences remain pending.',
        'Original word-ranking text exposure now has permanent article/target-context exclusions; canonical families and full source sentences remain pending.')
        for text in ledger['coverage']['pending']]
    sources.validate_ledger(ledger)
    with Path(output).open('x') as stream:
        stream.write(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register-ledger-output', type=Path)
    args = parser.parse_args()
    if args.register_ledger_output:
        register(args.register_ledger_output)
    else:
        meta, payloads = verify()
        print(json.dumps({'files': len(payloads), 'archiveSha256': ARCHIVE_SHA256, 'modelBytesUnchanged': True}))
