"""Deterministic contract tests; no downloaded dictionary required."""
import copy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from ranker import Decision, MorphAnalysis, PymorphyLexicon, decide


def candidate(word="шкафов", rank=100, cost=1.0, **changes):
    value = {"text": word, "canonicalKey": word.lower(), "terminalKey": word.lower(),
             "language": "ru", "isFallback": False, "frequencyRank": rank,
             "unitDistance": 1, "editCost": cost, "casePattern": "TITLE" if word.istitle() else "LOWER",
             "kind": "SPELLING"}
    value.update(changes)
    return value


def generation(*candidates, original="шкафоф"):
    items = list(candidates or [candidate()])
    return {"original": original, "completion": "COMPLETE", "isValidWord": False,
            "protectedReason": None, "prohibitsAutoReplace": False, "inspectedStates": 80,
            "verifiedTerminals": len(items), "alternatives": copy.deepcopy(items),
            "localSearch": {"completion": "COMPLETE", "inspectedStates": 60,
                            "verifiedTerminals": len(items), "alternatives": items}}


class Lexicon:
    def __init__(self, extra=None):
        self.entries = {
            "несколько": (MorphAnalysis("несколько", "NUMR"),),
            "шкафов": (MorphAnalysis("шкаф", "NOUN", "gent", "plur", "masc"),),
            "шкафом": (MorphAnalysis("шкаф", "NOUN", "ablt", "sing", "masc"),),
            "шкаф": (MorphAnalysis("шкаф", "NOUN", "nomn", "sing", "masc"),),
            "шкафе": (MorphAnalysis("шкаф", "NOUN", "loct", "sing", "masc"),),
            "с": (MorphAnalysis("с", "PREP"),), "в": (MorphAnalysis("в", "PREP"),),
            "новом": (MorphAnalysis("новый", "ADJF", "loct", "sing", "masc"),),
            "давай": (MorphAnalysis("давать", "VERB"),),
            "пойдём": (MorphAnalysis("пойти", "VERB", number="plur", person="1per"),)}
        self.entries.update(extra or {})

    def analyses(self, word):
        return self.entries.get(word.lower(), ())


