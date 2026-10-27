import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_public_corpus_preparation_v1 import candidate


def run_builder(folder,script,rows,extra=(),bad_hash=False):
    root=Path(folder);data=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows).encode()
    (root/'proposal.jsonl').write_bytes(data)
    manifest=dict(containsPersonalMessages=False,frozenBeforeScoring=True,
                  files={'proposal.jsonl':'0'*64 if bad_hash else hashlib.sha256(data).hexdigest()})
    (root/'manifest.json').write_text(json.dumps(manifest))
    command=[sys.executable,str(Path(__file__).with_name(script)),'--rows',str(root/'proposal.jsonl'),
             '--source-manifest',str(root/'manifest.json'),'--output',str(root/'output'),*extra]
    return subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)


class SpellingBuilderTest(unittest.TestCase):
    def test_real_incomplete_registries_prevent_any_output_corpus(self):
        with tempfile.TemporaryDirectory() as folder:
            # Artificial identity fixture: it tests coverage failure, not a proposed dictionary label.
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate(families=['fixture-only-family'])])
            self.assertEqual(2,result.returncode,result.stderr)
            report=json.loads(result.stdout);self.assertEqual('BLOCKED_COVERAGE',report['status'])
            self.assertFalse((Path(folder)/'output').exists());self.assertIn('control-ledger.json',report['inputBindings'])
            self.assertIn('lexical-ledger.json',report['inputBindings'])

    def test_real_supervised_family_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate()])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['lexicalOverlaps']['family'])
            self.assertFalse((Path(folder)/'output').exists())

    def test_real_punctuation_article_not_in_lexical_history_also_blocks_output(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate(article='4327487',families=['fixture-only-family'])])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['controlOverlaps']['article'])
            self.assertEqual(0,report['lexicalOverlaps']['article']);self.assertFalse((Path(folder)/'output').exists())

    def test_real_unsupported_name_is_blocked_even_with_an_unseen_family_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate(typed='ДАРСИ',expectedSpelling='дарси',families=['fixture-only-family'])])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['unsupportedTargetOverlaps'])
            self.assertFalse((Path(folder)/'output').exists())

    def test_prepared_family_from_rejected_unmanifested_material_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate(typed='привыкать',expectedSpelling='привыкать',families=['привыкать'])])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['lexicalOverlaps']['family'])
            self.assertFalse((Path(folder)/'output').exists())

    def test_ambiguous_template_family_is_blocked_in_default_profile(self):
        for lemma in ('весло','красить'):
            with tempfile.TemporaryDirectory() as folder:
                result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate(typed=lemma,expectedSpelling=lemma,families=[lemma])])
                self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
                self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['lexicalOverlaps']['family'])
                self.assertFalse((Path(folder)/'output').exists())

    def test_changed_proposal_bytes_cannot_reuse_a_frozen_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_spelling_v1.py',[candidate()],bad_hash=True)
            self.assertNotEqual(0,result.returncode);self.assertIn('PREPARATION_PROPOSAL_BINDING',result.stderr)
            self.assertFalse((Path(folder)/'output').exists())


if __name__=='__main__':unittest.main()
