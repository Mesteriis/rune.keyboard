"""Audit frozen project source identities for original historical model exports.

No archived script is imported or executed. External runtime identities and
candidate-generation reproduction are deliberately separate evidence.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).with_name('historical-model-sources-v1')
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
from holdout_ledger import keys_for, load_ledger, validate_ledger
import historical_data_fixtures as fixtures

ENTRY = 'public-word-ranking-data-articles-v1'
WORD_SHA = '8a5a11a16543315ff3114bf0034f54b455b5e432828098cf2030f85737c34466'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(name):
    if (not isinstance(name, str) or not name or '\\' in name or
            PurePosixPath(name).is_absolute() or any(x in ('', '.', '..') for x in name.split('/'))):
        raise ValueError('HISTORICAL_SOURCE_PATH')
    return name


def word_entry(root=ROOT, data=DATA):
    path = data / 'word-data-manifest.json'
    if sha(path) != WORD_SHA:
        raise ValueError('HISTORICAL_WORD_MANIFEST')
    manifest = json.loads(path.read_text())
    producer = root / 'tools/typing_experiments/prepare_word_ranking.py'
    lock = root / 'tools/model/rune-text-0.2/source-lock.json'
    source = json.loads(lock.read_text())
    if (manifest['containsPersonalMessages'] is not False or sha(producer) != manifest['preparationScriptSha256'] or
            manifest['sourceSha256'] != source['wikipediaContext']['files']['ru-0007.parquet']['sha256']):
        raise ValueError('HISTORICAL_WORD_SOURCE')
    articles = {article for part in manifest['partitions'].values() for article in part['articles']}
    return {'id': ENTRY, 'usage': 'historical-exclusion',
        'rowCount': sum(part['rows'] for part in manifest['partitions'].values()),
        'sourceArticleCount': len(articles),
        'bindings': {str(p.relative_to(root)): sha(p) for p in (path, producer, lock)},
        'keys': {'article': sorted(keys_for([{'article': a} for a in articles], 'article'))},
        'missingAxes': ['family', 'sentence', 'context'],
        'notes': 'Original public word-ranking train/dev/test text exposure; original manifest and all '
                 'advertised files reproduced byte-identically. Article exclusions only; '
                 'canonical families, target contexts and full source sentences remain pending.'}


def audit(root=ROOT, data=DATA, historical_build=None, verify_git=False):
    root, data = Path(root), Path(data)
    manifest = json.loads((data / 'manifest.json').read_text())
    if manifest.get('schemaVersion') != 1 or manifest.get('purpose') != 'HISTORICAL_MODEL_PROJECT_SOURCE_IDENTITIES':
        raise ValueError('HISTORICAL_SOURCE_SCHEMA')
    records = {}
    git_verified = 0
    payloads = None
    for record in manifest['sources']:
        name, digest = relative(record['path']), record['sha256']
        key = (name, digest)
        if key in records:
            raise ValueError('HISTORICAL_SOURCE_DUPLICATE')
        records[key] = record
        origin = record['origin']
        if origin == 'repository':
            path = root / name
        elif origin == 'archived-git':
            if re.fullmatch(r'[0-9a-f]{40}', record.get('gitObject', '')) is None:
                raise ValueError('HISTORICAL_GIT_OBJECT')
            filename = relative(record['file'])
            if filename != 'sources/' + digest + Path(name).suffix:
                raise ValueError('HISTORICAL_SOURCE_ARCHIVE_PATH')
            path = data / filename
        elif origin == 'derived-public-rows':
            if name != 'build/typing-refinement/data/all-rows.jsonl':
                raise ValueError('HISTORICAL_DERIVED_SOURCE')
            if payloads is None:
                payloads = fixtures.verify()
            raw = b''.join(payloads['typing-refinement/data/' + part + '-rows.jsonl']
                           for part in ('train', 'dev', 'test'))
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('HISTORICAL_SOURCE_IDENTITY')
            continue
        else:
            raise ValueError('HISTORICAL_SOURCE_ORIGIN')
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise ValueError('HISTORICAL_SOURCE_IDENTITY:' + name)
        if origin == 'archived-git' and verify_git:
            raw = subprocess.check_output(['git', 'cat-file', 'blob', record['gitObject']], cwd=root)
            if raw != path.read_bytes():
                raise ValueError('HISTORICAL_GIT_OBJECT_IDENTITY')
            git_verified += 1
    used = set()
    file_count = 0
    for name, export in manifest['exports'].items():
        relative(name)
        if not export['sources'] or not export['externalSources']:
            raise ValueError('HISTORICAL_EXPORT_SCOPE')
        for path, digest in export['sources'].items():
            if (relative(path), digest) not in records:
                raise ValueError('HISTORICAL_EXPORT_REFERENCE')
            used.add((path, digest))
        if historical_build is not None:
            base = Path(historical_build)
            receipt_path = base / name / 'receipt.json'
            if sha(receipt_path) != export['receiptSha256']:
                raise ValueError('HISTORICAL_EXPORT_RECEIPT')
            original = json.loads(receipt_path.read_text())
            suffix = '/build/' + name + '/'
            roots = {path.split(suffix)[0] for path in original['files'] if suffix in path}
            if len(roots) != 1:
                raise ValueError('HISTORICAL_EXPORT_ROOT')
            old_root = next(iter(roots))
            sources = {p[len(old_root)+1:]: h for p, h in original['sources'].items() if p.startswith(old_root + '/')}
            external = {Path(p).name: h for p, h in original['sources'].items() if not p.startswith(old_root + '/')}
            if sources != export['sources'] or external != export['externalSources']:
                raise ValueError('HISTORICAL_EXPORT_SOURCE_GRAPH')
            for original_path, digest in original['files'].items():
                if not original_path.startswith(old_root + '/build/'):
                    raise ValueError('HISTORICAL_EXPORT_FILE_PATH')
                path = base / relative(original_path[len(old_root + '/build/'):])
                if sha(path) != digest:
                    raise ValueError('HISTORICAL_EXPORT_FILE_IDENTITY')
                file_count += 1
    if used != set(records):
        raise ValueError('HISTORICAL_UNUSED_SOURCE')
    ledger = validate_ledger(load_ledger(root / 'tools/typing_experiments/holdout-ledger.json'))
    if [e for e in ledger['entries'] if e['id'] == ENTRY] != [word_entry(root, data)]:
        raise ValueError('HISTORICAL_WORD_EXCLUSION')
    return {'sourceVersions': len(records), 'exports': len(manifest['exports']),
        'gitObjectsVerified': git_verified,
        'archivedGitSources': sum(r['origin'] == 'archived-git' for r in records.values()),
        'originalExportFilesVerified': file_count, 'originalReceiptsVerified': historical_build is not None,
        'externalRuntimeIdentityEstablished': False, 'candidateGenerationReproduced': False,
        'modelCalls': 0}


def register(output):
    ledger = copy.deepcopy(load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json'))
    if any(entry['id'] == ENTRY for entry in ledger['entries']):
        raise ValueError('HISTORICAL_WORD_ALREADY_REGISTERED')
    ledger['entries'].append(word_entry())
    ledger['coverage']['pending'].append(
        'Original word-ranking text exposure now has permanent article exclusions; '
        'canonical families, target contexts and full source sentences remain pending.')
    validate_ledger(ledger)
    with Path(output).open('x') as stream:
        stream.write(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--historical-build', type=Path)
    group.add_argument('--register-ledger-output', type=Path)
    parser.add_argument('--verify-git', action='store_true')
    args = parser.parse_args()
    if args.register_ledger_output:
        register(args.register_ledger_output)
    else:
        print(json.dumps(audit(historical_build=args.historical_build, verify_git=args.verify_git), sort_keys=True))
