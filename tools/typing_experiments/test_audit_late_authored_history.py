import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from audit_late_authored_history import BASE,SPECS,archive_path,directory,training_chain,verify_derivation
from audit_authored_training_history import exclusions
from holdout_ledger import keys_for


class LateAuthoredHistoryTest(unittest.TestCase):
    def test_append_derivation_requires_exact_parent_rows_and_counts(self):
        parent=[dict(id='p',expectedApplied='полезно')];rows=parent+[dict(id='new')]
        manifest=dict(oldCorpusSha256='a'*64,oldRows=1,otherPartRows=1)
        verify_derivation(5,rows,manifest,parent,'a'*64)
        for changed in (rows[::-1],[dict(id='p',expectedApplied='полезны')]+rows[1:]):
            with self.assertRaisesRegex(ValueError,'PARENT_DERIVATION'):verify_derivation(5,changed,manifest,parent,'a'*64)
        with self.assertRaisesRegex(ValueError,'PARENT_DERIVATION'):verify_derivation(6,rows,manifest,parent,'b'*64)

    def test_continuations_require_known_parent_or_unchanged_inherited_row(self):
        parent=[dict(id='p',expectedApplied='полезно')];manifest=dict(parentCorpusSha256='a'*64,parentRows=1)
        rows=parent+[dict(id='new',parentTrainingId='p')]
        verify_derivation(7,rows,manifest,parent,'a'*64)
        for changed in ([dict(id='new',parentTrainingId='missing')],[dict(id='p',expectedApplied='полезны')],[dict(id='unparented')]):
            with self.assertRaisesRegex(ValueError,'PARENT_DERIVATION'):verify_derivation(7,changed,manifest,parent,'a'*64)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_ROWS'):verify_derivation(4,[dict(id='p'),dict(id='p')],{})

    def test_all_six_archives_are_hash_bound_and_preparation_scripts_are_not_executed(self):
        archive=Path(__file__).with_name('frozen_sources')
        for version,(_,filename,generator_sha,prepare_sha) in SPECS.items():
            self.assertTrue(archive_path(archive,BASE+filename,generator_sha).is_file())
            self.assertTrue(archive_path(archive,directory(version)+'/prepare.py',prepare_sha).is_file())
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);payload=b"raise RuntimeError('must not execute')\n";digest=hashlib.sha256(payload).hexdigest()
            (p/'prepare.py').write_bytes(payload)
            (p/'manifest.json').write_text(json.dumps(dict(sources={digest:dict(file='prepare.py',originalPath='build/corpus/prepare.py')})))
            self.assertEqual(p/'prepare.py',archive_path(p,'build/corpus/prepare.py',digest))
            (p/'prepare.py').write_bytes(payload+b'\n')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_IDENTITY'):archive_path(p,'build/corpus/prepare.py',digest)

    def test_selection_manifest_group_file_and_plan_must_agree(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/directory(4);p.mkdir(parents=True)
            metadata=p/'manifest.json';metadata.write_text('{}\n');digest=hashlib.sha256(b'{}\n').hexdigest()
            payload=json.dumps(dict(row=dict(id='p')))+'\n';group_sha=hashlib.sha256(payload.encode()).hexdigest()
            (p/'groups.jsonl').write_text(payload)
            (p/'selection.json').write_text(json.dumps(dict(corpusManifestSha256=digest,groupsSha256=group_sha,groups=1)))
            (p/'plan.json').write_text(json.dumps(dict(groupsSha256=group_sha,groups=1)))
            facts,_=training_chain(root,4,metadata,[dict(id='p')]);self.assertTrue(facts['consistent']);self.assertFalse(facts['modelExecutionEstablished'])
            with self.assertRaisesRegex(ValueError,'TRAINING_GROUP_ROW'):training_chain(root,4,metadata,[dict(id='p',changed=True)])
            metadata.write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'TRAINING_CHAIN'):training_chain(root,4,metadata,[dict(id='p')])

    def test_neuter_homographs_exclude_adverb_and_adjective_readings(self):
        class Dictionary:
            def analyses(self,word):
                return [SimpleNamespace(lemma='полезный')]+([SimpleNamespace(lemma='полезно')] if word=='полезно' else [])
        row=dict(id='r',purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',language='ru',family='полезный',
            candidateForms=['полезно','полезны'],leftContext='',original='полезн',applied='полезно',expectedApplied='полезны')
        entries,counts=exclusions('late',[row],Dictionary(),{'source':'a'*64})
        self.assertEqual(2,counts['dictionaryFamilies'])
        self.assertEqual(keys_for([dict(families=['полезный','полезно'])],'family'),set(entries[0]['keys']['family']))


if __name__=='__main__':unittest.main()