class RankerTests(unittest.TestCase):
    def setUp(self):
        self.lexicon = Lexicon()

    def test_context_inflection_kept_and_numeric_cost_is_production_formula(self):
        result = decide(generation(), "несколько", self.lexicon)
        self.assertEqual(result.word, "шкафов")
        self.assertEqual(result.scores[0]["basePenalty"], 22)
        self.assertEqual(result.scores[0]["penalty"], 6)

    def test_no_context_no_analysis_no_evidence(self):
        for prefix in ("", "несколько.", "несколько, ", "несколько\n", "xнесколько"):
            with self.subTest(prefix=prefix):
                self.assertIsNone(decide(generation(), prefix, self.lexicon).word)
        self.assertIsNone(decide(generation(), "неизвестное", self.lexicon).word)
        self.assertIsNone(decide(generation(), "несколько", Lexicon({"шкафов": ()})).word)
        self.assertIsNone(decide(generation(), "несколько", Lexicon({"несколько": ()})).word)

    def test_no_cross_punctuation_or_nonadjective_gap(self):
        for prefix in ("в. новом", "в\nновом", "в, неизвестное", "несколько и"):
            self.assertIsNone(decide(generation(), prefix, self.lexicon).word)

    def test_ambiguous_prepositions_accept_multiple_cases(self):
        for word in ("шкафов", "шкафом"):
            result = decide(generation(candidate(word)), "с", self.lexicon)
            self.assertEqual(result.word, word)
            self.assertEqual(result.scores[0]["morphologyBonus"], 0.75)
        for case in ("accs", "loct"):
            lexicon = Lexicon({"шкафе": (MorphAnalysis("шкаф", "NOUN", case, "sing", "masc"),)})
            self.assertEqual(decide(generation(candidate("шкафе")), "в", lexicon).word, "шкафе")

    def test_all_analyses_are_considered(self):
        extra = {"шкафе": (MorphAnalysis("шкаф", "NOUN", "nomn", "sing", "masc"),
                           MorphAnalysis("шкаф", "NOUN", "loct", "sing", "masc"))}
        self.assertEqual(decide(generation(candidate("шкафе")), "в", Lexicon(extra)).word, "шкафе")

    def test_adjective_agreement_and_bounded_three_words(self):
        result = decide(generation(candidate("шкафе")), "мы говорим о новом", self.lexicon)
        self.assertEqual(result.word, "шкафе")
        self.assertEqual(result.scores[0]["morphologyBonus"], 0.75)
        self.assertEqual(decide(generation(candidate("шкафе")), "в новом", self.lexicon).scores[0]["morphologyBonus"], 1)

    def test_short_word_permitted_with_evidence_only(self):
        lexicon = Lexicon({"дней": (MorphAnalysis("день", "NOUN", "gent", "plur"),)})
        self.assertEqual(decide(generation(candidate("дней"), original="днец"), "несколько", lexicon).word, "дней")
        result = decide(generation(candidate("пойдём"), original="пойдемм"), "давай", self.lexicon)
        self.assertEqual(result.word, "пойдём")

    def test_competing_candidates_and_original_require_margin(self):
        result = decide(generation(candidate(), candidate("шкафом")), "несколько", self.lexicon)
        self.assertEqual(result.reason, "insufficient_margin")
        result = decide(generation(candidate(rank=2**30)), "несколько", self.lexicon)
        self.assertEqual(result.reason, "insufficient_margin")
        result = decide(generation(candidate(), candidate("шкафом", cost=4)), "несколько", self.lexicon)
        self.assertEqual(result.word, "шкафов")

    def test_protected_valid_and_canonical_case_unchanged(self):
        for changes in ({"isValidWord": True}, {"protectedReason": "URL"}, {"prohibitsAutoReplace": True}):
            row = generation()
            row.update(changes)
            self.assertIsNone(decide(row, "несколько", self.lexicon).word)
        self.assertIsNone(decide(generation(candidate(kind="CANONICAL_CASE")), "несколько", self.lexicon).word)

    def test_supported_title_case_only(self):
        result = decide(generation(candidate("Шкафов"), original="Шкафоф"), "несколько", self.lexicon)
        self.assertEqual(result.word, "Шкафов")
        for original in ("ШКАФОФ", "шКафоф", "abc", "x" * 33):
            self.assertIsNone(decide(generation(original=original), "несколько", self.lexicon).word)

    def test_incomplete_outer_allowed_only_with_complete_local(self):
        for completion in ("STATES_EXHAUSTED", "VERIFIED_EXHAUSTED"):
            row = generation()
            row.update(completion=completion, prohibitsAutoReplace=True)
            self.assertEqual(decide(row, "несколько", self.lexicon).word, "шкафов")
        for completion in ("STATES_EXHAUSTED", "UNKNOWN", "UNAVAILABLE"):
            row = generation()
            row["localSearch"]["completion"] = completion
            self.assertIsNone(decide(row, "несколько", self.lexicon).word)
        for completion in ("UNKNOWN", "CANCELLED", "UNAVAILABLE", "READER_FAILURE", []):
            row = generation()
            row.update(completion=completion, prohibitsAutoReplace=True)
            self.assertIsNone(decide(row, "несколько", self.lexicon).word)

    def test_bad_numeric_candidate_fields(self):
        for field, bad in (("editCost", float("nan")), ("editCost", float("inf")), ("editCost", 10**1000), ("editCost", 0.1),
                           ("editCost", True), ("frequencyRank", 0), ("frequencyRank", 1.0),
                           ("frequencyRank", True), ("unitDistance", 2), ("unitDistance", True),
                           ("repetitionBonus", float("nan")), ("lengthDifference", -1)):
            with self.subTest(field=field, bad=bad):
                self.assertIsNone(decide(generation(candidate(**{field: bad})), "несколько", self.lexicon).word)

    def test_bad_candidate_identity_and_unknown_fields(self):
        for changes in ({"language": "en"}, {"isFallback": True}, {"isFallback": 0},
                        {"canonicalKey": "wrong"}, {"terminalKey": "wrong"}, {"casePattern": "UPPER"},
                        {"expected": "label"}):
            self.assertIsNone(decide(generation(candidate(**changes)), "несколько", self.lexicon).word)
        row = generation()
        row["expected"] = "label"
        self.assertEqual(decide(row, "несколько", self.lexicon).reason, "invalid_generation")

    def test_duplicate_and_bounds(self):
        self.assertEqual(decide(generation(candidate(), candidate()), "несколько", self.lexicon).reason, "duplicate_candidate")
        for section in (None, "localSearch"):
            for key, bad in (("inspectedStates", 8193), ("verifiedTerminals", 65),
                             ("verifiedTerminals", 0), ("inspectedStates", True)):
                row = generation()
                (row if section is None else row[section])[key] = bad
                self.assertIsNone(decide(row, "несколько", self.lexicon).word)

    def test_style_can_supply_evidence_and_invalid_values_fail_closed(self):
        for invalid in (object(), {}, "private"):
            self.assertEqual(decide(generation(), "несколько", self.lexicon, style=invalid).reason, "invalid_style")
        style = Mock()
        style.bonus.return_value = 1.0
        result = decide(generation(), "неизвестное", self.lexicon, style=style)
        self.assertEqual(result.word, "шкафов")
        self.assertEqual(result.scores[0]["styleBonus"], 1)
        for bad in (float("nan"), float("inf"), 10**1000, -0.1, 1.1, True, "1", None):
            style.bonus.return_value = bad
            self.assertEqual(decide(generation(), "несколько", self.lexicon, style=style).reason, "invalid_style")
        style.bonus.side_effect = ValueError("private text")
        self.assertEqual(decide(generation(), "несколько", self.lexicon, style=style).reason, "invalid_style")

    def test_repr_redacts_and_analysis_is_immutable(self):
        analysis = MorphAnalysis("private", grammemes={"NOUN"})
        self.assertNotIn("private", repr(analysis))
        self.assertNotIn("private", repr(Decision("private", "example", ({"word": "private"},))))
        self.assertIsInstance(analysis.grammemes, frozenset)
        with self.assertRaises(FrozenInstanceError):
            analysis.lemma = "changed"


