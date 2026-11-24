from pathlib import Path
import tempfile
import unittest
from unittest import mock

import import_taiga_context_exposure as subject


class TaigaContextExposureTest(unittest.TestCase):
    def test_capture_preserves_original_and_casefolded_source_contexts(self):
        parent = {'id': subject.taiga.ENTRY, 'rowCount': 1, 'keys': {'sentence': ['s']}}
        with mock.patch.object(subject.taiga, 'sentence_keys', return_value=(['s'], 1)), \
             mock.patch.object(subject.lexical, 'load_ledger', return_value={'entries': [parent]}):
            result = subject.source_keys('# text = По Москве\n'.encode())
        self.assertEqual(2, result['tokenOccurrences'])
        self.assertEqual(4, result['variants'])
        original = dict(language='ru', prefix='По ', typed='Москве', expectedSpelling='Москве')
        folded = dict(language='ru', prefix='по ', typed='москве', expectedSpelling='москве')
        for row in (original, folded):
            self.assertIn(subject.control.key_for(row, 'regression'), result['controlKeys'])
            self.assertTrue(subject.lexical.keys_for([row], 'context') <= set(result['contextKeys']))

    def test_corrupt_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.json'
            path.write_bytes(subject.FIXTURE.read_bytes() + b' ')
            with mock.patch.object(subject, 'FIXTURE', path), self.assertRaisesRegex(ValueError, 'TAIGA_CONTEXT_FIXTURE'):
                subject.fixture()

    def test_new_source_context_is_blocked_by_both_registries(self):
        row = dict(language='ru', prefix='Крещенская ', typed='вода', expectedSpelling='вода')
        controls = subject.control.load(subject.CONTROL)
        ledger = subject.lexical.load_ledger(subject.LEXICAL)
        prior_controls = dict(controls, entries=[e for e in controls['entries'] if e['id'] != subject.ENTRY])
        prior_ledger = dict(ledger, entries=[e for e in ledger['entries'] if e['id'] != subject.ENTRY + '-lexical'])
        prior_contexts = {key for entry in prior_controls['entries']
                          if entry['kind'] == 'regression' for key in entry['keys']}
        self.assertNotIn(subject.control.key_for(row, 'regression'), prior_contexts)
        # The word itself is now covered by a separate historical surface entry.
        # With the Taiga context removed, the surface guard still refuses it.
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            subject.control.assert_disjoint([row], prior_controls, 'regression')
        subject.lexical.assert_disjoint([row], prior_ledger, kinds=('context',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP'):
            subject.control.assert_disjoint([row], controls, 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([row], ledger, kinds=('context',), require_complete=False)


if __name__ == '__main__':
    unittest.main()
