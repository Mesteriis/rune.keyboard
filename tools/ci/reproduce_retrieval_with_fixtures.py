#!/usr/bin/env python3
"""Reproduce disclosed retrieval data using isolated historical prior fixtures."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import historical_model_fixtures as fixtures
import prepare_retrieval_test as retrieval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parquet', 'frequency', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    with fixtures.workspace('word') as prior:
        retrieval.prepare(args.parquet, args.frequency, args.output,
                          historical_reproduction=True, prior_root=prior)


if __name__ == '__main__':
    main()