class LexiconTests(unittest.TestCase):
    def test_dictionary_only_ambiguity_and_lru(self):
        class Dictionary:
            pass

        def parsed(case, method):
            tag = SimpleNamespace(POS="NOUN", case=case, number="sing", gender="masc", tense=None,
                                  person=None, grammemes={"NOUN", case})
            return SimpleNamespace(methods_stack=((method, "redacted"),), tag=tag, normal_form="замок")

        lexicon = PymorphyLexicon(cache_size=1)
        lexicon._dictionary_type = Dictionary
        lexicon._analyzer = Mock()
        lexicon._analyzer.parse.return_value = [parsed("nomn", Dictionary()), parsed("accs", Dictionary()),
                                               parsed("gent", object())]
        analyses = lexicon.analyses("замок")
        self.assertEqual({a.case for a in analyses}, {"nomn", "accs"})
        self.assertEqual(lexicon.analyses("Замок"), analyses)
        self.assertEqual(lexicon._analyzer.parse.call_count, 1)
        lexicon.analyses("шкаф")
        self.assertEqual(len(lexicon._cache), 1)
        self.assertNotIn("шкаф", repr(lexicon))
        self.assertEqual(lexicon.analyses("a" * 33), ())

    def test_cache_bound(self):
        for bad in (0, 16385, True, 1.0):
            with self.assertRaisesRegex(ValueError, "INVALID_CACHE_SIZE"):
                PymorphyLexicon(bad)


if __name__ == "__main__":
    unittest.main()
