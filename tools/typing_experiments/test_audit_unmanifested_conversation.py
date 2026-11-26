import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from audit_unmanifested_conversation import audit_rows,quarantine,verify_row,typo_is_derived,SEED
from control_ledger import (
    SCHEMA as CONTROL_SCHEMA, article_key, assert_disjoint as assert_control_disjoint,
    key_for, load as load_controls, surface_key,
)
from holdout_ledger import keys_for,assert_disjoint,validate_ledger
from import_tatoeba_history import sentence_hash
from recover_legacy_holdout import load_generator
from register_recovered_corpus_controls import PREFIX as RECOVERED_PREFIX, missing_entries, verified_rows as verified_recovered_rows
from register_rejected_conversation_controls import ENTRY_PREFIX, EXPERIMENTS, ORIGINAL, PARTS, ROOT, project, verified_rows
from test_holdout_ledger import ledger


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')]


class UnmanifestedAuditTest(unittest.TestCase):
    def setUp(self):
        self.generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
        text='Мы готовы были дома.';digest=sentence_hash(text)
        self.sentences={'123':dict(text=text,normalizedSha256=digest)}
        self.row=dict(id='convo-supervised-train-00000',word='готовы',family='1',prefix='Мы',article='tatoeba:123',sentenceHash=digest,
            selectionHash=hashlib.sha256((SEED+'123'+'готовы'+'Мы').encode()).hexdigest(),language='ru',split='train',
            typed='готвоы',expectedSpelling='готовы',cohort='typo',noAuto=False,group='transposition')

    def test_only_source_captured_derived_rows_are_accepted(self):
        verify_row(self.row,'train',self.sentences,self.generator)
        for change in (dict(prefix='Чужая фраза'),dict(extra='unverified'),dict(family='private-note'),dict(selectionHash='0'*64),dict(typed='чужая фраза')):
            with self.assertRaises(ValueError):verify_row(self.row|change,'train',self.sentences,self.generator)

    def test_typos_and_controls_preserve_the_public_source_token(self):
        self.assertTrue(typo_is_derived('слово','слво','missing_letter'))
        self.assertTrue(typo_is_derived('слово','слоово','repeated_letter'))
        self.assertTrue(typo_is_derived('слово','солво','transposition'))
        self.assertFalse(typo_is_derived('слово','слово','substitution'))
        row=self.row|dict(typed='@готовы',expectedSpelling='@готовы',cohort='correct',noAuto=True,group='protected')
        verify_row(row,'train',self.sentences,self.generator)
        with self.assertRaises(ValueError):verify_row(row|dict(noAuto=False),'train',self.sentences,self.generator)

    def covered_ledger(self):
        base=ledger(False);mapped=self.row|dict(sourceRepository='tatoeba')
        base['entries'].append(dict(id='tt-source',usage='historical-source-exclusion',bindings={'source':'a'*64},
            keys={k:sorted(keys_for([mapped],k)) for k in ('article','sentence')},missingAxes=[]))
        return base

    def test_missing_prepared_train_families_are_quarantined_without_claiming_training(self):
        base=self.covered_ledger();before=copy.deepcopy(base)
        facts=audit_rows([self.row],'train',self.sentences,self.generator,Dictionary(),base)
        self.assertEqual(1,facts['preparedTrainFamiliesNotAlreadySupervised'])
        receipt=dict(counts={'train':facts},bindings={'rows':'a'*64},sourceBindings={'tool':'b'*64})
        updated=quarantine(base,receipt,{'report':'c'*64});self.assertEqual(before,base)
        self.assertTrue(any(e['usage']=='prepared-training-quarantine' for e in updated['entries']))
        after=audit_rows([self.row],'train',self.sentences,self.generator,Dictionary(),updated)
        self.assertEqual('EXCLUSIONS_COMPLETE_FOR_THIS_ARTIFACT',after['status'])
        self.assertFalse(after['modelConsumptionEstablished']);self.assertFalse(after['retrospectiveQualification'])
        # Reusing the context in another source with a different typo stays blocked.
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([self.row|dict(article='456',typed='готовв')],updated,kinds=('context',))

    def test_context_only_exclusion_cannot_hide_other_axes(self):
        base=self.covered_ledger()
        entry=dict(id='context-only',usage='historical-context-exclusion',bindings={'rows':'a'*64},
            keys={'context':sorted(keys_for([self.row],'context'))},missingAxes=[])
        base['entries'].append(entry);validate_ledger(base)
        entry['keys']['family']=sorted(keys_for([dict(families=['готовый'])],'family'))
        with self.assertRaisesRegex(ValueError,'LEDGER_CONTEXT_SCOPE'):validate_ledger(base)
        del entry['keys']['family'];entry['missingAxes']=['family']
        with self.assertRaisesRegex(ValueError,'LEDGER_CONTEXT_SCOPE'):validate_ledger(base)

    def test_family_quarantine_does_not_mask_missing_source_coverage(self):
        facts=audit_rows([self.row],'train',self.sentences,self.generator,Dictionary(),ledger(False))
        self.assertEqual('ADDITIONAL_EXCLUSIONS_REQUIRED',facts['status'])
        self.assertEqual(1,facts['sourceKeys']['article']['notAlreadyExcluded'])

    def test_control_registration_partitions_keys_and_rejects_changed_rows(self):
        protected = self.row | dict(group='protected', typed='@готовы')
        bindings = {'source': 'a' * 64}
        by_kind = {entry['kind']: entry for entry in project([self.row, protected], bindings)}
        for kind, row in [('regression', self.row), ('protected', protected)]:
            self.assertEqual([key_for(row, kind)], by_kind[kind]['keys'])
            self.assertEqual([surface_key('ru', row['typed'])], by_kind[kind]['surfaceKeys'])
        self.assertEqual([article_key(self.row | {'sourceRepository': 'tatoeba'})],
                         by_kind['source']['articleKeys'])
        controls = dict(schema=CONTROL_SCHEMA, publicDataOnly=True, coverageComplete=False,
                        pending=['other sources'], entries=list(by_kind.values()))
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:protected'):
            assert_control_disjoint([protected], controls, 'protected')
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            assert_control_disjoint([self.row | {'prefix': 'Другой контекст'}], controls, 'regression')
        with self.assertRaisesRegex(ValueError, 'CONTROL_ARTICLE_OVERLAP'):
            assert_control_disjoint([self.row | {'typed': 'новое', 'sourceRepository': 'tatoeba'}],
                                    controls, 'regression')
        with tempfile.TemporaryDirectory() as folder:
            corpus = Path(folder)
            payload = (json.dumps(self.row) + '\n').encode()
            expected = {}
            for part in PARTS:
                name = part + '.jsonl'
                (corpus / name).write_bytes(payload)
                expected[(ORIGINAL / name).as_posix()] = hashlib.sha256(payload).hexdigest()
            self.assertEqual([self.row] * 3, list(verified_rows(corpus, expected)))
            (corpus / 'holdout.jsonl').write_bytes(payload + b'\n')
            with self.assertRaisesRegex(ValueError, 'REJECTED_CONVERSATION_ROWS:holdout'):
                list(verified_rows(corpus, expected))
            (corpus / 'manifest.json').touch()
            with self.assertRaisesRegex(ValueError, 'REJECTED_CONVERSATION_MANIFEST'):
                list(verified_rows(corpus, expected))

    def test_registered_control_keys_remain_bound_without_recovered_rows(self):
        ledger = load_controls(ROOT / EXPERIMENTS / 'control-ledger.json')
        early = ('supervised-v2', 'context-feature', 'available-clean-v6')
        joint = ('joint-original', 'joint-followup', 'joint-followup-v3', 'diagnostic-rare-ranking')
        batches = (
            ((ENTRY_PREFIX,), '3f8e7d260e8a00644e28c7a16e56480faf816adb78e1f1c374a1ab75c2d5f983'),
            (tuple(RECOVERED_PREFIX + name + '-' for name in early),
             'a06dd031d14fe8de1f3c58afabb430e9825a438cfa4ba7d9de6f42b14c1e8e81'),
            (tuple(RECOVERED_PREFIX + name + '-' for name in joint),
             'b3c34f184961271baa43f712580629c3e9c00f88bc2083c05723e7792f46547d'),
        )
        for prefixes, digest in batches:
            with self.subTest(prefixes=prefixes):
                entries = [entry for entry in ledger['entries'] if entry['id'].startswith(prefixes)]
                encoded = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
                self.assertEqual(digest, hashlib.sha256(encoded).hexdigest())

    def test_recovered_control_registration_respects_existing_keys_and_refuses_drift(self):
        entries = project([self.row, self.row | {'group': 'protected', 'typed': '@готовы'}],
                          {'source': 'a' * 64})
        previous = entries[0] | {'id': 'earlier-controls'}
        ledger = {'entries': [previous]}
        delta = missing_entries(entries, ledger)
        self.assertEqual(['regression', 'source'], [entry['kind'] for entry in delta])
        self.assertEqual([previous], ledger['entries'])
        ledger['entries'].extend(delta)
        self.assertEqual([], missing_entries(entries, ledger))
        ledger['entries'][1] = ledger['entries'][1] | {'keys': []}
        with self.assertRaisesRegex(ValueError, 'RECOVERED_CONTROL_REGISTRY_DRIFT'):
            missing_entries(entries, ledger)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            raw = (json.dumps(self.row) + '\n').encode()
            (source / 'holdout.jsonl').write_bytes(raw)
            expected = {'holdout.jsonl': hashlib.sha256(raw).hexdigest()}
            self.assertEqual([self.row], list(verified_recovered_rows(source, expected)))
            (source / 'holdout.jsonl').write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'RECOVERED_CONTROL_INPUT:holdout.jsonl'):
                list(verified_recovered_rows(source, expected))


if __name__=='__main__':unittest.main()
