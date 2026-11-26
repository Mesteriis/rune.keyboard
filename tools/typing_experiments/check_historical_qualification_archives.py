#!/usr/bin/env python3
"""Verify and optionally restore disclosed v3/v4 corpora; never qualify them."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import shutil

ROOT = Path(__file__).resolve().parent / 'historical-qualification-v3-v4'
BUILD = Path(__file__).resolve().parents[2] / 'build'
PURPOSE = 'DISCLOSED_HISTORICAL_CORPORA_NOT_QUALIFICATION'
MANIFESTS = {
    'v3': '56a5b994bc2048c4cf434a123ebbe2e2f7a746102b936a83d535fc582ceecee3',
    'v4': 'a1579d3596ba733dbf5fff49adb6c9dad5d7a54902fe5d98776329578328c9cc',
}
NAMES = frozenset({'manifest.json', 'protected-tokens.jsonl', 'punctuation-en.jsonl',
    'punctuation-es.jsonl', 'punctuation-ru.jsonl', 'spelling-en.jsonl',
    'spelling-es.jsonl', 'spelling-ru.jsonl'})


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_archive(path, archive_sha, manifest_sha, version):
    raw = Path(path).read_bytes()
    if digest(raw) != archive_sha:
        raise ValueError('HISTORICAL_ARCHIVE_IDENTITY')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:bz2') as archive:
        members = archive.getmembers()
        if (len(members) != len(NAMES) or {m.name for m in members} != NAMES or
                any(not m.isfile() or m.size > 4_000_000 for m in members)):
            raise ValueError('HISTORICAL_ARCHIVE_MEMBERS')
        data = {m.name: archive.extractfile(m).read() for m in members}
    if digest(data['manifest.json']) != manifest_sha:
        raise ValueError('HISTORICAL_MANIFEST_IDENTITY')
    manifest = json.loads(data['manifest.json'])
    if (manifest.get('corpusVersion') != version or manifest.get('containsPersonalMessages') is not False or
            not isinstance(manifest.get('files'), dict) or set(manifest['files']) != NAMES - {'manifest.json'}):
        raise ValueError('HISTORICAL_MANIFEST_SCOPE')
    for name, info in manifest['files'].items():
        expected = info if isinstance(info, str) else info.get('sha256') if isinstance(info, dict) else None
        if digest(data[name]) != expected:
            raise ValueError('HISTORICAL_ROW_IDENTITY')
    return data


def check_archive(path, archive_sha, manifest_sha, version):
    return len(read_archive(path, archive_sha, manifest_sha, version))


def load(root=ROOT):
    root = Path(root)
    catalog = json.loads((root / 'catalog.json').read_bytes())
    if catalog.get('schema') != 1 or catalog.get('purpose') != PURPOSE or set(catalog.get('archives', {})) != set(MANIFESTS):
        raise ValueError('HISTORICAL_CATALOG_SCOPE')
    result = {}
    for label, manifest_sha in MANIFESTS.items():
        entry = catalog['archives'][label]
        if (entry.get('archive') != f'qualification-{label}.tar.bz2' or
                entry.get('manifestSha256') != manifest_sha or entry.get('fileCount') != len(NAMES) or
                entry.get('originalPath') != f'tools/eval/smart-typing-0.3/qualification-{label}/corpus'):
            raise ValueError('HISTORICAL_CATALOG_IDENTITY')
        result[label] = read_archive(root / entry['archive'], entry['archiveSha256'], manifest_sha, int(label[1:]))
    return result


def check(root=ROOT):
    return {'files': {label: len(data) for label, data in load(root).items()}, 'independentQualification': False}


def restore(output, root=ROOT, build=BUILD):
    build = Path(build).resolve(strict=True)
    requested = Path(output)
    if requested.is_symlink():
        raise ValueError('HISTORICAL_RESTORE_OUTPUT')
    output = requested.resolve()
    if output == build or not output.is_relative_to(build) or output.exists() or not output.parent.is_dir():
        raise ValueError('HISTORICAL_RESTORE_OUTPUT')
    data = load(root)
    output.mkdir(mode=0o700)
    try:
        for label, files in data.items():
            target = output / label
            target.mkdir(mode=0o700)
            for name, content in files.items():
                with (target / name).open('xb') as stream:
                    stream.write(content)
    except BaseException:
        shutil.rmtree(output)
        raise
    return {'files': {label: len(files) for label, files in data.items()},
            'independentQualification': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore-output', type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.restore_output) if args.restore_output else check(), sort_keys=True))
