import copy
from types import SimpleNamespace
import unittest

from right_context_modal_source import ModalCopulaSource, modal_copula_cue
import test_right_context_continuation_source as fixtures


def modal(number='sing', gender='neut', lemma='мочь', tense='past', pos='VERB'):
    return SimpleNamespace(pos=pos, lemma=lemma, number=number, gender=gender, tense=tense)


class ModalSourceTest(unittest.TestCase):
    def setUp(self):
        parent = fixtures.ContinuationSourceTest(); parent.setUp()
        self.lexicon = parent.lexicon
        self.lexicon.words.update({
            'могло': (modal(),), 'могла': (modal(gender='femn'),),
            'могли': (modal('plur', None),), 'смогла': (modal(gender='femn', lemma='смочь'),),
            'быть': (modal(lemma='быть', pos='INFN', tense=None, gender=None),),
            'может': (modal(gender=None, tense='pres'),),
            'попросило': (modal(lemma='попросить'),),
        })
        self.args = parent.args | dict(previous='готв', proposed='готова', right_context=' покупка.')
        self.source = ModalCopulaSource(self.lexicon)

    def test_new_veto_only_blocks_contradictory_gender_or_number(self):
        self.assertIsNone(self.source.previous.refusal(left_context='могло быть ', **self.args))
        self.assertEqual('CONTRADICTORY_MODAL_COPULA_GENDER', self.source.refusal(left_context='могло быть ', **self.args))
        self.assertIsNone(self.source.refusal(left_context='могла быть ', **self.args))
        self.assertIsNone(self.source.refusal(left_context='смогла быть ', **self.args))
        args = self.args | dict(proposed='готовы', right_context=' будут ')
        self.assertEqual('CONTRADICTORY_MODAL_COPULA_NUMBER', self.source.refusal(left_context='могло быть ', **args))
        self.assertIsNone(self.source.refusal(left_context='могли быть ', **args))
        self.lexicon.words['готово'] = (fixtures.tag(gender='neut'),)
        self.lexicon.words['было'] = (fixtures.tag('VERB', gender='neut'),)
        args = copy.deepcopy(self.args)
        args['joint_search']['alternatives'].append(dict(text='готово', language='ru', unitDistance=1,
            editCost=1., kind='SPELLING', isFallback=False))
        args['compared_words'].append('готово')
        args['certificates']['готово'] = copy.deepcopy(args['certificates']['готов'])
        args.update(proposed='готово', right_context=' было ')
        self.assertIsNone(self.source.refusal(left_context='могло быть ', **args))

    def test_completed_adjacent_chain_only_no_punctuation_or_identifier_laundering(self):
        valid = ('могло быть ', 'ОН МОГЛО\tБЫТЬ\t', 'другая фраза. могло быть ')
        for left in valid:
            self.assertTrue(modal_copula_cue(left, self.lexicon), left)
        invalid = ('могло быть', 'могло быть, ', 'могло, быть ', 'могло. быть ',
                   'могло\nбыть ', 'могло не быть ', 'могло очень быть ',
                   'x_могло быть ', 'xмогло быть ', 'могло_быть ',
                   'могло быть и ', 'может быть ', 'попросило быть ')
        for left in invalid:
            self.assertFalse(modal_copula_cue(left, self.lexicon), left)
        chain = 'могло быть ' + ' ' * (128 - len('могло быть '))
        self.assertFalse(modal_copula_cue('x_' + chain, self.lexicon))
        self.assertFalse(modal_copula_cue('могло ' + ' ' * 128 + 'быть ', self.lexicon))

    def test_ambiguous_or_missing_dictionary_readings_cannot_create_a_universal_conflict(self):
        self.lexicon.words['могло'] += (modal(gender='femn'),)
        self.assertIsNone(self.source.refusal(left_context='могло быть ', **self.args))
        self.lexicon.words['могло'] = (modal(gender=None),)
        self.assertIsNone(self.source.refusal(left_context='могло быть ', **self.args))
        for tags in ((), (modal(pos='NOUN'),), (modal(tense=None),), (modal(number=None),)):
            self.lexicon.words['могло'] = tags
            self.assertFalse(modal_copula_cue('могло быть ', self.lexicon))
        self.lexicon.words['могло'] = (modal(),)
        self.lexicon.words['быть'] += (modal(pos='NOUN'),)
        self.assertFalse(modal_copula_cue('могло быть ', self.lexicon))

    def test_every_prior_veto_and_pre_scoring_decision_has_priority(self):
        for changes in (dict(previous_owned=False), dict(certificates={}), dict(external_veto_allowed=False),
                        dict(original_selected=True), dict(compared_words=['готв']),
                        dict(proposed='готв'), dict(right_context=' будут ')):
            args = self.args | changes
            expected = self.source.previous.refusal(left_context='могло быть ', **args)
            self.assertIsNotNone(expected)
            self.assertEqual(expected, self.source.refusal(left_context='могло быть ', **args))
        keys = ('right_context', 'original', 'previous', 'generation', 'joint_search', 'previous_owned', 'original_selected')
        args = {key: copy.deepcopy(self.args[key]) for key in keys}
        self.assertEqual(self.source.previous.precondition_refusal(left_context='могло быть ', **args),
                         self.source.precondition_refusal(left_context='могло быть ', **args))


if __name__ == '__main__':
    unittest.main()
