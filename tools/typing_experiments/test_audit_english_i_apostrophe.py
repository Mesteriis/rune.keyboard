import copy
import json
import unittest

import audit_english_i_apostrophe as audit
import screen_english_i_source as source


class EnglishIApostropheAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = source.SOURCE.read_bytes()
        cls.review = json.loads(audit.REVIEW.read_text())

    def test_complete_review_matches_pinned_source(self):
        self.assertEqual({'internal_apostrophe_preserve': 3,
                          'internal_apostrophe_preserve_other_admitted_punctuation': 1,
                          'internal_apostrophe_preserve_period': 1,
                          'internal_apostrophe_preserve_space': 1,
                          'opening_quote_pronoun': 5,
                          'opening_quote_pronoun_space': 5}, audit.audit(self.data, self.review))

    def test_refuses_missing_duplicate_and_mislabeled_cases(self):
        for kind in ('missing', 'duplicate', 'mislabeled'):
            review = copy.deepcopy(self.review)
            if kind == 'missing': review['rows'].pop()
            elif kind == 'duplicate': review['rows'].append(copy.deepcopy(review['rows'][0]))
            else: review['rows'][0]['label'] = 'internal_apostrophe_preserve'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                audit.audit(self.data, review)

    def test_rejects_source_mutation(self):
        with self.assertRaisesRegex(ValueError, 'EN_I_SOURCE_DIGEST'):
            audit.audit(self.data + b'changed', self.review)


if __name__ == '__main__':
    unittest.main()
