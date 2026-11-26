import unittest

import import_refinement_article_segments as subject
from holdout_ledger import keys_for


class RefinementArticleSegmentsTest(unittest.TestCase):
    def test_source_partitions_and_parent_identity(self):
        manifest = {'partitions': {p: {'articles': [str(i)]} for i, p in enumerate(('train', 'dev', 'test'), 1)}}
        parents = {'public-ranker-history-' + p: {'keys': {'article': sorted(keys_for([{'article': str(i)}], 'article'))}}
                   for i, p in enumerate(('train', 'dev', 'test'), 1)}
        self.assertEqual({'train': {'1'}, 'dev': {'2'}, 'test': {'3'}}, subject.partition_sets(manifest, parents))
        parents['public-ranker-history-train']['keys']['article'] = []
        with self.assertRaisesRegex(ValueError, 'REFINEMENT_ARTICLE_PARENT'):
            subject.partition_sets(manifest, parents)
        manifest['partitions']['train']['articles'] = ['1', '1']
        with self.assertRaisesRegex(ValueError, 'REFINEMENT_ARTICLE_MANIFEST'):
            subject.partition_sets(manifest, parents)

    def test_complete_source_extraction_refuses_missing_and_duplicate(self):
        collect = subject.article_segments.collect
        sets = {'train': {'1'}, 'dev': {'2'}}
        self.assertTrue(collect(sets, [(['1', '2'], ['Один.', 'Два.'])])['train'])
        with self.assertRaisesRegex(ValueError, 'ARTICLE_SEGMENT_MISSING'):
            collect(sets, [(['1'], ['Один.'])])
        with self.assertRaisesRegex(ValueError, 'ARTICLE_SEGMENT_DUPLICATE'):
            collect(sets, [(['1', '1', '2'], ['Один.', 'Один.', 'Два.'])])


if __name__ == '__main__': unittest.main()
