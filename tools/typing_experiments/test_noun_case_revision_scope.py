from types import SimpleNamespace
import unittest

from noun_case_revision_scope import NounCaseRevisionScope, revision_candidate


def tag(lemma, pos='NOUN', case=None, number='sing', **changes):
    return SimpleNamespace(**(dict(lemma=lemma, pos=pos, case=case, number=number,
                                  person=None, gender=None) | changes))


class Dictionary:
    def __init__(self):
        self.words = {'фотографией': [tag('фотография', case='ablt')],
                      'фотографию': [tag('фотография', case='accs')],
                      'показал': [tag('показать', pos='VERB')],
                      'мне': [tag('я', pos='NPRO', case='datv')],
                      'с': [tag('с', pos='PREP')],
                      'книгу': [tag('книга', case='accs')]}

    def analyses(self, word):
        return self.words.get(word, ())


class NounCaseRevisionScopeTest(unittest.TestCase):
    def test_dictionary_case_and_verb_cue_support_only_the_matching_revision(self):
        scope = NounCaseRevisionScope(Dictionary())
        self.assertIsNone(scope.refusal('том показал мне ', 'фотографией', 'фотографию'))
        self.assertEqual('NO_ACCUSATIVE_CUE', scope.refusal('рядом с ', 'фотографией', 'фотографию'))
        self.assertEqual('NO_ACCUSATIVE_CUE', scope.refusal('том ', 'фотографией', 'фотографию'))
        self.assertEqual('UNCHANGED', scope.refusal('том показал ', 'фотографией', 'фотографией'))
        self.assertEqual('DIFFERENT_OR_AMBIGUOUS_LEMMA', scope.refusal('том показал ', 'фотографией', 'книгу'))

    def test_mixed_case_number_pos_and_lemma_cannot_be_hidden_by_one_good_analysis(self):
        for word, analysis, reason in [
            ('фотографией', tag('фотография', case='datv'), 'PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL'),
            ('фотографией', tag('фотография', pos='ADJF', case='ablt'), 'PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL'),
            ('фотографией', tag('фотография', case='ablt', number='plur'), 'PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL'),
            ('фотографию', tag('фотография', case='nomn'), 'PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE'),
            ('фотографию', tag('другая', case='accs'), 'DIFFERENT_OR_AMBIGUOUS_LEMMA')]:
            dictionary = Dictionary(); dictionary.words[word].append(analysis)
            self.assertEqual(reason, NounCaseRevisionScope(dictionary).refusal('том показал ', 'фотографией', 'фотографию'))

    def test_revision_requires_complete_pool_actual_previous_and_source_admission(self):
        scope = NounCaseRevisionScope(Dictionary())
        args = dict(context='том показал мне ', original='фотографие', previous='фотографией',
                    proposed='фотографию', generation=dict(isValidWord=False, protectedReason=None),
                    joint_search=dict(completion='COMPLETE', alternatives=[dict(text='фотографией'), dict(text='фотографию')]),
                    admission={'фотографию': True})
        self.assertIsNone(revision_candidate(scope, **args))
        for change, reason in [
            (dict(generation={}), 'MISSING_SOURCE_EVIDENCE'),
            (dict(generation=dict(isValidWord=True, protectedReason=None)), 'ORIGINAL_PROTECTED'),
            (dict(generation=dict(isValidWord=False, protectedReason='MIXED_SCRIPT')), 'ORIGINAL_PROTECTED'),
            (dict(joint_search=dict(completion='CANCELLED', alternatives=args['joint_search']['alternatives'])), 'SEARCH_INCOMPLETE'),
            (dict(joint_search=dict(completion='COMPLETE', alternatives=[dict(text='фотографию')])), 'NO_RETRIEVED_REVISION'),
            (dict(joint_search=dict(completion='COMPLETE', alternatives=[dict(text='фотографией')])), 'NO_RETRIEVED_REVISION'),
            (dict(admission={'фотографию': False}), 'SOURCE_ADMISSION_REFUSED'),
            (dict(admission={}), 'MISSING_SOURCE_EVIDENCE'),
            (dict(previous='фотографие'), 'NO_RETRIEVED_REVISION'),
            (dict(original='фотографию'), 'ORIGINAL_PROTECTED')]:
            self.assertEqual(reason, revision_candidate(scope, **(args | change)))
        for pool in [[dict(text='фотографией'), dict(text='фотографию'), dict(text='фотографию')], ['bad']]:
            self.assertEqual('NO_RETRIEVED_REVISION', revision_candidate(scope, **(args | dict(joint_search=dict(completion='COMPLETE', alternatives=pool)))))


if __name__ == '__main__':
    unittest.main()
