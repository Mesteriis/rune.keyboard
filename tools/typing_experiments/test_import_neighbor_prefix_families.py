import unittest
from types import SimpleNamespace
import import_neighbor_prefix_families as subject


class FakeLexicon:
    def analyses(self, word):
        return [SimpleNamespace(lemma='слово'), SimpleNamespace(lemma='словить')] if word == 'слова' else []


class NeighborPrefixFamilyTest(unittest.TestCase):
    def test_prefixes_are_deduplicated_and_unknowns_quarantined(self):
        rows = [{'prefix': 'Слова неизвестно!'}, {'prefix': 'Слова неизвестно!'}]
        entry, counts = subject.make_entry(rows, {'id': subject.parent.ENTRY}, FakeLexicon(), {'source': '0' * 64}, '1' * 64)
        self.assertEqual(1, counts['prefixes'])
        self.assertEqual(2, counts['surfaces'])
        self.assertEqual(2, counts['familyKeys'])
        self.assertEqual(1, counts['unsupportedSurfaceKeys'])
        self.assertEqual([subject.parent.ENTRY], entry['parentEntries'])

    def test_invalid_source_or_parent_fails(self):
        for rows, parent in [([{'prefix': ''}], {'id': subject.parent.ENTRY}),
                             ([{'prefix': 'слова'}], {'id': 'wrong'}),
                             ([{'prefix': 'неизвестно'}], {'id': subject.parent.ENTRY})]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                subject.make_entry(rows, parent, FakeLexicon(), {'source': '0' * 64}, '1' * 64)


if __name__ == '__main__':
    unittest.main()
