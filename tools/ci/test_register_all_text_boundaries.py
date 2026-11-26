from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest import mock

import register_all_text_boundaries as subject
import historical_discovery


def load_tests(loader, tests, pattern):
    return historical_discovery.isolated_suite('test_register_all_text_boundaries', tests)


class AllTextBoundaryRegistrationTest(unittest.TestCase):
    def test_source_bound_rows_and_both_gates(self):
        rows, _, _ = subject.inputs()
        control, lexical = subject.entries()
        self.assertEqual(470, len(rows))
        self.assertEqual(258, len(control['surfaceKeys']))
        self.assertTrue(control['articleKeys'])
        self.assertTrue(lexical['keys']['context'])
        control_ledger = subject.control.load(subject.CONTROL)
        old_control = dict(control_ledger, entries=[e for e in control_ledger['entries'] if e['id'] != subject.ENTRY])
        old_surfaces = {key for entry in old_control['entries'] for key in entry.get('surfaceKeys', [])}
        candidate = next(row for row in rows if subject.control.surface_key('ru', row['typed']) not in old_surfaces)
        with self.assertRaisesRegex(ValueError, 'CONTROL_COVERAGE_INCOMPLETE'):
            subject.control.assert_disjoint([candidate | {'prefix': 'Иной контекст '}], old_control, 'regression')
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            subject.control.assert_disjoint([candidate | {'prefix': 'Иной контекст '}],
                                            subject.control.load(subject.CONTROL), 'regression')
        lexical_ledger = subject.lexical.load_ledger(subject.LEXICAL)
        old_lexical = dict(lexical_ledger, entries=[e for e in lexical_ledger['entries'] if e['id'] != subject.ENTRY + '-contexts'])
        old_contexts = {key for entry in old_lexical['entries'] for key in entry['keys'].get('context', [])}
        new_context = next(row for row in rows if not subject.lexical.keys_for([row], 'context') & old_contexts)
        subject.lexical.assert_disjoint([new_context], old_lexical, kinds=('context',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([new_context], lexical_ledger, kinds=('context',), require_complete=False)

    def test_modified_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            path = fixture / 'contexts.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'ALL_SOURCE_BINDING'):
                    subject.inputs()

    def test_rehashed_but_unrelated_token_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            path = fixture / 'contexts.jsonl'
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            rows[0]['typed'] = 'x' * len(rows[0]['typed'])
            rows[0]['expectedSpelling'] = rows[0]['typed']
            raw = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows).encode()
            path.write_bytes(raw)
            receipt_path = fixture / 'receipt.json'
            receipt = json.loads(receipt_path.read_bytes())
            receipt['contextsSha256'] = hashlib.sha256(raw).hexdigest()
            receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'ALL_SOURCE_RELATION'):
                    subject.inputs()


if __name__ == '__main__':
    unittest.main()
