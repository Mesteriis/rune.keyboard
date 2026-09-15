import json
import unittest
import evaluate_extra_epochs as e
import prepare_epoch_test as p

class AdditionalEpochEvaluationTest(unittest.TestCase):
    def test_improvement_requires_fresh_gain_and_no_old_regression(self):
        def report(before,after):return {'models':{'before':{'combinedCorrectTop1':before},'after':{'combinedCorrectTop1':after}}}
        self.assertTrue(e.accepts(900,901,2.1,2.0,report(1000,1001),[report(600,600),report(1200,1201)]))
        self.assertFalse(e.accepts(900,901,2.1,2.0,report(1000,1000),[report(600,601)]))
        self.assertFalse(e.accepts(900,901,2.1,2.0,report(1000,1001),[report(600,599)]))
        self.assertFalse(e.accepts(900,899,2.1,2.0,report(1000,1001),[report(600,601)]))
        self.assertTrue(e.accepts(900,900,2.1,2.0,report(1000,1001),[report(600,600)]))
        self.assertFalse(e.accepts(900,900,2.1,2.1,report(1000,1001),[report(600,600)]))

    def test_reserved_articles_and_rows_exclude_previous_experiment(self):
        old=json.loads((e.ROOT/'build/typing-refinement/data/manifest.json').read_text())
        fresh=json.loads((e.OUT/'data/manifest.json').read_text())
        self.assertFalse(p.excluded_articles(old)&p.excluded_articles(fresh))
        self.assertEqual(fresh['excludedInitialArticles'],old['scannedArticles'])
        self.assertEqual(fresh['partitions']['test']['rows'],1500)
        self.assertEqual(fresh['partitions']['test']['characters'],250000)
        self.assertFalse(fresh['partitions']['train']['articles'])
        self.assertFalse(fresh['partitions']['dev']['articles'])
        old['containsPersonalMessages']=True
        with self.assertRaises(ValueError):p.excluded_articles(old)

if __name__=='__main__':unittest.main()
