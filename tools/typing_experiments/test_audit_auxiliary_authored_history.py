import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_auxiliary_authored_history import BASE,SPECS,folder,source_path,verify_combination,verify_residual_reuse
from audit_late_authored_history import archive_path


def write_parent(root,name,identity):
    p=Path(root)/folder(name);p.mkdir(parents=True,exist_ok=True)
    (p/'groups.jsonl').write_text(json.dumps(dict(row=dict(id=identity)))+'\n');(p/'selection.json').write_text('{}\n')


def write_combination(root,name,parents,*,reverse=False):
    root=Path(root);p=root/folder(name);p.mkdir(parents=True,exist_ok=True)
    records=[json.loads(line) for parent in parents for line in (root/folder(parent)/'groups.jsonl').read_text().splitlines()]
    if reverse:records.reverse()
    payload=''.join(json.dumps(r)+'\n' for r in records);(p/'groups.jsonl').write_text(payload)
    bindings={folder(parent)+'/selection.json':hashlib.sha256((root/folder(parent)/'selection.json').read_bytes()).hexdigest() for parent in parents}
    (p/'selection.json').write_text(json.dumps(dict(purpose='COMBINED_AUTHORED_NATIVE_GROUPS',groups=len(records),groupsSha256=hashlib.sha256(payload.encode()).hexdigest(),parentSelections=bindings)))


class AuxiliaryAuthoredHistoryTest(unittest.TestCase):
    def test_exact_parent_order_is_required_even_when_all_hashes_match(self):
        with tempfile.TemporaryDirectory() as root:
            write_parent(root,'a','a');write_parent(root,'b','b');write_combination(root,'combined',('a','b'))
            facts,_=verify_combination(root,'combined',('a','b'));self.assertTrue(facts['exactOrderedParentGroups'])
            write_combination(root,'combined',('a','b'),reverse=True)
            with self.assertRaisesRegex(ValueError,'COMBINATION_LINEAGE'):verify_combination(root,'combined',('a','b'))

    def test_parent_receipt_changes_cannot_reuse_an_old_combination(self):
        with tempfile.TemporaryDirectory() as root:
            write_parent(root,'a','a');write_combination(root,'combined',('a',))
            (Path(root)/folder('a')/'selection.json').write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'COMBINATION_LINEAGE'):verify_combination(root,'combined',('a',))

    def test_duplicate_group_rows_are_not_independent_combined_examples(self):
        with tempfile.TemporaryDirectory() as root:
            write_parent(root,'a','same');write_parent(root,'b','same');write_combination(root,'combined',('a','b'))
            with self.assertRaisesRegex(ValueError,'COMBINATION_LINEAGE'):verify_combination(root,'combined',('a','b'))

    def test_residual_reuse_requires_bytes_and_plan_count(self):
        with tempfile.TemporaryDirectory() as root:
            write_parent(root,'parent','p');write_parent(root,'residual','p');p=Path(root)/folder('residual')
            digest=hashlib.sha256((p/'groups.jsonl').read_bytes()).hexdigest()
            (p/'plan.json').write_text(json.dumps(dict(groups=1,groupsSha256=digest)))
            facts,_=verify_residual_reuse(root,'residual','parent');self.assertFalse(facts['modelExecutionEstablished'])
            (p/'plan.json').write_text(json.dumps(dict(groups=2,groupsSha256=digest)))
            with self.assertRaisesRegex(ValueError,'RESIDUAL_REUSE'):verify_residual_reuse(root,'residual','parent')

    def test_source_paths_are_resolved_only_to_declared_local_inputs(self):
        directory=folder('left-sequence-v1');allowed={directory+'/prepare.py',BASE+'grammar_contrast_corpus.py'}
        self.assertEqual(directory+'/prepare.py',source_path('/old/checkout/'+directory+'/prepare.py',directory,allowed))
        for raw in ('../../private.py','/different/build/unknown/prepare.py','tools/other.py'):
            with self.assertRaisesRegex(ValueError,'SOURCE_PATH'):source_path(raw,directory,allowed)

    def test_eight_exact_generator_and_preparation_archives_survive_without_build(self):
        archive=Path(__file__).with_name('frozen_sources');paths=set()
        for name,module,digest,producer_sha,_,_ in SPECS:
            directory=folder('left-sequence-v1') if name=='left-sequence-v1-v2' else folder(name)
            paths.add(archive_path(archive,BASE+module,digest));paths.add(archive_path(archive,directory+'/prepare.py',producer_sha))
        self.assertEqual(8,len(paths))


if __name__=='__main__':unittest.main()
