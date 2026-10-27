"""Verify declared late-training source bytes without importing or running them.

This is a direct source-reference inventory, not transitive dependency closure,
model execution, feature parity or qualification evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ARCHIVE = Path(__file__).with_name('late_training_sources')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or PurePosixPath(value).is_absolute()
            or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('LATE_SOURCE_PATH')
    return value


def references(metadata, root):
    result = {}
    for raw, expected in metadata.get('sourceHashes', {}).items():
        path = Path(raw)
        if path.is_absolute():
            try:
                raw = str(path.resolve().relative_to(Path(root).resolve()))
            except ValueError:
                raise ValueError('LATE_SOURCE_PATH') from None
        name = relative(raw)
        if name in result:
            raise ValueError('LATE_SOURCE_DUPLICATE')
        result[name] = expected
    if not result:
        raise ValueError('LATE_SOURCE_EMPTY')
    return result


def audit(archive=ARCHIVE, historical_root=None):
    archive = Path(archive)
    manifest = json.loads((archive / 'manifest.json').read_text())
    if (manifest.get('schema') != 1 or manifest.get('purpose') != 'DECLARED_LATE_TRAINING_SOURCE_BYTES_ONLY'
            or not manifest.get('receipts') or not manifest.get('sources')):
        raise ValueError('LATE_SOURCE_SCHEMA')
    used = set()
    for name, source in manifest['sources'].items():
        relative(name)
        filename = relative(source['file'])
        if '/' in filename:
            raise ValueError('LATE_SOURCE_ARCHIVE_PATH')
        path = archive / filename
        if path.is_symlink() or digest(path) != source['sha256']:
            raise ValueError('LATE_SOURCE_ARCHIVE_IDENTITY')
    for name, receipt in manifest['receipts'].items():
        relative(name)
        if not receipt['sources']:
            raise ValueError('LATE_SOURCE_EMPTY')
        for source, expected in receipt['sources'].items():
            if manifest['sources'].get(source, {}).get('sha256') != expected:
                raise ValueError('LATE_SOURCE_REFERENCE')
            used.add(source)
        if historical_root is not None:
            path = Path(historical_root) / name
            if digest(path) != receipt['sha256']:
                raise ValueError('LATE_SOURCE_RECEIPT_IDENTITY')
            if references(json.loads(path.read_text()), historical_root) != receipt['sources']:
                raise ValueError('LATE_SOURCE_RECEIPT_REFERENCES')
    if used != set(manifest['sources']):
        raise ValueError('LATE_SOURCE_UNUSED')
    return dict(purpose=manifest['purpose'], receipts=len(manifest['receipts']),
                sourcePaths=len(used), distinctSourceHashes=len({s['sha256'] for s in manifest['sources'].values()}),
                archivedBytes=sum((archive / f).stat().st_size for f in {s['file'] for s in manifest['sources'].values()}),
                historicalReceiptsVerified=historical_root is not None,
                scriptsExecuted=False, modelCalls=0, modelExecutionEstablished=False,
                transitiveDependencyCoverageEstablished=False,
                manifestSha256=digest(archive / 'manifest.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(historical_root=args.historical_root), sort_keys=True))


if __name__ == '__main__':
    main()
