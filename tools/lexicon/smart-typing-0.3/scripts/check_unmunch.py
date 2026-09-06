#!/usr/bin/env python3
"""Reject lossy expansion: compare pinned unmunch against the native spelling oracle."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from pipeline_config import PACKAGE, build_root

ROOT = build_root()


def check(language: str, stem: str) -> dict:
    aff = ROOT / f'sources/libreoffice/{stem}.aff'
    dic = ROOT / f'sources/libreoffice/{stem}.dic'
    raw = ROOT / f'reports/{language}-unmunch-raw.txt'
    with raw.open('wb') as output, (ROOT / f'reports/{language}-unmunch.log').open('wb') as log:
        subprocess.run([str(ROOT / 'bin/unmunch'), str(dic), str(aff)], stdout=output,
                       stderr=log, check=True)
    lines = raw.read_bytes().splitlines()
    words = set()
    invalid_utf8 = 0
    for line in lines:
        try:
            words.add(line.decode('utf-8'))
        except UnicodeDecodeError:
            invalid_utf8 += 1
    frequency = (ROOT / f'sources/frequency/{language}_50k.txt').read_text(encoding='utf-8')
    probes = [line.rsplit(' ', 1)[0] for line in frequency.splitlines()]
    accepted = subprocess.run([str(ROOT / 'bin/spell_oracle'), str(aff), str(dic)],
                              input='\n'.join(probes)+'\n', text=True, encoding='utf-8',
                              capture_output=True, check=True)
    known = [line[2:] for line in accepted.stdout.splitlines() if line.startswith('1\t')]
    missing = [word for word in known if word not in words]
    witness = ROOT / f'reports/{language}-unmunch-missing-known.tsv'
    witness.write_text('word\toracle_accepts\tunmunch_contains\n' + ''.join(
        f'{word}\t1\t0\n' for word in missing), encoding='utf-8')
    directives = Counter(line.split()[0] for line in aff.read_text(encoding='utf-8').splitlines()
                         if line.strip() and not line.lstrip().startswith('#'))
    marker_words = sorted(word for word in words if '/' in word or '|' in word)
    return {'language': language, 'status': 'REJECTED' if missing or invalid_utf8 or marker_words else 'UNPROVEN',
            'directive_rows': dict(sorted(directives.items())), 'raw_rows': len(lines),
            'unique_valid_utf8': len(words), 'invalid_utf8_rows': invalid_utf8,
            'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
            'oracle_known_frequency_words': len(known), 'missing_known_frequency_words': len(missing),
            'missing_examples': missing[:30], 'continuation_marker_words': len(marker_words),
            'marker_examples': marker_words[:10], 'missing_witness_path': str(witness.relative_to(ROOT)),
            'oracle_stderr': accepted.stderr,
            'oracle_scope': 'The 50k public frequency list is a diagnostic probe, not held-out evaluation or an authoritative word source.'}


def main() -> None:
    report = [check('ru', 'ru_RU/ru_RU'), check('es', 'es/es_ES')]
    (ROOT / 'reports/unmunch-validation.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    for row in report:
        print(row['language'], row['status'], 'missing known:', row['missing_known_frequency_words'],
              'continuation markers:', row['continuation_marker_words'])


if __name__ == '__main__':
    main()
