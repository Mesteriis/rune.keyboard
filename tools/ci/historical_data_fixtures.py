"""Verify and install original public data fixtures; never train or score a model."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).with_name('historical-data-v1')
PINS = {
    'typing-refinement/data': '20b32e840b890aab726fabea30c6409fce058d0c9ba3dd64d603aaaa24475ce7',
    'typing-extra-epochs/data': '1d2a8f51d0fe2462b8610cb813d2b4330a41e3e6360a6f993acb00fee6de6361',
}
MAX_BYTES = 16 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_payloads(payloads):
    expected = set()
    lock = json.loads((ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())
    for directory, pinned in PINS.items():
        name = directory + '/manifest.json'
        if name not in payloads or sha(payloads[name]) != pinned:
            raise ValueError('HISTORICAL_MANIFEST_IDENTITY')
        metadata = json.loads(payloads[name])
        if (metadata['containsPersonalMessages'] is not False or
                metadata['sourceSha256'] != lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
                metadata['frequencySha256'] != lock['frequencyWords']['files']['ru_50k.txt']):
            raise ValueError('HISTORICAL_PUBLIC_SOURCE')
        expected.add(name)
        for filename, digest in metadata['files'].items():
            if PurePosixPath(filename).name != filename or filename in ('', '.', '..'):
                raise ValueError('HISTORICAL_MEMBER_PATH')
            name = directory + '/' + filename
            expected.add(name)
            if name not in payloads or sha(payloads[name]) != digest:
                raise ValueError('HISTORICAL_DATA_IDENTITY')
    if set(payloads) != expected:
        raise ValueError('HISTORICAL_MEMBER_SET')
    return expected


def read_bundle(data=DATA):
    data = Path(data)
    meta = json.loads((data / 'manifest.json').read_text())
    lock_path = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
    if meta.get('sourceLockSha256') != sha(lock_path.read_bytes()):
        raise ValueError('HISTORICAL_SOURCE_LOCK')
    archive = (data / 'files.tar.gz').read_bytes()
    if (meta.get('schemaVersion') != 1 or meta.get('purpose') != 'ORIGINAL_PUBLIC_DATA_REGRESSION_ONLY' or
            meta.get('archiveSha256') != sha(archive) or
            meta.get('articleAttributionSha256') != sha((data / 'articles.jsonl').read_bytes()) or
            meta.get('noticeSha256') != sha((data / 'NOTICE.md').read_bytes())):
        raise ValueError('HISTORICAL_ARCHIVE_IDENTITY')
    payloads = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as bundle:
        for member in bundle:
            if (not member.isfile() or member.name in payloads or member.name not in meta['files'] or
                    member.size != meta['files'][member.name]['bytes'] or member.size < 0):
                raise ValueError('HISTORICAL_ARCHIVE_MEMBER')
            total += member.size
            if total > MAX_BYTES:
                raise ValueError('HISTORICAL_ARCHIVE_LIMIT')
            stream = bundle.extractfile(member)
            raw = stream.read(member.size + 1)
            if len(raw) != member.size or sha(raw) != meta['files'][member.name]['sha256']:
                raise ValueError('HISTORICAL_ARCHIVE_PAYLOAD')
            payloads[member.name] = raw
    check_payloads(payloads)
    expected_generators = {}
    for directory in PINS:
        original = json.loads(payloads[directory + '/manifest.json'])
        name = 'prepare_refinement.py' if directory.startswith('typing-refinement') else 'prepare_epoch_test.py'
        name = 'tools/typing_experiments/' + name
        expected_generators[name] = original['preparationScriptSha256']
        if sha((ROOT / name).read_bytes()) != original['preparationScriptSha256']:
            raise ValueError('HISTORICAL_GENERATOR_IDENTITY')
    if meta.get('generators') != expected_generators:
        raise ValueError('HISTORICAL_GENERATOR_BINDING')
    if set(payloads) != set(meta['files']):
        raise ValueError('HISTORICAL_ARCHIVE_INCOMPLETE')
    ids = set()
    for directory in PINS:
        original = json.loads(payloads[directory + '/manifest.json'])
        ids.update(article for part in original['partitions'].values() for article in part['articles'])
    attributed = [json.loads(line) for line in (data / 'articles.jsonl').read_text().splitlines()]
    if (len(attributed) != len(ids) or {row['articleId'] for row in attributed} != ids or
            any(not row.get('title') or row.get('historyUrl') !=
                'https://ru.wikipedia.org/w/index.php?curid=' + row['articleId'] + '&action=history'
                for row in attributed)):
        raise ValueError('HISTORICAL_ATTRIBUTION_OR_EXCLUSION')
    return payloads


sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
from holdout_ledger import keys_for, load_ledger, validate_ledger

ENTRY = 'public-extra-epochs-data-history-v1'
LEDGER = ROOT / 'tools/typing_experiments/holdout-ledger.json'


def epoch_entry(payloads, data=DATA):
    directory = 'typing-extra-epochs/data/'
    original = json.loads(payloads[directory + 'manifest.json'])
    articles = {a for part in original['partitions'].values() for a in part['articles']}
    rows = [json.loads(line) for line in payloads[directory + 'test-rows.jsonl'].splitlines()]
    return {'id': ENTRY, 'usage': 'historical-exclusion', 'rowCount': len(rows),
        'sourceArticleCount': len(articles),
        'bindings': {str((Path(data) / name).relative_to(ROOT)): sha((Path(data) / name).read_bytes())
                     for name in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md')},
        'keys': {'article': sorted(keys_for([{'article': a} for a in articles], 'article')),
                 'context': sorted(keys_for(rows, 'context'))},
        'missingAxes': ['family', 'sentence'],
        'notes': 'Original additional-epoch public test exposure, now regression data. '
                 'Manifest 1d2a8f51d0fe2462b8610cb813d2b4330a41e3e6360a6f993acb00fee6de6361 '
                 'and all advertised data reproduced byte-identically. No canonical family/full-sentence claim.'}


def verify(data=DATA):
    payloads = read_bundle(data)
    ledger = validate_ledger(load_ledger(LEDGER))
    expected = epoch_entry(payloads, data)
    if [entry for entry in ledger['entries'] if entry['id'] == ENTRY] != [expected]:
        raise ValueError('HISTORICAL_LEDGER_BINDING')
    excluded = {key for entry in ledger['entries'] for key in entry['keys'].get('article', [])}
    for directory in PINS:
        metadata = json.loads(payloads[directory + '/manifest.json'])
        articles = {a for part in metadata['partitions'].values() for a in part['articles']}
        if not keys_for([{'article': a} for a in articles], 'article') <= excluded:
            raise ValueError('HISTORICAL_ARTICLE_EXCLUSION')
    return payloads


def register(output):
    payloads = read_bundle()
    ledger = copy.deepcopy(validate_ledger(load_ledger(LEDGER)))
    if any(entry['id'] == ENTRY for entry in ledger['entries']):
        raise ValueError('HISTORICAL_ALREADY_REGISTERED')
    ledger['entries'].append(epoch_entry(payloads))
    ledger['coverage']['pending'].append(
        'Original additional-epoch exposure has article/context exclusions; canonical families and full source sentences remain unproven.')
    validate_ledger(ledger)
    with Path(output).open('x') as stream:
        stream.write(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def install(build, data=DATA):
    payloads = verify(data)
    build = Path(build).resolve()
    build.mkdir(parents=True, exist_ok=True)
    targets = [build / name for name in PINS]
    for target in targets:
        if target.exists() or target.is_symlink() or target.parent.is_symlink():
            raise ValueError('FRESH_HISTORICAL_DATA_REQUIRED')
    installed = []
    with tempfile.TemporaryDirectory(prefix='.historical-data-', dir=build) as staging:
        staging = Path(staging)
        for name, raw in payloads.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        try:
            for directory, target in zip(PINS, targets):
                target.parent.mkdir(parents=True, exist_ok=True)
                # Recheck after staging, before publishing any directory.
                if target.exists() or target.is_symlink() or target.parent.is_symlink():
                    raise ValueError('FRESH_HISTORICAL_DATA_REQUIRED')
                (staging / directory).rename(target)
                installed.append(target)
        except Exception:
            for target in installed:
                shutil.rmtree(target)
            raise
    return {'files': len(payloads), 'bytes': sum(map(len, payloads.values())), 'modelCalls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--install-build', type=Path)
    group.add_argument('--register-ledger-output', type=Path)
    args = parser.parse_args()
    if args.register_ledger_output:
        register(args.register_ledger_output)
        return
    result = install(args.install_build) if args.install_build else {'files': len(verify()), 'modelCalls': 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
