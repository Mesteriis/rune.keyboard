import copy
import unittest
from right_context_training_exclusion import exclude_training_contexts


def row(key,group,families):return dict(contextHash=key,group=group,families=families,family=families[0])


class TrainingExclusionTest(unittest.TestCase):
    def test_whole_context_and_controls_leave_even_when_only_rival_family_was_trained(self):
        rows=[row('one',g,['новый','обученный']) for g in ['typo','correct','protected','unfinished']]
        rows.append(row('two','typo',['независимый']));before=copy.deepcopy(rows)
        kept,audit=exclude_training_contexts(rows,['обученный'])
        self.assertEqual([rows[-1]],kept);self.assertEqual(4,audit['excludedRows'])
        self.assertEqual(1,audit['excludedContexts']);self.assertEqual(before,rows)

    def test_no_expected_target_or_prediction_affects_exclusion(self):
        rows=[row('one','typo',['независимый'])|dict(expectedSpelling='обученный',proposed='обученный')]
        self.assertEqual(rows,exclude_training_contexts(rows,['обученный'])[0])

    def test_missing_or_inconsistent_family_evidence_fails_closed(self):
        for invalid in [row('a','typo',['семья'])|dict(families=[]),row('a','typo',['семья'])|dict(family='другая'),
                        row('a','typo',['семья'])|dict(families=None)]:
            with self.assertRaises(ValueError):exclude_training_contexts([invalid],['обученный'])
        with self.assertRaises(ValueError):exclude_training_contexts([row('a','typo',['одна']),row('a','correct',['другая'])],['обученный'])
        with self.assertRaises(ValueError):exclude_training_contexts([],[])


if __name__=='__main__':unittest.main()
