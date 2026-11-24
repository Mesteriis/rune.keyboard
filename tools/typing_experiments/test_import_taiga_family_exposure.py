import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import import_taiga_family_exposure as subject
from public_corpus_preparation_v1 import preflight
from test_public_corpus_preparation_v1 import candidate, controls
from source_identities import unsupported_surface_key


class FakeLexicon:
    def receipt(self):
        return {'packages': {'fixture': {'files': {'fixture.py': 'a' * 64}}}}

    def analyses(self, word):
        return [SimpleNamespace(lemma='слово'), SimpleNamespace(lemma='словить')] if word == 'слова' else []


class TaigaFamilyExposureTest(unittest.TestCase):
    def test_dictionary_identity_ignores_only_generated_record(self):
        receipt = {'packages': {'fixture': {'files': {'fixture.py': 'a' * 64, 'fixture.dist-info/RECORD': 'b' * 64}}}}
        changed = json.loads(json.dumps(receipt))
        changed['packages']['fixture']['files']['fixture.dist-info/RECORD'] = 'c' * 64
        self.assertEqual(subject.dictionary_identity(receipt), subject.dictionary_identity(changed))
        changed['packages']['fixture']['files']['fixture.py'] = 'd' * 64
        self.assertNotEqual(subject.dictionary_identity(receipt), subject.dictionary_identity(changed))

    def test_capture_keeps_all_analyses_and_exact_unknowns(self):
        parent = {'id': subject.taiga.ENTRY, 'rowCount': 1, 'keys': {'sentence': ['s']}}
        with mock.patch.object(subject.taiga, 'sentence_keys', return_value=(['s'], 1)), \
             mock.patch.object(subject.ledger, 'load_ledger', return_value={'entries': [parent]}):
            result = subject.capture('# text = Слова неизвестнослово СЛОВА\n'.encode(), FakeLexicon())
        self.assertEqual(2, result['eligibleSurfaces'])
        self.assertEqual(1, result['unknownSurfaces'])
        self.assertEqual(2, len(result['familyKeys']))
        self.assertEqual(2, len(result['exactSurfaceKeys']))
        self.assertIn(unsupported_surface_key('неизвестнослово'), result['exactSurfaceKeys'])

    def test_corrupt_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.json'
            path.write_bytes(subject.FIXTURE.read_bytes() + b' ')
            with mock.patch.object(subject, 'FIXTURE', path), self.assertRaisesRegex(ValueError, 'TAIGA_FAMILY_FIXTURE'):
                subject.fixture()

    def test_new_source_surface_is_blocked_by_real_preflight(self):
        raw = json.loads(subject.LEDGER.read_bytes())
        current = subject.ledger.validate_ledger(raw)
        entry = next(e for e in current['entries'] if e['id'] == subject.ENTRY)
        key = unsupported_surface_key('словами')
        self.assertIn(key, entry['unsupportedSurfaceKeys'])
        self.assertFalse(any(key in e.get('unsupportedSurfaceKeys', []) for e in current['entries'] if e['id'] != subject.ENTRY))
        result = preflight([candidate(typed='словами', expectedSpelling='словами')],
                           'spelling', current, controls(), 'new-families')
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['unsupportedTargetOverlaps'])


if __name__ == '__main__':
    unittest.main()
