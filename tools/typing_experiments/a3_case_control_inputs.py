#!/usr/bin/env python3
"""Disclose synthetic case-key probes and quarantine their inputs, not labels."""
import argparse
import json
from pathlib import Path
import re

import a3_case_sidecar_audit as audit
import build_chat_rare_candidate as packed
import control_ledger as controls
import pack_rare_word_lexicon as packer
import screen_case_lowercase_evidence as case

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'public-a3-case-rare-synthetic-inputs-v1'


def make_rows(case_keys, rare_keys, lower_keys):
    keys = sorted({w for w in case_keys if re.fullmatch('[а-яё]{3,4}', w)} & rare_keys - lower_keys)
    return [{'id': f'a3-case-{i:04d}-{j}', 'split': 'calibration', 'language': 'ru',
             'prefix': prefix, 'typed': word} for i, word in enumerate(keys)
            for j, prefix in enumerate(('', 'я вижу'))]


def register(ledger, rows, bindings, sidecar_sha):
    ledger = controls.validate(ledger)
    if any(entry['id'] == ENTRY for entry in ledger['entries']): raise ValueError('A3_ALREADY_REGISTERED')
    keys = sorted({controls.key_for(r, 'regression') for r in rows})
    surfaces = sorted({controls.surface_key('ru', r['typed']) for r in rows})
    entry = {'id': ENTRY, 'kind': 'regression', 'language': 'ru', 'rowCount': len(rows),
             'bindings': bindings, 'keys': keys, 'surfaceKeys': surfaces,
             'sidecarSha256': sidecar_sha,
             'note': 'Synthetic disclosed case-key inputs; no name or desired-output labels.'}
    return controls.validate(ledger | {'entries': ledger['entries'] + [entry]})


def run(sidecar, output, ledger_path):
    sidecar, output = sidecar.resolve(strict=True), output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    receipt_path = sidecar / 'receipt.json'; metadata = json.loads(receipt_path.read_text())
    words = sidecar / 'words.tsv'
    if (metadata.get('purpose') != 'disclosed_lowercase_source_screen_not_qualification' or
            packer.sha256(words) != metadata.get('wordsSha256') or
            metadata.get('extractorSha256') != packer.sha256(ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py') or
            packer.sha256(audit.CASE) != case.CASE_SHA or packer.sha256(audit.RARE) != audit.RARE_SHA):
        raise ValueError('A3_SOURCE_IDENTITY')
    lower = {line.split('\t')[0] for line in words.read_text().splitlines()}
    rows = make_rows(case.parse_case(audit.CASE.read_bytes()), set(packed.unpack(audit.RARE)), lower)
    if not rows: raise ValueError('A3_EMPTY')
    paths = (Path(__file__), Path(controls.__file__), Path(audit.__file__), Path(case.__file__),
             Path(packed.__file__), Path(packer.__file__), audit.CASE, audit.RARE,
             ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py',
             ROOT / 'tools/typing_experiments/rare_word_supplement.py')
    bindings = {str(p.relative_to(ROOT)): packer.sha256(p) for p in paths}
    proposal = register(controls.load(ledger_path), rows, bindings, metadata['wordsSha256'])
    output.mkdir(parents=True, mode=0o700)
    with (output / 'rows.jsonl').open('x', encoding='utf-8') as stream:
        for row in rows: stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    (output / 'control-ledger.json').write_text(json.dumps(proposal, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': len(rows), 'surfaces': len({r['typed'] for r in rows}),
                      'rowsSha256': packer.sha256(output / 'rows.jsonl')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sidecar', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, default=ROOT / 'tools/typing_experiments/control-ledger.json')
    args = parser.parse_args(); run(args.sidecar, args.output, args.ledger)
