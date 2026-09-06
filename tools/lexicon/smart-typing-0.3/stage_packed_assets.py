"""Offline, immutable staging of the reviewed APK lexicon allowlist. No generation or network."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

MANIFEST_SHA = '7ce207ab7d05b8800a1d8921f6e55fe81f429f8158bf8ebcebf581cbee7255f0'
SOURCE_SHA = 'ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48'
LOCK_SHA = '28750e183ef99ea33da58b20036e2f0dcb3f7e1f76e8528c21074ac7d6615b70'
PREFIX = 'app/src/main/assets/'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def output_root(value, project):
    path = value.absolute()
    build = project.resolve() / 'build'
    require('..' not in path.parts and path.is_relative_to(build) and path != build, 'OUTPUT_SCOPE')
    for ancestor in [path, *path.parents]:
        require(not ancestor.is_symlink(), 'OUTPUT_SYMLINK')
        if ancestor == build:
            break
    return path


def stage(entries, output):
    """Validate the whole allowlist before any copy, then reject drift instead of overwriting it."""
    paths = [entry['path'] for entry in entries]
    require(len(paths) == len(set(paths)), 'DUPLICATE_PATH')
    for entry in entries:
        relative = Path(entry['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative).startswith(PREFIX), 'ASSET_PATH')
        source = entry['source']
        require(source.is_file() and source.stat().st_size == entry['bytes'] and digest(source) == entry['sha256'], 'INPUT_HASH')
        destination = output / relative
        for ancestor in [destination, *destination.parents]:
            require(not ancestor.is_symlink(), 'OUTPUT_SYMLINK')
            if ancestor == output:
                break
        if destination.exists():
            require(destination.is_file() and destination.stat().st_size == entry['bytes'] and digest(destination) == entry['sha256'], 'OUTPUT_DRIFT')
    assets = output / PREFIX
    if assets.exists():
        actual = {str(file.relative_to(output)) for file in assets.rglob('*') if file.is_file() or file.is_symlink()}
        require(actual <= set(paths), 'UNLISTED_ASSET')
    inventory = [{key: value for key, value in entry.items() if key != 'source'} for entry in entries]
    data = (json.dumps(inventory, indent=2) + '\n').encode()
    record = output / 'asset-inventory.json'
    require(not record.is_symlink(), 'OUTPUT_SYMLINK')
    if record.exists():
        require(record.read_bytes() == data, 'INVENTORY_DRIFT')
    for entry in entries:
        destination = output / entry['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            # Exclusive creation; never overwrite an existing staged file.
            with entry['source'].open('rb') as source, destination.open('xb') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
        require(digest(destination) == entry['sha256'], 'STAGED_HASH')
    if not record.exists():
        with record.open('xb') as target:
            target.write(data)
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-package', 'index-root', 'rank-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output = output_root(args.output, Path.cwd())
    package = Path(__file__).resolve().parent
    manifest = package / 'packed-asset-manifest.json'
    frozen = args.source_package / 'frozen-output-manifest.json'
    lock = args.source_package / 'source-lock.json'
    require(digest(manifest) == MANIFEST_SHA and digest(frozen) == SOURCE_SHA and digest(lock) == LOCK_SHA, 'TRUST_HASH')
    records = json.loads(manifest.read_text())
    require([r['language'] for r in records] == ['ENGLISH', 'SPANISH', 'RUSSIAN'], 'LANGUAGES')
    entries = []
    for lang, record in zip(('en', 'es', 'ru'), records):
        for part, filename, component in (('trie', lang + '.trie', 'orthographic'),
                                          ('lengths', lang + '.trie.lengths', 'orthographic'),
                                          ('ranks', lang + '.ranks', 'frequency-CC-BY-SA-4.0')):
            source = (args.rank_root / 'rank-assets' if part == 'ranks' else args.index_root / 'assets') / filename
            asset = record[part]
            entries.append(dict(asset, path=PREFIX + asset['path'], source=source, component=component, compression='STORE'))
        require(record['notices'] == records[0]['notices'], 'NOTICE_SET')
    require(len(records[0]['notices']) == 14, 'NOTICE_COUNT')
    for asset in records[0]['notices']:
        source = args.source_package / 'notices' / Path(asset['path']).name
        entries.append(dict(asset, path=PREFIX + asset['path'], source=source, component='original-notice', compression='DEFAULT'))
    for source, name in ((manifest, 'packed-asset-manifest.json'), (frozen, 'frozen-output-manifest.json'),
                         (lock, 'source-lock.json'), (package / 'PACKAGED_LEXICONS.md', 'PACKAGED_LEXICONS.md'),
                         (package / 'packed-source-provenance.json', 'packed-source-provenance.json')):
        entries.append({'path': PREFIX + 'smarttyping/lexicon/provenance/' + name, 'source': source,
                        'bytes': source.stat().st_size, 'sha256': digest(source), 'component': 'provenance', 'compression': 'DEFAULT'})
    inventory = stage(sorted(entries, key=lambda item: item['path']), output)
    print('PASS staged_assets', len(inventory), 'binary_components', 9, 'original_notices', 14,
          'total_bytes', sum(item['bytes'] for item in inventory))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('FAIL', type(error).__name__)
        raise SystemExit(2)
