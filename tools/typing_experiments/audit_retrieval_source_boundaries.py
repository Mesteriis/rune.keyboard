"""Audit source-token boundaries of the frozen historical retrieval corpus."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import register_retrieval_history as fixture
from audit_wordrank_source_boundaries import digest, inspect

LOCK = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
BOUNDARY = ROOT / 'tools/typing_experiments/audit_wordrank_source_boundaries.py'


def run(parquet, output):
    import pyarrow.parquet as pq
    parquet = Path(parquet).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('SOURCE_BOUNDARY_OUTPUT')
    lock = LOCK.read_bytes()
    source = json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size != source['bytes'] or digest(parquet) != source['sha256']:
        raise ValueError('SOURCE_BOUNDARY_IDENTITY')
    rows, _, bindings = fixture.inputs()
    wanted = {row['articleId'] for row in rows}
    articles = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            article = str(article)
            if article in wanted:
                if article in articles:
                    raise ValueError('SOURCE_BOUNDARY_DUPLICATE_ARTICLE')
                articles[article] = unicodedata.normalize('NFC', text or '')
    if set(articles) != wanted:
        raise ValueError('SOURCE_BOUNDARY_ARTICLE')
    affected, failures, counts = [], [], Counter()
    for row in rows:
        try:
            found, stats = inspect([row], articles)
        except ValueError as error:
            if str(error) != 'SOURCE_BOUNDARY_COMPOUND':
                raise
            failures.append({'id': row['id'], 'reason': str(error)})
        else:
            affected.extend(found)
            counts.update(stats)
    if len(affected) != 9 or len(failures) != 1 or counts['rows'] != 1799:
        raise ValueError('SOURCE_BOUNDARY_SCOPE')
    if LOCK.read_bytes() != lock or digest(parquet) != source['sha256'] or fixture.inputs()[2] != bindings:
        raise ValueError('SOURCE_BOUNDARY_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    raw = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                  for row in sorted(affected, key=lambda row: row['id'])).encode()
    failure_raw = (json.dumps(failures, sort_keys=True, separators=(',', ':')) + '\n').encode()
    (output / 'contexts.jsonl').write_bytes(raw)
    (output / 'unresolved.json').write_bytes(failure_raw)
    receipt = dict(scope='disclosed-historical-source-boundary-audit', independentQualification=False,
                   counts=dict(sorted(counts.items())), unresolved=len(failures), sourceArticles=len(wanted),
                   sourceSha256=source['sha256'], sourceLockSha256=hashlib.sha256(lock).hexdigest(),
                   archiveRowsSha256=fixture.ROWS_SHA, contextsSha256=hashlib.sha256(raw).hexdigest(),
                   unresolvedSha256=hashlib.sha256(failure_raw).hexdigest(), analyzerSha256=digest(Path(__file__)),
                   boundaryAnalyzerSha256=digest(BOUNDARY))
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'counts': receipt['counts'], 'unresolved': len(failures)}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.parquet, args.output)
