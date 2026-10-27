import copy
from types import SimpleNamespace
import unittest
from holdout_ledger import keys_for
from import_natural_context_history import verify_article,entries_for
from recover_legacy_holdout import load_generator
from right_context_sentence_audit import _source_hash


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')] if word in ('готов','готовы') else []


def row(**changes):
    return dict(word='готовы',rival='готов',typed='готвоы',prefix='Они',rightContext=' были дома.',article='123',
        contextHash=_source_hash('Они','готовы',' были дома.'),selectionHash='a'*64)|changes


class NaturalHistoryTest(unittest.TestCase):
    def test_source_prefix_word_and_suffix_must_match_the_actual_article(self):
        generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
        verify_article('Они готовы были дома.',[row()],generator)
        with self.assertRaisesRegex(ValueError,'SOURCE_CAPTURE'):verify_article('Они готовы ушли.',[row()],generator)
        with self.assertRaisesRegex(ValueError,'WINDOW_IDENTITY'):verify_article('Они готовы были дома.',[row(contextHash='0'*64)],generator)

    def test_source_article_window_context_and_both_candidate_families_are_excluded(self):
        original=[row()];before=copy.deepcopy(original)
        entries,counts=entries_for('fixture',original,Dictionary(),{'file':'b'*64})
        self.assertEqual(before,original);self.assertEqual([],entries[0]['missingAxes'])
        self.assertEqual(keys_for([dict(families=['готовый'])],'family'),set(entries[0]['keys']['family']))
        self.assertEqual(1,counts['rows']);self.assertEqual([],counts['unresolvedCandidateAnalyses'])

    def test_unknown_rival_is_not_guessed_and_keeps_family_coverage_incomplete(self):
        entries,counts=entries_for('fixture',[row(rival='нераспознано')],Dictionary(),{'file':'b'*64})
        self.assertEqual(['family'],entries[0]['missingAxes']);self.assertEqual('historical-family-exclusion',entries[1]['usage'])
        self.assertEqual('rival',counts['unresolvedCandidateAnalyses'][0]['field'])

    def test_empty_and_duplicate_pool_identities_fail(self):
        for rows in ([],[row(),row()]):
            with self.assertRaises(ValueError):entries_for('fixture',rows,Dictionary(),{'file':'b'*64})


if __name__=='__main__':unittest.main()
