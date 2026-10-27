import copy
import unittest

from right_context_agreement_delta_source import AgreementDeltaSource
import test_right_context_continuation_source as fixtures


class AgreementDeltaTest(unittest.TestCase):
    def setUp(self):
        parent = fixtures.ContinuationSourceTest()
        parent.setUp()
        self.lexicon = parent.lexicon
        self.lexicon.words.update({
            'верен': (fixtures.tag(lemma='верный'),),
            'весел': (fixtures.tag(lemma='весёлый'),),
            'верны': (fixtures.tag(number='plur', gender=None, lemma='верный'),),
            'верный': (fixtures.tag('ADJF', lemma='верный', case='nomn'),),
            'ветер': (fixtures.tag('NOUN', lemma='ветер', case='nomn'),),
            'был': (fixtures.tag('VERB'),),
        })
        words = ['верен', 'весел', 'верны', 'верный', 'ветер']
        self.args = parent.args | dict(original='верел', previous='верен', proposed='весел', right_context=' был ',
            generation=dict(original='верел', isValidWord=False, protectedReason=None),
            compared_words=['верел'] + words,
            joint_search=dict(completion='COMPLETE', alternatives=[dict(text=w, language='ru', unitDistance=2,
                editCost=2., kind='SPELLING', isFallback=False) for w in words]),
            certificates={w: copy.deepcopy(parent.args['certificates']['готов']) for w in words})
        self.source = AgreementDeltaSource(self.lexicon)

    def test_grammar_neutral_lemma_change_cannot_use_an_agreement_certificate(self):
        self.assertIsNone(self.source.previous.refusal(left_context='', **self.args))
        self.assertEqual('NO_NEW_AGREEMENT_FOR_LEMMA_CHANGE', self.source.refusal(left_context='', **self.args))

    def test_raw_acquisition_and_real_inflection_are_not_locked(self):
        for changes in (dict(previous='верел'), dict(previous='верны', proposed='верен')):
            self.assertIsNone(self.source.refusal(left_context='', **(self.args | changes)))

    def test_cross_lemma_with_different_agreement_and_cross_role_stay_available(self):
        for previous in ('верны', 'верный', 'ветер'):
            self.assertIsNone(self.source.refusal(left_context='', **(self.args | dict(previous=previous))))

    def test_shared_lemma_reading_is_not_erased_by_an_ambiguous_surface(self):
        self.lexicon.words['верен'] += (fixtures.tag(lemma='весёлый'),)
        self.assertIsNone(self.source.refusal(left_context='', **self.args))

    def test_common_vetoes_and_pre_scoring_identity_are_preserved(self):
        for changes in (dict(previous_owned=False), dict(certificates={}), dict(external_veto_allowed=False),
                        dict(original_selected=True), dict(compared_words=['верел', 'весел'])):
            args = self.args | changes
            self.assertEqual(self.source.previous.refusal(left_context='', **args),
                             self.source.refusal(left_context='', **args))
        keys = ('right_context', 'original', 'previous', 'generation', 'joint_search', 'previous_owned', 'original_selected')
        args = {key: self.args[key] for key in keys}
        self.assertEqual(self.source.previous.precondition_refusal(left_context='', **args),
                         self.source.precondition_refusal(left_context='', **args))


if __name__ == '__main__':
    unittest.main()
