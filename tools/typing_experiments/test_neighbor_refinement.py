import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import json
import neighbor_refinement as refinement


class NeighborRefinementTest(unittest.TestCase):
    def test_evaluation_rejects_any_locally_correct_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);frozen=root/'frozen.json'
            frozen.write_text(json.dumps({'thresholds':{'minimumScore':-8,'minimumMargin':2}}))
            good=dict(id='good',topScore=-3,margin=3,improvement=True,regression=False,correct=True,control=False)
            bad=dict(id='bad',topScore=-3,margin=3,improvement=False,regression=True,correct=False,control=False)
            for index,rows in enumerate(([good],[good,bad],[dict(good,control=True)],[])):
                with patch.object(refinement,'records',return_value=rows),patch.object(refinement.recovery,'digest',return_value='digest'):
                    passed=refinement.evaluate(root,root,root,frozen,root/f'out{index}.json')
                    self.assertEqual(index==0,passed)

    def test_normalization_is_per_token_and_tied_candidate_abstains(self):
        records=[dict(topScore=-1,margin=0,correct=True,control=False),
                 dict(topScore=-2,margin=2,correct=True,control=False),
                 dict(topScore=-1.5,margin=1,correct=False,control=False)]
        policy=refinement.recovery.calibrate(records)
        self.assertGreater(policy['minimumMargin'],1)
        self.assertEqual(1,sum(r['topScore']>=policy['minimumScore'] and r['margin']>=policy['minimumMargin'] for r in records))


if __name__=='__main__':unittest.main()
