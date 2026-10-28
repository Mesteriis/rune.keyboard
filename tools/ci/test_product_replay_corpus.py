import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import generate_product_replay_v1 as corpus
import register_product_replay_v1 as disclosure
import control_ledger as controls
import holdout_ledger as lexical
from public_corpus_preparation_v1 import preflight


class ProductReplayCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[json.loads(line) for line in (corpus.DATA/'inputs.jsonl').read_text().splitlines()]
        cls.origins=[json.loads(line) for line in (corpus.DATA/'origins.jsonl').read_text().splitlines()]
        cls.controls=controls.load(disclosure.CONTROL_PATH)
        cls.lexical=lexical.load_ledger(disclosure.LEXICAL_PATH)

    def test_all_derived_bytes_reproduce_from_the_three_pinned_sources(self):
        for name,data in corpus.build().items():self.assertEqual(data,(corpus.DATA/name).read_bytes())
        self.assertEqual(2160,len(self.rows));self.assertEqual(540,len(self.origins))
        self.assertEqual(2160,len({row['id'] for row in self.rows}))
        for lang in corpus.LANGUAGES:self.assertEqual(720,sum(row['language']==lang for row in self.rows))
        self.assertTrue(all(set(row)=={'id','split','language','prefix','typed'} for row in self.rows))
        for group,origin in enumerate(self.origins):
            rows=self.rows[group*4:group*4+4]
            self.assertEqual(list(corpus.variants(origin['target']['word'])),[row['typed'] for row in rows])
            self.assertTrue(all(row['prefix']==' '.join(word['word'] for word in origin['context']) for row in rows))

    def test_source_payload_or_provenance_drift_is_rejected_before_generation(self):
        for drift in ('source','url','license','author'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder)/'data';shutil.copytree(corpus.DATA,root)
                if drift=='source':
                    p=root/'sources/en_50k.txt';p.write_bytes(p.read_bytes()+b'changed 1\n')
                else:
                    p=root/'source-lock.json';lock=json.loads(p.read_text())
                    if drift=='url':lock['files']['en']['url']='https://example.invalid/source'
                    elif drift=='license':lock['contentLicense']='unknown'
                    else:lock['author']='unknown'
                    p.write_text(json.dumps(lock))
                with self.assertRaises(ValueError):corpus.build(root)

    def test_surface_disclosure_survives_case_and_prefix_changes_in_every_language(self):
        for language in corpus.LANGUAGES:
            word=next(origin['target']['word'] for origin in self.origins if origin['language']==language)
            row=dict(language=language,prefix='previously unseen regression prefix',typed=' '+word.upper()+' ')
            with self.assertRaisesRegex(ValueError,'CONTROL_SURFACE_OVERLAP'):
                controls.assert_disjoint([row],self.controls,'protected')
            proposal=dict(row,id='new',expectedSpelling=row['typed'],families=['claimed-new-family'],
                article='999999999999',contextHash='0'*64)
            result=preflight([proposal],'spelling',self.lexical,self.controls)
            self.assertEqual('BLOCKED_OVERLAP',result['status'])
            self.assertGreater(result['controlOverlaps']['surface'],0)
        self.assertEqual(controls.surface_key('es','cancio\u0301n'),controls.surface_key('es','CANCIÓN'))
        self.assertNotEqual(controls.surface_key('en','same'),controls.surface_key('es','same'))
        self.assertNotEqual(controls.surface_key('ru','ёлка'),controls.surface_key('ru','елка'))

    def test_contexts_and_surface_keys_match_both_committed_registries_exactly(self):
        expected,ru=disclosure.expected_entries()
        self.assertEqual(expected,[e for e in self.controls['entries'] if e['id'].startswith(disclosure.ENTRY)])
        self.assertEqual([ru],[e for e in self.lexical['entries'] if e['id'].startswith(disclosure.ENTRY)])
        self.assertIn('family',ru['missingAxes']);self.assertNotIn('family',ru['keys'])
        self.assertFalse(self.controls['coverageComplete']);self.assertFalse(self.lexical['coverage']['complete'])
        disclosure.check()

    def test_invalid_surface_metadata_and_duplicate_registration_fail(self):
        entry=next(e for e in self.controls['entries'] if e['kind']=='regression')
        for values in ([],['invalid'],[{}],[entry['surfaceKeys'][0]]*2):
            changed=copy.deepcopy(self.controls)
            next(e for e in changed['entries'] if e['id']==entry['id'])['surfaceKeys']=values
            with self.assertRaises(ValueError):controls.validate(changed)
        with self.assertRaisesRegex(ValueError,'ALREADY_REGISTERED'):
            disclosure.updated(self.controls,self.lexical)

    def test_corpus_and_new_exclusions_verify_in_a_minimal_tree_without_build_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ci=root/'tools/ci';ci.mkdir(parents=True)
            shutil.copytree(corpus.DATA,ci/'product-replay-v1')
            for name in ('generate_product_replay_v1.py','register_product_replay_v1.py'):
                shutil.copyfile(corpus.ROOT/'tools/ci'/name,ci/name)
            tools=root/'tools/typing_experiments';tools.mkdir()
            for name in ('control_ledger.py','holdout_ledger.py','source_identities.py','conversation_split_checks.py',
                         'control-ledger.json','holdout-ledger.json'):
                shutil.copyfile(corpus.ROOT/'tools/typing_experiments'/name,tools/name)
            self.assertFalse((root/'build').exists())
            for name in ('generate_product_replay_v1.py','register_product_replay_v1.py'):
                result=subprocess.run([sys.executable,str(ci/name),'--check'],cwd=root,capture_output=True,text=True)
                self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            self.assertFalse((root/'build').exists())


if __name__=='__main__':unittest.main()
