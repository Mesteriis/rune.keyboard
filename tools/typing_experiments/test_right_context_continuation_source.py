import copy
from types import SimpleNamespace
import unittest

from right_context_continuation_source import ContinuationSourceScope
from right_context_source_scope import RightContextSourceScope


def tag(pos='ADJS', number='sing', gender='masc', case=None, lemma='готовый'):
    return SimpleNamespace(pos=pos, number=number, gender=gender, case=case, lemma=lemma)


class Dictionary:
    def __init__(self):
        self.words = {
            'готов': (tag(),), 'готова': (tag(gender='femn'),),
            'готовы': (tag(number='plur', gender=None),),
            'покупка': (tag('NOUN', gender='femn', case='nomn', lemma='покупка'),),
            'продажа': (tag('NOUN', gender='femn', case='nomn', lemma='продажа'),),
            'он': (tag('NPRO', case='nomn', lemma='он'),),
            'будут': (tag('VERB', number='plur', gender=None),),
            'были': (tag('VERB', number='plur', gender=None),),
            'была': (tag('VERB', gender='femn'),),
            'друг': (tag('NOUN', case='nomn', lemma='друг'),),
            'другу': (tag('NOUN', case='datv', lemma='друг'),),
            'позволяет': (tag('VERB'),),
            'и': (tag('CONJ'), tag('NOUN', case='nomn')),
            'или': (tag('CONJ'),),
        }

    def analyses(self, word):
        return self.words.get(word, ())


