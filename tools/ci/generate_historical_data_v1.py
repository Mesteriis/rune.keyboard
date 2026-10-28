"""Freeze byte-identical public historical datasets with per-article attribution."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile

import historical_data_fixtures as fixtures

NOTICE = '''# Original public historical test data

Host-side regression fixtures only; not packaged in the Android application.
The two original manifests and every file they advertise are preserved byte for
byte. No new training, qualification or model selection is performed.

Source: Wikimedia contributors, Russian Wikipedia snapshot 20231101, distributed
as wikimedia/wikipedia, parquet conversion revision
`a634f78b1c435397c07001e175fa74cc4ad5e775`, `20231101.ru/train/0007.parquet`.
Dataset: https://huggingface.co/datasets/wikimedia/wikipedia
Each consumed article is credited by title and a contributor-history link in
`articles.jsonl`; the retained article IDs also appear in the original manifests.
Source texts were normalized/tokenized, truncated and combined with synthetic
spelling errors by the two hash-bound preparation scripts. These changes are
covered by the original source terms, not by the repository code license.

The pinned dataset notice records CC-BY-SA-3.0 and GFDL-1.3, with some text
available only under Creative Commons. Use this text collection under
Creative Commons Attribution-ShareAlike 3.0:
https://creativecommons.org/licenses/by-sa/3.0/
Legal terms: https://creativecommons.org/licenses/by-sa/3.0/legalcode
See also `tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md` and `source-lock.json`.
Historical generators and vocabulary provenance remain bound in each manifest.
The archive includes derived examples, not the source frequency list.

These articles are permanently excluded from fresh qualification by the durable
holdout ledger. Missing canonical-family/full-sentence provenance remains open.
'''


def build(source_build, parquet, frequency, output):
    import pyarrow.parquet as pq
    lock = json.loads((fixtures.ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())
    if (fixtures.sha(parquet.read_bytes()) != lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
            fixtures.sha(frequency.read_bytes()) != lock['frequencyWords']['files']['ru_50k.txt']):
        raise ValueError('HISTORICAL_RAW_SOURCE_IDENTITY')
    payloads = {}
    articles = set()
    generators = {}
    for directory in fixtures.PINS:
        name = directory + '/manifest.json'
        raw = (source_build / name).read_bytes()
        if fixtures.sha(raw) != fixtures.PINS[directory]:
            raise ValueError('HISTORICAL_MANIFEST_IDENTITY')
        manifest = json.loads(raw)
        payloads[name] = raw
        for filename in manifest['files']:
            payloads[directory + '/' + filename] = (source_build / directory / filename).read_bytes()
        script = 'prepare_refinement.py' if directory.startswith('typing-refinement') else 'prepare_epoch_test.py'
        script = 'tools/typing_experiments/' + script
        if fixtures.sha((fixtures.ROOT / script).read_bytes()) != manifest['preparationScriptSha256']:
            raise ValueError('HISTORICAL_GENERATOR_IDENTITY')
        generators[script] = manifest['preparationScriptSha256']
        articles.update(article for part in manifest['partitions'].values() for article in part['articles'])
    fixtures.check_payloads(payloads)
    credits = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'title']):
        for identity, title in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            identity = str(identity)
            if identity in articles:
                if identity in credits or not title:
                    raise ValueError('HISTORICAL_ARTICLE_IDENTITY')
                credits[identity] = {'articleId': identity, 'title': title,
                    'historyUrl': 'https://ru.wikipedia.org/w/index.php?curid=' + identity + '&action=history'}
        if len(credits) == len(articles):
            break
    if set(credits) != articles:
        raise ValueError('HISTORICAL_ARTICLE_MISSING')
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w', format=tarfile.USTAR_FORMAT) as bundle:
        for name, raw in sorted(payloads.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            bundle.addfile(info, io.BytesIO(raw))
    compressed = gzip.compress(archive.getvalue(), mtime=0)
    attribution = ''.join(json.dumps(credits[n], ensure_ascii=False, sort_keys=True) + '\n'
                          for n in sorted(credits, key=int)).encode()
    meta = {'schemaVersion': 1, 'purpose': 'ORIGINAL_PUBLIC_DATA_REGRESSION_ONLY',
        'archiveSha256': fixtures.sha(compressed), 'articleAttributionSha256': fixtures.sha(attribution),
        'noticeSha256': fixtures.sha(NOTICE.encode()), 'generators': generators,
        'sourceLockSha256': fixtures.sha((fixtures.ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_bytes()),
        'files': {name: {'sha256': fixtures.sha(raw), 'bytes': len(raw)} for name, raw in sorted(payloads.items())}}
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in [('files.tar.gz', compressed), ('articles.jsonl', attribution), ('NOTICE.md', NOTICE.encode()),
                      ('manifest.json', (json.dumps(meta, indent=2, sort_keys=True) + '\n').encode())]:
        (output / name).write_bytes(raw)
    print(json.dumps({'files': len(payloads), 'articles': len(credits), 'compressedBytes': len(compressed)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-build', type=Path, required=True)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--frequency', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source_build, args.parquet, args.frequency, args.output)
