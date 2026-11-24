#!/usr/bin/env python3
"""Rebuild the original v3/v4 test archives from public source shards."""
import argparse
import base64
import bz2
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

import check_historical_qualification_archives as historical
from recover_early_ru_sources import archived_source

REPO = historical.ROOT.parents[2]
INDEX_SHA256 = '3887d90ca7a19f714eb3b6205bbcdafdcd3b9cca356e4ceb1ca89651cf4fff76'
KINDS = {'spelling': 3400, 'punctuation': 400}


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_generator(manifest):
    def source(suffix):
        name, digest = next((name, digest) for name, digest in manifest['sources'].items()
                            if name.endswith('/' + suffix))
        return archived_source(REPO, name, digest)

    spec = importlib.util.spec_from_file_location('frozen_qualification', source('generate_corpus.py'))
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    return generator, json.loads(source('source-lock.json').read_bytes())


def article_sets(version, language, bindings):
    name = f'{version}-{language}.json'
    punctuation_name = f'punctuation-ru-attribution/{name}'
    spelling_name = f'article-maps/{name}'
    expected = {punctuation_name} if language == 'ru' else {punctuation_name, spelling_name}
    if set(bindings) != expected:
        raise ValueError('QUALIFICATION_REPLAY_SOURCE_MAP_SET')
    data = {}
    for path, digest in bindings.items():
        raw = (historical.ROOT / path).read_bytes()
        if historical.digest(raw) != digest:
            raise ValueError('QUALIFICATION_REPLAY_SOURCE_MAP')
        data[path] = json.loads(raw)
    punctuation = data[punctuation_name]
    spelling = (punctuation['ruSpelling'] if language == 'ru'
                else data[spelling_name]['matchingArticlesByRow'])
    return {kind: {str(article) for ids in rows.values() for article in ids}
            for kind, rows in (('punctuation', punctuation['punctuation']), ('spelling', spelling))}


def fingerprint_set(encoded, count):
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != count * 32:
        raise ValueError('QUALIFICATION_REPLAY_FINGERPRINT_COUNT')
    digests = {raw[i:i + 32] for i in range(0, len(raw), 32)}
    if len(digests) != count:
        raise ValueError('QUALIFICATION_REPLAY_DUPLICATE_FINGERPRINT')
    return digests


def download(lock, pin, path):
    url = (f"https://huggingface.co/datasets/{lock['repository']}/resolve/"
           f"{lock['parquetRevision']}/{pin['repositoryPath']}")
    for attempt in range(5):
        result = subprocess.run([
            'curl', '--silent', '--show-error', '--fail', '--location',
            '--proto', '=https', '--proto-redir', '=https', '--http1.1', '--continue-at', '-',
            '--max-time', '160', '--max-filesize', str(pin['bytes']),
            '--output', str(path), url + f'?download=true&runeReplay={time.time_ns()}',
        ], check=False)
        if result.returncode == 0:
            return
        if result.returncode not in (6, 18, 28, 56, 92) or attempt == 4:
            raise ValueError('QUALIFICATION_REPLAY_DOWNLOAD:' + path.name)
        time.sleep(min(2 ** attempt, 8))


def verify_shard(path, pin):
    if path.stat().st_size != pin['bytes'] or file_sha(path) != pin['sha256']:
        raise ValueError('QUALIFICATION_REPLAY_SHARD:' + path.name)


def recover_pools(path, language, generator, lock, known, article_ids, fingerprints):
    import pyarrow.parquet as parquet

    pools = {kind: {} for kind in KINDS}
    needed = set().union(*article_ids.values())
    visited = set()
    selection = lock['articleSelection']
    seed = lock['corpusSeed']
    generators = {
        'spelling': lambda text: generator.spelling_candidates(text, language, known, set(), seed),
        'punctuation': lambda text: generator.punctuation_candidates(text, language, seed),
    }
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
        for number, content in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            article = str(number)
            if article not in needed:
                continue
            value = hashlib.sha256(f"{selection['seed']}:{language}:{article}".encode()).digest()
            if int.from_bytes(value[:8], 'big') % selection['modulus'] != selection['residue']:
                continue
            visited.add(article)
            for kind in KINDS:
                if article not in article_ids[kind]:
                    continue
                for item in generators[kind](content or ''):
                    digest = hashlib.sha256(generator.canonical(item)).digest()
                    if digest in fingerprints[kind]:
                        pools[kind][digest] = item
    if visited != needed or any(set(pools[kind]) != fingerprints[kind] for kind in KINDS):
        raise ValueError('QUALIFICATION_REPLAY_SOURCE_COVERAGE:' + language)
    return {kind: list(items.values()) for kind, items in pools.items()}


