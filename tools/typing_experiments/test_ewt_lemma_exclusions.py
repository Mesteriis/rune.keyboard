import copy
import json
import unittest

import english_family_keys as family
import ewt_lemma_exclusions as subject
import holdout_ledger as lexical


class EwtLemmaExclusionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=subject.FIXTURE.read_bytes()
        cls.ledger=json.loads(subject.LEDGER.read_bytes())

    def test_real_fixture_and_parent_are_bound_and_detect_known_overlap(self):
        value=subject.fixture(self.raw)
        self.assertIn(family.key_for('go'),value['keys'])
        self.assertEqual(10485,len(value['keys']))
        entry=subject.entry(self.ledger,self.raw)
        self.assertEqual('historical-family-exclusion',entry['usage'])
        self.assertFalse(value['independentQualification'])
        self.assertFalse(value['familyCoverageComplete'])

    def test_tampered_fixture_and_parent_fail(self):
        changed=json.loads(self.raw)
        changed['keys'][0]='invalid'
        with self.assertRaisesRegex(ValueError,'EWT_LEMMA_FIXTURE'):
            subject.fixture(json.dumps(changed).encode())
        changed=json.loads(self.raw)
        changed['counts']['outsideVocabularyRows']=0
        with self.assertRaisesRegex(ValueError,'EWT_LEMMA_FIXTURE'):
            subject.fixture(json.dumps(changed).encode())
        ledger=copy.deepcopy(self.ledger)
        next(x for x in ledger['entries'] if x['id']==subject.PARENT)['rowCount']+=1
        with self.assertRaisesRegex(ValueError,'EWT_LEMMA_PARENT'):
            subject.parent(ledger)

    def test_raw_sources_and_vocabulary_are_hash_pinned(self):
        with self.assertRaisesRegex(ValueError,'EWT_LEMMA_SOURCE_DRIFT'):
            subject.extract({},subject.ewt.LOCK.read_bytes(),b'bad vocabulary',self.ledger)
        with self.assertRaisesRegex(ValueError,'EWT_SOURCE_SET'):
            subject.extract({},subject.ewt.LOCK.read_bytes(),subject.VOCAB.read_bytes(),self.ledger)

    def test_committed_entry_matches_source_bound_fixture(self):
        expected=subject.entry(self.ledger,self.raw)
        actual=[e for e in lexical.validate_ledger(copy.deepcopy(self.ledger))['entries'] if e['id']==subject.ENTRY]
        self.assertEqual([expected],actual)


if __name__=='__main__':unittest.main()
