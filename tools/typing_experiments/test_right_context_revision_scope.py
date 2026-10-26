import copy
from types import SimpleNamespace
import unittest
from right_context_revision_scope import RightContextRevisionScope


def tag(pos='ADJS', number='sing', lemma='готовый', case=None, gender=None):
    return SimpleNamespace(pos=pos,number=number,lemma=lemma,case=case,gender=gender)


class Dictionary:
    def __init__(self):self.words={'готов':[tag()],'готовы':[tag(number='plur')],
        'будут':[tag(pos='VERB',number='plur')], 'он':[tag(pos='NPRO',case='nomn')]}
    def analyses(self,word):return self.words.get(word,())


class ScopeTest(unittest.TestCase):
    def setUp(self):
        self.dictionary=Dictionary();self.ids={'готов':10,'готовы':10}
        self.scope=RightContextRevisionScope(self.dictionary,self.ids)
        self.args=dict(right_context=' будут ',original='готв',previous='готов',proposed='готовы',
            generation=dict(original='готв',isValidWord=False,protectedReason=None),
            joint_search=dict(completion='COMPLETE',alternatives=[dict(text=w,language='ru',unitDistance=1) for w in ['готов','готовы']]),
            previous_admitted=True,admission={'готовы':True})
    def refusal(self,**changes):return self.scope.refusal(**(self.args|changes))

    def test_completed_number_conflict_same_lemma_and_independent_certificates(self):
        self.assertIsNone(self.refusal())
        self.assertEqual('NO_COMPLETED_RIGHT_NUMBER_CONFLICT',self.refusal(right_context=' будут'))
        self.assertEqual('NO_COMPLETED_RIGHT_NUMBER_CONFLICT',self.refusal(right_context=''))
        self.assertEqual('CONTRADICTORY_RIGHT_NUMBER_CUE',self.refusal(right_context=' будут он '))

    def test_a_number_match_cannot_override_an_explicit_gender_conflict(self):
        self.dictionary.words['готов']=[tag(gender='masc')]
        self.dictionary.words['было']=[tag(pos='VERB',gender='neut')]
        self.dictionary.words['будет']=[tag(pos='VERB')]
        self.dictionary.words['она']=[tag(pos='NPRO',case='nomn',gender='femn')]
        for context in [' было ', ' будет она ']:
            self.assertEqual('CONTRADICTORY_RIGHT_GENDER_CUE',self.refusal(
                right_context=context,previous='готовы',proposed='готов',admission={'готов':True}))

    def test_no_acquisition_or_revival_of_an_unadmitted_replacement(self):
        for admitted in [False,None,1]:
            self.assertEqual('NO_ADMITTED_PREVIOUS_REPLACEMENT',self.refusal(previous_admitted=admitted))
        self.assertEqual('NO_ADMITTED_PREVIOUS_REPLACEMENT',self.refusal(previous='готв'))
        self.assertEqual('UNCHANGED',self.refusal(proposed='готов'))
        self.assertEqual('NO_RETRIEVED_REVISION',self.refusal(proposed='неизвестно'))

    def test_known_protected_and_missing_original_evidence_refuse(self):
        for changes,reason in [({'isValidWord':True},'ORIGINAL_PROTECTED'),({'protectedReason':'IDENTIFIER'},'ORIGINAL_PROTECTED'),({'original':'другое'},'MISSING_ORIGINAL_EVIDENCE')]:
            self.assertEqual(reason,self.refusal(generation=self.args['generation']|changes))
        self.dictionary.words['готв']=[tag(pos='NOUN')]
        self.assertEqual('ORIGINAL_PROTECTED',self.refusal())

    def test_pool_completion_language_distance_bounds_and_previous_presence(self):
        pool=self.args['joint_search']
        self.assertEqual('SEARCH_INCOMPLETE',self.refusal(joint_search=pool|{'completion':'CANCELLED'}))
        for key,value in [('language','en'),('unitDistance',4),('unitDistance',True)]:
            bad=copy.deepcopy(pool);bad['alternatives'][0][key]=value
            self.assertEqual('INVALID_RETRIEVED_POOL',self.refusal(joint_search=bad))
        self.assertEqual('NO_RETRIEVED_PREVIOUS',self.refusal(joint_search=pool|{'alternatives':pool['alternatives'][1:]}))
        self.assertEqual('NO_RETRIEVED_PREVIOUS',self.refusal(joint_search=pool|{'alternatives':pool['alternatives']*2}))

    def test_source_admission_is_explicit_and_never_borrowed_from_the_previous_word(self):
        self.assertEqual('MISSING_PROPOSAL_ADMISSION',self.refusal(admission={'готов':True}))
        self.assertEqual('MISSING_PROPOSAL_ADMISSION',self.refusal(admission={'готовы':1}))
        self.assertEqual('PROPOSAL_ADMISSION_REFUSED',self.refusal(admission={'готовы':False}))

    def test_every_dictionary_analysis_and_both_packed_lemma_ids_must_agree(self):
        for word,reason in [('готов','PREVIOUS_NOT_UNAMBIGUOUS_SHORT_PREDICATE'),('готовы','PROPOSAL_NOT_UNAMBIGUOUS_SHORT_PREDICATE')]:
            self.dictionary.words[word].append(tag(pos='ADVB'))
            self.assertEqual(reason,self.refusal())
            self.dictionary.words[word].pop()
        self.dictionary.words['готовы']=[tag(number='plur',lemma='другой')]
        self.assertEqual('DIFFERENT_DICTIONARY_LEMMA',self.refusal())
        self.dictionary.words['готовы']=[tag(number='plur')]
        for word in ['готов','готовы']:
            for value in [None,0,-1,True]:
                self.ids[word]=value
                self.assertEqual('PACKED_LEMMA_UNAVAILABLE',self.refusal())
            self.ids[word]=10
        self.ids['готовы']=20
        self.assertEqual('DIFFERENT_PACKED_LEMMA',self.refusal())


if __name__ == '__main__':unittest.main()
