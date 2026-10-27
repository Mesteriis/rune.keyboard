from types import SimpleNamespace
import copy
import unittest
from right_context_source_scope import RightContextSourceScope


def tag(pos='ADJS', number='sing', gender='masc', case=None, lemma='готовый'):
    return SimpleNamespace(pos=pos,number=number,gender=gender,case=case,lemma=lemma)


class Dictionary:
    def __init__(self):self.words={'готов':[tag()],'готовы':[tag(number='plur',gender=None)],
         'будут':[tag(pos='VERB',number='plur',gender=None)],'было':[tag(pos='VERB',gender='neut')],
         'они':[tag(pos='NPRO',number='plur',gender=None,case='nomn')]}
    def analyses(self,word):return self.words.get(word,())


class SourceScopeTest(unittest.TestCase):
    def setUp(self):
        self.dictionary=Dictionary();self.scope=RightContextSourceScope(self.dictionary)
        self.args=dict(right_context=' будут ',original='готв',previous='готв',proposed='готовы',previous_owned=True,original_selected=False,external_veto_allowed=True,
             generation=dict(original='готв',isValidWord=False,protectedReason=None),
             joint_search=dict(completion='COMPLETE',alternatives=[dict(text=w,language='ru',unitDistance=1,
                  editCost=1.0,kind='SPELLING',isFallback=False) for w in ['готов','готовы']]),
             compared_words=['готв','готов','готовы'],certificates={'готовы':dict(publicOriginalAllowed=True,
                  originalMorphologyAvailable=True,originalMorphologyPresent=False,targetMorphologyAvailable=True,
                  targetMorphologyPresent=True,targetLemmaId=10)})
    def refusal(self,**changes):return self.scope.refusal(**(self.args|changes))

    def test_raw_acquisition_and_existing_word_reconsideration_have_the_same_independent_source(self):
        self.assertIsNone(self.refusal())
        self.assertIsNone(self.refusal(previous='готов'))
        self.assertIsNone(self.refusal(right_context=' они '))
        self.assertEqual('UNCHANGED',self.refusal(proposed='готв'))
        self.assertEqual('ORIGINAL_PREFERRED',self.refusal(previous='готов',proposed='готв'))

    def test_no_future_unfinished_word_or_unproven_ownership_is_accepted(self):
        for suffix in ['', ' будут', ' они', ' будут_тест ', ', будут ']:
            self.assertEqual('NO_COMPLETED_RIGHT_CUE',self.refusal(right_context=suffix))
        for value in [False,None,1]:
            self.assertEqual('PREVIOUS_OWNERSHIP_UNPROVEN',self.refusal(previous_owned=value))
        self.assertEqual('INVALID_WORD_INPUT',self.refusal(original='готв_тест'))
        self.assertEqual('EXPLICIT_ORIGINAL_CHOICE',self.refusal(original_selected=True))
        self.assertEqual('ORIGINAL_CHOICE_UNPROVEN',self.refusal(original_selected=None))
        for value in [False,None,1]:
            self.assertEqual('EXTERNAL_VETO_OR_UNAVAILABLE',self.refusal(external_veto_allowed=value))

    def test_main_dictionary_morphology_and_public_original_protection_all_remain_mandatory(self):
        self.assertEqual('ORIGINAL_PROTECTED',self.refusal(generation=self.args['generation']|{'isValidWord':True}))
        self.assertEqual('ORIGINAL_PROTECTED',self.refusal(generation=self.args['generation']|{'protectedReason':'URL'}))
        self.dictionary.words['готв']=[tag(pos='NOUN')]
        self.assertEqual('ORIGINAL_PROTECTED',self.refusal());self.dictionary.words.pop('готв')
        for key,value,reason in [('publicOriginalAllowed',False,'ORIGINAL_PROTECTED'),
            ('originalMorphologyPresent',True,'ORIGINAL_PROTECTED'),('originalMorphologyAvailable',False,'MORPHOLOGY_UNAVAILABLE'),
            ('targetMorphologyAvailable',False,'MORPHOLOGY_UNAVAILABLE'),('targetMorphologyPresent',False,'TARGET_NOT_UNAMBIGUOUSLY_KNOWN'),
            ('targetLemmaId',None,'TARGET_NOT_UNAMBIGUOUSLY_KNOWN'),('targetLemmaId',True,'TARGET_NOT_UNAMBIGUOUSLY_KNOWN')]:
            c=self.args['certificates']['готовы']|{key:value}
            self.assertEqual(reason,self.refusal(certificates={'готовы':c}))
        self.assertEqual('MISSING_SOURCE_CERTIFICATE',self.refusal(certificates={}))
        self.assertEqual('INCONSISTENT_SOURCE_CERTIFICATE',self.refusal(certificates={'готовы':self.args['certificates']['готовы']|{'publicOriginalRefusal':'ORIGINAL_VALID'}}))

    def test_complete_comparison_cannot_drop_a_difficult_rival(self):
        self.assertEqual('INCOMPLETE_MODEL_COMPARISON',self.refusal(compared_words=['готв','готовы']))
        self.assertEqual('INCOMPLETE_MODEL_COMPARISON',self.refusal(compared_words=list(reversed(self.args['compared_words']))))
        self.assertEqual('SEARCH_INCOMPLETE',self.refusal(joint_search=self.args['joint_search']|{'completion':'STATES_EXHAUSTED'}))
        pool=copy.deepcopy(self.args['joint_search']);pool['alternatives']*=2
        self.assertEqual('INVALID_PREVIOUS_OR_POOL',self.refusal(joint_search=pool))

    def test_gender_conflict_and_homonymous_or_wrong_part_candidates_do_not_become_winners(self):
        self.assertEqual('CONTRADICTORY_RIGHT_NUMBER_CUE',self.refusal(right_context=' было '))
        self.dictionary.words['готовы']=[tag(number='sing',gender='masc')]
        self.assertEqual('CONTRADICTORY_RIGHT_GENDER_CUE',self.refusal(right_context=' было '))
        self.dictionary.words['готовы'].append(tag(pos='ADVB'))
        self.assertEqual('PROPOSAL_NOT_UNAMBIGUOUS_SHORT_PREDICATE',self.refusal())

    def test_candidate_cost_language_and_kind_are_not_borrowed_from_another_source(self):
        for key,value in [('kind','COMMON_CONFUSION'),('isFallback',True),('editCost',float('nan'))]:
            pool=copy.deepcopy(self.args['joint_search']);pool['alternatives'][1][key]=value
            self.assertEqual('INVALID_PROPOSAL_METADATA',self.refusal(joint_search=pool))
        pool=copy.deepcopy(self.args['joint_search']);pool['alternatives'][1]['language']='en'
        self.assertEqual('INVALID_RETRIEVED_POOL',self.refusal(joint_search=pool))


if __name__ == '__main__':unittest.main()
