import copy
import hashlib
from types import SimpleNamespace
import unittest

import audit_wordrank_synthetic_labels as audit


class WordrankSyntheticLabelAuditTest(unittest.TestCase):
    def test_full_disclosed_fixture_is_reproducible(self):
        result = audit.audit()
        self.assertEqual(9000, result['rows'])
        self.assertEqual((6000, 1200, 1800), tuple(result['counts'][p] for p in ('train', 'dev', 'test')))
        self.assertFalse(result['historicalHelperIdentityEstablished'])
        self.assertFalse(result['historicalExecutionEstablished'])
        self.assertFalse(result['independentQualification'])

    def test_row_identity_and_synthetic_label_mutations_are_rejected(self):
        helper = SimpleNamespace(digest=lambda data: hashlib.sha256(data).hexdigest())
        selector = {'SEED': 'fixture', 'partition': lambda article: 'train',
                    'mutate': lambda word, identity, edits, vocabulary: (word, [])}
        article, word, prefix = '12', 'word', 'prefix '
        context = helper.digest((prefix.lower() + '\0' + word).encode())
        identity = helper.digest(('fixture:' + article + ':' + context).encode())
        edits = (1, 1, 2, 2, 3, 0)[int(identity[:8], 16) % 6]
        row = {'articleId': article, 'expectedSpelling': word, 'prefix': prefix,
               'id': 'wordrank-' + identity[:24], 'partition': 'train', 'errorCount': edits,
               'language': 'ru', 'family': word, 'template': 'article-' + article, 'split': 'calibration',
               'category': f'edit-{edits}', 'cohort': 'correct' if edits == 0 else 'typo',
               'noAuto': edits == 0, 'typed': word, 'operations': []}
        audit.check_rows([row], selector, helper, set())
        for key, value in [('id', 'wrong'), ('partition', 'test'), ('language', 'en'),
                           ('family', 'wrong'), ('template', 'wrong'), ('split', 'holdout'), ('errorCount', 99),
                           ('category', 'wrong'), ('cohort', 'wrong'), ('noAuto', None),
                           ('typed', 'wrong'), ('operations', ['wrong'])]:
            with self.subTest(field=key):
                changed = copy.deepcopy(row)
                changed[key] = value
                with self.assertRaisesRegex(ValueError, 'WORDRANK_AUDIT_ROW'):
                    audit.check_rows([changed], selector, helper, set())
        with self.assertRaisesRegex(ValueError, 'WORDRANK_AUDIT_ROW'):
            audit.check_rows([row, row], selector, helper, set())

    def test_source_scope_refuses_missing_and_duplicate_definitions(self):
        for source in (b'def other(): pass\n', b'def f(): pass\ndef f(): pass\n'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'WORDRANK_AUDIT_SOURCE_SCOPE'):
                audit.functions(source, ('f',), {})


if __name__ == '__main__':
    unittest.main()
