from pathlib import Path
import unittest
from control_ledger import load


class PublicControlSnapshotTest(unittest.TestCase):
    def setUp(self):self.ledger=load(Path(__file__).with_name('control-ledger.json'))

    def test_all_punctuation_components_and_languages_are_persisted(self):
        entries=[e for e in self.ledger['entries'] if e['kind']=='punctuation']
        self.assertEqual(9,len(entries));self.assertEqual(3600,sum(e['rowCount'] for e in entries))
        self.assertEqual({'en','ru','es'},{e['language'] for e in entries})

    def test_known_ru_punctuation_identity_survives_without_original_corpora(self):
        keys={k for e in self.ledger['entries'] if e['kind']=='punctuation' for k in e['keys']}
        self.assertIn('42a780b228b43e70eb7ce7449434f545fbdc4fc7af1cb2b214e84b230401a618',keys)
        self.assertFalse(self.ledger['coverageComplete'])


if __name__=='__main__':unittest.main()
