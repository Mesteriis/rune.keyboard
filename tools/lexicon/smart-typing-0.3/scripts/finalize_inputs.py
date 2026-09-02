#!/usr/bin/env python3
"""Freeze normalized forms, separately licensed frequency data, notices and provenance."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import unicodedata
from expand_affixes import ROOT, file_record, write_words
from pipeline_config import PACKAGE, load_lock


def normalize(word: str) -> str:
    # Unicode default lowercase equals RU/EN/ES lowercase; no casefold, NFKC or accent stripping.
    return unicodedata.normalize('NFC', unicodedata.normalize('NFC', word).lower())


def english_forms() -> dict:
    raw = (ROOT/'reports/en-scowl60-latin1.txt').read_bytes().decode('iso-8859-1').splitlines()
    if len(raw) < 50000:
        raise ValueError('SCOWL output unexpectedly small: refuse the known BSD grep failure')
    surfaces = {unicodedata.normalize('NFC', word) for word in raw if 0 < len(word) <= 32}
    if any(any(c.isspace() for c in word) for word in surfaces):
        raise ValueError('Unexpected whitespace in SCOWL word forms')
    keys = {normalize(word) for word in surfaces}
    for known in ['children', 'running', 'café', 'jalapeño', 'fiancée']:
        if known not in keys:
            raise ValueError(f'SCOWL word-form/diacritic sentinel missing: {known}')
    return {'language': 'en', 'profile': 'SCOWL60-en_US-default-nonvariants-accents-keep-max32',
            'input_encoding': 'ISO-8859-1', 'selected_source_rows': len(raw),
            'over_32_codepoints': sum(len(word)>32 for word in raw),
            'nfc_changed': sum(unicodedata.normalize('NFC', word) != word for word in raw),
            'case_changed': sum(word.lower() != word for word in surfaces),
            'surface_forms': write_words(ROOT/'outputs/en.surface-forms.txt', surfaces),
            'canonical_keys': write_words(ROOT/'outputs/en.words.txt', keys)}


def frequency_component(language: str) -> dict:
    rows = []
    for rank, line in enumerate((ROOT/f'sources/frequency/{language}_50k.txt').read_text(encoding='utf-8').splitlines(), 1):
        word, count = line.rsplit(' ', 1)
        if not count.isdecimal() or any(c in word for c in '\t\r\n'):
            raise ValueError('Malformed frequency source')
        rows.append((normalize(word), rank, word, int(count)))
    path = ROOT/f'outputs/frequency/{language}.tsv'
    path.parent.mkdir(exist_ok=True)
    path.write_text('key\tsource_rank\tsource_word\tsource_count\n'+''.join(
        f'{key}\t{rank}\t{word}\t{count}\n' for key, rank, word, count in sorted(rows)), encoding='utf-8')
    counts = Counter(key for key, _, _, _ in rows)
    return {'language': language, 'license': 'CC-BY-SA-4.0', 'data': file_record(path),
            'source_rows': len(rows), 'normalized_key_collision_groups': sum(n>1 for n in counts.values()),
            'policy': 'Preserve every source rank, source word and source count. Never aggregate or mix with orthographic assets.'}


def archive_inventory() -> list[dict]:
    records = []
    for archive_path in sorted((ROOT/'downloads').glob('*.tar.gz')):
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise ValueError('Cannot read archive member')
                    records.append({'archive': str(archive_path.relative_to(ROOT)), 'member': member.name,
                                    'sha256': hashlib.sha256(handle.read()).hexdigest(), 'bytes': member.size})
                elif member.issym() or member.islnk():
                    records.append({'archive': str(archive_path.relative_to(ROOT)), 'member': member.name,
                                    'link_target': member.linkname})
    return records


def copy_scowl_notice() -> None:
    revision = '5ef55f9c42730ebe4394a78b77855468a6f15dd2'
    archive_name = f'downloads/scowl-{revision}.tar.gz'
    records = load_lock()
    matching = [record for record in records if record['path'] == archive_name]
    if len(matching) != 1:
        raise ValueError('Expected one pinned SCOWL archive in source-lock.json')
    archive_path = ROOT/archive_name
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != matching[0]['sha256']:
        raise ValueError(f'SHA-256 mismatch: {archive_name}')
    with tarfile.open(archive_path) as archive:
        member = archive.getmember(f'wordlist-{revision}/scowl/Copyright')
        if not member.isfile():
            raise ValueError('SCOWL Copyright must be a regular archive member')
        source = archive.extractfile(member)
        if source is None:
            raise ValueError('Cannot read SCOWL Copyright from verified archive')
        (ROOT/'notices/SCOWL-Copyright.txt').write_bytes(source.read())


def copy_notices() -> list[dict]:
    hun = ROOT/'sources/hunspell-e184e22c51fe213f4490e9b36998f0ad3e5e606b'
    copy_scowl_notice()
    sources = {'RU-Lebedev.txt': ROOT/'sources/libreoffice/ru_RU/README_ru_RU.txt',
               'ES-LICENSE.md': ROOT/'sources/libreoffice/es/LICENSE.md',
               'ES-README.txt': ROOT/'sources/libreoffice/es/README_hunspell_es.txt',
               'ES-MPL-1.1.txt': ROOT/'sources/libreoffice/es/MPL-1.1.txt',
               'FrequencyWords-README.md': ROOT/'sources/frequency/README.md',
               'FrequencyWords-code-MIT.txt': ROOT/'sources/frequency/LICENSE'}
    for name in ['COPYING', 'COPYING.LESSER', 'COPYING.MPL', 'license.hunspell', 'license.myspell', 'AUTHORS']:
        sources['Hunspell-'+name+'.txt'] = hun/name
    for name, source in sources.items():
        shutil.copyfile(source, ROOT/'notices'/name)
    return [file_record(path) for path in sorted((ROOT/'notices').iterdir()) if path.is_file()]


def remaining_diagnostics(language: str) -> dict:
    missing = (ROOT/f'reports/{language}-finite-missing-known.txt').read_text(encoding='utf-8').splitlines()
    categories = {'hyphenated': [], 'trailing_period': [], 'other': []}
    for word in missing:
        categories['hyphenated' if '-' in word else 'trailing_period' if word.endswith('.') else 'other'].append(word)
    path = ROOT/f'reports/{language}-residual-categories.json'
    path.write_text(json.dumps(categories, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (ROOT/f'reports/{language}-finite-oracle.tsv').open(encoding='utf-8') as source:
        rejected = [line[2:].rstrip('\n') for line in source if line.startswith('0\t')]
    (ROOT/f'reports/{language}-rejected-forms.json').write_text(json.dumps(rejected, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'residual_categories': {kind: len(words) for kind, words in categories.items()},
            'residual_scope': 'Categories describe spelling shape, not proof that every omission is an implicit BREAK derivation. The finite profile intentionally does not synthesize hyphen joins or terminal-dot variants.',
            'rejected_forms': rejected}


def main() -> None:
    report = json.loads((ROOT/'reports/finite-expansion.json').read_text(encoding='utf-8'))
    report.append(english_forms())
    for item in report:
        if item['language'] in {'ru', 'es'}:
            item.update(remaining_diagnostics(item['language']))
        for key in ['canonical_keys', 'surface_forms']:
            words = (ROOT/item[key]['path']).read_text(encoding='utf-8').splitlines()
            if words != sorted(set(words)) or any(not 0<len(word)<=32 or
                    unicodedata.normalize('NFC', word) != word or any(c.isspace() for c in word) for word in words):
                raise ValueError('Output violates canonical form invariants')
    finite_logs = [ROOT/'reports/finite-expansion.log', ROOT/'reports/finite-expansion-repeat.log']
    previous = [[json.loads(line.split(' ', 1)[1]) for line in p.read_text(encoding='utf-8').splitlines()
                 if line.startswith(('ru {', 'es {'))] for p in finite_logs]
    repeat_ok = len(previous[0]) == len(previous[1]) == 2 and all(
        a['canonical_keys']['sha256'] == b['canonical_keys']['sha256'] and
        a['surface_forms']['sha256'] == b['surface_forms']['sha256']
        for a,b in zip(previous[0],previous[1]))
    manifest = {'schema': 1, 'status': 'FROZEN_SOURCE_PIPELINE_NOT_RUNTIME_QUALIFICATION',
                'normalization': 'NFC -> RU/EN/ES Unicode lowercase -> NFC; sorted Unicode codepoints (same order as UTF-8 bytes); LF; unique keys; original-case NFC surfaces retained separately; no accent stripping, no yo/e collapse, no NFKC/casefold',
                'languages': sorted(report, key=lambda item:item['language']),
                'frequency': [frequency_component(lang) for lang in ['ru', 'en', 'es']],
                'notices': copy_notices(), 'finite_repeat_identical': repeat_ok,
                'source_lock': file_record(ROOT/'source-lock.json'),
                'transformation_sources': [file_record(path) for path in [PACKAGE/'pipeline.py', *sorted((PACKAGE/'scripts').iterdir())] if path.suffix in {'.py','.cxx'}]}
    (ROOT/'reports/archive-members.json').write_text(json.dumps(archive_inventory(), indent=2)+'\n', encoding='utf-8')
    (ROOT/'output-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if not repeat_ok:
        raise ValueError('Finite expansion reproducibility has not been established')
    for item in manifest['languages']:
        print(item['language'], item['canonical_keys'])


if __name__ == '__main__':
    main()
