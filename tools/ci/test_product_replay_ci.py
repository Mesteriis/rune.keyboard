import copy
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import product_replay_ci as gate


class ProductReplayCiTest(unittest.TestCase):
    def test_frozen_baseline_matches_manifest_and_all_corpus_disclosures(self):
        meta=gate.validate()
        self.assertEqual(2160,meta['rows'])
        self.assertEqual({'en':720,'ru':720,'es':720},meta['languages'])
        self.assertEqual('e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea',meta['projectionSha256'])

    def test_original_multilingual_corpus_and_disclosures_are_retained_in_second_profile(self):
        meta=gate.validate_history()
        self.assertEqual(12000,meta['rows'])
        self.assertEqual({'en':4000,'ru':4000,'es':4000},meta['languages'])
        self.assertEqual(['tools/eval/smart-typing-0.3/'+name for name in gate.history.FILES],meta['inputPaths'])
        entries,ru=gate.history.expected_entries()
        self.assertEqual(3,len(entries));self.assertTrue(all(e['rowCount']==4000 for e in entries))
        self.assertIn('family',ru['missingAxes']);self.assertNotIn('family',ru['keys'])

    def test_wrong_compressed_hash_or_missing_acceptance_cannot_reach_replay(self):
        for change in ('hash','acceptance'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);shutil.copytree(gate.corpus.DATA,root/'data')
                data=root/'data';p=data/'baseline-manifest.json';meta=json.loads(p.read_text())
                if change=='hash':meta['fileSha256']='0'*64
                else:meta['acceptance']='docs/acceptance/does-not-exist.md'
                p.write_text(json.dumps(meta))
                with mock.patch.object(gate.corpus,'DATA',data), \
                     mock.patch.object(gate.corpus,'build',return_value={}), \
                     mock.patch.object(gate.disclosure,'check'), \
                     self.assertRaises(ValueError):gate.validate()

    def test_driver_nonzero_is_preserved_and_zero_without_complete_receipt_is_not_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'output'
            with mock.patch.object(gate,'validate',return_value={'rows':2160,'projectionSha256':'a'*64}), \
                 mock.patch.object(gate.subprocess,'run',return_value=SimpleNamespace(returncode=42)):
                self.assertEqual(42,gate.run(Path('/synthetic/java'),output))
            output.mkdir();(output/'receipt.json').write_text(json.dumps({'status':'COMPLETE','rows':2160}))
            with mock.patch.object(gate,'validate',return_value={'rows':2160,'projectionSha256':'a'*64}), \
                 mock.patch.object(gate.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
                 self.assertRaisesRegex(ValueError,'NOT_PROVEN'):
                gate.run(Path('/synthetic/java'),output)

    def test_success_requires_baseline_and_candidate_hashes_and_row_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'output'; output.mkdir()
            baseline='a'*64; candidate='b'*64
            receipt={'status':'COMPLETE','deterministic':True,'baselineMatches':True,
                     'deterministicNeighborSearch':True,'rows':2160,'projectionSha256':candidate}
            comparison={'passed':True,'differentRows':0,'baselineRows':2160,'candidateRows':2160,
                        'toleratedScoreDifferences':3,
                        'scoreAbsoluteTolerance':gate.projection.BASELINE_SCORE_ABS_TOLERANCE,
                        'baselineProjectionSha256':baseline,'candidateProjectionSha256':candidate}
            (output/'receipt.json').write_text(json.dumps(receipt))
            path=output/'baseline-comparison.json'
            with mock.patch.object(gate,'validate',return_value={'rows':2160,'projectionSha256':baseline}), \
                 mock.patch.object(gate,'sha',return_value='fixed'), \
                 mock.patch.object(gate.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
                path.write_text(json.dumps(comparison))
                self.assertEqual(0,gate.run(Path('/synthetic/java'),output))
                self.assertIn('--deterministic-neighbor-search',run.call_args.args[0])
                (output/'receipt.json').write_text(json.dumps(receipt | {'deterministicNeighborSearch':False}))
                with self.assertRaisesRegex(ValueError,'NOT_PROVEN'):
                    gate.run(Path('/synthetic/java'),output)
                (output/'receipt.json').write_text(json.dumps(receipt))
                for key,value in (('baselineProjectionSha256','c'*64),('candidateProjectionSha256','c'*64),
                                  ('candidateRows',2159),('toleratedScoreDifferences',-1)):
                    changed=comparison | {key:value}; path.write_text(json.dumps(changed))
                    with self.subTest(key=key),self.assertRaisesRegex(ValueError,'NOT_PROVEN'):
                        gate.run(Path('/synthetic/java'),output)


if __name__=='__main__':unittest.main()
