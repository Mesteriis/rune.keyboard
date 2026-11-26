#!/usr/bin/env python3
"""Compare actual host model scores for the two A2 controller request streams."""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

import a2_request_parity
import final_product_replay as replay


def run(source: Path, output: Path, timeout: float) -> None:
    source = source.resolve(strict=True)
    root = output.resolve()
    replay.require(root.is_relative_to(replay.REPO / 'build') and not root.exists(), 'FRESH_BUILD_ROOT_REQUIRED')
    replay.require(0 < timeout <= 300, 'INVALID_TIMEOUT')
    receipt = json.loads((source / 'receipt.json').read_text())
    replay.require(receipt['status'] == 'PASS' and receipt['modelCalls'] == 0, 'REQUEST_RECEIPT')
    freeze = source / 'source-freeze.json'
    replay.require(replay.sha256(freeze) == receipt['sourceFreezeSha256'], 'SOURCE_FREEZE_DRIFT')
    binding = json.loads(freeze.read_text())['bindings']
    replay.verify_bound_files({'files': binding['files']})
    observed = []
    for state in ('off', 'on'):
        path = source / state / 'observations.jsonl'
        replay.require(replay.sha256(path) == receipt['observationsSha256'][state], 'OBSERVATION_DRIFT')
        observed.append(replay.read_jsonl(path))
    replay.require(a2_request_parity.compare_requests(*observed) == receipt['requests'], 'REQUEST_RECEIPT_DRIFT')
    requests = [replay.request_manifest(data, 'holdout') for data in observed]
    replay.require(len(requests[0]) == 2004 and requests[0] == requests[1], 'HOLDOUT_REQUESTS')
    replay.require(replay.sha256(replay.MODEL) == replay.MODEL_SHA256 and
                   replay.sha256(replay.RUNNER) == replay.RUNNER_SHA256, 'MODEL_RUNNER_IDENTITY')
    root.mkdir(parents=True, mode=0o700)
    processes, selectors_, buffers = [], [], [bytearray(), bytearray()]
    errors = {}
    try:
        for _ in range(2):
            process = subprocess.Popen([str(replay.RUNNER), str(replay.MODEL)], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            processes.append(process)
            selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
            selectors_.append(selector)
        with (root / 'scores.jsonl').open('x', encoding='utf-8') as stream:
            for i, pair in enumerate(zip(*requests), 1):
                responses = []
                for n, request in enumerate(pair):
                    process = processes[n]
                    process.stdin.write(replay.canonical(replay.runner_request(request)) + b'\n'); process.stdin.flush()
                    deadline = time.monotonic() + timeout
                    while b'\n' not in buffers[n]:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0 or not selectors_[n].select(remaining): raise TimeoutError('MODEL_TIMEOUT')
                        block = os.read(process.stdout.fileno(), 65536)
                        replay.require(bool(block), 'RUNNER_CLOSED')
                        buffers[n].extend(block)
                        replay.require(len(buffers[n]) <= 65536, 'RUNNER_RESPONSE_BOUND')
                    line, _, tail = buffers[n].partition(b'\n'); buffers[n] = bytearray(tail)
                    response = json.loads(line)
                    replay.validate_response(request, response)
                    responses.append(response)
                normalized = [{key: value for key, value in response.items() if key != 'durationMillis'}
                              for response in responses]
                if normalized[0] != normalized[1]:
                    replay.write_json(root / 'mismatch.json', {'ordinal': i, 'responses': responses})
                    raise ValueError('SCORE_PARITY')
                if 'error' in normalized[0]:
                    code = normalized[0]['error']; errors[code] = errors.get(code, 0) + 1
                stream.write(replay.canonical(normalized[0]).decode() + '\n')
                stream.flush()
                if i % 100 == 0: print(f'scored {i}/{len(requests[0])}', file=sys.stderr, flush=True)
    finally:
        for selector in selectors_: selector.close()
        for process in processes:
            if process.stdin: process.stdin.close()
            if process.poll() is None: process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            if process.stdout: process.stdout.close()
    replay.verify_bound_files({'files': binding['files']})
    replay.require(replay.sha256(replay.MODEL) == replay.MODEL_SHA256 and replay.sha256(replay.RUNNER) == replay.RUNNER_SHA256,
                   'MODEL_RUNNER_DRIFT')
    replay.write_json(root / 'receipt.json', {'status': 'INCOMPLETE' if errors else 'PASS',
        'errors': errors, 'requests': len(requests[0]),
        'requestReceiptSha256': replay.sha256(source / 'receipt.json'), 'modelSha256': replay.MODEL_SHA256,
        'runnerSha256': replay.RUNNER_SHA256, 'scoresSha256': replay.sha256(root / 'scores.jsonl'),
        'toolSha256': replay.sha256(Path(__file__)), 'comparison': 'exact numeric scores; duration excluded'})
    replay.require(not errors, 'MODEL_ERRORS_RETAINED')


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    run(args.source, args.output, args.timeout)
