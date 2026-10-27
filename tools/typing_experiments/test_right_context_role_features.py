from types import SimpleNamespace
import unittest
from right_context_role_features import FEATURES,FEATURE_NAMES,RightContextRoleFeatures,preceding_clause_words,role_revision_features
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_revision_features import revision_features


def tag(pos='NOUN',case='nomn',number='sing',gender='femn',tense=None):
    return SimpleNamespace(pos=pos,case=case,number=number,gender=gender,tense=tense)


class Dictionary:
    def __init__(self):
        self.words={'модели':[tag(number='plur'),tag(case='datv'),tag(case='gent')],
          'девочка':[tag()], 'она':[tag(pos='NPRO')],
          'будешь':[tag(pos='VERB',case=None,gender=None,tense='futr')],
          'была':[tag(pos='VERB',case=None,tense='past')],
          'пришла':[tag(pos='VERB',case=None,tense='past')],
          'готова':[tag(pos='ADJS',case=None)],
          'готов':[tag(pos='ADJS',case=None,gender='masc')]}
    def analyses(self,word):return self.words.get(word,())


class RoleFeaturesTest(unittest.TestCase):
    def test_new_layout_preserves_frozen_legacy_vector_and_checks_its_extension(self):
        lex=Dictionary();right=RightContextGrammarFeatures(lex);role=RightContextRoleFeatures(lex)
        args=([0.]*146,right,' будешь ','готва','готова')
        old=revision_features(*args)
        new=role_revision_features(args[0],right,role,'ты пришла, и теперь ',args[2],args[3],args[4])
        self.assertEqual(FEATURES,len(new));self.assertEqual(old,new[:len(old)])
        for bad in [(0.,),tuple([float('nan')]*len(FEATURE_NAMES))]:
            class Invalid:
                def extract(self,*args):return bad
            with self.assertRaises(ValueError):role_revision_features(args[0],right,Invalid(),'',args[2],args[3],args[4])

    def values(self,left='',right=' модели ',candidate='готова'):
        values=RightContextRoleFeatures(Dictionary()).extract(left,right,candidate)
        self.assertEqual(len(FEATURE_NAMES),len(values))
        return dict(zip(FEATURE_NAMES,values))

    def test_possible_plural_subject_does_not_erase_singular_complement_readings(self):
        v=self.values()
        self.assertEqual(1,v['right_nominal_case_alternative'])
        self.assertEqual(1,v['right_nominal_number_ambiguous'])
        self.assertEqual(0,v['right_nominal_case_unambiguous'])
        self.assertEqual(1,self.values(right=' девочка ')['right_nominal_case_unambiguous'])

    def test_unfinished_word_is_not_a_subject_and_future_copula_does_not_supply_gender(self):
        self.assertEqual(0,self.values(right=' модели')['right_nominal_is_noun'])
        self.assertEqual(0,self.values(right=' будешь ')['right_gender_available'])
        self.assertEqual(1,self.values(right=' была ')['right_gender_available'])
        self.assertEqual(1,self.values(right=' будешь она ')['right_nominal_is_pronoun'])

    def test_preceding_past_gender_survives_comma_without_becoming_hard_authority(self):
        v=self.values(left='ты пришла, и теперь ')
        self.assertEqual(1,v['left_past_gender_supported'])
        self.assertEqual(0,v['left_past_gender_conflict'])
        self.assertEqual(1,self.values(left='ты пришла, и теперь ',candidate='готов')['left_past_gender_conflict'])
        self.assertEqual(0,self.values(left='ты пришла. теперь ')['left_past_gender_available'])
        self.assertEqual(0,self.values(left='ты пришла\nтеперь ')['left_past_gender_available'])

    def test_unknown_and_identifiers_cannot_be_laundered_into_cues(self):
        self.assertEqual((),preceding_clause_words('prefix_пришла '))
        self.assertEqual((),preceding_clause_words('prefix-пришла '))
        self.assertEqual((),preceding_clause_words('пришла'))
        self.assertEqual((),preceding_clause_words('я' * 130 + ' '))
        self.assertTrue(all(v==0 for v in RightContextRoleFeatures(Dictionary()).extract('',' неизвестный ','неизвестный')))


if __name__=='__main__':unittest.main()
