import copy
import ast
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from audit_frozen_context_descendants import (SPECS,entries_for,folder,verify_filtered,
    verify_pool_ancestry,verify_variants)
from audit_late_authored_history import archive_path
from holdout_ledger import keys_for
from recover_natural_frozen_corpus import read_metadata, select
from recover_side_context_corpora import EVIDENCE, V5_PLAN, read_v5_plan
from right_context_training_exclusion import exclude_training_contexts


def variants(natural=False):
    base=dict(id='0',source='source',selectionHash='s',article='123',contextHash='a'*64,
        word='готовы',rival='готов',typed='готвоы',prefix='Они',rightContext=' были дома.',
        group='typo',noAuto=False,expectedSpelling='готовы',families=['готовый'],family='готовый')
    if natural:base['cohort']='typo'
    else:base['retainBaseline']=False
    forms=[('готвоы','typo',False,False,' были дома.')]
    if not natural:forms.append(('готвоы','unfinished',False,True,' были'))
    forms.extend([('готовы','correct',True,False,' были дома.'),('@готовы','protected',True,False,' были дома.')])
    rival=('готов','correct_rival',True,False,' были дома.')
    if natural:forms.insert(-1,rival)
    else:forms.append(rival)
    result=[]
    for i,(typed,group,control,retain,suffix) in enumerate(forms):
        row=base|dict(id=str(i),typed=typed,group=group,noAuto=control,rightContext=suffix,
            expectedSpelling=typed if control else base['word'])
        if natural:row['cohort']='correct' if control else 'typo'
        else:row['retainBaseline']=retain
        result.append(row)
    return result


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')] if word in ('готовы','готов') else []


