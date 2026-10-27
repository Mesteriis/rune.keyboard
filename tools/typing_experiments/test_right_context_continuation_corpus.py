import copy
from types import SimpleNamespace
import unittest

from right_context_continuation_corpus import generate
from right_context_training_groups import query


class Dictionary:
    def analyses(self, word):
        if word in {'вежлив', 'вежливы'}:
            return (SimpleNamespace(pos='ADJS', number='plur' if word.endswith('ы') else 'sing', gender=None if word.endswith('ы') else 'masc'),)
        return ()


def parent(**changes):
    return dict(id='authored-one', purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train',
                language='ru', family='вежливый', kind='unknown_original',
                original='вежлв', applied='вежлв', expectedApplied='вежлив',
                candidateForms=['вежлив', 'вежливы'], leftContext='', rightContext=' он ',
                scenario='right_pronoun') | changes


class ContinuationCorpusTest(unittest.TestCase):
    def test_early_nominal_waits_then_same_word_count_closure_can_supply_a_target(self):
        rows = generate([parent()], Dictionary())
        selected = [r for r in rows if r['scenario'] == 'nominal_wait_then_closure']
        self.assertEqual([' он ', ' он .'], [r['rightContext'] for r in selected])
        self.assertEqual(['вежлв', 'вежлив'], [r['expectedApplied'] for r in selected])
        self.assertEqual(['insufficient_right_evidence', 'unknown_original'], [r['kind'] for r in selected])
        self.assertEqual(query(selected[0]), query(selected[1]))

    def test_new_copula_and_list_require_their_actual_typed_boundary(self):
        rows = generate([parent()], Dictionary())
        copula = [r for r in rows if r['scenario'] == 'nominal_wait_then_copula']
        self.assertEqual(['вежлв', 'вежлив'], [r['expectedApplied'] for r in copula])
        listed = [r for r in rows if r['scenario'] == 'additive_wait_then_closure']
        self.assertTrue(all(r['expectedApplied'] == 'вежлв' for r in listed[:-1]))
        self.assertEqual('вежливы', listed[-1]['expectedApplied'])
        self.assertTrue(listed[-1]['rightContext'].endswith('.'))

    def test_left_plural_copula_is_a_distinct_label_blind_query(self):
        rows = generate([parent()], Dictionary())
        selected = [r for r in rows if r['scenario'] == 'additive_left_plural_copula']
        self.assertTrue(selected)
        self.assertTrue(all(r['leftContext'] == 'были ' and r['expectedApplied'] == 'вежливы' for r in selected))
        self.assertNotEqual(query(parent()), query(selected[0]))

    def test_finite_alternative_and_unanchored_reciprocal_do_not_invent_a_role(self):
        rows = generate([parent()], Dictionary())
        for scenario in ('nominal_then_finite_unresolved', 'alternative_role_unresolved',
                         'reciprocal_without_left_subject_unresolved'):
            selected = [r for r in rows if r['scenario'] == scenario]
            self.assertTrue(selected)
            self.assertTrue(all(r['expectedApplied'] == r['applied'] for r in selected))

    def test_correct_original_stays_protected_even_under_a_plural_context(self):
        rows = generate([parent(kind='correct_original', original='вежлив', applied='вежлив')], Dictionary())
        self.assertTrue(rows)
        self.assertTrue(all(r['original'] == r['applied'] == r['expectedApplied'] for r in rows))
        self.assertTrue(all(r['kind'] == 'correct_original' for r in rows))

    def test_source_rows_are_immutable_and_unrelated_old_training_is_preserved(self):
        source = parent(); before = copy.deepcopy(source)
        rows = generate([source], Dictionary())
        self.assertEqual(before, source)
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        old = parent(scenario='plural_copula', rightContext=' будут ')
        self.assertEqual([old], generate([old], Dictionary()))

    def test_natural_and_changed_parent_schemas_are_rejected(self):
        for changes in ({'split': 'calibration'}, {'purpose': 'NATURAL_PUBLIC_CONTEXT'},
                        {'kind': 'other'}, {'leftContext': 'другое '}, {'rightContext': ' он работает '}):
            with self.assertRaises(ValueError):
                generate([parent(**changes)], Dictionary())


if __name__ == '__main__':
    unittest.main()
