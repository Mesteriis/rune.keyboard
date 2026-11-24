"""Trace historical refinement and epoch target fragments to source tokens."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import historical_data_fixtures as fixtures
from audit_wordrank_source_boundaries import digest, inspect

LOCK = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
DATASETS = {'refinement': tuple('typing-refinement/data/' + part + '-rows.jsonl' for part in ('train', 'dev', 'test')),
            'epoch': ('typing-extra-epochs/data/test-rows.jsonl',)}


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
    payloads = fixtures.verify()
    raw_data = {name: b''.join(payloads[path] for path in paths) for name, paths in DATASETS.items()}
    datasets = {name: [json.loads(line) for line in raw.splitlines()] for name, raw in raw_data.items()}
    wanted = {row['articleId'] for rows in datasets.values() for row in rows}
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
    results = {name: inspect(rows, articles) for name, rows in datasets.items()}
    if LOCK.read_bytes() != lock or digest(parquet) != source['sha256']:
        raise ValueError('SOURCE_BOUNDARY_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, (rows, counts) in results.items():
        label = name
        raw = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for row in rows).encode()
        (output / (label + '-contexts.jsonl')).write_bytes(raw)
        receipt = dict(scope='disclosed-historical-source-boundary-audit', independentQualification=False,
                       counts=counts, sourceArticles=len({r['articleId'] for r in datasets[name]}),
                       sourceSha256=source['sha256'], sourceLockSha256=hashlib.sha256(lock).hexdigest(),
                       archiveRowsSha256=hashlib.sha256(raw_data[name]).hexdigest(), contextsSha256=hashlib.sha256(raw).hexdigest(),
                       analyzerSha256=digest(Path(__file__)), boundaryAnalyzerSha256=digest(ROOT / 'tools/typing_experiments/audit_wordrank_source_boundaries.py'))
        (output / (label + '-receipt.json')).write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        print(label, json.dumps(counts, sort_keys=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.parquet, args.output)
