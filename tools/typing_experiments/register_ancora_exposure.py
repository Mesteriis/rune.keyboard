"""Rebuild and check exclusions for the disclosed Catalan and Spanish AnCora test files."""
import argparse
import hashlib
import json
from pathlib import Path

import control_ledger as control
import holdout_ledger as lexical
from public_corpus_preparation_v1 import ancora_document_key

HERE = Path(__file__).resolve().parent
SOURCES = {
    'ca': ('Catalan', 'f232d0a2a8911456ea0c08c6f6f72a00a2ec619a',
           '5f8d0ad5053cc855c658710cefc003d583f63e40f9c712a48c90f8be1d57dc2c', 187, 1846),
    'es': ('Spanish', '3ea1f747220979d91787a6d04b85734a42bf22a4',
           '4d74d95cfe5a53eacaa7adf3b7ae6ef76a7df9806fd519113e25d74c43ad2b9c', 168, 1721),
}
PROJECTION_SHA256 = {
    'ca': '10fdab8240cc0d96604dadbd105cf97068c131b6d957775888741225a9523fba',
    'es': 'd046f3e30267a2bb6cab7e48882455a0e4a8eace256198f5deae9b59f8f7f52d',
}


def source_location(language):
    name, revision, *_ = SOURCES[language]
    filename = f'{language}_ancora-ud-test.conllu'
    return filename, f'https://raw.githubusercontent.com/UniversalDependencies/UD_{name}-AnCora/{revision}/{filename}'


def entries(language, raw):
    name, revision, digest, document_count, sentence_count = SOURCES[language]
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('ANCORA_EXPOSURE_SOURCE_HASH')
    repository = f'ud-{name.lower()}-ancora'
    documents, sentences, identifiers = set(), set(), set()
    document = None
    for block in raw.decode('utf-8').strip().split('\n\n'):
        comments = [line.split(' = ', 1) for line in block.splitlines() if line.startswith('# ') and ' = ' in line]
        metadata = dict(comments)
        if '# newdoc id' in metadata:
            document = ancora_document_key(dict(sourceRepository=repository, sourceLanguage=language,
                article='ancora:' + metadata['# newdoc id'], sourceRevision=revision))
            if document in documents:
                raise ValueError('ANCORA_EXPOSURE_DUPLICATE_DOCUMENT')
            documents.add(document)
        identifier, text = metadata.get('# sent_id'), metadata.get('# text')
        if not document or not identifier or not text or identifier in identifiers:
            raise ValueError('ANCORA_EXPOSURE_SENTENCE')
        identifiers.add(identifier)
        digest_key = lexical.source_segment_hash(text)
        sentences.update(lexical.keys_for([{'contextHash': digest_key, 'sourceSegmentHash': digest_key}], 'sentence'))
    if (len(documents), len(identifiers)) != (document_count, sentence_count):
        raise ValueError('ANCORA_EXPOSURE_SOURCE_COUNTS')
    _, url = source_location(language)
    common = dict(id=f'public-ud-ancora-test-exposure-v1-{language}', bindings={url: digest},
        rowCount=sentence_count, sourceRepository=repository, sourceLanguage=language)
    return (dict(common, language='en', kind='source', keys=[], articleKeys=sorted(documents)),
            dict(common, usage='historical-source-exclusion', missingAxes=[],
                 keys={'article': sorted(documents), 'sentence': sorted(sentences)}))


def check(directory=None):
    registries = (control.load(HERE/'control-ledger.json'), lexical.load_ledger(HERE/'holdout-ledger.json'))
    for language in SOURCES:
        identity = f'public-ud-ancora-test-exposure-v1-{language}'
        actual = tuple(next((row for row in registry['entries'] if row['id'] == identity), None)
                       for registry in registries)
        serialized = json.dumps(actual, sort_keys=True, separators=(',', ':')).encode()
        if hashlib.sha256(serialized).hexdigest() != PROJECTION_SHA256[language]:
            raise ValueError('ANCORA_EXPOSURE_REGISTRY_DRIFT')
        if directory is not None:
            filename, _ = source_location(language)
            if actual != entries(language, (directory/filename).read_bytes()):
                raise ValueError('ANCORA_EXPOSURE_SOURCE_PROJECTION_DRIFT')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path, help='Also rebuild from a directory with both pinned files.')
    parser.add_argument('--output', type=Path, help='Write proposed entries to a fresh file instead of checking the registries.')
    args = parser.parse_args()
    if args.output is None:
        check(args.source_directory)
        print('Pinned AnCora exclusions match both registries')
        return
    if args.source_directory is None:
        parser.error('--source-directory is required with --output')
    projection = [entries(language, (args.source_directory/source_location(language)[0]).read_bytes())
                  for language in SOURCES]
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(projection, stream, indent=2, sort_keys=True)
        stream.write('\n')


if __name__ == '__main__':
    main()
