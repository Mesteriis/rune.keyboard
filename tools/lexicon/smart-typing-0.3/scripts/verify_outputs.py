#!/usr/bin/env python3
"""Verify outputs against the immutable approved identities, never a newly accepted baseline."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from pipeline_config import PACKAGE, assert_record, build_root, load_frozen_manifest, load_lock, safe_path
from expand_affixes import read_rules

ROOT = build_root()


def verify_frozen(root: Path) -> int:
    load_lock()
    frozen = load_frozen_manifest()
    records = [frozen['source_lock']] + frozen['notices']
    for language in frozen['languages']:
        records += [language['canonical_keys'], language['surface_forms']]
    records += [component['data'] for component in frozen['frequency']]
    for record in records:
        assert_record(safe_path(root, record['path']), record)
    return len(records)


def main() -> None:
    count = verify_frozen(ROOT)
    subprocess.run([sys.executable, str(PACKAGE/'scripts/fetch_sources.py')], check=True)
    generated = json.loads((ROOT/'output-manifest.json').read_text())
    expected_paths = {'pipeline.py'} | {str(path.relative_to(PACKAGE)) for path in (PACKAGE/'scripts').iterdir() if path.suffix in {'.py', '.cxx'}}
    actual_paths = [record['path'] for record in generated['transformation_sources']]
    if set(actual_paths) != expected_paths or len(actual_paths) != len(expected_paths):
        raise ValueError('Transformation provenance is incomplete or duplicated')
    frozen = load_frozen_manifest()
    for component, fields in [('languages', ('canonical_keys', 'surface_forms')), ('frequency', ('data',))]:
        approved = {item['language']: item for item in frozen[component]}
        produced = {item['language']: item for item in generated[component]}
        if produced.keys() != approved.keys() or len(generated[component]) != len(approved):
            raise ValueError('Generated manifest language set differs from frozen identities')
        for language in approved:
            for field in fields:
                if produced[language][field] != approved[language][field]:
                    raise ValueError('Generated manifest output identity differs from frozen contract')
    for record in generated['transformation_sources']:
        if record.get('scope') != 'tool':
            raise ValueError('Transformation provenance must refer to package source, not cached scripts')
        assert_record(safe_path(PACKAGE, record['path']), record)
    if not generated['finite_repeat_identical']:
        raise ValueError('Finite expansion repeat has not been established')
    scowl = json.loads((ROOT/'reports/scowl-reproducibility.json').read_text())
    if not scowl['identical'] or scowl['first_sha256'] != '2d85306ee69f0b01925d703299efc67d4830aef72e990d816a0ab040d2fb55b2' or scowl['first_sha256'] != scowl['second_sha256']:
        raise ValueError('SCOWL must reproduce the frozen selection in two clean builds')
    es = ROOT/'sources/libreoffice/es/es_ES'
    flags = subprocess.run([str(ROOT/'bin/spell_oracle'), str(es)+'.aff', str(es)+'.dic', '--flags'],
                           input='GS\n☎️\nS🥇G\n', text=True, encoding='utf-8', capture_output=True, check=True).stdout
    if flags != '71\t71,83\tGS\n9742\t9742,65039\t☎️\n83\t83,65533\tS🥇G\n':
        raise ValueError('Pinned native Unicode flag semantics changed')
    with tempfile.TemporaryDirectory(dir=ROOT/'work') as directory:
        aff = Path(directory)/'unsupported.aff'
        aff.write_text('SET UTF-8\nCOMPOUNDRULE 1\n', encoding='utf-8')
        try:
            read_rules(aff, Path(directory)/'unused.dic', [], 'test')
        except ValueError as error:
            if 'Unsupported affix directives' not in str(error):
                raise
        else:
            raise ValueError('Unsupported lexical directive was silently accepted')
    print(f'PASS: {count} frozen output/notice/lock identities, current source provenance, native flag and profile guards')


if __name__ == '__main__':
    main()
