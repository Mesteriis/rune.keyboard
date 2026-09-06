import copy
import unittest

from original_applicability import annotate, classify


def fixture(word="word"):
    return {"split": "holdout", "mode": "ready",
            "input": {"id": "public-1", "language": "en", "prefix": "", "typed": "word"},
            "observation": {
                "stateBeforeCandidates": {"typedWord": word, "leadingBoundary": "",
                                          "composingText": word},
                "candidateView": {"candidates": [{"role": "ORIGINAL", "id": "original", "text": "word"}],
                                  "selectedCandidateId": None},
                "actualOriginal": word, "actualModelRequest": None, "requestToken": None,
                "autoEdit": None, "beforeBoundary": {"text": "word"},
                "afterBoundary": {"text": "word "}, "afterBackspace": {"text": "word"}}}


class ApplicabilityTest(unittest.TestCase):
    def test_owned_word_without_model_request_still_requires_original(self):
        row = fixture()
        self.assertEqual(("ownedWord", True), classify(row))
        row["observation"]["candidateView"]["candidates"] = []
        self.assertEqual(("ownedWord", False), classify(row))

    def test_wrong_or_duplicate_original_fails(self):
        row = fixture()
        row["observation"]["candidateView"]["candidates"][0]["text"] = "wrong"
        self.assertEqual(("ownedWord", False), classify(row))
        row = fixture()
        row["observation"]["candidateView"]["candidates"] *= 2
        self.assertEqual(("ownedWord", False), classify(row))

    def test_no_word_requires_no_stale_candidates_and_exact_text(self):
        for word in (None, ""):
            row = fixture(word)
            row["observation"]["candidateView"]["candidates"] = []
            self.assertEqual(("noWord", True), classify(row))
            for field in ("beforeBoundary", "afterBoundary", "afterBackspace"):
                broken = copy.deepcopy(row)
                broken["observation"][field]["text"] += "!"
                self.assertEqual(("noWord", False), classify(broken))
            row["observation"]["candidateView"]["candidates"] = fixture()["observation"]["candidateView"]["candidates"]
            self.assertEqual(("noWord", False), classify(row))

    def test_boundary_only_state_is_not_an_owned_word(self):
        row = fixture("")
        row["observation"]["candidateView"]["candidates"] = []
        row["observation"]["stateBeforeCandidates"].update(leadingBoundary=" .", composingText=" .")
        self.assertEqual(("noWord", True), classify(row))

    def test_duplicate_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ROW"):
            annotate([fixture(), fixture()])


if __name__ == "__main__":
    unittest.main()
