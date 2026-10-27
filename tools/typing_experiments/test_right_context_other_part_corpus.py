from types import SimpleNamespace
import unittest
from right_context_other_part_corpus import generate


def tag(lemma,pos,case=None):
    return SimpleNamespace(lemma=lemma,pos=pos,case=case,number='sing',gender='masc')


class Dictionary:
    def __init__(self):self.words={'важен':[tag('важный','ADJS')],'вагон':[tag('вагон','NOUN','nomn')]}
    def analyses(self,word):return self.words.get(word,())


class OtherPartCorpusTest(unittest.TestCase):
    def rows(self):
        rows,skipped=generate(Dictionary(),pairs=[('важен','вагон','этот ',' будет новым ')])
        self.assertFalse(skipped);return rows

    def test_the_same_unknown_input_has_opposite_targets_with_visible_context(self):
        rows=self.rows();typos={r['original'] for r in rows if r['kind']=='unknown_original'}
        self.assertTrue(typos)
        for typo in typos:
            r=[r for r in rows if r['original']==typo and r['applied']==typo and r['rightContext']==' будет ']
            self.assertTrue(any(x['leftContext']=='этот ' and x['expectedApplied']=='вагон' for x in r))
            self.assertTrue(any(x['leftContext']=='он ' and x['expectedApplied']=='важен' for x in r))
            self.assertFalse(Dictionary().analyses(typo))

    def test_no_subject_and_unfinished_suffixes_always_retain_the_applied_word(self):
        weak=[r for r in self.rows() if r['kind']=='insufficient_right_evidence']
        self.assertTrue(weak);self.assertTrue(all(r['applied']==r['expectedApplied'] for r in weak))

    def test_controls_and_all_competing_families_are_explicit(self):
        rows=self.rows();self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertTrue(all(r['contrastFamilies']==['вагон','важный'] for r in rows))
        self.assertTrue(all(r['original']==r['applied']==r['expectedApplied'] for r in rows if r['kind']=='correct_original'))
        self.assertTrue(all(len(r['original'])>=3 for r in rows))

    def test_an_authored_noun_role_can_retain_its_other_dictionary_readings(self):
        lex=Dictionary();lex.words['вагон'].append(tag('другой','ADJS'))
        rows,_=generate(lex,pairs=[('важен','вагон','этот ',' будет новым ')])
        self.assertTrue(any(r['expectedApplied']=='вагон' and r['leftContext']=='этот ' for r in rows))
        self.assertTrue(all('другой' in r['contrastFamilies'] for r in rows))

    def test_guessed_unknown_or_wrong_part_targets_do_not_become_training_labels(self):
        for word in ['вагон','важен']:
            lex=Dictionary();lex.words.pop(word)
            with self.assertRaises(ValueError):generate(lex,pairs=[('важен','вагон','этот ',' будет новым ')])


if __name__=='__main__':unittest.main()
