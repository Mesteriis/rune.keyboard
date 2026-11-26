#!/usr/bin/env python3
"""Disclose aligned short Taiga PROPN inputs for A3 risk screening."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import a3_case_sidecar_audit as audit
import build_chat_rare_candidate as packed
import control_ledger as controls
import import_taiga_dev_exposure as taiga
import pack_rare_word_lexicon as packer

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'public-a3-taiga-propn-dev-regression-v1'


def select(data, rare, lower):
    rows = []; counts = {'unaligned': 0, 'eligibleTokens': 0}
    for block_index, block in enumerate(data.decode('utf-8').strip().split('\n\n')):
        lines = block.splitlines()
        texts = [line.removeprefix('# text = ') for line in lines if line.startswith('# text = ')]
        if len(texts) != 1: raise ValueError('TAIGA_TEXT_COUNT')
        text = unicodedata.normalize('NFC', texts[0])
        for line in lines:
            if not line or line.startswith('#'): continue
            fields = line.split('\t')
            if len(fields) != 10: raise ValueError('TAIGA_TOKEN_SHAPE')
            if not fields[0].isdigit() or fields[3] != 'PROPN': continue
            word = unicodedata.normalize('NFC', fields[1]); folded = word.casefold()
            if not re.fullmatch('[А-ЯЁ][а-яё]{2,3}', word) or folded not in rare or folded in lower: continue
            counts['eligibleTokens'] += 1
            matches = list(re.finditer(r'(?<![\w-])' + re.escape(word) + r'(?![\w-])', text))
            if len(matches) != 1: counts['unaligned'] += 1; continue
            prefix = text[:matches[0].start()].rstrip()[-128:]
            rows.append({'id': f'a3-taiga-{block_index:05d}-{fields[0]}', 'split': 'calibration',
                         'language': 'ru', 'prefix': prefix, 'typed': folded})
    if len({r['id'] for r in rows}) != len(rows): raise ValueError('TAIGA_DUPLICATE_ID')
    return rows, counts


def register(ledger, rows, bindings):
    ledger = controls.validate(ledger)
    if any(e['id'] == ENTRY for e in ledger['entries']): raise ValueError('A3_ALREADY_REGISTERED')
    entry = {'id': ENTRY, 'kind': 'regression', 'language': 'ru', 'rowCount': len(rows),
             'bindings': bindings, 'keys': sorted({controls.key_for(r, 'regression') for r in rows}),
             'surfaceKeys': sorted({controls.surface_key('ru', r['typed']) for r in rows}),
             'note': 'Disclosed Taiga PROPN inputs, no claim of intended typing or fresh holdout.'}
    return controls.validate(ledger | {'entries': ledger['entries'] + [entry]})


def run(source, sidecar, output):
    root = output.resolve(); sidecar = sidecar.resolve(strict=True)
    if root.exists() or not root.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    lock = json.loads(taiga.LOCK.read_text()); data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != lock['sha256']: raise ValueError('TAIGA_SOURCE_HASH')
    source_keys, _ = taiga.sentence_keys(data, lock['sha256'])
    from holdout_ledger import load_ledger
    ledger = load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
    imported = next((e for e in ledger['entries'] if e['id'] == taiga.ENTRY), None)
    if not imported or imported['keys']['sentence'] != source_keys: raise ValueError('TAIGA_EXPOSURE_MISSING')
    metadata = json.loads((sidecar / 'receipt.json').read_text()); wordfile = sidecar / 'words.tsv'
    if (metadata.get('wordsSha256') != packer.sha256(wordfile) or
            metadata.get('extractorSha256') != packer.sha256(ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py') or
            packer.sha256(audit.RARE) != audit.RARE_SHA): raise ValueError('A3_SOURCE_IDENTITY')
    lower = {line.split('\t')[0] for line in wordfile.read_text().splitlines()}
    rows, counts = select(data, packed.unpack(audit.RARE), lower)
    if not rows: raise ValueError('A3_NO_CONTROLS')
    paths = (Path(__file__), Path(controls.__file__), Path(taiga.__file__), taiga.LOCK, audit.RARE,
             ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py')
    bindings = {str(p.relative_to(ROOT)): packer.sha256(p) for p in paths}
    proposal = register(controls.load(ROOT / 'tools/typing_experiments/control-ledger.json'), rows, bindings)
    root.mkdir(parents=True, mode=0o700)
    with (root / 'rows.jsonl').open('x', encoding='utf-8') as stream:
        for row in rows: stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    (root / 'control-ledger.json').write_text(json.dumps(proposal, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'rows': len(rows), 'surfaces': len({r['typed'] for r in rows}), **counts,
                      'rowsSha256': packer.sha256(root / 'rows.jsonl')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'sidecar', 'output'): p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args(); run(args.source, args.sidecar, args.output)
