import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_ewt_product_candidates as subject


class EwtProductCandidatesTest(unittest.TestCase):
    def test_real_disclosed_candidate_contexts_are_registered(self):
        expected=subject.entry();ledger=subject.control.load(subject.LEDGER)
        self.assertEqual([expected],[e for e in ledger['entries'] if e['id']==subject.ENTRY])
        fixture=json.loads(subject.FIXTURE.read_bytes())
        self.assertEqual(945,len(expected['keys']))
        self.assertEqual(1,fixture['caseOnlyChanges'])
        self.assertEqual(0,fixture['otherChanges'])

    def test_candidate_sources_and_applied_edit_are_all_covered(self):
        gen=dict(alternatives=[{'text':'one'}],compactAlternatives=[{'text':'two'}],
            localSearch={'alternatives':[{'text':'three'}]},neighborRecovery={'alternatives':[{'text':'four'}]})
        obs=dict(candidateView={'candidates':[{'text':'shown'}]},fullTokenGeneration=gen,
            actualRequestGeneration=None,manualSearchGeneration=None,autoEdit={'applied':'applied'})
        self.assertEqual({'one','two','three','four','shown','applied'},subject.candidates(obs))
        obs['fullTokenGeneration']['localSearch']={'alternatives':[{}]}
        with self.assertRaisesRegex(ValueError,'EWT_CANDIDATE_ROW'):
            subject.candidates(obs)

    def test_changed_fixture_source_binding_is_refused(self):
        value=json.loads(subject.FIXTURE.read_bytes());value['sourceFixtureSha256']='0'*64
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.json';path.write_text(json.dumps(value))
            with mock.patch.object(subject,'FIXTURE',path):
                with self.assertRaisesRegex(ValueError,'EWT_CANDIDATE_FIXTURE'):
                    subject.entry()


if __name__=='__main__':unittest.main()
