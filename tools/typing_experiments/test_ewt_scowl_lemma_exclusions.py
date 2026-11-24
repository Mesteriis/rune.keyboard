import copy
import json
import unittest

import english_family_keys as family
import ewt_scowl_lemma_exclusions as subject


def token(number, lemma, pos='NOUN'):
    return f'{number}\tword\t{lemma}\t{pos}\t_\t_\t0\troot\t_\t_\n'.encode()


class ScowlExclusionsTest(unittest.TestCase):
    def test_scan_requires_public_dictionary_and_skips_already_excluded(self):
        new, old, unknown = (family.key_for(s) for s in ('aardvark', 'home', 'rareword'))
        keys, counts = subject.scan({'part':token(1, 'Aardvark') + token(2, 'home') + token(3, 'rareword')},
                                    {new, old}, {old})
        self.assertEqual([new], keys)
        self.assertEqual({'NOUN':1}, counts)
        self.assertNotIn(unknown, keys)

    def test_bad_source_and_archive_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_IDENTITY'):
            subject.dictionary(b'not the pinned archive')
        for raw in (b'broken\n', token('bad', 'word'), token(1, 'word', 'INVALID')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                subject.scan({'part':raw}, set(), set())

    def test_fixture_and_parent_are_required_for_the_registered_entry(self):
        ledger = json.loads(subject.prior.LEDGER.read_bytes())
        raw = subject.FIXTURE.read_bytes()
        result = subject.entry(ledger, raw)
        self.assertEqual(84, len(result['keys']['family']))
        self.assertEqual(162, result['rowCount'])
        with self.assertRaisesRegex(ValueError, 'FIXTURE_IDENTITY'):
            subject.entry(ledger, raw + b' ')
        changed = copy.deepcopy(ledger)
        changed['entries'] = [e for e in changed['entries'] if e['id'] != subject.packaged.ENTRY]
        with self.assertRaisesRegex(ValueError, 'PARENT'):
            subject.entry(changed, raw)

    def test_new_public_lemma_reaches_real_family_overlap_gate(self):
        from public_corpus_preparation_v1 import preflight
        from test_public_corpus_preparation_v1 import candidate, controls
        ledger = json.loads(subject.prior.LEDGER.read_bytes())
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                        sentenceHash='b'*64, englishLemmas=['fedayeen'], prefix='a ',
                        typed='fedayeen', expectedSpelling='fedayeen')
        old = copy.deepcopy(ledger)
        old['entries'] = [e for e in old['entries'] if e['id'] != subject.ENTRY]
        self.assertEqual(0, preflight([row], 'spelling', old, controls(), 'new-families')['lexicalOverlaps']['family'])
        result = preflight([row], 'spelling', ledger, controls(), 'new-families')
        self.assertEqual(1, result['lexicalOverlaps']['family'])
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertIn('en', result['unsupportedLexicalLanguages'])


if __name__ == '__main__':
    unittest.main()
