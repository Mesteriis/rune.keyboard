import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import english_family_keys as family
import ewt_frequency_lemma_exclusions as subject


class FrequencyExclusionsTest(unittest.TestCase):
    def frequency(self, raw):
        with patch.object(subject, 'FREQUENCY_BYTES', len(raw)), patch.object(
                subject, 'FREQUENCY_SHA', hashlib.sha256(raw).hexdigest()):
            return subject.frequency_keys(raw)

    def test_frequency_threshold_and_supported_shapes(self):
        keys = self.frequency(b'alpha 5\nbeta 4\nALPHA 6\nbad1 10\n')
        self.assertEqual({family.key_for('alpha')}, keys)

    def test_wrong_identity_and_malformed_source_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_IDENTITY'):
            subject.frequency_keys(b'wrong source')
        for raw in (b'alpha x\n', b'alpha 0\n', b'broken\n'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'SOURCE_FORMAT'):
                self.frequency(raw)

    def test_fixture_and_parent_required(self):
        ledger = json.loads(subject.prior.LEDGER.read_bytes())
        raw = subject.FIXTURE.read_bytes()
        entry = subject.entry(ledger, raw)
        self.assertEqual(845, len(entry['keys']['family']))
        self.assertEqual(1623, entry['rowCount'])
        with self.assertRaisesRegex(ValueError, 'FIXTURE_IDENTITY'):
            subject.entry(ledger, raw + b' ')
        old = copy.deepcopy(ledger)
        old['entries'] = [e for e in old['entries'] if e['id'] != subject.scowl.ENTRY]
        with self.assertRaisesRegex(ValueError, 'PARENT'):
            subject.entry(old, raw)

    def test_new_lemma_reaches_real_overlap_gate(self):
        from public_corpus_preparation_v1 import preflight
        from test_public_corpus_preparation_v1 import candidate, controls
        ledger = json.loads(subject.prior.LEDGER.read_bytes())
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                        sentenceHash='b'*64, englishLemmas=['suckup'], prefix='a ',
                        typed='suckup', expectedSpelling='suckup')
        old = copy.deepcopy(ledger)
        old['entries'] = [e for e in old['entries'] if e['id'] != subject.ENTRY]
        self.assertEqual(0, preflight([row], 'spelling', old, controls(), 'new-families')['lexicalOverlaps']['family'])
        result = preflight([row], 'spelling', ledger, controls(), 'new-families')
        self.assertEqual(1, result['lexicalOverlaps']['family'])
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertIn('en', result['unsupportedLexicalLanguages'])


if __name__ == '__main__':
    unittest.main()
