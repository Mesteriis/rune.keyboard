from types import SimpleNamespace
import unittest
from right_context_role_corpus import generate


def tag(number='sing',gender='masc'):
    return SimpleNamespace(pos='ADJS',number=number,gender=gender,lemma='полезный')


class Dictionary:
    def __init__(self):self.words={'полезен':[tag()],'полезна':[tag(gender='femn')],
        'полезно':[tag(gender='neut')],'полезны':[tag(number='plur',gender=None)]}
    def analyses(self,word):return self.words.get(word,())


class RoleCorpusTest(unittest.TestCase):
    def rows(self):
        lex=Dictionary()
        rows,skipped=generate(lex,{'полезен':list(lex.words)},pairs=[('полезен','полезны')])
        self.assertFalse(skipped)
        return rows

    def test_singular_future_without_gender_never_teaches_a_masculine_default(self):
        rows=[r for r in self.rows() if not r['leftContext'] and r['rightContext'] in (' будет ',' будешь ',' буду ')]
        self.assertTrue(rows)
        self.assertTrue(all(r['expectedApplied']==r['applied'] for r in rows))

    def test_feminine_and_neuter_have_explicit_strong_cues_and_raw_acquisition_states(self):
        rows=self.rows()
        for target,cue in [('полезна',' она '),('полезно',' оно ')]:
            subset=[r for r in rows if r['kind']=='unknown_original' and r['expectedApplied']==target and r['rightContext']==cue]
            self.assertTrue(any(r['applied']==r['original'] for r in subset))
        self.assertTrue(any(r['leftContext']=='ты пришла, и теперь ' and r['expectedApplied']=='полезна' for r in rows))

    def test_complement_alternatives_do_not_teach_plural_without_a_subject(self):
        rows=self.rows()
        for suffix in (' модели ',' традиции ',' организации '):
            weak=[r for r in rows if not r['leftContext'] and r['rightContext']==suffix]
            self.assertTrue(weak)
            self.assertTrue(all(r['expectedApplied']==r['applied'] for r in weak))
            self.assertTrue(any(r['leftContext']=='она ' and r['rightContext']==suffix and r['expectedApplied']=='полезна' for r in rows))

    def test_correct_originals_and_unique_identity_remain_explicit(self):
        rows=self.rows()
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertTrue(all(r['purpose']=='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY' for r in rows))
        self.assertTrue(all(r['original']==r['applied']==r['expectedApplied'] for r in rows if r['kind']=='correct_original'))


if __name__=='__main__':unittest.main()