class FrozenDescendantTest(unittest.TestCase):
    def test_recovered_side_receipt_binds_payloads_and_exact_v5_filter(self):
        _, plan = read_v5_plan()
        self.assertFalse(plan['modelScoresUsed'])
        self.assertEqual(38, len(set(plan['excludedFamilies'])))
        receipt = json.loads(V5_PLAN.with_name('side-context-recovery.json').read_bytes())
        expected = json.loads(EVIDENCE.read_bytes())['receipt']['bindings']
        self.assertEqual(14, len(receipt['files']))
        for path, digest in receipt['files'].items():
            self.assertEqual(expected['build/' + path], digest)
        self.assertEqual(35016, sum(part['rows'] for part in receipt['stats'].values()))
        filters = receipt['freshSideV5Exclusions']
        manifest = V5_PLAN.with_name('fresh-side-v5-manifest.json').read_bytes()
        self.assertEqual(SPECS['fresh-side-v5']['manifestSha256'], hashlib.sha256(manifest).hexdigest())
        self.assertEqual(filters, json.loads(manifest)['exclusionAudits'])
        self.assertEqual(0, filters['calibration']['excludedRows'])
        self.assertEqual(4, filters['holdout']['excludedRows'])
        self.assertEqual(1, filters['holdout']['excludedContexts'])

    def test_recovered_natural_plan_and_manifest_bind_original_outputs(self):
        raw_plan, raw_manifest = read_metadata()
        plan, manifest = json.loads(raw_plan), json.loads(raw_manifest)
        root = Path(__file__).resolve().parents[2]
        evidence = root / 'docs/acceptance/2026-10-27-frozen-context-descendants-evidence.json'
        bindings = json.loads(evidence.read_bytes())['receipt']['bindings']
        self.assertEqual(7, len(plan['sourceHashes']))
        self.assertEqual(plan['sourceHashes'], manifest['sourceContextBindings'])
        for name, digest in manifest['files'].items():
            self.assertEqual(bindings['build/right-context-natural-frozen-20261027/corpus/' + name], digest)
        with tempfile.TemporaryDirectory() as directory:
            pools = Path(directory)
            first = Path(next(iter(plan['sourceHashes']))).parent.name
            (pools / (first + '.jsonl')).write_bytes(b'changed pool')
            with self.assertRaisesRegex(ValueError, 'NATURAL_FROZEN_POOL_DIGEST'):
                select(pools, plan, manifest)

    def test_both_variant_constructions_preserve_input_and_source_capture(self):
        for natural in (False,True):
            rows=variants(natural);before=copy.deepcopy(rows)
            self.assertEqual([rows[0]],verify_variants(rows,natural));self.assertEqual(before,rows)

    def test_changed_protected_or_unfinished_variant_cannot_hide_under_same_context(self):
        for index,field,value in [(1,'rightContext',' были дома.'),(3,'expectedSpelling','готовы'),(4,'article','456')]:
            rows=variants();rows[index][field]=value
            with self.assertRaisesRegex(ValueError,'VARIANT_IDENTITY'):verify_variants(rows)

    def test_missing_duplicate_reordered_variants_fail(self):
        for rows in (variants()[:-1],variants()+[variants()[0]],list(reversed(variants()))):
            with self.assertRaises(ValueError):verify_variants(rows)

    def test_whole_context_filter_preserves_exact_parent_order_and_audit(self):
        parent=variants();other=[r|dict(id='other-'+r['id'],contextHash='b'*64,families=['другой'],family='другой') for r in variants()]
        parent+=other;kept,audit=exclude_training_contexts(parent,['готовый'])
        self.assertEqual(audit,verify_filtered(parent,kept,['готовый'],audit))
        for changed,changed_audit in [(list(reversed(kept)),audit),(kept,audit|dict(excludedRows=0)),(parent,audit)]:
            with self.assertRaisesRegex(ValueError,'FILTER_LINEAGE'):verify_filtered(parent,changed,['готовый'],changed_audit)

    def test_natural_capture_requires_exact_pinned_pool_ancestry(self):
        row=variants(True)[0];parent={k:row[k] for k in ('source','selectionHash','word','typed','prefix','rightContext','article')}
        verify_pool_ancestry([row],[parent])
        for changed in (parent|dict(prefix='Другой'),parent|dict(source='other')):
            with self.assertRaisesRegex(ValueError,'POOL_ANCESTRY'):verify_pool_ancestry([row],[changed])
        with self.assertRaisesRegex(ValueError,'POOL_DUPLICATES'):verify_pool_ancestry([row],[parent,parent])

    def test_dictionary_families_ignore_declared_stems_and_corrupt_protected_strings(self):
        rows=variants();rows=[r|dict(family='12345',families=['12345']) for r in rows]
        entries,counts=entries_for('fixture','holdout',rows,[rows[0]],Dictionary(),{'file':'b'*64})
        self.assertEqual(keys_for([dict(families=['готовый'])],'family'),set(entries[0]['keys']['family']))
        self.assertEqual([],counts['unresolved']);self.assertEqual(1,counts['dictionaryFamilies'])

    def test_unknown_canonical_candidate_keeps_family_coverage_incomplete(self):
        rows=variants();capture=rows[0]|dict(rival='неизвестно')
        entries,counts=entries_for('fixture','holdout',rows,[capture],Dictionary(),{'file':'b'*64})
        self.assertEqual(['family'],entries[0]['missingAxes']);self.assertEqual('rival',counts['unresolved'][0]['field'])
        self.assertEqual('historical-family-exclusion',entries[1]['usage'])

    def test_four_preparation_archives_survive_without_build(self):
        archive=Path(__file__).with_name('frozen_sources')
        for name,spec in SPECS.items():
            self.assertTrue(archive_path(archive,folder(name)+'/'+spec['script'],spec['scriptSha256']).is_file())

    def test_sentence_preparation_chain_matches_original_evidence(self):
        root=Path(__file__).resolve().parents[2]
        archive=Path(__file__).with_name('frozen_sources')
        for evidence,path in (
            ('2026-10-27-right-context-other-part-training-evidence.json',
             'build/right-context-reliable-side-v5-20261027/prepare.py'),
            ('2026-10-27-right-context-role-kotlin-evidence.json',
             'build/right-context-sentence-corpus-v6-20261027/prepare.py'),
            ('2026-10-27-right-context-source-parity-and-selection-evidence.json',
             'build/right-context-sentence-pairs-v2-v6-20261027/prepare.py'),
        ):
            with self.subTest(path=path):
                record=json.loads((root/'docs/acceptance'/evidence).read_text())
                self.assertTrue(archive_path(archive,path,record['bindings'][path]).is_file())

    def test_unattested_available_v6_source_snapshots_are_stable(self):
        directory=Path(__file__).with_name('historical_provenance_sources')
        snapshots=(('available_calibration_v6_reconstructed.py',
                    'eaf5b962490ae7d4572efb4c5ef502be03257a0deebf022cc5b6c6bbaec4211d'),
                   ('available_clean_v6_reconstructed.py',
                    '28cd94ab4f4df8f9a85691f4e6e152047559cca36c1aee02fab6693c70838325'))
        for name,expected in snapshots:
            with self.subTest(name=name):
                raw=(directory/name).read_bytes()
                self.assertEqual(expected,hashlib.sha256(raw).hexdigest())
                ast.parse(raw,filename=name)

    def test_noun_case_preparer_matches_frozen_cohort_manifest(self):
        root = Path(__file__).resolve().parents[2]
        evidence = root / 'docs/acceptance/2026-10-26-noun-case-training-evidence.json'
        digest = json.loads(evidence.read_bytes())['cohortManifest']['preparerSha256']
        archive = Path(__file__).with_name('frozen_sources')
        path = archive_path(archive, 'build/noun-case-focus-v3-20261026/prepare.py', digest)
        ast.parse(path.read_bytes(), filename=path.name)

    def test_earlier_v6_source_snapshots_are_stable(self):
        directory = Path(__file__).with_name('historical_provenance_sources')
        snapshots = {
            'grammar_focused_preparer.py': '3a933cb6764555d5a9c6cee39cb834f82ef6a5f6df9aafc5c55a2f08de7420da',
            'noun_focus_v2_preparer.py': '79e2c466c4b12ae3297c8c1d6fb4f855ee7e7146ae5c39d3397630f4f623f731',
            'noun_broad_v2_preparer.py': 'a7840751e07a3f2b379d500d9c30a2dfc43cc5a8298824a92a4215b5169f2f7d',
            'noun_instrumental_preparer.py': '7db34adc55ebca18ac0d01334482d7a13587adb4e193cca34b63b806f8e99553',
            'right_context_focused_v2_preparer.py': '8e2b6ebce4ea21e812d6dc96b9a3379c965586e48d468104c4359b417c628cf9',
            'right_context_fresh_matched_v5_preparer.py': '66d98a53b16d1db21f7059c367d76602e58b97a590ab56300adab8ad166dd2c9',
        }
        for name, digest in snapshots.items():
            with self.subTest(name=name):
                raw = (directory / name).read_bytes()
                self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
                ast.parse(raw, filename=name)


if __name__=='__main__':unittest.main()
