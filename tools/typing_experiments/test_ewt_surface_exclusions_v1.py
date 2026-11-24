import unittest
from unittest import mock

import control_ledger as control
import ewt_surface_exclusions_v1 as subject
from test_holdout_ledger import ledger
from test_public_corpus_preparation_v1 import candidate, controls
from public_corpus_preparation_v1 import preflight


class EwtSurfaceExclusionsTest(unittest.TestCase):
    def test_fixture_is_exact_public_surfaces_not_a_family_claim(self):
        keys = subject.load()
        self.assertEqual(16913, len(keys))
        self.assertIn(control.surface_key('en', 'went'), keys)
        with self.assertRaisesRegex(ValueError, 'EWT_SURFACE_IDENTITY'):
            subject.load(subject.FIXTURE.read_bytes() + b' ')

    def test_missing_or_changed_source_lock_fails_closed(self):
        with mock.patch.object(subject.ewt, 'LOCK', mock.Mock(read_bytes=lambda: b'changed')):
            with self.assertRaisesRegex(ValueError, 'EWT_SURFACE_IDENTITY'):
                subject.load()
        with self.assertRaisesRegex(ValueError, 'EWT_SURFACE_LOCK'):
            subject.generate({}, b'changed')

    def test_actual_gate_checks_both_typed_and_target_only_for_family_profile(self):
        for typed, target in (('went', 'unlikelyzzzzword'), ('unlikelyzzzzword', 'went')):
            with self.subTest(typed=typed):
                row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                    sentenceHash='f'*64, prefix='we ', typed=typed, expectedSpelling=target)
                strict = preflight([row], 'spelling', ledger(False), controls(), 'new-families')
                self.assertEqual(1, strict['englishSourceSurfaceOverlaps'])
                self.assertEqual('BLOCKED_OVERLAP', strict['status'])
                self.assertIn('en', strict['unsupportedLexicalLanguages'])
                sentence = preflight([row], 'spelling', ledger(False), controls(), 'new-sentences')
                self.assertEqual(0, sentence['englishSourceSurfaceOverlaps'])
                self.assertNotEqual('READY_TO_FREEZE', sentence['status'])

    def test_surface_fixture_corruption_cannot_produce_a_clean_gate(self):
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                        sentenceHash='f'*64, prefix='we ', typed='went', expectedSpelling='went')
        with mock.patch.object(subject, 'FIXTURE_SHA', '0'*64):
            with self.assertRaisesRegex(ValueError, 'EWT_SURFACE_IDENTITY'):
                preflight([row], 'spelling', ledger(False), controls(), 'new-families')


if __name__ == '__main__':
    unittest.main()
