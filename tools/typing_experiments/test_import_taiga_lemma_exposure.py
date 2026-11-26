import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import import_taiga_lemma_exposure as subject
from public_corpus_preparation_v1 import preflight
from test_public_corpus_preparation_v1 import candidate, controls
from source_identities import unsupported_surface_key


class FakeLexicon:
    def receipt(self):
        return {'packages': {'fixture': {'files': {'fixture.py': 'a' * 64}}}}

    def analyses(self, word):
        return [SimpleNamespace(lemma='слово'), SimpleNamespace(lemma='словить')] if word == 'слово' else []


class TaigaLemmaExposureTest(unittest.TestCase):
    def test_annotated_lemmas_and_all_dictionary_analyses_are_retained(self):
        parent = {'id': subject.taiga.ENTRY, 'rowCount': 1, 'keys': {'sentence': ['s']}}
        data = ('# text = Слова\n1\tСлова\tслово\tNOUN\t_\t_\t0\troot\t_\t_\n'
                '2\tUNK\tunknown\tX\t_\t_\t1\tdep\t_\t_\n').encode()
        with mock.patch.object(subject.taiga, 'sentence_keys', return_value=(['s'], 1)), \
             mock.patch.object(subject.ledger, 'load_ledger', return_value={'entries': [parent]}):
            result = subject.capture(data, FakeLexicon())
        self.assertEqual((2, 1, 1), (result['tokenRows'], result['eligibleRows'], result['unsupportedRows']))
        self.assertEqual(2, len(result['familyKeys']))
        self.assertEqual([unsupported_surface_key('слово')], result['exactSurfaceKeys'])

    def test_corrupt_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.json'
            path.write_bytes(subject.FIXTURE.read_bytes() + b' ')
            with mock.patch.object(subject, 'FIXTURE', path), self.assertRaisesRegex(ValueError, 'TAIGA_LEMMA_FIXTURE'):
                subject.fixture()

    def test_new_annotated_lemma_is_blocked_by_real_preflight(self):
        current = subject.ledger.validate_ledger(json.loads(subject.LEDGER.read_bytes()))
        entry = next(e for e in current['entries'] if e['id'] == subject.ENTRY)
        key = unsupported_surface_key('бежать')
        self.assertIn(key, entry['unsupportedSurfaceKeys'])
        self.assertFalse(any(key in e.get('unsupportedSurfaceKeys', []) for e in current['entries'] if e['id'] != subject.ENTRY))
        result = preflight([candidate(typed='бежать', expectedSpelling='бежать')], 'spelling', current, controls(), 'new-families')
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['unsupportedTargetOverlaps'])


if __name__ == '__main__':
    unittest.main()
