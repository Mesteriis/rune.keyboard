from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import json

import english_ewt_control_screen as subject


class EnglishEwtControlScreenTest(unittest.TestCase):
    def test_selects_unannotated_ascii_rows_without_treating_them_as_gold(self):
        data=(b'# text = synthetic\n'
              b'1\tcat\tcat\tNOUN\t_\t_\t0\troot\t_\t_\n'
              b'2\tteh\tthe\tX\t_\t_\t0\troot\t_\tCorrectForm=the\n'
              b'3\t!\t!\tPUNCT\t_\t_\t0\tpunct\t_\t_\n')
        rows,counts=subject.test_controls(data)
        self.assertEqual([('cat','NOUN')],rows)
        self.assertEqual(1,counts['annotatedCorrectionExcluded'])
        self.assertEqual(1,counts['unsupportedShapeExcluded'])

    def test_protected_prior_exclusions_and_ambiguous_pool(self):
        vocab={'cat':100,'cut':80,'dog':90}
        rows=[('cat','NOUN'),('teh','X'),('cot','NOUN'),('zzz','PROPN')]
        result=subject.screen(rows,vocab,Counter({('substitute','a','o'):3}),{'teh'},0.5)
        counts=result['counts']
        self.assertEqual(1,counts['vocabularyOriginalProtected'])
        self.assertEqual(1,counts['priorAnnotatedWordExcluded'])
        self.assertEqual(2,counts['unseenUnknownRows'])
        self.assertEqual(1,counts['candidateAvailable'])
        self.assertEqual(1,counts['multipleCandidates'])
        self.assertEqual(1,counts['noCandidate'])
        self.assertEqual(1,result['byPos']['PROPN']['noCandidate'])

    def test_single_candidate_survives_every_finite_margin(self):
        result=subject.screen([('cta','PROPN')],{'cat':100},Counter({('transpose','a','t'):1}),set(),0.5)
        self.assertEqual(1,result['counts']['singleCandidate'])
        self.assertEqual(1,result['counts']['marginAtLeast:3.0'])

    def test_invalid_source_or_empty_model_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'EWT_CONTROL_ROW'):
            subject.test_controls(b'1\tbad\n')
        with self.assertRaisesRegex(ValueError,'EWT_CONTROL_MODEL'):
            subject.screen([],{},Counter(),set(),0.5)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'receipt.json';p.write_bytes(b'bad')
            with mock.patch.object(subject,'RECEIPT',p):
                with self.assertRaisesRegex(ValueError,'EWT_CONTROL_RECEIPT_DRIFT'):
                    subject.run(Path(folder))

    def test_missing_target_exclusions_stop_before_source_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'ledger.json';ledger.write_text('{}')
            with mock.patch.object(subject.targets,'LEDGER',ledger), \
                 mock.patch.object(subject.targets,'entry',return_value={'id':subject.targets.ENTRY}), \
                 mock.patch.object(subject.lexical,'validate_ledger',return_value={'entries':[]}), \
                 mock.patch.object(subject.model,'run') as model_run:
                with self.assertRaisesRegex(ValueError,'EWT_CONTROL_TARGET_EXCLUSIONS'):
                    subject.run(Path(folder))
                model_run.assert_not_called()

    def test_retained_aggregate_binds_the_exact_experiment_and_code(self):
        path=subject.ROOT/'docs/acceptance/2026-11-03-u11-ewt-control-screen.json'
        value=json.loads(path.read_bytes())
        self.assertEqual(subject.RECEIPT_SHA,value['experimentReceiptSha256'])
        self.assertEqual(subject.model.sha(Path(subject.__file__).read_bytes()),value['analyzerSha256'])
        self.assertEqual(subject.model.sha(Path(subject.model.__file__).read_bytes()),value['modelSha256'])
        self.assertEqual(subject.model.LOCK_SHA,value['sourceLockSha256'])
        self.assertFalse(value['labelsQualified'])
        self.assertFalse(value['independentQualification'])
        self.assertFalse(value['productBehaviorMeasured'])
        counts=value['screen']['counts']
        self.assertEqual(counts['unseenUnknownRows'],counts['candidateAvailable']+counts['noCandidate'])
        self.assertEqual(counts['candidateAvailable'],counts['singleCandidate']+counts['multipleCandidates'])


if __name__=='__main__':unittest.main()
