import copy
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import import_wiktionary_historical_exclusions as subject
from public_corpus_preparation_v1 import preflight
from source_identities import unsupported_surface_key
from test_public_corpus_preparation_v1 import candidate, controls


class HistoricalWiktionaryTest(unittest.TestCase):
    def test_capture_preserves_all_ambiguous_forms_and_yo(self):
        rows = [dict(word='ёлка', forms=[['ёлки\u0301', []], ['ёлке', []]]),
                dict(word='ёлкин', forms=[['ёлки', []], ['ёлкина', []]]),
                dict(word='стол', forms=[['стола', []]])]
        raw = lzma.compress(('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n').encode())
        parents = {'historical': {unsupported_surface_key('ёлки')}}
        with mock.patch.object(subject, 'SOURCE_SHA', subject.sha(raw)), \
             mock.patch.object(subject, 'SOURCE_BYTES', len(raw)), \
             mock.patch.object(subject, 'SOURCE_ENTRIES', len(rows)):
            result = subject.capture(raw, parents)
            self.assertEqual([['ёлка', 'ёлка'], ['ёлка', 'ёлке'], ['ёлка', 'ёлки'],
                              ['ёлкин', 'ёлки'], ['ёлкин', 'ёлкин'], ['ёлкин', 'ёлкина']], result['pairs'])
            self.assertEqual([['ёлка', 'ёлка'], ['ёлкин', 'ёлкин']], result['sourceTitles'])
            self.assertEqual({'historical': [unsupported_surface_key('ёлки')]}, result['matchesByParent'])
            with self.assertRaisesRegex(ValueError, 'WIKTIONARY_SOURCE_IDENTITY'):
                subject.capture(raw + b' ', parents)

    def test_fixture_and_parent_mutations_are_rejected(self):
        base = json.loads(subject.LEDGER.read_bytes())
        fixture = json.loads(subject.FIXTURE.read_bytes())
        changed = copy.deepcopy(fixture)
        changed['pairs'].pop()
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_FIXTURE'):
            subject.entry(base, changed)
        changed = copy.deepcopy(fixture)
        changed['sourceTitles'][0][1] = 'иное'
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_TITLES'):
            subject.entry(base, changed)
        changed = copy.deepcopy(base)
        parent = next(e for e in changed['entries'] if e['id'] == subject.previous.ENTRY)
        parent['notes'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_PARENT'):
            subject.entry(changed, fixture)
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / 'projection.json'
            altered.write_bytes(subject.TEXT_FIXTURE.read_bytes() + b' ')
            with mock.patch.object(subject, 'TEXT_FIXTURE', altered):
                with self.assertRaisesRegex(ValueError, 'WIKTIONARY_TEXT_FIXTURE'):
                    subject.parent_keys(base)

    def test_new_form_is_blocked_and_registry_remains_incomplete(self):
        current = json.loads(subject.LEDGER.read_bytes())
        registered = next(e for e in current['entries'] if e['id'] == subject.ENTRY)
        self.assertEqual(registered, subject.entry(current, json.loads(subject.FIXTURE.read_bytes())))
        before = copy.deepcopy(current)
        before['entries'] = [e for e in before['entries'] if e['id'] != subject.ENTRY]
        old = {k for e in before['entries'] for k in e.get('unsupportedSurfaceKeys', [])}
        form = next(f for _, f in json.loads(subject.FIXTURE.read_bytes())['pairs']
                    if unsupported_surface_key(f) not in old)
        row = candidate(typed=form, expectedSpelling=form)
        self.assertEqual(0, preflight([row], 'spelling', before, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertEqual(1, preflight([row], 'spelling', current, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertFalse(current['coverage']['complete'])

    def test_portable_check_without_build_or_source_dump(self):
        base = json.loads(subject.LEDGER.read_bytes())
        prior = next(e for e in base['entries'] if e['id'] == subject.previous.ENTRY)
        files = set(prior['bindings']) | {
            'tools/typing_experiments/import_wiktionary_historical_exclusions.py',
            'tools/typing_experiments/wiktionary-historical-exclusions-v1.json',
            'tools/typing_experiments/holdout-ledger.json',
            'tools/typing_experiments/conversation_split_checks.py',
            'tools/typing_experiments/wiktionary-historical-text-boundaries-v1.json',
            'tools/typing_experiments/audit_wiktionary_text_boundaries.py',
        }
        with tempfile.TemporaryDirectory(prefix='rune-wiktionary-portable-') as folder:
            root = Path(folder)
            for name in files:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(subject.ROOT / name, dest)
            script = root / 'tools/typing_experiments/import_wiktionary_historical_exclusions.py'
            result = subprocess.run([sys.executable, '-B', str(script), '--check'], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse((root / 'build').exists())
            self.assertEqual(15833, json.loads(result.stdout)['surfaces'])


if __name__ == '__main__':
    unittest.main()
