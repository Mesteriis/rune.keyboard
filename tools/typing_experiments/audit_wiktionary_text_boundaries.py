"""Project source-bound unknown text words and all matching Wiktionary forms."""
import argparse
import hashlib
import json
from pathlib import Path

import audit_unimorph_text_boundaries as source_audit
import import_unimorph_early_exclusions as historical
import import_wiktionary_historical_exclusions as dictionary

ROOT = Path(__file__).resolve().parents[2]


def selected_records(records, matches):
    if set(records) != set(source_audit.TEXT_PARENTS) or not set(records) <= set(matches):
        raise ValueError('WIKTIONARY_TEXT_PARTITIONS')
    return [record for name in source_audit.TEXT_PARENTS for record in records[name]
            if record['surfaceKey'] in matches[name]]


def capture(parquet, wiktionary):
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '25.0.1':
        raise ValueError('WIKTIONARY_TEXT_DECODER_VERSION')
    helpers = (Path(__file__).resolve(), Path(source_audit.__file__).resolve(),
               Path(historical.__file__).resolve(), Path(dictionary.__file__).resolve(),
               ROOT / 'tools/typing_experiments/selector_text_preflight_v1.py',
               ROOT / 'tools/typing_experiments/source_identities.py')
    helper_hashes = {path: source_audit.file_sha(path) for path in helpers}
    if source_audit.file_sha(parquet) != source_audit.SOURCE_SHA:
        raise ValueError('WIKTIONARY_TEXT_SOURCE_IDENTITY')
    raw_dictionary = Path(wiktionary).read_bytes()
    ledger_path = historical.LEDGER
    raw_ledger = ledger_path.read_bytes()
    base = json.loads(raw_ledger)
    existing = [e for e in base['entries'] if e['id'] == dictionary.ENTRY]
    if len(existing) != 1 or existing[0] != dictionary.entry(base, json.loads(dictionary.FIXTURE.read_bytes())):
        raise ValueError('WIKTIONARY_TEXT_PARENT')
    archives = source_audit.specs()
    parts = {name: [json.loads(line) for line in raw.splitlines()] for name, raw in archives.items()}
    wanted = {row['articleId'] for rows in parts.values() for row in rows}
    sources = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            if article in wanted:
                if article in sources: raise ValueError('WIKTIONARY_TEXT_DUPLICATE')
                sources[article] = text
    if set(sources) != wanted: raise ValueError('WIKTIONARY_TEXT_MISSING')
    entries = {e['id']: e for e in base['entries']}
    parents = historical.parent_keys(base)
    records = {}
    for name in source_audit.TEXT_PARENTS:
        unknown = set(entries[name]['unsupportedSurfaceKeys'])
        records[name] = source_audit.source_matches(name, parts[name], sources, unknown, unknown)
        parents[name] = {record['surfaceKey'] for record in records[name]}
    fixture = dictionary.capture(raw_dictionary, parents)
    selected = fixture['matchesByParent']
    projection = dict(schema=1, sourceSha256=source_audit.SOURCE_SHA,
        dictionarySha256=dictionary.SOURCE_SHA,
        archiveSha256={name: hashlib.sha256(raw).hexdigest() for name, raw in archives.items()},
        records=selected_records(records, selected))
    if (source_audit.file_sha(parquet) != source_audit.SOURCE_SHA or
            Path(wiktionary).read_bytes() != raw_dictionary or ledger_path.read_bytes() != raw_ledger or
            source_audit.specs() != archives or
            any(source_audit.file_sha(path) != value for path, value in helper_hashes.items())):
        raise ValueError('WIKTIONARY_TEXT_INPUT_DRIFT')
    return dict(projection=projection, dictionaryFixture=fixture)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--wiktionary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.parquet, args.wiktionary), ensure_ascii=False, sort_keys=True, indent=2))
