from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest import mock

import register_shared_text_boundaries as subject
import historical_discovery


def load_tests(loader, tests, pattern):
    return historical_discovery.isolated_suite('test_register_shared_text_boundaries', tests)


class SharedTextBoundaryRegistrationTest(unittest.TestCase):
    def test_source_bound_rows_and_both_gates(self):
        rows, _, _ = subject.inputs()
        control, lexical = subject.entries()
        self.assertEqual(179, len(rows))
        self.assertEqual(97, len(control['surfaceKeys']))
        self.assertTrue(control['articleKeys'])
        self.assertTrue(lexical['keys']['context'])
        candidate = rows[0]
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            subject.control.assert_disjoint([candidate | {'prefix': 'Иной контекст '}],
                                            subject.control.load(subject.CONTROL), 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([candidate], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',), require_complete=False)

    def test_modified_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            path = fixture / 'contexts.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'SHARED_SOURCE_BINDING'):
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
                with self.assertRaisesRegex(ValueError, 'SHARED_SOURCE_RELATION'):
                    subject.inputs()


if __name__ == '__main__':
    unittest.main()
