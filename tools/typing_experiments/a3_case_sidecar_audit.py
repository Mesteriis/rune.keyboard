#!/usr/bin/env python3
"""Aggregate overlap of current canonical-case keys and an A3 source screen."""
import argparse
import json
from pathlib import Path
import re

import build_chat_rare_candidate as packed
import pack_rare_word_lexicon as packer
import screen_case_lowercase_evidence as case

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'app/src/main/assets/smarttyping/lexicon/case/ru.case'
RARE = ROOT / 'app/src/main/assets/smarttyping/lexicon/ru.rare'
RARE_SHA = '434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e'


def summarize(case_keys, rare_keys, lower_keys):
    short = {w for w in case_keys if re.fullmatch('[а-яё]{3,4}', w)}
    return {'shortCaseKeys': len(short), 'inRare': len(short & rare_keys),
            'inLowerEvidence': len(short & lower_keys),
            'inRareWithoutLowerEvidence': len((short & rare_keys) - lower_keys)}


def run(sidecar, output):
    sidecar, output = sidecar.resolve(strict=True), output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    metadata = json.loads((sidecar / 'receipt.json').read_text())
    words_file = sidecar / 'words.tsv'
    if (metadata.get('purpose') != 'disclosed_lowercase_source_screen_not_qualification' or
            metadata.get('wordsSha256') != packer.sha256(words_file) or
            metadata.get('extractorSha256') != packer.sha256(ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py') or
            packer.sha256(CASE) != case.CASE_SHA or packer.sha256(RARE) != RARE_SHA):
        raise ValueError('A3_SOURCE_IDENTITY')
    lower = []
    for line in words_file.read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) != 2 or not re.fullmatch('[а-яё]{3,4}', fields[0]) or not fields[1].isdigit() or int(fields[1]) < 1:
            raise ValueError('A3_SIDECAR_ROW')
        lower.append(fields[0])
    if lower != sorted(set(lower)) or len(lower) != metadata['uniqueWords']: raise ValueError('A3_SIDECAR_ROWS')
    result = summarize(case.parse_case(CASE.read_bytes()), set(packed.unpack(RARE)), set(lower))
    result.update(purpose='disclosed_case_key_screen_not_name_qualification', caseSha256=case.CASE_SHA,
                  rareSha256=RARE_SHA, sidecarSha256=metadata['wordsSha256'],
                  sidecarReceiptSha256=packer.sha256(sidecar / 'receipt.json'),
                  scriptSha256=packer.sha256(Path(__file__)))
    output.mkdir(parents=True, mode=0o700)
    (output / 'report.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sidecar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); run(args.sidecar, args.output)
