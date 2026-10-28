"""Freeze original public model test payloads with explicit path templates."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile

import historical_model_fixtures as fixtures
import historical_model_sources as sources
import historical_data_fixtures as core

NOTICE = '''# Original historical model test fixtures

Host-only public regression data and original full reference models, not new
training or qualification. Model CBMs, decoded weights, rows and observations
are preserved byte for byte. Original SHA-256 identities are recorded per file.
The CBMs retain public upstream CatBoost build metadata; original project/user
paths are not included. No model weights are reserialized or replaced.

Receipts, source-freeze maps and logs replace original project/external paths
with $ROOT/$EXTERNAL tokens. Receipt hashes are updated for the transformed
metadata. At runtime, isolated temporary workspaces rebase these tokens and
rehash metadata edges. Original candidate/source/data/model byte identities are
retained; external runtimes and candidate reproduction are not established.

Public Wikipedia snapshot 20231101, wikimedia/wikipedia parquet conversion
revision a634f78b1c435397c07001e175fa74cc4ad5e775:
https://huggingface.co/datasets/wikimedia/wikipedia
The original word-ranking manifests and all advertised payloads are preserved.
The text was normalized, truncated and combined with synthetic spelling errors
by its hash-bound original preparation script. Each of the 4,920 consumed
articles is credited by title and contributor-history link in articles.jsonl.
Core refinement/additional-epoch attribution remains in historical-data-v1.
Use the text collection under CC-BY-SA-3.0, not the repository code license:
https://creativecommons.org/licenses/by-sa/3.0/
https://creativecommons.org/licenses/by-sa/3.0/legalcode
The original source notice also records GFDL-1.3; see
 tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md and source-lock.json.

The baseline export's 4,000 rows match already-versioned public qualification-v2
spelling/protected-token rows; their original attribution/licensing is retained.
Project-authored fixtures and model assets retain their existing project terms.
All these data remain permanently excluded from fresh qualification. Original
assertions execute in isolated source snapshots; no archived script is executed.
'''


def generate(build, parquet, output):
    import pyarrow.parquet as pq
    sources.audit(historical_build=build)
    original_data = core.verify()
    index = json.loads((sources.DATA / 'manifest.json').read_text())
    lock_path = sources.ROOT / 'tools/model/rune-text-0.2/source-lock.json'
    lock = json.loads(lock_path.read_text())
    if sources.sha(parquet) != lock['wikipediaContext']['files']['ru-0007.parquet']['sha256']:
        raise ValueError('MODEL_FIXTURE_PUBLIC_PARQUET')
    roots = set()
    aliases = {}
    for name in index['exports']:
        receipt = json.loads((build / name / 'receipt.json').read_text())
        root = next(iter(receipt['files'])).split('/build/' + name + '/')[0]
        roots.add(root)
        for path in receipt['sources']:
            if not path.startswith(root + '/'):
                alias = '$EXTERNAL/' + Path(path).name
                if alias in aliases.values() and path not in aliases:
                    raise ValueError('MODEL_FIXTURE_EXTERNAL_COLLISION')
                aliases[path] = alias
    aliases.update({root: '$ROOT' for root in roots})
    replacements = sorted(aliases.items(), key=lambda pair: -len(pair[0]))

    def sanitize(raw):
        value = raw.decode()
        for old, new in replacements:
            value = value.replace(old, new)
        # Never publish an original project/cache owner path in derived metadata.
        if '/Users/' in value or '/home/' in value:
            raise ValueError('MODEL_FIXTURE_UNMAPPED_METADATA_PATH')
        return value.encode()

    payloads, records = {}, {}

    def add(name, profiles, mode='raw', raw=None):
        sources.relative(name)
        original = (build / name.removeprefix('build/')).read_bytes() if raw is None else raw
        content = sanitize(original) if mode == 'template' else original
        payloads[name] = content
        records[name] = {'profiles': profiles, 'mode': mode, 'originalSha256': fixtures.digest(original),
                         'sha256': fixtures.digest(content), 'bytes': len(content)}

    for export, profile in [('morphology-public-export-v3', 'baseline'), ('typing-refinement/candidates-v2', 'refinement')]:
        receipt = json.loads((build / export / 'receipt.json').read_text())
        for path in receipt['files']:
            filename = Path(path).name
            mode = 'raw' if filename in ('rows.jsonl', 'observations.jsonl', 'inputs.tsv') else 'template'
            add('build/' + export + '/' + filename, [profile], mode)
        prefix = 'build/' + export + '/'
        receipt = json.loads(sanitize((build / export / 'receipt.json').read_bytes()))
        receipt['files'] = {'$ROOT/' + prefix + Path(path).name: fixtures.digest(payloads[prefix + Path(path).name])
                            for path in receipt['files']}
        add(prefix + 'receipt.json', [profile], 'template', raw=(json.dumps(receipt, sort_keys=True, indent=2)+'\n').encode())
        records[prefix + 'receipt.json']['originalSha256'] = index['exports'][export]['receiptSha256']

    for part in ('train', 'dev', 'test'):
        path = 'typing-refinement/verified-observations/' + part + '.jsonl'
        binding = json.loads((build / 'typing-refinement/verified-observations/manifest.json').read_text())
        if sources.sha(build / path) != binding['partitions'][part]:
            raise ValueError('MODEL_FIXTURE_OBSERVATION_IDENTITY')
        add('build/' + path, ['refinement'])
    add('build/typing-refinement/verified-observations/manifest.json', ['refinement', 'word'], 'template')
    add('build/typing-extra-epochs/observations/manifest.json', ['word'], 'template')
    for name, profile in [('typing-experiments/catboost-reference.cbm','baseline'),
                          ('typing-experiments/parity.json','baseline'),
                          ('typing-refinement/ranker/pairwise.cbm','refinement'),
                          ('typing-refinement/ranker/pairwise.bin','refinement')]:
        add('build/' + name, [profile])
    for name, expected in fixtures.MODEL_PINS.items():
        if fixtures.digest(payloads[name]) != expected:
            raise ValueError('MODEL_FIXTURE_ORIGINAL_REFERENCE')
    word_path = build / 'typing-word-ranking/data'
    word = json.loads((word_path / 'manifest.json').read_text())
    if sources.sha(word_path / 'manifest.json') != sources.WORD_SHA:
        raise ValueError('MODEL_FIXTURE_ORIGINAL_WORD_MANIFEST')
    for name in ['manifest.json', *word['files']]:
        if name != 'manifest.json' and sources.sha(word_path / name) != word['files'][name]:
            raise ValueError('MODEL_FIXTURE_ORIGINAL_WORD_DATA')
        add('build/typing-word-ranking/data/' + name, ['word'])
    for directory, expected in core.PINS.items():
        if fixtures.digest(original_data[directory + '/manifest.json']) != expected:
            raise ValueError('MODEL_FIXTURE_ORIGINAL_CORE_DATA')
    public = {}
    for path in index['exports']['morphology-public-export-v3']['sources']:
        if path.endswith('.jsonl'):
            public.update((r['id'], r) for r in map(json.loads, (sources.ROOT / path).read_text().splitlines()))
    baseline = [json.loads(line) for line in payloads['build/morphology-public-export-v3/rows.jsonl'].splitlines()]
    if len(baseline) != 4000 or any(public.get(row['id']) != row for row in baseline):
        raise ValueError('MODEL_FIXTURE_BASELINE_PUBLIC_IDENTITY')
    assets = {'app/src/main/assets/smarttyping/experiments/ru-context.bin':
              {'profiles': ['baseline'], 'sha256': 'c97774d38d35393cbe0e99ea4271e40409fbdce0c08cc21fda5f3f7bf4fd006b'},
              'tools/model/rune-text-0.2/source-lock.json': {'profiles': ['refinement'], 'sha256': sources.sha(lock_path)},
              'tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json':
              {'profiles': ['baseline'], 'sha256': sources.sha(sources.ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json')}}
    articles = {a for part in word['partitions'].values() for a in part['articles']}
    credits = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'title']):
        for identity, title in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            identity = str(identity)
            if identity in articles:
                credits[identity] = {'articleId': identity, 'title': title,
                    'historyUrl': 'https://ru.wikipedia.org/w/index.php?curid=' + identity + '&action=history'}
        if set(credits) == articles:
            break
    if set(credits) != articles:
        raise ValueError('MODEL_FIXTURE_ATTRIBUTION_MISSING')
    attribution = ''.join(json.dumps(credits[n], sort_keys=True, ensure_ascii=False)+'\n' for n in sorted(credits, key=int)).encode()
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w', format=tarfile.USTAR_FORMAT) as bundle:
        for name, raw in sorted(payloads.items()):
            info = tarfile.TarInfo(name); info.size = len(raw); info.mode = 0o644; info.mtime = 0
            bundle.addfile(info, io.BytesIO(raw))
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='wb', filename='', mtime=0) as stream:
        stream.write(archive.getvalue())
    raw = compressed.getvalue()
    meta = {'schemaVersion':1, 'purpose':'ORIGINAL_HISTORICAL_TEST_FIXTURES', 'archiveSha256':fixtures.digest(raw),
            'sourceIndexSha256': sources.sha(sources.DATA/'manifest.json'),
            'coreManifestSha256': sources.sha(core.DATA/'manifest.json'),
            'articleAttributionSha256': fixtures.digest(attribution), 'noticeSha256':fixtures.digest(NOTICE.encode()),
            'files':records, 'repositoryFiles':assets}
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in [('files.tar.gz',raw),('articles.jsonl',attribution),('NOTICE.md',NOTICE.encode()),
                      ('manifest.json',(json.dumps(meta,sort_keys=True,indent=2)+'\n').encode())]:
        (output/name).write_bytes(raw)
    print(json.dumps({'files':len(payloads),'compressedBytes':(output/'files.tar.gz').stat().st_size,
                      'articles':len(credits),'archiveSha256':meta['archiveSha256']}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-build',type=Path,required=True)
    parser.add_argument('--parquet',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    generate(args.historical_build,args.parquet,args.output)
