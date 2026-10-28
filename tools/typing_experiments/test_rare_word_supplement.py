import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("rare_word_supplement.py")
SPEC = importlib.util.spec_from_file_location("rare_word_supplement", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class RareWordSupplementTest(unittest.TestCase):
    def test_extracts_mid_sentence_capitalized_cyrillic_forms_only_once_per_article(self):
        text = (
            "Кармен вышла на сцену. Затем Кармен встретила Мигеля. "
            "Обычное слово и Сесил остались; HTML5 и Иван-Петров исключены."
        )
        self.assertEqual(
            ["кармен", "мигеля", "сесил"],
            list(MODULE.capitalized_forms(text)),
        )
        self.assertEqual(
            {"кармен", "мигеля", "сесил"},
            set(MODULE.capitalized_forms(text)),
        )

    def test_distance_one_variants_cover_disclosed_missing_targets(self):
        cases = {
            "кармн": "кармен",
            "миеля": "мигеля",
            "кароин": "каролин",
            "америкн": "американ",
        }
        for typed, expected in cases.items():
            with self.subTest(typed=typed):
                self.assertIn(expected, MODULE.one_edit_variants(typed))

    def test_supplement_and_dictionary_are_merged_without_original_or_duplicates(self):
        dictionary = {"кармен", "карман", "каролин"}
        supplement = {"кармен", "мигеля", "аполло"}
        self.assertEqual(
            ["карман", "кармен"],
            MODULE.membership_candidates("кармн", dictionary.__contains__, supplement),
        )
        self.assertEqual(
            ["мигеля"],
            MODULE.membership_candidates("миеля", dictionary.__contains__, supplement),
        )
        self.assertEqual([], MODULE.membership_candidates("аполло", dictionary.__contains__, supplement))

    def test_frequency_and_article_thresholds_reject_one_article_noise(self):
        totals = {"кармен": 4, "опечатка": 9, "редкое": 2}
        articles = {"кармен": 3, "опечатка": 1, "редкое": 2}
        self.assertEqual(
            ["кармен"],
            MODULE.select_words(totals, articles, minimum_occurrences=3, minimum_articles=2),
        )

    def test_augmented_records_keep_existing_order_and_add_bounded_feature_records(self):
        existing = [{"text": "карман", "canonicalKey": "карман", "unitDistance": 1,
                     "frequencyRank": 100, "editCost": 1.0, "isFallback": False}]
        supplement = {"кармен"}
        augmented = MODULE.augment_candidates(
            "кармн", existing, {"карман", "кармен"}.__contains__, supplement,
            {"кармен": 7},
        )
        self.assertEqual(["карман", "кармен"], [row["text"] for row in augmented])
        self.assertEqual(50_007, augmented[1]["frequencyRank"])
        self.assertEqual(1, augmented[1]["unitDistance"])
        self.assertEqual(1.0, augmented[1]["editCost"])
        self.assertFalse(augmented[1]["isFallback"])

    def test_exact_supplement_membership_protects_source_before_generation(self):
        self.assertIsNone(MODULE.augment_candidates(
            "сесил", [], set().__contains__, {"сесил"}, {"сесил": 1},
        ))


if __name__ == "__main__":
    unittest.main()
