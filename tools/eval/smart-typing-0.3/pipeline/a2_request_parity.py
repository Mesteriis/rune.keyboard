#!/usr/bin/env python3
"""Compare current controller model requests with the experimental window off/on."""
import argparse
from collections import Counter
import os
from pathlib import Path

import final_product_replay as replay


def compare_requests(first, second):
    replay.require(len(first) == len(second) and
                   [(r['id'], r['split'], r['language']) for r in first] ==
                   [(r['id'], r['split'], r['language']) for r in second],
                   'EXPORT_ROW_COMPLETENESS')
    replay.require([r.get('actualModelRequest') for r in first] ==
                   [r.get('actualModelRequest') for r in second], 'REQUEST_PARITY')
    return {split: len(replay.request_manifest(first, split)) for split in ('calibration', 'holdout')}


def run(output: Path, java: Path) -> None:
    root = output.resolve()
    replay.require(root.is_relative_to(replay.REPO / 'build') and not root.exists(), 'FRESH_BUILD_ROOT_REQUIRED')
    replay.require(not any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')),
                   'UNDECLARED_JAVA_OPTIONS')
    java = java.resolve(strict=True)
    _, rows, manifest = replay.load_original_spelling_rows()
    sources, jars, android = replay.compile_inputs(java)
    binding = replay.immutable_bindings(java, sources, jars, android, rows, bind_native_model=False)
    root.mkdir(parents=True, mode=0o700)
    replay.write_json(root / 'source-freeze.json', {'bindings': binding, 'corpusManifest': manifest,
        'toolSha256': replay.sha256(Path(__file__)), 'modelCalls': 0})
    import base64
    inputs = root / 'inputs.tsv'
    with inputs.open('x', encoding='ascii') as stream:
        for index, row in enumerate(rows):
            encode = lambda v: base64.b64encode(v.encode()).decode('ascii')
            stream.write('\t'.join([str(index), encode(row['id']), row['split'], row['language'],
                                    encode(row['prefix']), encode(row['typed'])]) + '\n')
    jar, _ = replay.compile_harness(root, java, sources, jars, android)
    observed = []
    try:
        for state in ('off', 'on'):
            os.environ['JAVA_TOOL_OPTIONS'] = '-Drune.replay.prefixWindow=' + ('true' if state == 'on' else 'false')
            target = root / state
            target.mkdir()
            replay.run_harness(target, java, jars, android, jar, inputs, target / 'observations.jsonl', 'export')
            data = replay.read_jsonl(target / 'observations.jsonl')
            replay.require(len(data) == len(rows) and [r['id'] for r in data] == [r['id'] for r in rows],
                           'EXPORT_ROW_COMPLETENESS')
            replay.require(all(r['status'] == 'EXPORTED' for r in data), 'EXPORT_STATUS')
            observed.append(data)
    finally:
        os.environ.pop('JAVA_TOOL_OPTIONS', None)
    counts = compare_requests(*observed)
    replay.verify_bound_files({'files': binding['files']})
    replay.write_json(root / 'receipt.json', {'status': 'PASS', 'rows': len(rows), 'requests': counts,
        'modelCalls': 0, 'qualificationWithoutModel': dict(Counter(
            f"{r['language']}:{r['currentQualificationWithoutModel']}" for r in observed[0])),
        'sourceFreezeSha256': replay.sha256(root / 'source-freeze.json'),
        'inputsSha256': replay.sha256(inputs), 'jarSha256': replay.sha256(jar),
        'observationsSha256': {state: replay.sha256(root / state / 'observations.jsonl') for state in ('off', 'on')}})
    print(f"requests match: calibration={counts['calibration']} holdout={counts['holdout']}")


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java', type=Path, default=Path('/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java'))
    args = parser.parse_args()
    run(args.output, args.java)
