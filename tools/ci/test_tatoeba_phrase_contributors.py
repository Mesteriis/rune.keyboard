import json
import unittest

from tatoeba_phrase_contributors import account_groups


DATE = '2020-01-01 00:00:00'
OTHER_DATE = '2020-01-02 00:00:00'


def cc0(sentence):
    return f'{sentence}\trus\tслово\t{DATE}\n'


def detailed(sentence, owner='sample-account', text='слово', modified=DATE):
    return f'{sentence}\trus\t{text}\t{owner}\t{DATE}\t{modified}\n'


def outcomes(*flags):
    return [(f'chat-regression-{i}-control', flag) for i, flag in enumerate(flags, 1)]


class ContributorTest(unittest.TestCase):
    def test_grouping_counts_each_owner_once_and_never_exports_names(self):
        result = account_groups(
            outcomes(True, True, False, False),
            [cc0(i) for i in range(1, 5)],
            [detailed(1), detailed(2), detailed(3, 'other-account'), detailed(4)],
        )
        self.assertEqual(2, result['changedPhrases'])
        self.assertEqual(2, result['accounts'])
        self.assertEqual(1, result['accountsWithChangedPhrase'])
        self.assertEqual(3, result['largestAccountPhraseCount'])
        self.assertNotIn('-account', json.dumps(result))

    def test_match_requires_same_text_and_modification_date_and_named_owner(self):
        result = account_groups(
            outcomes(True, True, False, True, False),
            [cc0(i) for i in range(1, 6)],
            [detailed(1), detailed(2, text='другое'), detailed(3, modified=OTHER_DATE),
             detailed(4, owner=r'\N')],
        )
        self.assertEqual(1, result['phrasesWithAccount'])
        self.assertEqual(4, result['phrasesWithoutAccount'])
        self.assertEqual(2, result['changedPhrasesWithoutAccount'])
        self.assertEqual(1, result['detailedJoin']['differentText'])
        self.assertEqual(1, result['detailedJoin']['differentModificationTime'])
        self.assertEqual(1, result['detailedJoin']['missingOwner'])
        self.assertEqual(1, result['detailedJoin']['missingSentence'])

    def test_rejects_malformed_or_duplicated_identity(self):
        for phrases, source, detail in (
            (outcomes(True), [], [detailed(1)]),
            (outcomes(True) * 2, [cc0(1)], [detailed(1)]),
            (outcomes(True), [cc0(1)] * 2, [detailed(1)]),
            (outcomes(True), [cc0(1)], [detailed(1)] * 2),
            (outcomes(True), [cc0(1)], [detailed(1, owner=DATE)]),
        ):
            with self.subTest(phrases=phrases, source=source, detail=detail), self.assertRaises(ValueError):
                account_groups(phrases, source, detail)
