import struct
import unittest

import english_family_keys as family
import ewt_packaged_lemma_exclusions as subject


def toy_trie():
    # root -> a -> sibling b; both nodes are terminals.
    nodes = [(0,1,0,0), (ord('a'),0,2,1), (ord('b'),0,0,2)]
    return struct.pack('<4sIII', b'RTR1', 2, len(nodes), 16) + b''.join(struct.pack('<IIII', *x) for x in nodes)


def token(index, lemma, pos='NOUN'):
    return '\t'.join([index, lemma, lemma, pos, '_', '_', '0', 'root', '_', '_']) + '\n'


class EwtPackagedLemmaTest(unittest.TestCase):
    def test_exact_terminal_lookup_and_nonterminal_rejection(self):
        trie = subject.Trie(toy_trie())
        self.assertTrue(trie.contains('a'))
        self.assertTrue(trie.contains('b'))
        self.assertFalse(trie.contains('c'))
        self.assertFalse(trie.contains('aa'))

    def test_corrupt_header_and_sibling_cycle_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'TRIE_HEADER'):
            subject.Trie(toy_trie()[:-1])
        raw = bytearray(toy_trie())
        struct.pack_into('<I', raw, 16 + 16 + 8, 1)
        with self.assertRaisesRegex(ValueError, 'TRIE_ORDER'):
            subject.Trie(bytes(raw)).contains('z')

    def test_scan_excludes_prior_lemmas_and_counts_repeated_rows(self):
        data = {'public.conllu': (token('1','a') + token('2','b') + token('3','b') +
                                 token('4','c') + token('5-6','b') + token('6','b!')).encode()}
        keys, counts = subject.scan(data, subject.Trie(toy_trie()), {family.key_for('a')})
        self.assertEqual([family.key_for('b')], keys)
        self.assertEqual({'matchedTokenRows':3,'newTokenRows':2,'matchedDistinctLemmas':2,'newDistinctLemmas':1}, counts)

    def test_malformed_source_rows_fail_closed(self):
        for value in ('not-a-row\n', token('0','a'), token('1','a','BOGUS')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                subject.scan({'public.conllu':value.encode()}, subject.Trie(toy_trie()), set())

    def test_actual_registered_entry_and_old_exclusions_are_preserved(self):
        import json
        ledger = json.loads(subject.prior.LEDGER.read_bytes())
        expected = subject.entry(ledger, subject.FIXTURE.read_bytes())
        logical = subject.lexical.validate_ledger(ledger)
        self.assertEqual([expected], [e for e in logical['entries'] if e['id'] == subject.ENTRY])
        self.assertEqual(850, len(expected['keys']['family']))
        self.assertFalse(logical['coverage']['complete'])

    def test_mutated_fixture_is_rejected_before_registration(self):
        with self.assertRaisesRegex(ValueError, 'EWT_PACKAGED_FIXTURE_IDENTITY'):
            subject.entry({}, subject.FIXTURE.read_bytes()+b' ')

    def test_new_public_lemma_is_blocked_by_existing_family_preflight(self):
        import json
        from public_corpus_preparation_v1 import preflight
        from test_public_corpus_preparation_v1 import candidate, controls
        ledger = subject.lexical.validate_ledger(json.loads(subject.prior.LEDGER.read_bytes()))
        previous = dict(ledger, entries=[e for e in ledger['entries'] if e['id'] != subject.ENTRY])
        row = candidate(language='en', sourceRepository='ud-english-ewt', article='ewt:synthetic-new-doc',
                        sentenceHash='f'*64, englishLemmas=['gastroenteritis'], prefix='Public example ',
                        typed='gastroenteritis', expectedSpelling='gastroenteritis')
        before = preflight([row], 'spelling', previous, controls(), 'new-families')
        after = preflight([row], 'spelling', ledger, controls(), 'new-families')
        self.assertEqual(0, before['lexicalOverlaps']['family'])
        self.assertEqual(1, after['lexicalOverlaps']['family'])
        self.assertEqual('BLOCKED_OVERLAP', after['status'])
        self.assertFalse(after['modelQualityQualified'])


if __name__ == '__main__':
    unittest.main()
