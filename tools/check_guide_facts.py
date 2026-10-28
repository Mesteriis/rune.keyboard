#!/usr/bin/env python3
"""Check current guide facts against writer, feature registry and loaded assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'app/src/main/java/io/github/mesteriis/rune/keyboard/'
REGISTRY = BASE + 'settings/AdditionalFeature.kt'
MODELS = BASE + 'smarttyping/experiments/ExperimentModels.kt'
FROZEN = BASE + 'smarttyping/experiments/FrozenExperimentAssets.kt'
ENCODING = 'app/src/debug/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/DiagnosticsEncoding.kt'
ASSETS = 'app/src/main/assets/smarttyping/experiments/'
DOCS = ['docs/USER_GUIDE.ru.md', 'docs/DEBUG_DIAGNOSTICS.md']


def integer(source, name):
    match = re.search(r'const\s+val\s+' + re.escape(name) + r'\s*=\s*([0-9_]+)\s*(?://[^\n]*)?$', source, re.M)
    if not match:
        raise ValueError('UNREVIEWED_CONSTANT')
    return int(match[1].replace('_', ''))


def inspect(root=ROOT):
    errors = []
    try:
        guide = (root / DOCS[0]).read_text()
        debug = (root / DOCS[1]).read_text()
        registry = (root / REGISTRY).read_text()
        keys = re.findall(r'AdditionalFeature\(SettingsCodec\.(KEY_[A-Z_]+)', registry)
        if not keys or len(keys) != len(set(keys)):
            raise ValueError('UNREVIEWED_FEATURE_REGISTRY')
        counts = re.findall(r'все\s+\*{0,2}(\d+)\*{0,2}\s+дополнитель', guide)
        if not counts or any(int(n) != len(keys) for n in counts):
            errors.append('GUIDE_ADDITIONAL_FEATURE_COUNT')
        encoding = (root / ENCODING).read_text()
        schemas = re.findall(re.escape('\\"schema\\":') + r'(\d+)', encoding)
        if len(set(schemas)) != 1:
            raise ValueError('UNREVIEWED_WRITER_SCHEMA')
        schema = int(schemas[0])
        for name, text in zip(DOCS, [guide, debug]):
            markers = re.findall(r'<!-- Q2:diagnostics-schema=(\d+) -->', text)
            if markers != [str(schema)] or f'schema {schema}' not in text:
                errors.append('CURRENT_DIAGNOSTICS_SCHEMA ' + name)
        if f'schema 1–{schema}' not in guide or f'для schema 4–{schema}' not in guide or '`editorType`' not in guide:
            errors.append('GUIDE_DIAGNOSTICS_COMPATIBILITY')
        for name in ['WORD_CONTEXT', 'CONTEXTUAL_RANKER', 'INFINITIVE_REVISION', 'NOUN_CASE_REVISION']:
            if '`' + name + '`' not in debug:
                errors.append('DEBUG_CURRENT_SOURCE ' + name)
        models = (root / MODELS).read_text()
        frozen = (root / FROZEN).read_text()
        expected = {
            'ru-ranker.bin': (integer(frozen, 'RANK_BYTES'), '—'),
            'ru-ranking-context.bin': (integer(frozen, 'RANKING_CONTEXT_BYTES'), str(integer(models, 'RANKING_WINDOW'))),
            'ru-context.bin': (integer(frozen, 'CONTEXT_BYTES'), str(integer(models, 'WINDOW'))),
        }
        block = re.search(r'<!-- Q2:ExperimentAssets:begin -->(.*?)<!-- Q2:ExperimentAssets:end -->', guide, re.S)
        rows = re.findall(r'^\| [^\n|]+ \| `([^`]+)` \| (\d+) \| ([^|\n]+) \|$', block[1], re.M) if block else []
        if len(rows) != len(expected) or {name for name, _, _ in rows} != set(expected):
            errors.append('GUIDE_EXPERIMENT_ASSET_TABLE')
        for name, size, window in rows:
            if name not in expected or (int(size), window.strip()) != expected[name]:
                errors.append('GUIDE_EXPERIMENT_ASSET_FACT ' + name)
            elif (root / (ASSETS + name)).stat().st_size != int(size):
                errors.append('GUIDE_EXPERIMENT_ACTUAL_BYTES ' + name)
        index = (root / 'docs/acceptance/README.md').read_text()
        if '../plans/2026-10-27-review-completion.md' not in index:
            errors.append('ACCEPTANCE_INDEX_CURRENT_REVIEW')
    except (OSError, ValueError, IndexError):
        errors.append('UNREADABLE_OR_UNREVIEWED_GUIDE_SOURCE')
    return errors


if __name__ == '__main__':
    errors = inspect()
    print('\n'.join(errors) if errors else 'Guide source facts PASS: feature count, current diagnostics and separate ranking/tap resources')
    raise SystemExit(bool(errors))
