import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import selector_text_preflight_files_v1 as subject
from test_holdout_ledger import ledger
from test_public_corpus_preparation_v1 import candidate, controls
from test_selector_text_preflight_v1 import Lexicon, sample


class Dictionary(Lexicon):
    def receipt(self):
        return {'test': 'dictionary-only'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class TextPreflightFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source.parquet'; self.source.write_bytes(b'public source fixture')
        self.lock = self.root/'lock.json'
        self.lock.write_text(json.dumps({'wikipediaContext':{'files':{'ru-0007.parquet':
            {'bytes':self.source.stat().st_size, 'sha256':sha(self.source.read_bytes())}}}}))
        self.lex = self.root/'lex.json'; self.lex.write_text(json.dumps(ledger(False)))
        self.ctrl = self.root/'control.json'; self.ctrl.write_text(json.dumps(controls()))
        self.data = self.root/'data'; self.data.mkdir()
        texts, rows, self.sources = sample()
        files = {}
        for part in subject.PARTS:
            for kind, values in (('text', texts[part]), ('rows', rows[part])):
                name = f'{part}-{kind}.jsonl'
                raw = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in values).encode()
                (self.data/name).write_bytes(raw); files[name] = sha(raw)
        self.manifest = self.data/'manifest.json'
        self.manifest.write_text(json.dumps(dict(containsPersonalMessages=False,
            sourceSha256=sha(self.source.read_bytes()), files=files)))

    def batches(self, path):
        yield list(self.sources), list(self.sources.values())

    def run_preflight(self, reader=None):
        return subject.assess_files(self.data, self.source, self.lock, self.lex, self.ctrl,
                                    Dictionary(), reader or self.batches)

    def set_word_row(self, row):
        path = self.data/'train-rows.jsonl'
        path.write_text(json.dumps(row, ensure_ascii=False)+'\n')
        manifest = json.loads(self.manifest.read_bytes())
        manifest['files'][path.name] = sha(path.read_bytes())
        self.manifest.write_text(json.dumps(manifest))

    def source_bound_row(self, text='когда мы уже домик сегодня'):
        self.sources['904'] = text
        match = re.search('домик', text)
        return candidate(partition='train', article='904', articleId='904', families=['домик'],
            typed='домк', expectedSpelling='домик', prefix=text[:match.start()],
            sourceSegmentHash=subject.holdout_ledger.source_segment_hash(text),
            contextHash=subject.source_context_hash(text, match, subject.selector.load_generator()))

    def test_bound_source_and_inputs_never_permit_publication(self):
        result = self.run_preflight()
        self.assertEqual('BLOCKED_COVERAGE', result['status'])
        self.assertTrue(result['sourceIdentityVerified'])
        self.assertFalse(result['sourceDecoderAttested'])
        self.assertFalse(result['publicationPermitted'])
        self.assertEqual(sha(self.source.read_bytes()), result['bindings']['sourceSha256'])
        self.assertEqual(sha(self.lock.read_bytes()), result['bindings']['inputs']['source-lock.json'])

    def test_bound_word_row_overlap_is_not_hidden_by_clean_text(self):
        row = candidate(partition='train', article='900', families=['проверка'],
                        typed='API36', expectedSpelling='проверка', prefix='Сохранить')
        path = self.data/'train-rows.jsonl'
        path.write_text(json.dumps(row, ensure_ascii=False)+'\n')
        manifest = json.loads(self.manifest.read_bytes())
        manifest['files'][path.name] = sha(path.read_bytes())
        self.manifest.write_text(json.dumps(manifest))
        result = self.run_preflight()
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['wordRowPreflight']['controlOverlaps']['protected'])
        self.assertEqual(1, result['wordRowSourceAttestation']['invalidIdentity'])
        self.assertIn('public_corpus_preparation_v1.py', result['bindings']['helpers'])
        self.assertFalse(result['publicationPermitted'])

    def test_word_only_article_is_verified_against_source_and_dictionary(self):
        self.set_word_row(self.source_bound_row())
        result = self.run_preflight()
        self.assertEqual('BLOCKED_COVERAGE', result['status'])
        self.assertEqual(1, result['wordRowSourceAttestation']['verified'])
        self.assertFalse(result['sourceDecoderAttested'])
        self.assertFalse(result['sourceLabelsQualified'])
        self.assertIn('qualification-v2/generate_corpus.py', result['bindings']['helpers'])
        self.assertFalse(result['publicationPermitted'])

    def test_forged_context_family_and_article_are_not_attested(self):
        for change, reason in (({'contextHash':'e'*64}, 'unmatchedSource'),
                               ({'sourceSegmentHash':'e'*64}, 'unmatchedSource'),
                               ({'families':['стена']}, 'dictionaryMismatch'),
                               ({'article':'905'}, 'invalidIdentity')):
            with self.subTest(reason=reason):
                row = self.source_bound_row() | change
                self.set_word_row(row)
                result = self.run_preflight()
                self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
                self.assertEqual(1, result['wordRowSourceAttestation'][reason])
                self.assertFalse(result['publicationPermitted'])

    def test_missing_row_article_and_partial_source_token_are_not_attested(self):
        row = self.source_bound_row()
        self.set_word_row(row)
        del self.sources['904']
        result = self.run_preflight()
        self.assertEqual(1, result['wordRowSourceAttestation']['missingArticle'])
        self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
        self.set_word_row(self.source_bound_row('когда мы уже домик-левый сегодня'))
        result = self.run_preflight()
        self.assertEqual(1, result['wordRowSourceAttestation']['unmatchedSource'])
        self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
        for apostrophe in ("'", '’', 'ʼ'):
            with self.subTest(apostrophe=apostrophe):
                self.set_word_row(self.source_bound_row('когда мы уже домик' + apostrophe + 'левый сегодня'))
                result = self.run_preflight()
                self.assertEqual(1, result['wordRowSourceAttestation']['unmatchedSource'])
                self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
                self.set_word_row(self.source_bound_row('когда мы уже левый' + apostrophe + 'домик сегодня'))
                result = self.run_preflight()
                self.assertEqual(1, result['wordRowSourceAttestation']['unmatchedSource'])
                self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])

    def test_identical_source_windows_are_not_assigned_an_arbitrary_occurrence(self):
        sentence = 'слово '*55 + 'домик сейчас.'
        text = ' '.join([sentence]*3)
        match = re.search('домик', text)
        row = candidate(partition='train', article='904', articleId='904', families=['домик'],
            typed='домк', expectedSpelling='домик', prefix=text[:match.start()][-128:].lstrip(),
            sourceSegmentHash=subject.holdout_ledger.source_segment_hash(sentence),
            contextHash=subject.source_context_hash(text, match, subject.selector.load_generator()))
        result = subject.attest_word_rows({'train':[row], 'dev':[], 'test':[]}, {'904':text},
                                          Dictionary(), subject.selector.load_generator())
        self.assertEqual(1, result['ambiguousSource'])
        self.assertEqual(0, result['verified'])

    def test_modified_source_or_proposal_is_rejected(self):
        self.source.write_bytes(b'wrong source')
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_SOURCE_IDENTITY'):
            self.run_preflight()
        self.source.write_bytes(b'public source fixture')
        (self.data/'train-text.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_IDENTITY'):
            self.run_preflight()

    def test_source_changed_during_scan_is_rejected(self):
        def drift(path):
            yield list(self.sources), list(self.sources.values())
            path.write_bytes(b'public source fixturf')
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
            self.run_preflight(drift)

    def test_mutated_dictionary_receipt_is_rejected(self):
        class MutableDictionary(Dictionary):
            state = {'version': 'original'}
            def receipt(self):
                return self.state
        dictionary = MutableDictionary()
        def drift(path):
            yield list(self.sources), list(self.sources.values())
            dictionary.state['version'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
            subject.assess_files(self.data, self.source, self.lock, self.lex, self.ctrl,
                                 dictionary, drift)

    def test_word_preflight_helper_drift_is_rejected(self):
        original = subject.file_sha
        changed = False
        def measured(path):
            if Path(path).name == 'public_corpus_preparation_v1.py' and changed:
                return 'f'*64
            return original(path)
        def drift(path):
            nonlocal changed
            yield list(self.sources), list(self.sources.values())
            changed = True
        with mock.patch.object(subject, 'file_sha', side_effect=measured):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.run_preflight(drift)

    def test_missing_and_duplicate_source_are_rejected(self):
        def missing(path):
            yield ['901'], [self.sources['901']]
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_MISSING_SOURCE'):
            self.run_preflight(missing)
        def duplicate(path):
            yield ['901','901','902','903'], [self.sources['901'],self.sources['901'],self.sources['902'],self.sources['903']]
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DUPLICATE_SOURCE'):
            self.run_preflight(duplicate)


if __name__ == '__main__':
    unittest.main()
