import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from audit_authored_training_history import SPECS,archived_generator,exclusions,training_chain,unproven_examples,verify_payload
from holdout_ledger import assert_disjoint
from test_holdout_ledger import ledger


class Dictionary:
    def analyses(self,word):
        return [SimpleNamespace(lemma=w) for w in ('красивый','красить')] if word in ('красив','красивы') else []


def row():
    return dict(id='template-1',purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',language='ru',
        family='красивый',candidateForms=['красив','красивы'],leftContext='',rightContext=' они ',
        original='краси',applied='краси',expectedApplied='краси')


class AuthoredHistoryTest(unittest.TestCase):
    def test_all_ambiguous_dictionary_readings_are_excluded_without_guessing_typos(self):
        entries,counts=exclusions('test',[row()],Dictionary(),{'source':'a'*64})
        self.assertEqual(2,counts['dictionaryFamilies']);self.assertEqual('prepared-training-quarantine',entries[0]['usage'])
        base=ledger(False);base['entries'].extend(entries)
        for lemma in ('красить','красивый'):
            with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
                assert_disjoint([dict(families=[lemma])],base,kinds=('family',),usages=('prepared-training-quarantine',))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([dict(prefix='',typed='другаяопечатка',expectedSpelling='красивы')],base,kinds=('context',))
        self.assertEqual(3,counts['contexts'])

    def test_unknown_declared_family_or_candidate_cannot_be_promoted(self):
        for change in (dict(family='выдуманный'),dict(candidateForms=['неизвестно','красивы']),dict(split='holdout')):
            with self.assertRaises(ValueError):exclusions('test',[row()|change],Dictionary(),{'source':'a'*64})

    def test_exact_reproduction_checks_count_labels_and_order(self):
        rows=[row(),row()|dict(id='template-2')]
        payload=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows).encode();digest=hashlib.sha256(payload).hexdigest()
        manifest=dict(rows=2,corpusSha256=digest)
        self.assertEqual(payload,verify_payload(rows,manifest,digest))
        for changed in (rows[::-1],rows[:1],[rows[0]|dict(expectedApplied='чужой')]+rows[1:]):
            with self.assertRaisesRegex(ValueError,'REPRODUCTION_MISMATCH'):verify_payload(changed,manifest,digest)

    def test_three_archived_generators_are_loadable_and_tampering_is_rejected(self):
        archive=Path(__file__).with_name('frozen_sources')
        for _,_,digest,_,_ in SPECS:
            module,path=archived_generator(archive,digest);self.assertTrue(callable(module.generate))
            with tempfile.TemporaryDirectory() as folder:
                copied=Path(folder);(copied/'manifest.json').write_text(json.dumps(dict(sources={digest:dict(file=path.name,originalPath='tools/typing_experiments/right_context_contrast_corpus.py')})))
                (copied/path.name).write_bytes(path.read_bytes()+b'\n')
                with self.assertRaisesRegex(ValueError,'GENERATOR_IDENTITY'):archived_generator(copied,digest)

    def test_training_chain_rejects_mismatched_group_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'groups.jsonl').write_text('{}\n');digest=hashlib.sha256(b'{}\n').hexdigest()
            (p/'selection.json').write_text(json.dumps(dict(corpusSha256='a'*64,groupsSha256=digest,acceptedGroups=1)))
            (p/'plan.json').write_text(json.dumps(dict(groupsSha256=digest,groups=1)))
            facts,_=training_chain(p,'a'*64);self.assertTrue(facts['consistent']);self.assertFalse(facts['modelExecutionEstablished'])
            (p/'groups.jsonl').write_text('{}\n{}\n')
            with self.assertRaisesRegex(ValueError,'TRAINING_CHAIN'):training_chain(p,'a'*64)

    def test_matching_unproven_examples_do_not_leak_text_or_corpus_fingerprints(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);payload=b'{"prefix":"fixture-private-content"}\n';digest=hashlib.sha256(payload).hexdigest()
            (p/'authored.jsonl').write_bytes(payload);(p/'authored-manifest.json').write_text(json.dumps(dict(rows=1,sha256=digest)))
            facts=unproven_examples(p);encoded=json.dumps(facts)
            self.assertTrue(facts['manifestMatchesObservedRows']);self.assertEqual('UNPROVEN_ORIGIN',facts['provenanceStatus'])
            self.assertFalse(facts['imported']);self.assertNotIn(digest,encoded);self.assertNotIn('fixture-private-content',encoded)
            (p/'authored.jsonl').write_bytes(payload+b'{}\n')
            self.assertFalse(unproven_examples(p)['manifestMatchesObservedRows'])


if __name__=='__main__':unittest.main()
