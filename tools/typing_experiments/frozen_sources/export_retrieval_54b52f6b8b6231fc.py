#!/usr/bin/env python3
"""Observe baseline and manual retrieval; production receives typed tokens only."""
from pathlib import Path
import argparse
import base64
import importlib.util
import os
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('retrieval_export_support', ROOT / 'tools/morphology/evaluate.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def export(rows_path, output, java):
    root = support.output_directory(output)
    rows_path = rows_path.resolve(strict=True)
    rows = support.read_jsonl(rows_path)
    support.validate_rows(rows)
    replay = support.load_replay()
    java = java.resolve(strict=True)
    sources, jars, android = replay.compile_inputs(java)
    sources = [p for p in sources if (
        '/smarttyping/correction/' in str(p) or
        '/smarttyping/lexicon/' in str(p) and p.name != 'LocalCandidateWorker.kt' or
        p.name in ('KeyboardState.kt', 'ScoringContract.kt'))]
    sources.append(ROOT / 'tools/morphology/ProductionRetrieval.kt')
    frozen = support.bindings([rows_path, *sources, *jars, android, java, *replay.asset_paths(),
        Path(__file__), ROOT / 'tools/morphology/evaluate.py', support.PIPELINE / 'final_product_replay.py',
        replay.SOURCE_MANIFEST, replay.TOOLCHAIN])
    support.write_json(root / 'source-freeze.json', frozen)
    support.write_jsonl(root / 'rows.jsonl', rows)
    inputs = root / 'inputs.tsv'
    inputs.write_text(''.join(f'{i}\t{base64.b64encode(r["typed"].encode()).decode("ascii")}\n' for i, r in enumerate(rows)))
    jar, compile_command = replay.compile_harness(root, java, sources, jars, android)
    command = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-cp',
        os.pathsep.join(map(str, [jar, jars[1], jars[2], android])),
        'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.ProductionRetrieval', str(inputs), str(replay.ASSETS)]
    started = time.perf_counter()
    with (root / 'observations.jsonl').open('xb') as out, (root / 'generation.log').open('xb') as log:
        subprocess.run(command, stdout=out, stderr=log, timeout=1200, check=True)
    elapsed = time.perf_counter() - started
    observations = support.read_jsonl(root / 'observations.jsonl')
    support.verify_observations(rows, observations)
    for row, obs in zip(rows, observations, strict=True):
        manual = obs.get('manual')
        if manual is not None:
            support.require(manual['original'] == row['typed'] and len(manual['alternatives']) <= 7, 'MANUAL_BOUND')
    support.verify_bindings(frozen)
    support.write_json(root / 'receipt.json', dict(schemaVersion=1, scope='host-production-manual-retrieval',
        androidPerformanceMeasured=False, rows=len(rows), elapsedSeconds=elapsed, commands=[compile_command, command],
        sources=frozen, files=support.bindings([root / n for n in
            ('rows.jsonl', 'inputs.tsv', 'observations.jsonl', 'source-freeze.json', 'compile.log', 'generation.log')])))
    print(f'Exported {len(rows)} rows in {elapsed:.3f}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('rows', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--java', type=Path, default='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java')
    args = parser.parse_args()
    export(args.rows, args.output, args.java)
