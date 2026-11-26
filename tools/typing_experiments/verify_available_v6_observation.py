"""Verify one disclosed v6 observation against its pinned public source shard.

This proves only source-text correspondence for this one observation. It does
not recreate the historical selection, corpus, audit or model qualification.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
OBSERVATION = ROOT / 'tools/typing_experiments/historical_provenance_sources/available_clean_v6_logged_calibration_row.json'
OBSERVATION_SHA256 = '5061b2449adfe6b306b354432de6a3d2dbfe1823e86a489d64e914ea659d9490'
SOURCE_SHA256 = '588e30523cfed480151b4bd5c1a7d7211dc03971fee399a3db6af3ad04e42c87'
SOURCE_BYTES = 209795982
SOURCE_URL = 'https://huggingface.co/datasets/wikimedia/wikipedia/resolve/a634f78b1c435397c07001e175fa74cc4ad5e775/20231101.ru/train/0018.parquet'
ARTICLE_URL = 'https://ru.wikipedia.org/wiki/%D0%94%D0%B5%D0%BF%D0%BE%D1%80%D1%82%D0%B0%D1%86%D0%B8%D0%B8%20%D0%B8%D0%B7%20%D0%9B%D0%B0%D1%82%D0%B2%D0%B8%D0%B9%D1%81%D0%BA%D0%BE%D0%B9%20%D0%A1%D0%A1%D0%A0'
ARTICLE_TITLE = 'Депортации из Латвийской ССР'


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify(source, observation=OBSERVATION):
    import pyarrow.parquet as parquet

    source, observation = Path(source), Path(observation)
    verifier = Path(__file__).resolve()
    initial_code = file_sha(verifier)
    raw = observation.read_bytes()
    if hashlib.sha256(raw).hexdigest() != OBSERVATION_SHA256:
        raise ValueError('V6_OBSERVATION_IDENTITY')
    if source.stat().st_size != SOURCE_BYTES or file_sha(source) != SOURCE_SHA256:
        raise ValueError('V6_SOURCE_IDENTITY')
    row = json.loads(raw)
    if row['source'] != '0018.parquet' or row['split'] != 'calibration' or row['group'] != 'typo':
        raise ValueError('V6_OBSERVATION_SCOPE')
    normalized = ' '.join(unicodedata.normalize('NFC',
        row['prefix'] + ' ' + row['word'] + row['rightContext']).casefold().split())
    if hashlib.sha256(normalized.encode()).hexdigest() != row['contextHash']:
        raise ValueError('V6_OBSERVATION_CONTEXT')
    prefix = unicodedata.normalize('NFC', row['prefix'])
    suffix = unicodedata.normalize('NFC', row['rightContext'])
    pattern = re.compile(re.escape(prefix) + r'\s*' + re.escape(row['word']) + re.escape(suffix), re.IGNORECASE)
    matches = []
    rows = 0
    for batch in parquet.ParquetFile(source).iter_batches(batch_size=64, columns=['id', 'url', 'title', 'text']):
        for article, url, title, text in zip(*(batch.column(i).to_pylist() for i in range(4)), strict=True):
            rows += 1
            if str(article) != row['article']:
                continue
            if not isinstance(text, str):
                raise ValueError('V6_SOURCE_TEXT')
            occurrences = sum(1 for _ in pattern.finditer(unicodedata.normalize('NFC', text)))
            matches.append((url, title, occurrences))
    if matches != [(ARTICLE_URL, ARTICLE_TITLE, 1)]:
        raise ValueError('V6_SOURCE_ARTICLE_OR_CONTEXT')
    if (source.stat().st_size != SOURCE_BYTES or file_sha(source) != SOURCE_SHA256 or
            observation.read_bytes() != raw or file_sha(verifier) != initial_code):
        raise ValueError('V6_SOURCE_DRIFT')
    return dict(scope='one-disclosed-calibration-observation', sourceSha256=SOURCE_SHA256,
                sourceBytes=SOURCE_BYTES, observationSha256=OBSERVATION_SHA256,
                articleUrl=ARTICLE_URL, articleTitle=ARTICLE_TITLE, sourceRows=rows,
                matchingArticles=1, matchingContexts=1, verifierSha256=initial_code,
                pyarrowVersion=importlib.metadata.version('pyarrow'),
                sourceDecoderAttested=False, independentQualification=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.source), ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
