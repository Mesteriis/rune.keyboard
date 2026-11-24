import copy
import json
import unittest

import holdout_ledger as lexical
import control_ledger as control
import english_family_keys as family
import public_corpus_preparation_v1 as preparation
import register_ewt_error_targets as subject


class RegisterEwtErrorTargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=subject.FIXTURE.read_bytes()
        cls.ledger=json.loads(subject.LEDGER.read_bytes())

    def test_fixture_is_frozen_and_entry_is_in_real_ledger(self):
        value=subject.receipt(self.raw)
        expected=subject.entry(self.ledger,self.raw)
        entries=lexical.validate_ledger(copy.deepcopy(self.ledger))['entries']
        self.assertEqual([expected],[e for e in entries if e['id']==subject.ENTRY])
        self.assertEqual(425,len(value['targetSurfaceKeys']))
        self.assertFalse(value['results']['independentQualification'])

    def test_mutated_receipt_and_parent_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'EWT_TARGET_RECEIPT_DRIFT'):
            subject.receipt(self.raw+b' ')
        altered=copy.deepcopy(self.ledger)
        next(e for e in altered['entries'] if e['id']==subject.parent.PARENT)['rowCount']+=1
        with self.assertRaisesRegex(ValueError,'EWT_LEMMA_PARENT'):
            subject.entry(altered,self.raw)

    def test_new_public_target_is_refused_by_real_preflight(self):
        old=copy.deepcopy(self.ledger)
        old['entries']=[e for e in old['entries'] if e['id']!=subject.ENTRY]
        known={key for entry in lexical.validate_ledger(copy.deepcopy(old))['entries'] for key in entry['keys'].get('family',[])}
        new=set(subject.receipt(self.raw)['targetSurfaceKeys'])-known
        self.assertEqual(109,len(new))
        word=next(word for word in subject.model.parse_vocab(subject.model.VOCAB.read_bytes())
                  if family.key_for(word) in new)
        row=dict(id='ewt-target-probe',language='en',sourceRepository='tatoeba',article='tatoeba:123',
            sentenceHash='b'*64,englishLemmas=[word],prefix='unique public probe ',typed=word,
            noAuto=True,cohort='protected',expectedCandidate=0,candidates=[' '+word])
        controls=control.load(subject.ROOT/'tools/typing_experiments/control-ledger.json')
        before=preparation.preflight([row],'protected',old,controls,'new-families')
        after=preparation.preflight([row],'protected',copy.deepcopy(self.ledger),controls,'new-families')
        self.assertEqual(0,before['lexicalOverlaps']['family'])
        self.assertEqual(1,after['lexicalOverlaps']['family'])
        self.assertEqual('BLOCKED_OVERLAP',after['status'])
        self.assertIn('en',after['unsupportedLexicalLanguages'])


if __name__=='__main__':unittest.main()
