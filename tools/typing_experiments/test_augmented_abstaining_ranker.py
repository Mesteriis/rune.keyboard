import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("augmented_abstaining_ranker.py")
SPEC = importlib.util.spec_from_file_location("augmented_abstaining_ranker", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class FakeMorphology:
    def __init__(self, words):
        self.words = set(words)

    def contains(self, word):
        return word in self.words


class AugmentedAbstainingRankerTest(unittest.TestCase):
    def row(self, typed="кармн", language="ru"):
        return {"typed": typed, "language": language}

    def test_adds_public_membership_candidate(self):
        augmenter = MODULE.Augmenter(FakeMorphology({"карман"}), {"кармен"}, {"кармен": 3})
        alternatives = [{"text": "карман", "canonicalKey": "карман", "unitDistance": 1,
                         "frequencyRank": 7, "editCost": 1.0, "isFallback": False}]
        result = augmenter.apply(self.row(), alternatives)
        self.assertEqual(["карман", "кармен"], [item["text"] for item in result])

    def test_exact_source_membership_abstains_before_candidate_ranking(self):
        augmenter = MODULE.Augmenter(FakeMorphology(set()), {"сесил"}, {"сесил": 1})
        self.assertIsNone(augmenter.apply(self.row("сесил"), []))

    def test_non_russian_rows_are_unchanged(self):
        augmenter = MODULE.Augmenter(FakeMorphology(set()), set(), {})
        alternatives = [{"text": "word"}]
        self.assertIs(alternatives, augmenter.apply(self.row("wrd", "en"), alternatives))


if __name__ == "__main__":
    unittest.main()
