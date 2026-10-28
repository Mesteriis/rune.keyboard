#!/usr/bin/env python3
"""Portable model-free replay of the current local cascade; never sends labels to Kotlin."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import final_product_replay as harness
import replay_projection as projection

INPUT_FIELDS = ('id', 'split', 'language', 'prefix', 'typed')
ANDROID_PERSONALIZATION = harness.REPO / 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/personalization/AndroidTypingPersonalization.kt'


def load_inputs(paths):
    records, identities = [], set()
    for path in paths:
        with Path(path).open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line, object_pairs_hook=projection.unique_object,
                                 parse_constant=projection.invalid_constant)
                if not isinstance(row, dict) or not all(isinstance(row.get(key), str) for key in INPUT_FIELDS):
                    raise ValueError('REPLAY_INPUT_SHAPE')
                if not row['id'] or row['id'] in identities: raise ValueError('REPLAY_INPUT_ID')
                if row['language'] not in ('en', 'ru', 'es') or row['split'] not in ('train', 'calibration', 'holdout'):
                    raise ValueError('REPLAY_INPUT_SCOPE')
                identities.add(row['id'])
                record = {key: row[key] for key in INPUT_FIELDS}
                # Historical IDs can embed cohort names. Keep them in host-only metadata;
                # the controller receives an opaque ordinal, never that incidental label.
                record['sourceId'] = record['id']
                record['id'] = f"replay-{len(records):08d}"
                records.append(record)
    if not records: raise ValueError('REPLAY_INPUT_EMPTY')
    return records


def bindings(paths):
    return {harness.path_key(path): harness.sha256(path) for path in paths}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--java', type=Path, required=True)
    result.add_argument('--rows', type=Path, action='append', required=True)
    result.add_argument('--output', type=Path, required=True)
    result.add_argument('--baseline', type=Path)
    return result


def run(args):
    root = args.output.resolve()
    if root.exists() or not root.is_relative_to(harness.REPO / 'build'):
        raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    if any(os.environ.get(key) for key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')):
        raise ValueError('UNDECLARED_JAVA_OPTIONS')
    java = args.java.resolve(strict=True)
    rows = load_inputs(args.rows)
    sources, jars, android = harness.compile_inputs(java)
    assets = sorted(path for path in harness.ASSETS.rglob('*') if path.is_file())
    bound_paths = list(dict.fromkeys([*sources, *assets, *args.rows, *jars, android, java,
        Path(__file__), Path(projection.__file__), Path(harness.__file__), harness.SOURCE_MANIFEST,
        harness.TOOLCHAIN, ANDROID_PERSONALIZATION, *([args.baseline] if args.baseline else [])]))
    before = bindings(bound_paths)
    root.mkdir(parents=True, mode=0o700)
    receipt = {'schemaVersion': 1, 'mode': 'current-product', 'status': 'STARTED',
        'files': before, 'rows': len(rows), 'languages': dict(Counter(row['language'] for row in rows)),
        'inputFieldsSent': list(INPUT_FIELDS), 'opaqueControllerIds': True, 'modelCalls': 0,
        'boundaryDiagnostics': True, 'baselineCompared': args.baseline is not None}
    started = time.monotonic()
    try:
        encode = lambda value: base64.b64encode(value.encode('utf-8')).decode('ascii')
        inputs = root / 'inputs.tsv'
        with inputs.open('x', encoding='ascii') as stream:
            for index, row in enumerate(rows):
                stream.write('\t'.join([str(index), encode(row['id']), row['split'], row['language'],
                    encode(row['prefix']), encode(row['typed'])]) + '\n')
        receipt['labelFreeInputsSha256'] = harness.sha256(inputs)
        identities = root / 'input-identities.jsonl'
        harness.write_jsonl(identities, [{'index': index, 'id': row['id'], 'sourceId': row['sourceId']}
            for index, row in enumerate(rows)])
        receipt['hostOnlyIdentitiesSha256'] = harness.sha256(identities)
        os.environ['JAVA_TOOL_OPTIONS'] = '-Drune.replay.boundaryDiagnostics=true'
        compile_started = time.monotonic()
        jar, _ = harness.compile_harness(root, java, sources, jars, android)
        receipt['compileSeconds'] = time.monotonic() - compile_started
        receipt['jarSha256'] = harness.sha256(jar)
        projections = []
        for name in ('first', 'second'):
            run_root = root / name
            run_root.mkdir()
            output = run_root / 'observations.jsonl'
            run_started = time.monotonic()
            harness.run_harness(run_root, java, jars, android, jar, inputs, output, 'current-product')
            observed = projection.read_projection(output)
            if len(observed) != len(rows): raise ValueError('REPLAY_ROW_COUNT')
            for expected, actual in zip(rows, observed):
                if any(expected[key] != actual[key] for key in INPUT_FIELDS): raise ValueError('REPLAY_INPUT_IDENTITY')
            projections.append(observed)
            receipt[name] = {'elapsedSeconds': time.monotonic() - run_started,
                'observationsSha256': harness.sha256(output)}
        determinism = projection.compare(*projections)
        harness.write_json(root / 'determinism.json', determinism)
        receipt['deterministic'] = determinism['passed']
        if not determinism['passed']: raise ValueError('REPLAY_NONDETERMINISTIC:see determinism.json')
        with (root / 'projection.jsonl').open('xb') as stream:
            stream.write(projection.projection_bytes(projections[1]))
        receipt['projectionSha256'] = harness.sha256(root / 'projection.jsonl')
        if args.baseline:
            compared = projection.compare(projection.read_projection(args.baseline), projections[1])
            harness.write_json(root / 'baseline-comparison.json', compared)
            receipt['baselineMatches'] = compared['passed']
            if not compared['passed']: raise ValueError('REPLAY_BASELINE_DRIFT:see baseline-comparison.json')
        if before != bindings(bound_paths): raise ValueError('REPLAY_BOUND_FILE_DRIFT')
        receipt.update(status='COMPLETE', exitCode=0)
        return 0
    except Exception as error:
        receipt.update(status='FAILED', exitCode=1, failureType=type(error).__name__)
        if isinstance(error, subprocess.CalledProcessError):
            receipt['subprocessExitCode'] = error.returncode
        elif isinstance(error, subprocess.TimeoutExpired):
            receipt['subprocessTimeoutSeconds'] = error.timeout
        raise
    finally:
        os.environ.pop('JAVA_TOOL_OPTIONS', None)
        receipt['elapsedSeconds'] = time.monotonic() - started
        harness.write_json(root / 'receipt.json', receipt)


if __name__ == '__main__':
    # Raw observations may contain supplied corpus text. Keep every output private by default.
    os.umask(0o077)
    try: sys.exit(run(parser().parse_args()))
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
