import json
import math
import struct
import unittest
import numpy as np
from pathlib import Path
import train


def tree_score(blob, features):
    assert blob[:4]==b'RET1'
    n,count,scale,bias=struct.unpack_from('<IIff',blob,4)
    assert n==22 and 0<count<=128
    offset=20; result=0
    for _ in range(count):
        depth,=struct.unpack_from('<I',blob,offset);offset+=4
        assert 0<depth<=6
        leaf=0
        for d in range(depth):
            index,border=struct.unpack_from('<If',blob,offset);offset+=8
            assert 0<=index<n and math.isfinite(border)
            if np.float32(features[index])>border:leaf|=1<<d
        leaves=struct.unpack_from('<'+'f'*(1<<depth),blob,offset);offset+=4*(1<<depth)
        assert all(math.isfinite(v) for v in leaves)
        result+=leaves[leaf]
    assert offset==len(blob)
    return result*scale+bias

class ModelsTest(unittest.TestCase):
    def test_public_identity_and_split(self):
        rows,_,_=train.load_public()
        fit={r['template'] for r,o in rows if r['split']=='calibration'}
        holdout={r['template'] for r,o in rows if r['split']=='holdout'}
        self.assertTrue(fit and holdout)
        self.assertFalse(fit&holdout)

    def test_exported_trees_match_catboost(self):
        from catboost import CatBoostClassifier
        model=CatBoostClassifier().load_model(str(train.OUT/'catboost-reference.cbm'))
        rows,_,_=train.load_public()
        vectors=[train.features(r['prefix'],r['typed'],c) for r,o in rows
                 for c in o['generation']['alternatives']]
        vectors=np.array(vectors)
        expected=model.predict(vectors,prediction_type='RawFormulaVal')
        actual=np.array([tree_score((train.ASSETS/'ru-ranker.bin').read_bytes(),v) for v in vectors])
        error=float(np.max(np.abs(expected-actual)))
        self.assertLess(error,1e-5)
        print(json.dumps({'treeParityRows':len(vectors),'maxAbsoluteError':error}))

    def test_neural_bounds_and_context(self):
        blob=(train.ASSETS/'ru-context.bin').read_bytes()
        self.assertEqual(blob[:4],b'REC1')
        a=np.frombuffer(blob[16:],dtype='<f4').astype(np.float64)
        n=len(train.ALPHABET); w=train.WINDOW*n*train.HIDDEN
        weights=[a[:w].reshape(train.WINDOW*n,train.HIDDEN),a[w:w+train.HIDDEN],
                 a[w+train.HIDDEN:-n].reshape(train.HIDDEN,n),a[-n:]]
        x=train.probabilities(weights,'мы идем ');y=train.probabilities(weights,'он хочет ')
        self.assertTrue(np.isfinite(x).all());self.assertAlmostEqual(float(x.sum()),1)
        self.assertGreater(float(np.abs(x-y).sum()),.01)
        for p in json.loads((train.OUT/'parity.json').read_text()):
            self.assertAlmostEqual(train.context_score(weights,p['context'],p['candidate']),p['contextScore'],places=8)

if __name__=='__main__':unittest.main()
