import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import prepare_refinement as prepare
import rank_refinement as rank

class RefinementTest(unittest.TestCase):
    def test_mutations_are_reproducible_and_never_known_words(self):
        vocabulary={'работать','работа','домой','слово','слова'}
        for word in vocabulary:
            first=prepare.perturb(word,'fixture',vocabulary)
            self.assertEqual(first,prepare.perturb(word,'fixture',vocabulary))
            if first:
                typed,kind=first
                self.assertNotIn(typed,vocabulary)
                self.assertGreaterEqual(len(typed),4)
                self.assertIn(kind,('deletion','repetition','transposition','neighbour'))
        assignments={prepare.partition(str(i)) for i in range(1000)}
        self.assertEqual(assignments,{'train','dev','test'})

    def test_feature_vectors_distinguish_edit_types(self):
        def vector(typed,word):
            return rank.features('пойти к ',typed,dict(text=word,unitDistance=1,frequencyRank=300,editCost=1,isFallback=False))
        for typed,word,index in [('сллво','слово',27),('слвоо','слово',28),('слво','слово',29),('словво','слово',30),('словво','слово',31)]:
            f=vector(typed,word)
            self.assertEqual(len(f),95);self.assertEqual(f[index],1)
            self.assertTrue(np.isfinite(f).all())
            self.assertEqual(f[35+len(rank.ENDINGS)+rank.PREPOSITIONS.index('к')],1)

    def test_training_rejects_tampered_split_and_wrong_partition(self):
        original=rank.ROOT/'build/typing-refinement/verified-observations'
        self.assertEqual(len(rank.verified_groups(original/'train.jsonl','train')),4942)
        with self.assertRaises(ValueError): rank.verified_groups(original/'test.jsonl','test')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'manifest.json').write_bytes((original/'manifest.json').read_bytes())
            (root/'train.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'OBSERVATION_IDENTITY'):rank.verified_groups(root/'train.jsonl','train')

    def test_selected_export_matches_reference(self):
        from catboost import CatBoostRanker
        out=rank.ROOT/'build/typing-refinement/ranker'
        model=CatBoostRanker().load_model(str(out/'pairwise.cbm'))
        groups=rank.verified_groups(rank.ROOT/'build/typing-refinement/verified-observations/dev.jsonl','dev')
        vectors=np.array([rank.features(r['prefix'],r['typed'],c) for r,cs,_ in groups for c in cs])
        expected=model.predict(vectors)
        blob=(out/'pairwise.bin').read_bytes()
        actual=np.array([rank.tree_score(blob,v) for v in vectors])
        self.assertLess(float(np.max(np.abs(expected-actual))),1e-5)

if __name__=='__main__':unittest.main()
