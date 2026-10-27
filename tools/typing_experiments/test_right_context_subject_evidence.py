from types import SimpleNamespace
import unittest
from right_context_grammar_features import FEATURE_NAMES,RightContextGrammarFeatures
from right_context_subject_evidence import ReliableRightContextGrammarFeatures,SubjectEvidenceLexicon
from right_context_source_scope import RightContextSourceScope


def tag(pos,case=None,number='sing',gender='neut'):
    return SimpleNamespace(pos=pos,case=case,number=number,gender=gender,lemma='пример')


class Dictionary:
    def __init__(self):self.words={'и':[tag('CONJ'),tag('NOUN','nomn')],
        'в':[tag('PREP'),tag('NOUN','nomn')],'по':[tag('PREP'),tag('NOUN','nomn')],
        'же':[tag('PRCL'),tag('NOUN','nomn')],
        'модели':[tag('NOUN','nomn',number='plur'),tag('NOUN','datv')],
        'она':[tag('NPRO','nomn',gender='femn')],
        'будут':[tag('VERB',number='plur',gender=None)],
        'готовы':[tag('ADJS',number='plur',gender=None)]}
    def analyses(self,word):return self.words.get(word,())


class SubjectEvidenceTest(unittest.TestCase):
    def test_function_homographs_cannot_supply_a_subject_but_dictionary_stays_unchanged(self):
        lex=Dictionary();safe=ReliableRightContextGrammarFeatures(lex);legacy=RightContextGrammarFeatures(lex)
        for word in ['и','в','по','же']:
            raw=lex.analyses(word);before=tuple(raw)
            old=dict(zip(FEATURE_NAMES,legacy.extract(' '+word+' ','готовы')))
            new=dict(zip(FEATURE_NAMES,safe.extract(' '+word+' ','готовы')))
            self.assertEqual(1,old['right_subject_available']);self.assertEqual(0,new['right_subject_available'])
            self.assertEqual(before,tuple(lex.analyses(word)))
            self.assertTrue(any(a.pos in {'PREP','CONJ','PRCL'} for a in SubjectEvidenceLexicon(lex).analyses(word)))

    def test_ordinary_case_ambiguity_and_pronouns_are_preserved(self):
        lex=Dictionary();safe=ReliableRightContextGrammarFeatures(lex);old=RightContextGrammarFeatures(lex)
        for suffix in [' модели ',' она ',' будут ',' будут она ']:
            self.assertEqual(old.extract(suffix,'готовы'),safe.extract(suffix,'готовы'))

    def test_finite_copula_survives_but_a_later_function_word_adds_no_subject(self):
        v=dict(zip(FEATURE_NAMES,ReliableRightContextGrammarFeatures(Dictionary()).extract(' будут и ','готовы')))
        self.assertEqual(1,v['right_copula_available']);self.assertEqual(1,v['right_copula_number_supported'])
        self.assertEqual(0,v['right_subject_available'])

    def test_source_admission_refuses_the_function_word_without_invoking_a_model(self):
        scope=RightContextSourceScope(Dictionary())
        for suffix in [' и ',' в ',' по ',' же ']:
            reason=scope.precondition_refusal(right_context=suffix,original='готв',previous='готв',
                generation=dict(original='готв',isValidWord=False,protectedReason=None),
                joint_search=dict(completion='COMPLETE',alternatives=[dict(text='готовы',language='ru',unitDistance=1)]),
                previous_owned=True,original_selected=False)
            self.assertEqual('NO_COMPLETED_RIGHT_CUE',reason)


if __name__=='__main__':unittest.main()
