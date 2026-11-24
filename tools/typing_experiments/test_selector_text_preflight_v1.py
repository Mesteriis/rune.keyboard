import unittest
from types import SimpleNamespace

import selector_text_preflight_v1 as subject
from test_holdout_ledger import ledger, row as historical_row
from test_public_corpus_preparation_v1 import candidate, controls


class Lexicon:
    def analyses(self, word):
        return [] if word == 'неизвестно' else [SimpleNamespace(lemma=word)]


def sample():
    texts = {'train': [{'articleId':'901', 'text':'мы слово'}],
             'dev': [{'articleId':'902', 'text':'кот'}],
             'test': [{'articleId':'903', 'text':'сад'}]}
    return texts, {part:[] for part in texts}, {'901':'мы слово', '902':'кот', '903':'сад'}


class SelectorTextPreflightTest(unittest.TestCase):
    def assess(self, texts, rows, sources, registry=None):
        return subject.assess(texts, rows, sources, Lexicon(), ledger(False), registry or controls())

    def test_clean_disjoint_text_still_cannot_publish(self):
        texts, rows, sources = sample()
        result = self.assess(texts, rows, sources)
        self.assertEqual('BLOCKED_COVERAGE', result['status'])
        self.assertFalse(result['publicationPermitted'])
        self.assertFalse(result['sourceIdentityVerified'])
        self.assertFalse(result['independentQualification'])

    def test_word_rows_cannot_hide_historical_lexical_or_control_overlap(self):
        for word_row, axis in (
                (historical_row(partition='train', language='ru'), 'lexical'),
                (historical_row(partition='train', language='ru', article='777', families=['редчайший'],
                                contextHash='f'*64), 'control')):
            with self.subTest(axis=axis):
                texts, rows, sources = sample()
                rows['train'].append(word_row)
                result = self.assess(texts, rows, sources)
                self.assertEqual('BLOCKED_OVERLAP', result['status'])
                self.assertGreater(result['historicalOverlapCount'], 0)
                self.assertFalse(result['publicationPermitted'])

    def test_word_rows_check_protected_context_even_if_text_is_disjoint(self):
        texts, rows, sources = sample()
        rows['train'].append(candidate(partition='train', article='900', families=['проверка'],
            typed='API36', expectedSpelling='проверка', prefix='Сохранить'))
        result = self.assess(texts, rows, sources)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['wordRowPreflight']['controlOverlaps']['protected'])

    def test_word_row_identity_errors_are_reported(self):
        texts, rows, sources = sample()
        incomplete = candidate(partition='train')
        del incomplete['id']
        rows['train'].append(incomplete)
        result = self.assess(texts, rows, sources)
        self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
        self.assertIn('row-id', result['wordRowPreflight']['identityErrors'])
        self.assertFalse(result['publicationPermitted'])

    def test_english_surface_overlap_is_counted_as_historical_exposure(self):
        texts, rows, sources = sample()
        rows['train'].append(candidate(partition='train', language='en', sourceRepository='tatoeba',
            article='tatoeba:999999999', sentenceHash='f'*64,
            prefix='we ', typed='went', expectedSpelling='went'))
        result = self.assess(texts, rows, sources)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['wordRowPreflight']['englishSourceSurfaceOverlaps'])
        self.assertGreater(result['historicalOverlapCount'], 0)
        self.assertFalse(result['publicationPermitted'])

    def test_protected_and_punctuation_contexts_are_both_checked(self):
        texts, rows, sources = sample()
        registry = controls()
        for kind in ('protected', 'punctuation'):
            row = dict(language='ru', prefix='мы ', typed='слово', currentWord='слово', expectedBoundary=' ')
            registry['entries'].append(dict(id='extra-'+kind, kind=kind, language='ru', rowCount=1,
                bindings={'file':'a'*64}, keys=[subject.control.key_for(row,kind)]))
        result = self.assess(texts, rows, sources, registry)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual({'protected':1,'punctuation':1}, result['additionalControlOverlaps'])

    def test_source_compound_unknown_and_truncation_are_blocked(self):
        for fragment, source, field in [('северо запад','северо-запад','sourceTokenFragments'),
                                        ('д артаньян', "д'артаньян", 'sourceTokenFragments'),
                                        ('д артаньян', 'д’артаньян', 'sourceTokenFragments'),
                                        ('неизвестно','неизвестно','unresolvedSurfaces'),
                                        ('доми','домик','truncatedInsideWord')]:
            texts, rows, sources = sample()
            texts['train'][0]['text'] = fragment; sources['901'] = source
            result = self.assess(texts, rows, sources)
            self.assertGreater(result['textIdentityBlockers'][field], 0)
            self.assertFalse(result['publicationPermitted'])

    def test_original_source_punctuation_context_is_checked(self):
        texts, rows, sources = sample()
        sources['901'] = 'Мы, слово'
        registry = controls()
        row = dict(language='ru', prefix='Мы, ', typed='слово')
        registry['entries'].append(dict(id='source-protected', kind='protected', language='ru', rowCount=1,
            bindings={'file':'a'*64}, keys=[subject.control.key_for(row, 'protected')]))
        result = self.assess(texts, rows, sources, registry)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['additionalControlOverlaps']['protected'])

    def test_quotes_around_complete_words_are_not_internal_apostrophes(self):
        for source in ("'слово'", '’слово’'):
            with self.subTest(source=source):
                texts, rows, sources = sample()
                texts['train'][0]['text'] = 'слово'
                sources['901'] = source
                result = self.assess(texts, rows, sources)
                self.assertEqual(0, result['textIdentityBlockers']['sourceTokenFragments'])

    def test_split_leakage_and_duplicate_articles_are_rejected(self):
        texts, rows, sources = sample()
        texts['dev'][0]['text'] = 'слово'; sources['902'] = 'слово'
        result = self.assess(texts, rows, sources)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertGreater(result['crossPartitionOverlapCount'], 0)
        texts['dev'][0]['articleId'] = '901'
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DUPLICATE_ARTICLE'):
            self.assess(texts, rows, sources)

    def test_wrong_source_and_missing_partition_fail_closed(self):
        texts, rows, sources = sample()
        sources['901'] = 'совсем другое'
        with self.assertRaisesRegex(ValueError, 'TEXT_AUDIT_SOURCE_MISMATCH'):
            self.assess(texts, rows, sources)
        texts, rows, sources = sample()
        texts['test'] = []
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_EMPTY_PARTITION'):
            self.assess(texts, rows, sources)


if __name__ == '__main__':
    unittest.main()
