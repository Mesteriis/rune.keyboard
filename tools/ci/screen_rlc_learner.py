"""Count a pinned learner corpus without exporting text or scoring a model."""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'c84fb2de7db3668c59cd8cda7f79642bc59d9ac3'
PINS = {
    'documents.csv': '64df0d513271aee2485edd180d5b80227f0a075d348ae5db42922ead888bbe85',
    'sentences.csv': '2afd8fd075f8670ee7938e99e2efe033a4e038525c2bb50c1e471e410926be3d',
    'annotations.csv': '298b3f88436eef1653dadc781015535e3ce40b6a2c3b1f2bcddfe1d6f73c42ea',
}
WORD = re.compile(r'(?<!\w)[а-яё]{2,6}(?!\w)')


def analyze(documents, sentences, annotations):
    document_ids = [row['id'] for row in documents]
    sentence_ids = [row['id'] for row in sentences]
    if len(set(document_ids)) != len(document_ids) or len(set(sentence_ids)) != len(sentence_ids):
        raise ValueError('RLC_DUPLICATE_ID')
    document_set = set(document_ids)
    if any(row['document_id'] not in document_set for row in sentences):
        raise ValueError('RLC_UNKNOWN_DOCUMENT')
    sentence_set = set(sentence_ids)
    orphan_annotations = [row for row in annotations if row['sentence_id'] not in sentence_set]
    annotated = {row['sentence_id'] for row in annotations}
    counts = collections.Counter()
    sources = collections.Counter(row['annotation_source'] for row in annotations)
    docs = set()
    words = set()
    for row in sentences:
        counts['sentences'] += 1
        if row['status']:
            continue
        counts['blankStatus'] += 1
        if row['text'] != row['corrected']:
            continue
        counts['unchangedSentence'] += 1
        if row['id'] in annotated:
            counts['unchangedWithAnnotations'] += 1
            continue
        counts['unchangedWithoutAnnotations'] += 1
        docs.add(row['document_id'])
        tokens = WORD.findall(row['text'])
        counts['shortLowercaseTokens'] += len(tokens)
        words.update(tokens)
    return {'counts': dict(counts), 'documents': len(documents),
            'candidateDocuments': len(docs), 'distinctShortLowercaseTokens': len(words),
            'annotations': len(annotations), 'annotationSources': dict(sources),
            'orphanAnnotations': len(orphan_annotations),
            'orphanSentenceReferences': len({row['sentence_id'] for row in orphan_annotations}),
            'orphanAnnotationSources': dict(collections.Counter(row['annotation_source'] for row in orphan_annotations)),
            'qualified': False, 'modelCalls': 0, 'reportContainsRawText': False}


def run(source, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('RLC_OUTPUT')
    raw = {name: (source / name).read_bytes() for name in PINS}
    if any(hashlib.sha256(raw[name]).hexdigest() != digest for name, digest in PINS.items()):
        raise ValueError('RLC_SOURCE_IDENTITY')
    rows = {name: list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline='')))
            for name, data in raw.items()}
    result = analyze(rows['documents.csv'], rows['sentences.csv'], rows['annotations.csv'])
    if any((source / name).read_bytes() != data for name, data in raw.items()):
        raise ValueError('RLC_SOURCE_DRIFT')
    result.update(revision=REVISION, sourceSha256=PINS,
                  auditorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='aggregate-only-learner-corpus-screen')
    output.mkdir(parents=True, mode=0o700)
    (output / 'report.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)
