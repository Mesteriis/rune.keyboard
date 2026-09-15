import json
import unittest
from collections import Counter
import prepare_word_ranking as p
import evaluate_word_ranking as e

class WordRankingDataTest(unittest.TestCase):
    def test_exact_complex_edits_and_reproducible_controls(self):
        self.assertEqual(p.distance('слово','слово'),0)
        self.assertEqual(p.distance('слвоо','слово'),1)
        self.assertEqual(p.distance('молоко','малако'),2)
        self.assertEqual(p.distance('работать','рбота'),3)
        vocabulary={'молоко','работать','слово','работа'}
        for word in vocabulary:
            for count in (0,1,2,3):
                result=p.mutate(word,'test',count,vocabulary)
                self.assertEqual(result,p.mutate(word,'test',count,vocabulary))
                self.assertIsNotNone(result)
                mutated,operations=result
                self.assertEqual(p.distance(word,mutated),count)
                self.assertEqual(len(operations),count)
                if count:self.assertNotIn(mutated,vocabulary)
                else:self.assertEqual(mutated,word)
        with self.assertRaises(ValueError):p.mutate('слово','test',4,vocabulary)

    def test_train_dev_manifest_caps_and_exclusion(self):
        root=e.OUT/'data';m=json.loads((root/'manifest.json').read_text())
        old,_,_,_=p.prior_evidence()
        train=set(m['partitions']['train']['articles']);dev=set(m['partitions']['dev']['articles']);test=set(m['partitions']['test']['articles'])
        self.assertFalse(train&dev or train&test or dev&test or (train|dev|test)&old)
        self.assertEqual(m['excludedInitialArticles'],2155)
        for part in ('train','dev'):
            path=root/f'{part}-rows.jsonl'
            self.assertEqual(p.public.file_hash(path),m['files'][path.name])
            rows=[json.loads(s) for s in path.read_text().splitlines()]
            self.assertEqual(Counter(r['errorCount'] for r in rows),p.QUOTAS[part])
            self.assertEqual(len(rows),len({r['id'] for r in rows}))
            for row in rows:
                self.assertEqual(p.partition(row['articleId']),part)
                self.assertEqual(p.distance(row['typed'],row['expectedSpelling']),row['errorCount'])
                self.assertEqual(row['noAuto'],row['errorCount']==0)

    def test_promotion_needs_hard_gain_and_preserves_each_guard(self):
        def r(a,b):return {'models':{'before':{'combinedCorrectTop1':a},'after':{'combinedCorrectTop1':b}}}
        self.assertTrue(e.accepts(r(100,102),r(50,50),r(50,52),[r(90,90)]))
        self.assertFalse(e.accepts(r(100,101),r(50,52),r(50,49),[r(90,90)]))
        self.assertFalse(e.accepts(r(100,101),r(50,49),r(50,52),[r(90,90)]))
        self.assertFalse(e.accepts(r(100,102),r(50,50),r(50,52),[r(90,89)]))
        self.assertFalse(e.accepts(r(100,100),r(50,50),r(50,50),[r(90,90)]))

if __name__=='__main__':unittest.main()
