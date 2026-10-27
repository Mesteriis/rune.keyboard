import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from audit_applied_authored_history import GENERATOR,PRODUCER,PRODUCER_SHA,SPECS,verify_parent,verify_reuse,verify_selection
from audit_authored_training_history import exclusions
from audit_late_authored_history import archive_path
from holdout_ledger import keys_for


def selection_fixture(folder,row):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);metadata=folder/'corpus/manifest.json';metadata.parent.mkdir(exist_ok=True);metadata.write_text('{}\n')
    payload=json.dumps(dict(row=row))+'\n';(folder/'groups.jsonl').write_text(payload);digest=hashlib.sha256(payload.encode()).hexdigest()
    (folder/'selection.json').write_text(json.dumps(dict(groups=1,groupsSha256=digest,corpusManifestSha256=hashlib.sha256(b'{}\n').hexdigest())))
    (folder/'plan.json').write_text(json.dumps(dict(groups=1,groupsSha256=digest)))
    return metadata


class AppliedAuthoredHistoryTest(unittest.TestCase):
    def test_selection_must_embed_exact_reproduced_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            row=dict(id='p',expectedApplied='честна');metadata=selection_fixture(folder,row)
            facts,_=verify_selection(folder,metadata,[row]);self.assertTrue(facts['allGroupRowsMatchCorpus']);self.assertFalse(facts['modelExecutionEstablished'])
            with self.assertRaisesRegex(ValueError,'SELECTED_ROW'):verify_selection(folder,metadata,[row|dict(expectedApplied='честная')])
            metadata.write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'SELECTION_BINDING'):verify_selection(folder,metadata,[row])

    def test_reuse_requires_identical_group_bytes_and_matching_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder)/'parent';alias=Path(folder)/'alias';row=dict(id='p')
            selection_fixture(parent,row);selection_fixture(alias,row)
            facts,_=verify_reuse(alias,parent,[row]);self.assertTrue(facts['exactParentGroupBytes'])
            (alias/'plan.json').write_text(json.dumps(dict(groups=2,groupsSha256='a'*64)))
            with self.assertRaisesRegex(ValueError,'REUSE_PLAN'):verify_reuse(alias,parent,[row])
            (alias/'groups.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'GROUP_REUSE'):verify_reuse(alias,parent,[row])

    def test_parent_extension_keeps_exact_original_labels_order_and_counts(self):
        parent=[dict(id='p',expectedApplied='честна')];rows=parent+[dict(id='new')]
        manifest=dict(oldRows=1,appliedRoleRows=1,oldCorpusSha256='a'*64)
        verify_parent(rows,manifest,parent,'a'*64)
        for changed in (rows[::-1],[parent[0]|dict(expectedApplied='честная')]+rows[1:]):
            with self.assertRaisesRegex(ValueError,'PARENT_DERIVATION'):verify_parent(changed,manifest,parent,'a'*64)

    def test_both_historical_generators_and_unexecuted_driver_are_archived(self):
        archive=Path(__file__).with_name('frozen_sources')
        for _,_,digest,_ in SPECS:self.assertTrue(archive_path(archive,GENERATOR,digest).is_file())
        self.assertTrue(archive_path(archive,PRODUCER,PRODUCER_SHA).is_file())

    def test_alternative_full_adjective_lemma_is_conservatively_excluded(self):
        class Dictionary:
            def analyses(self,word):return [SimpleNamespace(lemma='честный')]+([SimpleNamespace(lemma='честной')] if word=='честная' else [])
        row=dict(id='r',purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',language='ru',family='честный',candidateForms=['честна','честная'],
            leftContext='вот эта ',original='честн',applied='честная',expectedApplied='честна')
        entries,counts=exclusions('applied',[row],Dictionary(),{'source':'a'*64})
        self.assertEqual(2,counts['dictionaryFamilies'])
        self.assertTrue(keys_for([dict(families=['честной'])],'family')<=set(entries[0]['keys']['family']))


if __name__=='__main__':unittest.main()
