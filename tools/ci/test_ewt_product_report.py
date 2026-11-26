import json
from pathlib import Path
import unittest

import ewt_product_report as subject


class EwtProductReportTest(unittest.TestCase):
    def test_aggregate_retains_reasons_without_token_payload(self):
        labels=[{'kind':'annotated'},{'kind':'unannotated-unknown'}]
        rows=[{'boundaryDiagnostics':[{'source':'NONE','reason':'ORIGINAL_VALID','text':'not-output'}]},
              {'boundaryDiagnostics':[{'source':'CANONICAL_CASE','reason':'AUTO_REPLACE'}]}]
        result=subject.diagnostic_counts(labels,rows)
        self.assertEqual({'NONE:ORIGINAL_VALID':1},result['annotated'])
        self.assertEqual({'CANONICAL_CASE:AUTO_REPLACE':1},result['unannotated-unknown'])
        self.assertNotIn('not-output',json.dumps(result))

    def test_missing_unknown_or_duplicate_diagnostics_are_refused(self):
        labels=[{'kind':'annotated'}]
        for rows in ([],[{'boundaryDiagnostics':[]}],
                     [{'boundaryDiagnostics':[{'source':'unexpected','reason':'ORIGINAL_VALID'}]}],
                     [{'boundaryDiagnostics':[{'source':'NONE','reason':'unknown'}]}],
                     [{'boundaryDiagnostics':[{'source':'NONE','reason':'ORIGINAL_VALID'}]*2}]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):subject.diagnostic_counts(labels,rows)

    def test_retained_report_has_expected_binding_and_no_qualification(self):
        path=subject.ROOT/'docs/acceptance/2026-11-03-u11-ewt-product-replay.json'
        report=json.loads(path.read_bytes())
        self.assertEqual(subject.replay.model.sha(Path(subject.__file__).read_bytes()),report['analyzerSha256'])
        self.assertEqual(351,report['summary']['rows'])
        self.assertEqual(533,report['inputContexts'])
        self.assertEqual(945,report['candidateContexts'])
        self.assertEqual(186,sum(report['boundaryDiagnostics']['annotated'].values()))
        self.assertFalse(report['independentQualification'])
        self.assertFalse(report['labelsQualified'])


if __name__=='__main__':unittest.main()
