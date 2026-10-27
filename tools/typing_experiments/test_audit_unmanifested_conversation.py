import copy
import hashlib
from types import SimpleNamespace
import unittest
from audit_unmanifested_conversation import audit_rows,quarantine,verify_row,typo_is_derived,SEED
from holdout_ledger import keys_for,assert_disjoint,validate_ledger
from import_tatoeba_history import sentence_hash
from recover_legacy_holdout import load_generator
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


if __name__=='__main__':unittest.main()
