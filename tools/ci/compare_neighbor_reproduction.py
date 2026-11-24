"""Compare a local neighbor corpus against its historical public receipt."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORICAL = ROOT / 'tools/typing_experiments/historical_provenance_sources/joint-neighbor-receipts/neighbor-corpus-manifest.json'
HISTORICAL_SHA = '2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e'
GENERATOR = ROOT / 'tools/typing_experiments/neighbor_recovery.py'
SUPPORT = (ROOT / 'tools/typing_experiments/prepare_external_spelling_holdout.py',
           ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py')
FILES = ('calibration.jsonl', 'holdout.jsonl', 'train.jsonl')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(historical, current, payloads, generator_sha):
    if not isinstance(historical, dict) or not isinstance(current, dict):
        raise ValueError('NEIGHBOR_MANIFEST')
    if set(historical.get('files', {})) != set(FILES) or set(current.get('files', {})) != set(FILES) or set(payloads) != set(FILES):
        raise ValueError('NEIGHBOR_FILE_SET')
    if current.get('generator') != generator_sha:
        raise ValueError('NEIGHBOR_GENERATOR_IDENTITY')
    file_results = {}
    for name in FILES:
        actual = sha(payloads[name])
        if actual != current['files'][name]:
            raise ValueError('NEIGHBOR_GENERATED_FILE_DRIFT')
        file_results[name] = {'actualSha256': actual, 'historicalSha256': historical['files'][name],
                              'matches': actual == historical['files'][name]}
    old_metadata = {k: v for k, v in historical.items() if k not in ('generator', 'files')}
    new_metadata = {k: v for k, v in current.items() if k not in ('generator', 'files')}
    return {'fileResults': file_results, 'metadataMatches': old_metadata == new_metadata,
            'allFilesMatch': all(item['matches'] for item in file_results.values()),
            'historicalGeneratorSha256': historical.get('generator'),
            'generatedWithSha256': generator_sha, 'historicalGeneratorRecovered': False,
            'qualified': False, 'scope': 'local-historical-row-reproduction-only'}


def verify_inputs(root, historical):
    """Check the local input bytes at comparison time against the historical receipt."""
    root = Path(root).resolve()
    shards = [f'build/typing-ranker-v2/ru-{number:04d}.parquet' for number in range(11, 18)]
    sources = historical.get('sources')
    if not isinstance(sources, dict) or set(sources) != set(shards):
        raise ValueError('NEIGHBOR_SOURCE_SET')
    expected = {name: (sources[name]['sha256'], sources[name]['bytes']) for name in shards}
    for name, field in (
        ('app/src/main/assets/smarttyping/lexicon/ru.morph', 'morphology'),
        ('build/smart-typing-0.3/corpus-inputs/ru_50k.txt', 'frequency'),
        ('app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin', 'context'),
    ):
        expected[name] = (historical[field], None)
    actual = {}
    for name, (digest, size) in expected.items():
        path = root / name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError('NEIGHBOR_INPUT_PATH')
        with path.open('rb') as stream:
            actual[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual[name] != digest or (size is not None and path.stat().st_size != size):
            raise ValueError('NEIGHBOR_INPUT_IDENTITY')
    return actual


def run(corpus, output):
    corpus = Path(corpus).resolve(strict=True)
    output = Path(output).resolve()
    if not corpus.is_relative_to(ROOT / 'build') or output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_OUTPUT_SCOPE')
    old_raw, new_raw, generator = HISTORICAL.read_bytes(), (corpus / 'manifest.json').read_bytes(), GENERATOR.read_bytes()
    if sha(old_raw) != HISTORICAL_SHA:
        raise ValueError('NEIGHBOR_HISTORICAL_RECEIPT')
    support = {path: path.read_bytes() for path in SUPPORT}
    payloads = {name: (corpus / name).read_bytes() for name in FILES}
    historical = json.loads(old_raw)
    result = compare(historical, json.loads(new_raw), payloads, sha(generator))
    input_sha = verify_inputs(ROOT, historical)
    if (HISTORICAL.read_bytes() != old_raw or (corpus / 'manifest.json').read_bytes() != new_raw or
            GENERATOR.read_bytes() != generator or any(path.read_bytes() != data for path, data in support.items()) or
            any((corpus / name).read_bytes() != data for name, data in payloads.items())):
        raise ValueError('NEIGHBOR_INPUT_DRIFT')
    result.update(inputSha256AtComparison=input_sha,
                  supportingSourceSha256AtComparison={str(path.relative_to(ROOT)): sha(data) for path, data in support.items()},
                  historicalReceiptSha256=sha(old_raw), generatedManifestSha256=sha(new_raw),
                  comparatorSha256=sha(Path(__file__).read_bytes()))
    output.mkdir(parents=True, mode=0o700)
    (output / 'report.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['allFilesMatch'] and result['metadataMatches'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.corpus, args.output))
