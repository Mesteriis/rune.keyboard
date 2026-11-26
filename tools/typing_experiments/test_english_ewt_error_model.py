import unittest
from pathlib import Path
import tempfile
from unittest import mock

import english_ewt_error_model as subject


class EnglishEwtErrorModelTest(unittest.TestCase):
    def test_single_edits_and_candidate_generation(self):
        self.assertEqual(('transpose','h','e'),subject.one_edit('the','teh'))
        self.assertEqual(('delete','o'),subject.one_edit('book','bok'))
        self.assertEqual(('insert','o'),subject.one_edit('bok','book'))
        self.assertEqual(('substitute','a','o'),subject.one_edit('cat','cot'))
        for a,b in (('same','same'),('foo','quux'),('bad-word','badword')):
            self.assertIsNone(subject.one_edit(a,b))
        choices=subject.candidates('teh',{'the':100,'ten':90,'tea':80})
        self.assertIn('the',choices)
        self.assertNotIn('teh',choices)
        self.assertEqual(('transpose','h','e'),choices['the'])

    def test_split_excludes_exact_seen_targets_and_protects_known_originals(self):
        def row(typed,target):return (typed,target,subject.one_edit(target,typed))
        groups={'train':[row('teh','the')], 'dev':[row('teh','the'),row('cta','cat')],
                'test':[row('cta','cat'),row('dgo','dog'),row('dog','dig')]}
        result=subject.evaluate(groups,{'the':100,'cat':90,'dog':80,'dig':70})
        self.assertEqual(1,result['developmentExcludedTargetOverlap'])
        self.assertEqual(1,result['testExcludedTargetOverlap'])
        self.assertEqual(1,result['test']['protectedOriginal'])
        self.assertEqual(1,result['test']['scored'])
        self.assertFalse(result['independentQualification'])
        self.assertNotIn('channel',result)

    def test_empty_split_cannot_generate_claim(self):
        with self.assertRaisesRegex(ValueError,'EWT_MODEL_EMPTY_TRAIN'):
            subject.evaluate({'train':[],'dev':[],'test':[]},{})
        with self.assertRaisesRegex(ValueError,'EWT_MODEL_EMPTY_DEVELOPMENT'):
            subject.evaluate({'train':[('teh','the',('transpose','h','e'))],'dev':[],'test':[]},{'the':5})

    def test_source_partitions_must_have_disjoint_documents(self):
        def source(document):
            return ('# newdoc id = '+document+'\n1\tteh\t_\tX\t_\t_\t0\troot\t_\tCorrectForm=the\n').encode()
        data={f'en_ewt-ud-{p}.conllu':source('same' if p!='test' else 'different') for p in subject.PARTS}
        with mock.patch.object(subject.ewt,'rows_from_sources',return_value=[None]*16622):
            with self.assertRaisesRegex(ValueError,'EWT_MODEL_DOCUMENT_OVERLAP'):
                subject.annotations(data,{})

    def test_pinned_source_and_vocabulary_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            lock=Path(folder)/'lock.json';lock.write_bytes(b'fake')
            with mock.patch.object(subject.ewt,'LOCK',lock):
                with self.assertRaisesRegex(ValueError,'EWT_MODEL_INPUT_DRIFT'):
                    subject.run(Path(folder))
        with self.assertRaisesRegex(ValueError,'EWT_MODEL_VOCAB'):
            subject.parse_vocab(b'word zero\n')


if __name__=='__main__':unittest.main()
