import unittest
from right_context_input_audit import classify_input_change


class InputAuditTest(unittest.TestCase):
    def test_reports_exact_case_and_spacing_without_modifying_input(self):
        for before,after,expected in [('мама дома','мама дома','UNCHANGED'),
             ('мама дома','Мама дома','CASE_ONLY'),('мама  дома','мама дома','WHITESPACE_RUNS_ONLY'),
             ('мама\nдома','Мама дома','CASE_AND_WHITESPACE_RUNS')]:
            self.assertEqual(expected,classify_input_change(before,after))

    def test_first_character_loss_and_word_substitution_are_content_changes(self):
        for before,after in [('зочу домой','очу домой'),('мама дома','мама дому'),
                             ('мама дома','мама дом'),('Straße','Strasse')]:
            self.assertEqual('CONTENT_CHANGED',classify_input_change(before,after))

    def test_word_merges_and_splits_are_not_disguised_as_whitespace_runs(self):
        for before,after in [('не много','немного'),('немного','не много'),('мой дом','мойдом')]:
            self.assertEqual('CONTENT_CHANGED',classify_input_change(before,after))

    def test_punctuation_changes_and_noncase_unicode_changes_are_not_accepted(self):
        for before,after in [('я дома.','я дома!'),('ёлка','елка'),('е\u0308лка','ёлка')]:
            self.assertEqual('CONTENT_CHANGED',classify_input_change(before,after))


if __name__ == '__main__':unittest.main()
