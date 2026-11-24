"""Read the source parquet inside the bound text diagnostic.

This is a diagnostic only: registry coverage, source labels and independence
remain unproved. The caller of assess_files must establish trust in the lock;
the command line uses the tracked lock. Runtime hashes identify inspected
modules and recorded installed package files, but are not a signature or a
complete native dependency attestation.
"""
import argparse
from importlib import metadata
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

import selector_text_preflight_files_v1 as previous

PYARROW_VERSION = '25.0.1'
ROOT = Path(__file__).resolve().parents[2]


def package_identity(distribution):
    """Hash each recorded installed file; this does not authenticate the wheel."""
    entries = distribution.files
    if not entries:
        raise ValueError('TEXT_PREFLIGHT_DECODER_FILES')
    files = {}
    for entry in entries:
        name = str(entry)
        path = PurePosixPath(name)
        if not name or path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('TEXT_PREFLIGHT_DECODER_PATH')
        if name.endswith('.pyc'):
            continue
        if name in files:
            raise ValueError('TEXT_PREFLIGHT_DECODER_FILES')
        installed = Path(distribution.locate_file(entry))
        if not installed.is_file():
            raise ValueError('TEXT_PREFLIGHT_DECODER_FILE_MISSING')
        files[name] = previous.file_sha(installed)
    if not files:
        raise ValueError('TEXT_PREFLIGHT_DECODER_FILES')
    encoded = json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    return {'recordedFileCount': len(files), 'recordedFilesSha256': hashlib.sha256(encoded).hexdigest()}


def decoder_identity():
    import pyarrow
    import pyarrow.lib
    import pyarrow._parquet
    import pyarrow.parquet
    if metadata.version('pyarrow') != PYARROW_VERSION or pyarrow.__version__ != PYARROW_VERSION:
        raise ValueError('TEXT_PREFLIGHT_DECODER_VERSION')
    paths = {'reader': Path(__file__), 'pyarrow': Path(pyarrow.__file__),
             'arrowLib': Path(pyarrow.lib.__file__), 'arrowParquet': Path(pyarrow._parquet.__file__),
             'parquetModule': Path(pyarrow.parquet.__file__)}
    return {'version': PYARROW_VERSION, 'files': {name: previous.file_sha(path) for name, path in paths.items()},
            'package': package_identity(metadata.distribution('pyarrow'))}


def read_source_batches(path):
    import pyarrow.parquet as parquet
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
        ids, texts = batch.column(0).to_pylist(), batch.column(1).to_pylist()
        if len(ids) != len(texts):
            raise ValueError('TEXT_PREFLIGHT_DECODER_COLUMNS')
        for article, text in zip(ids, texts, strict=True):
            if (not isinstance(article, str) or not article.isascii() or not article.isdecimal()
                    or not isinstance(text, str)):
                raise ValueError('TEXT_PREFLIGHT_DECODER_ROW')
        yield ids, texts


def assess_files(data, source, lock_path, lexical_path, controls_path, lexicon):
    identity = decoder_identity()
    report = previous.assess_files(data, source, lock_path, lexical_path, controls_path,
                                   lexicon, read_source_batches)
    if decoder_identity() != identity:
        raise ValueError('TEXT_PREFLIGHT_DECODER_DRIFT')
    report['bindings']['decoder'] = identity
    report['scope'] = 'bound-parquet-diagnostic-not-admission'
    # Hashes bind the imported decoder files, not the whole native supply chain.
    report['sourceDecoderAttested'] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon
    report = assess_files(args.data, args.source, previous.SOURCE_LOCK,
                          previous.LEXICAL, previous.CONTROLS, PymorphyLexicon(cache_size=16384))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
