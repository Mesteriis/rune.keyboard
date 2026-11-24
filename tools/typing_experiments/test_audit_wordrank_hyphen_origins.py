import unittest
from types import SimpleNamespace
import audit_wordrank_hyphen_origins as subject


class Lexicon:
    def analyses(self, word):
        return [] if word in subject.EXPECTED else [SimpleNamespace(lemma=word)]


def sample():
    words=[('прайм','тайм'),('прайм','тайм'),('прайм','тайм'),('кибер','девушки'),('галло','романской')]
    rows=[];articles={}
    for i,(head,tail) in enumerate(words):
        article=str(i+1);prefix='контекст '+str(i)+' '
        rows.append(dict(id='row'+str(i),language='ru',articleId=article,prefix=prefix,expectedSpelling=head))
        articles[article]=prefix+head+'-'+tail+' здесь'
    return rows,articles


class HyphenOriginTest(unittest.TestCase):
    def test_source_bound_compounds_preserve_unknown_heads_and_tail_families(self):
        rows,articles=sample();result=subject.derive(rows,articles,Lexicon())
        self.assertEqual(5,len(result));self.assertEqual({'прайм-тайм','кибер-девушки','галло-романской'}, {r['typed'] for r in result})
        self.assertEqual(['тайм'],result[0]['tailFamilies'])

    def test_missing_duplicate_and_changed_source_are_rejected(self):
        rows,articles=sample()
        with self.assertRaises(ValueError):subject.derive(rows,{},Lexicon())
        broken=dict(articles);broken['1']='другой контекст'
        with self.assertRaises(ValueError):subject.derive(rows,broken,Lexicon())
        duplicate=dict(articles);duplicate['1']=articles['1']+' '+articles['1']
        with self.assertRaises(ValueError):subject.derive(rows,duplicate,Lexicon())
        with self.assertRaises(ValueError):subject.derive(rows+[rows[0]],articles,Lexicon())


if __name__=='__main__':unittest.main()
