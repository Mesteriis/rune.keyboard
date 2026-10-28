#!/usr/bin/env python3
"""Check explicit packaged numeric-asset NOTICE rows against exact review policy."""
import json
from pathlib import Path
import re

import fdroid_data_policy as data_policy

ROOT = Path(__file__).resolve().parents[1]
ASSETS = 'app/src/main/assets/smarttyping/experiments'
POLICY = 'fdroid/review-data-policy.json'


def declared_digest(data, filename):
    assets = data.get('assets')
    if isinstance(assets, dict) and isinstance(assets.get(filename), dict):
        return assets[filename].get('sha256')
    model = data.get('model')
    if isinstance(model, dict) and model.get('asset') == filename:
        return model.get('sha256')
    if filename == 'ru-neighbor-ranker.bin':
        return data.get('rankerSha256')
    if filename in {'ru-infinitive-revision-ranker.bin', 'ru-noun-case-ranker.bin'}:
        return data.get('modelSha256')
    return None


def inspect(root=ROOT):
    errors = []
    try:
        policy = data_policy.parse_policy((root / POLICY).read_bytes())
        # Reuse the authoritative path/digest/provenance/action/prefix-collision gate.
        data_policy.check(root, policy)
        selected = [e for e in policy['entries'] if e['path'].startswith(ASSETS + '/')
                    and Path(e['path']).suffix in {'.bin', '.gram', '.ctx'}]
        entries = {Path(e['path']).name: e for e in selected}
        if len(entries) != len(selected) or any(Path(e['path']).parent.as_posix() != ASSETS for e in selected):
            raise ValueError('UNREVIEWED_NUMERIC_LAYOUT')
        if not entries:
            raise ValueError('EMPTY_NUMERIC_ASSET_SET')
        notice = data_policy.relative_file(root, ASSETS + '/NOTICE.md').read_text()
        block = re.search(r'<!-- Q2:BinaryNotice:begin -->(.*?)<!-- Q2:BinaryNotice:end -->', notice, re.S)
        rows = re.findall(r'^\| `([^`]+)` \| ([^\n]+?) \| `([^`]+)` \|$', block[1], re.M) if block else []
        names = [name for name, _, _ in rows]
        if names != sorted(entries):
            errors.append('NUMERIC_NOTICE_INVENTORY')
        for name, attribution, provenance in rows:
            if name not in entries:
                continue
            entry = entries[name]
            if not attribution.strip() or provenance != Path(entry['provenance']).name:
                errors.append('NUMERIC_NOTICE_PROVENANCE ' + name)
            data = json.loads((root / entry['provenance']).read_text())
            if not isinstance(data, dict) or declared_digest(data, name) != entry['sha256']:
                errors.append('NUMERIC_NOTICE_DECLARED_DIGEST ' + name)
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        errors.append('UNREADABLE_OR_UNREVIEWED_NUMERIC_NOTICE')
    return errors


if __name__ == '__main__':
    errors = inspect()
    print('\n'.join(errors) if errors else 'Typing numeric-asset NOTICE and exact review policy PASS')
    raise SystemExit(bool(errors))
