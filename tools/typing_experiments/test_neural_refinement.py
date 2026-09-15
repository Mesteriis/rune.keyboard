"""Host contract tests for the refinement's public data and portable bytes."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import neural_refinement as n

class NeuralRefinementTests(unittest.TestCase):
    def test_export_parity_and_finite_probabilities(self):
        rng=np.random.default_rng(123)
        for w,h in ((24,24),(48,48)):
            model=n.Model(w,h,[rng.normal(0,.1,s).astype(np.float32) for s in ((w*34,h),(h,),(h,34),(34,))])
            with tempfile.TemporaryDirectory() as d:
                decoded=n.export_model(model,Path(d)/'model.bin')
            for context in ('','мы идём домой','я '*100,'x!?😀'):
                actual=n.probabilities(decoded,context)
                # Independent scalar runtime-shaped calculation on float32 export.
                x=([0]*w+n.ids(context[-w:]))[-w:]
                a,b,c,e=model.weights
                hidden=[np.tanh(float(b[j])+sum(float(a[i*34+v,j]) for i,v in enumerate(x))) for j in range(h)]
                z=np.array([float(e[k])+sum(hidden[j]*float(c[j,k]) for j in range(h)) for k in range(34)])
                p=np.exp(z-z.max()); p/=p.sum()
                np.testing.assert_allclose(actual,p,atol=1e-12,rtol=1e-12)
                self.assertTrue(np.isfinite(actual).all())
                self.assertAlmostEqual(float(actual.sum()),1.0)
            for terminal in (False,True):
                history='мы идём '
                word='домой'+(' ' if terminal else '')
                total=0.0
                for c in word:
                    total+=np.log(max(n.probabilities(decoded,history)[n.ids(c)[0]],1e-9))
                    history=(history+c)[-w:]
                expected=float(np.clip((total/len(word)+3)*.25,-.5,.5))
                self.assertAlmostEqual(n.context_score(decoded,'мы идём','домой',end_of_word=terminal),expected,places=12)
            self.assertEqual(n.context_score(decoded,'ctx','word','en'),0)
            self.assertEqual(n.context_score(decoded,'ctx',''),0)
            self.assertEqual(n.context_score(decoded,'ctx','а'*129),0)

    def test_decoder_rejects_corruption(self):
        model=n.Model(24,24,[np.zeros(s,dtype=np.float32) for s in ((24*34,24),(24,),(24,34),(34,))])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.bin'; n.export_model(model,path); raw=path.read_bytes()
            for bad in (b'',raw[:-1],raw+b'x',b'REC2'+raw[4:],raw[:16]+struct.pack('<f',float('nan'))+raw[20:],raw[:16]+struct.pack('<f',33)+raw[20:]):
                path.write_bytes(bad)
                with self.assertRaises(ValueError): n.load_model(path)

    def test_only_verified_train_dev_inputs(self):
        manifest=json.loads((n.DATA/'manifest.json').read_text())
        train=n.verified_text(n.DATA,'train',manifest)
        dev=n.verified_text(n.DATA,'dev',manifest)
        self.assertFalse({r['articleId'] for r in train}&{r['articleId'] for r in dev})
        with patch.object(Path,'read_bytes',side_effect=AssertionError('must reject before opening')):
            with self.assertRaises(ValueError): n.verified_text(n.DATA,'test',manifest)
        manifest['files']['dev-text.jsonl']='0'*64
        with self.assertRaises(ValueError): n.verified_text(n.DATA,'dev',manifest)

if __name__=='__main__': unittest.main()
