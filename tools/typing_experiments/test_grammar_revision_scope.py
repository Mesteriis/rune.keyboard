from types import SimpleNamespace
import unittest

from grammar_revision_scope import InfinitiveRevisionScope, revision_candidate


def tag(lemma, pos, **extra):
    return SimpleNamespace(**dict(dict(lemma=lemma, pos=pos, number=None, gender=None,
                                      person=None, case=None), **extra))


class Dictionary:
    def __init__(self):
        self.words = {
            'надо': [tag('надо', 'PRED')], 'хочу': [tag('хотеть', 'VERB')],
            'начал': [tag('начать', 'VERB')],
            'тебе': [tag('ты', 'NPRO', case='datv')],
            'учиться': [tag('учиться', 'INFN')],
            'учишься': [tag('учиться', 'VERB', number='sing', person='2per')],
            'трудиться': [tag('трудиться', 'INFN')],
        }

    def analyses(self, word):
        return self.words.get(word.casefold(), ())


class GrammarRevisionScopeTest(unittest.TestCase):
    def setUp(self):
        self.lexicon = Dictionary()
        self.scope = InfinitiveRevisionScope(self.lexicon)

    def test_same_lemma_finite_to_infinitive_only_with_preceding_cue(self):
        for context in ('тебе надо ', 'я хочу ', 'он начал немного ', 'я хочу тебе '):
            self.assertIsNone(self.scope.refusal(context, 'учишься', 'учиться'))
        for context in ('ты ', 'надо, ', 'надо. ты ', 'надо\nты ', 'он начал книгу '):
            self.assertEqual(self.scope.refusal(context, 'учишься', 'учиться'), 'NO_INFINITIVE_CUE')

    def test_ambiguous_dictionary_analyses_and_different_lemma_do_not_expand_scope(self):
        self.assertEqual(self.scope.refusal('надо ', 'учишься', 'трудиться'), 'DIFFERENT_LEMMA')
        self.lexicon.words['учишься'].append(tag('другое', 'NOUN'))
        self.assertEqual(self.scope.refusal('надо ', 'учишься', 'учиться'), 'PREVIOUS_NOT_UNAMBIGUOUS_FINITE')
        self.lexicon.words['учишься'].pop()
        self.lexicon.words['учиться'].append(tag('другое', 'NOUN'))
        self.assertEqual(self.scope.refusal('надо ', 'учишься', 'учиться'), 'PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE')

    def test_original_protection_and_admission_are_required_independently_of_grammar(self):
        arguments = dict(context='надо ', original='учищься', previous='учишься', proposed='учиться',
                         generation=dict(isValidWord=False, protectedReason=None),
                         joint_search=dict(completion='COMPLETE', alternatives=[dict(text='учиться')]),
                         admission={'учиться': True})
        self.assertIsNone(revision_candidate(self.scope, **arguments))
        for change, reason in [
            (dict(generation={}), 'MISSING_SOURCE_EVIDENCE'),
            (dict(generation=dict(isValidWord=True, protectedReason=None)), 'ORIGINAL_PROTECTED'),
            (dict(generation=dict(isValidWord=False, protectedReason='URL')), 'ORIGINAL_PROTECTED'),
            (dict(admission={'учиться': False}), 'SOURCE_ADMISSION_REFUSED'),
            (dict(joint_search=dict(completion='PARTIAL')), 'SEARCH_INCOMPLETE'),
            (dict(joint_search=dict(completion='COMPLETE', alternatives=[])), 'NO_RETRIEVED_REVISION'),
            (dict(previous='учищься'), 'NO_RETRIEVED_REVISION'),
        ]:
            self.assertEqual(revision_candidate(self.scope, **dict(arguments, **change)), reason)

    def test_no_candidate_or_context_is_read_from_a_label(self):
        self.assertEqual(self.scope.refusal('надо ', 'учишься', 'незнакомое'), 'PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE')
        self.assertEqual(self.scope.refusal('надо ', 'учишься', 'учишься'), 'UNCHANGED')
        self.assertEqual(self.scope.refusal('надо ', 'незнакомое', 'учиться'), 'PREVIOUS_NOT_UNAMBIGUOUS_FINITE')


if __name__ == '__main__':
    unittest.main()
