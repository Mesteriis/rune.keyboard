#!/usr/bin/env python3
"""Descriptive chat report with independently checked editor Undo text.

This does not make exposed data an independent holdout or qualify a policy.
The historical v1 reporter remains unchanged for bound receipts.
"""
import argparse
import hashlib
import json
from pathlib import Path

import chat_corpus_report as historical


def verify_undo_text(observations):
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError('CHAT_UNDO_OBSERVATION')
        before = observation.get('beforeBoundary')
        after = observation.get('afterBackspace')
        claimed = observation.get('restoredBeforeBoundaryExactly')
        if (not isinstance(before, dict) or not isinstance(after, dict) or
                not isinstance(before.get('text'), str) or not isinstance(after.get('text'), str) or
                type(claimed) is not bool):
            raise ValueError('CHAT_UNDO_EVIDENCE')
        if claimed != (before['text'] == after['text']):
            raise ValueError('CHAT_UNDO_FLAG_MISMATCH')


def report(rows, observations):
    verify_undo_text(observations)
    result = historical.report(rows, observations)
    result['schema'] = 2
    result['undoVerification'] = 'before-boundary-text-equals-after-backspace-text'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'observations', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('CHAT_OUTPUT_EXISTS')
    paths = {'rows': args.rows, 'observations': args.observations}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    helper_paths = [Path(__file__), Path(historical.__file__),
                    Path(historical.__file__).with_name('typing_quality_slices.py')]
    helpers = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in helper_paths}
    parsed = {name: [json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip()]
              for name, data in raw.items()}
    result = report(parsed['rows'], parsed['observations'])
    if any(path.read_bytes() != raw[name] for name, path in paths.items()):
        raise ValueError('CHAT_INPUT_DRIFT')
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != helpers[path.name] for path in helper_paths):
        raise ValueError('CHAT_HELPER_DRIFT')
    result['inputs'] = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
    result['helpers'] = helpers
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