class ContinuationSourceTest(unittest.TestCase):
    def setUp(self):
        self.lexicon = Dictionary()
        self.source = ContinuationSourceScope(self.lexicon)
        self.legacy = RightContextSourceScope(self.lexicon)
        self.args = dict(right_context=' будут ', original='готв', previous='готв', proposed='готовы',
            generation=dict(original='готв', isValidWord=False, protectedReason=None),
            joint_search=dict(completion='COMPLETE', alternatives=[dict(text=w, language='ru', unitDistance=1,
                editCost=1., kind='SPELLING', isFallback=False) for w in ('готов', 'готова', 'готовы')]),
            previous_owned=True, original_selected=False, external_veto_allowed=True,
            compared_words=['готв', 'готов', 'готова', 'готовы'],
            certificates={w: dict(publicOriginalAllowed=True, publicOriginalRefusal=None,
                originalMorphologyAvailable=True, originalMorphologyPresent=False,
                targetMorphologyAvailable=True, targetMorphologyPresent=True, targetLemmaId=1)
                for w in ('готов', 'готова', 'готовы')})

    def refusal(self, left='', **changes):
        return self.source.refusal(left_context=left, **(self.args | changes))

    def test_left_plural_copula_overrides_first_singular_subject_not_protection(self):
        args = self.args | dict(right_context=' покупка ')
        self.assertEqual('CONTRADICTORY_RIGHT_NUMBER_CUE', self.legacy.refusal(**args))
        self.assertIsNone(self.source.refusal(left_context='были ', **args))
        self.assertEqual('CONTRADICTORY_FINITE_COPULA_NUMBER', self.refusal('были ', right_context=' покупка ', proposed='готова'))
        self.assertEqual('CONTRADICTORY_FINITE_COPULA_GENDER', self.refusal('была ', right_context=' он ', proposed='готов'))
        self.assertEqual('NOMINAL_CONTINUATION_INCOMPLETE', self.refusal('были, ', right_context=' покупка '))

    def test_right_and_postsubject_copulas_supply_independent_agreement(self):
        for suffix in (' будут покупка ', ' покупка будут '):
            self.assertIsNone(self.refusal(right_context=suffix))
        self.assertEqual('CONTRADICTORY_FINITE_COPULA_NUMBER', self.refusal('была '))
        self.assertEqual('CONTRADICTORY_FINITE_COPULA_NUMBER', self.refusal(right_context=' покупка была '))

    def test_nominal_only_waits_until_observed_closure(self):
        for suffix in (' покупка ', ' покупка', ' покупка прода'):
            self.assertIsNotNone(self.refusal(right_context=suffix, proposed='готова'))
        self.assertIsNone(self.refusal(right_context=' покупка .', proposed='готова'))
        self.assertEqual('CONTRADICTORY_RIGHT_GENDER_CUE', self.refusal(right_context=' покупка .', proposed='готов'))

    def test_closed_lists_allow_possible_patterns_without_forcing_plural(self):
        for suffix in (' покупка и продажа.', ' покупка, продажа.', ' покупка или продажа.'):
            self.assertIsNone(self.refusal(right_context=suffix))
            self.assertIsNone(self.refusal(right_context=suffix, proposed='готова'))
        for suffix in (' покупка,', ' покупка и '):
            self.assertEqual('NOMINAL_LINK_INCOMPLETE', self.refusal(right_context=suffix))

    def test_reciprocal_and_non_copula_finite_roles_are_not_singular_subject_proof(self):
        for suffix in (' друг ', ' друг другу.'):
            self.assertEqual('RECIPROCAL_ROLE_UNRESOLVED', self.refusal(right_context=suffix))
            self.assertIsNone(self.refusal('были ', right_context=suffix))
        self.assertEqual('FOLLOWING_FINITE_ROLE_UNRESOLVED', self.refusal(right_context=' он позволяет ', proposed='готов'))
        self.assertIsNone(self.refusal(right_context=' покупка была .', proposed='готова'))
        self.assertEqual('CONTRADICTORY_RIGHT_GENDER_CUE', self.refusal(right_context=' он была .', proposed='готова'))

    def test_identifier_and_window_boundaries_cannot_become_clause_closure(self):
        for suffix in (' будут _тест ', ' будут ' + 'я' * 130 + ' ', ' будут ' + 'он ' * 9):
            self.assertEqual('CONTINUATION_BOUNDARY_UNPROVEN', self.refusal(right_context=suffix))
        self.assertEqual('NO_COMPLETED_RIGHT_CUE', self.refusal(right_context=' и '))

    def test_every_common_veto_still_matches_the_legacy_source(self):
        variants = [dict(previous_owned=False), dict(original_selected=True), dict(original_selected=None),
                    dict(external_veto_allowed=False), dict(compared_words=['готв', 'готовы']),
                    dict(certificates={}), dict(proposed='готв'),
                    dict(generation=self.args['generation'] | {'isValidWord': True}),
                    dict(joint_search=self.args['joint_search'] | {'completion': 'STATES_EXHAUSTED'})]
        for key, value in (('kind', 'COMMON_CONFUSION'), ('editCost', float('nan')), ('isFallback', True)):
            pool = copy.deepcopy(self.args['joint_search'])
            pool['alternatives'][-1][key] = value
            variants.append(dict(joint_search=pool))
        for changes in variants:
            arguments = self.args | changes
            expected = self.legacy.refusal(**arguments)
            self.assertIsNotNone(expected)
            self.assertEqual(expected, self.source.refusal(left_context='были ', **arguments))

    def test_morphology_certificates_and_ambiguous_targets_are_not_overridden(self):
        for field, value in (('publicOriginalAllowed', False), ('originalMorphologyPresent', True),
                             ('targetMorphologyPresent', False), ('targetLemmaId', 0),
                             ('originalMorphologyAvailable', False), ('targetMorphologyAvailable', False)):
            certificates = copy.deepcopy(self.args['certificates'])
            certificates['готовы'][field] = value
            arguments = self.args | dict(certificates=certificates, right_context=' покупка ')
            self.assertEqual(self.legacy.refusal(**arguments), self.source.refusal(left_context='были ', **arguments))
        self.lexicon.words['готовы'] += (tag('ADVB'),)
        self.assertEqual('PROPOSAL_NOT_UNAMBIGUOUS_SHORT_PREDICATE', self.refusal('были ', right_context=' покупка '))

    def test_pre_scoring_gate_preserves_common_vetoes_and_defers_only_without_a_cue(self):
        keys = ('right_context', 'original', 'previous', 'generation', 'joint_search', 'previous_owned', 'original_selected')
        args = {key: self.args[key] for key in keys}
        self.assertIsNone(self.source.precondition_refusal(left_context='были ', **(args | dict(right_context=' покупка '))))
        self.assertEqual('NOMINAL_CONTINUATION_INCOMPLETE', self.source.precondition_refusal(left_context='', **(args | dict(right_context=' покупка '))))
        for changes in (dict(previous_owned=False), dict(original_selected=True),
                        dict(generation=self.args['generation'] | {'isValidWord': True}),
                        dict(joint_search=self.args['joint_search'] | {'completion': 'STATES_EXHAUSTED'})):
            altered = args | changes
            self.assertEqual(self.legacy.precondition_refusal(**altered),
                             self.source.precondition_refusal(left_context='были ', **altered))


if __name__ == '__main__':
    unittest.main()
