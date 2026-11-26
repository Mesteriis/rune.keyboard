import unittest
from types import SimpleNamespace

import import_neighbor_history_families as subject


class FakeLexicon:
    def analyses(self, word):
        if word == 'слова':
            return [SimpleNamespace(lemma='слово'), SimpleNamespace(lemma='словить')]
        return []


class NeighborFamilyTest(unittest.TestCase):
    def test_all_dictionary_analyses_and_unknown_surfaces_are_retained(self):
        rows = [{'word': 'слова'}, {'word': 'слова'}, {'word': 'неизвестноеслово'}]
        entry, counts = subject.make_entry(rows, {'id': subject.parent.ENTRY}, FakeLexicon(), {'source': '0' * 64}, '1' * 64)
        self.assertEqual(2, counts['surfaces'])
        self.assertEqual(2, counts['familyKeys'])
        self.assertEqual(1, counts['unsupportedSurfaceKeys'])
        self.assertEqual([subject.parent.ENTRY], entry['parentEntries'])

    def test_unknown_only_and_invalid_or_wrong_parent_are_rejected(self):
        for rows, parent in [([{'word': 'unknown'}], {'id': subject.parent.ENTRY}),
                             ([{'word': 'слова'}], {'id': 'other'}),
                             ([{'word': 'неизвестноеслово'}], {'id': subject.parent.ENTRY})]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                subject.make_entry(rows, parent, FakeLexicon(), {'source': '0' * 64}, '1' * 64)


if __name__ == '__main__':
    unittest.main()