def serialize(generator, rows):
    ordered = sorted(rows, key=lambda row: (row['split'] != 'calibration', row['id']))
    return b''.join(generator.canonical(row) + b'\n' for row in ordered)


def reproduce(version, metadata, temporary, inputs):
    manifest = metadata['manifest']
    generator, lock = load_generator(manifest)
    original = generator.canonical(manifest) + b'\n'
    if historical.digest(original) != historical.MANIFESTS[version]:
        raise ValueError('QUALIFICATION_REPLAY_ORIGINAL_MANIFEST')
    files = {'manifest.json': original}
    for language in generator.LANGUAGES:
        selected = metadata['languages'][language]
        article_ids = article_sets(version, language, selected['sourceMaps'])
        fingerprints = {kind: fingerprint_set(selected['fingerprints'][kind], count)
                        for kind, count in KINDS.items()}
        frequency = REPO / f'tools/ci/product-replay-v1/sources/{language}_50k.txt'
        if file_sha(frequency) != lock['frequencyWords'][frequency.name]:
            raise ValueError('QUALIFICATION_REPLAY_VOCABULARY')
        known = generator.vocabulary(frequency, language)
        filename = lock['languageFiles'][language]
        pin = lock['files'][filename]
        if pin['sha256'] != manifest['source']['files'][filename]:
            raise ValueError('QUALIFICATION_REPLAY_SHARD_BINDING')
        with tempfile.TemporaryDirectory(dir=temporary) as working:
            shard = (inputs if inputs is not None else Path(working)) / filename
            if inputs is None:
                download(lock, pin, shard)
            verify_shard(shard, pin)
            pools = recover_pools(shard, language, generator, lock, known, article_ids, fingerprints)
            verify_shard(shard, pin)
        files[f'spelling-{language}.jsonl'] = serialize(
            generator, generator.spelling_rows(pools['spelling'], language, known, lock['corpusSeed']))
        files[f'punctuation-{language}.jsonl'] = serialize(
            generator, generator.punctuation_rows(pools['punctuation'], language))
        print(version, language, 'replayed', flush=True)
    files['protected-tokens.jsonl'] = serialize(
        generator, [row for language in generator.LANGUAGES for row in generator.protected_rows(language)])
    if {name: historical.digest(raw) for name, raw in files.items() if name != 'manifest.json'} != manifest['files']:
        raise ValueError('QUALIFICATION_REPLAY_OUTPUT_IDENTITY:' + version)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for name, raw in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
    return bz2.compress(stream.getvalue())


def ensure(inputs=None):
    root = historical.ROOT
    catalog = json.loads((root / 'catalog.json').read_bytes())['archives']
    paths = {version: root / f'qualification-{version}.tar.bz2' for version in historical.MANIFESTS}
    missing = []
    for version, path in paths.items():
        if path.is_symlink():
            raise ValueError('QUALIFICATION_REPLAY_ARCHIVE_PATH')
        if path.exists():
            historical.check_archive(path, catalog[version]['archiveSha256'],
                                     historical.MANIFESTS[version], int(version[1:]))
        else:
            missing.append(version)
    raw = (root / 'replay-index.json').read_bytes()
    if historical.digest(raw) != INDEX_SHA256:
        raise ValueError('QUALIFICATION_REPLAY_INDEX')
    metadata = json.loads(raw)['versions']
    if missing:
        with tempfile.TemporaryDirectory(prefix='.qualification-replay-', dir=root) as work:
            staging = Path(work)
            for version in missing:
                payload = reproduce(version, metadata[version], staging, inputs)
                path = staging / paths[version].name
                path.write_bytes(payload)
                historical.check_archive(path, catalog[version]['archiveSha256'],
                                         historical.MANIFESTS[version], int(version[1:]))
            for version in missing:
                # A concurrent writer must not have its archive overwritten.
                paths[version].hardlink_to(staging / paths[version].name)
    print(json.dumps(historical.check()), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, help='Read pinned Parquet files from this directory')
    ensure(parser.parse_args().inputs)
