import copy
import unittest

from right_context_surface_source import SurfaceAwareContinuationSource, nominal_surface_refusal
import test_right_context_continuation_source as fixtures


class SurfaceSourceTest(unittest.TestCase):
    def setUp(self):
        parent = fixtures.ContinuationSourceTest()
        parent.setUp()
        self.lexicon, self.args = parent.lexicon, parent.args
        self.lexicon.words.update({
            'н': (fixtures.tag('NOUN', gender='femn', case='nomn', lemma='эн'),),
            'я': (fixtures.tag('NPRO', gender=None, case='nomn', lemma='я'),),
            'нина': (fixtures.tag('NOUN', gender='femn', case='nomn', lemma='нина'),),
            'сми': (fixtures.tag('NOUN', number='plur', gender=None, case='nomn', lemma='сми'),),
        })
        self.source = SurfaceAwareContinuationSource(self.lexicon)

    def test_initial_dot_is_not_a_completed_nominal_subject(self):
        for suffix in (' Н.', ' н.', ' Н .', ' Н. Иванов '):
            args = self.args | dict(right_context=suffix, proposed='готова')
            self.assertIsNone(self.source.previous.refusal(left_context='', **args))
            self.assertEqual('SINGLE_LETTER_NOMINAL_UNPROVEN', self.source.refusal(left_context='', **args))

    def test_genuine_pronouns_names_and_acronyms_keep_their_readings(self):
        for suffix, proposed in [(' Я.', 'готов'), (' я.', 'готов'), (' Нина.', 'готова'), (' СМИ.', 'готовы')]:
            self.assertIsNone(self.source.refusal(left_context='', **(self.args | dict(right_context=suffix, proposed=proposed))))

    def test_unfinished_and_identifier_text_does_not_manufacture_a_letter(self):
        for suffix in (' Н', ' Н_тест ', ' Н-test ', 'Н.'):
            self.assertIsNone(nominal_surface_refusal(suffix, self.lexicon))
        self.assertEqual('SINGLE_LETTER_NOMINAL_UNPROVEN', nominal_surface_refusal(' Н ', self.lexicon))

    def test_common_vetoes_keep_priority_over_the_surface_guard(self):
        for changes in (dict(previous_owned=False), dict(original_selected=True), dict(certificates={}),
                        dict(external_veto_allowed=False), dict(generation=self.args['generation'] | {'isValidWord': True})):
            args = self.args | dict(right_context=' Н.', proposed='готова') | changes
            self.assertEqual(self.source.previous.refusal(left_context='', **args), self.source.refusal(left_context='', **args))

    def test_pre_scoring_gate_blocks_initial_and_preserves_input(self):
        keys = ('right_context', 'original', 'previous', 'generation', 'joint_search', 'previous_owned', 'original_selected')
        args = {key: self.args[key] for key in keys} | dict(right_context=' Н.')
        before = copy.deepcopy(args)
        self.assertEqual('SINGLE_LETTER_NOMINAL_UNPROVEN', self.source.precondition_refusal(left_context='', **args))
        self.assertEqual(before, args)
        self.assertIsNone(self.source.precondition_refusal(left_context='были ', **(args | dict(right_context=' покупка '))))


if __name__ == '__main__':
    unittest.main()
