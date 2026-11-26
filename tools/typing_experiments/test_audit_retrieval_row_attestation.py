import unittest
from types import SimpleNamespace

import audit_retrieval_row_attestation as subject


class Lexicon:
    def analyses(self, word):
        return [SimpleNamespace(lemma='домик')] if word == 'домик' else []


def row(article, target='домик'):
    return dict(id='synthetic-'+article, partition='test', language='ru', articleId=article,
                expectedSpelling=target, typed='тест', prefix='когда мы уже ')


class RetrievalRowAttestationTest(unittest.TestCase):
    def test_whole_source_is_attested_and_fragments_and_unknowns_are_refused(self):
        rows = [row('1'), row('2'), row('3', 'квазислово')]
        articles = {'1':'когда мы уже домик сегодня', '2':'когда мы уже домик-левый сегодня',
                    '3':'когда мы уже квазислово сегодня'}
        prepared, refused, attest = subject.inspect(rows, articles, Lexicon(), subject.target.selector.load_generator())
        self.assertEqual(1, len(prepared))
        self.assertEqual({'dictionaryUnresolved':1, 'partialSourceToken':1}, refused)
        self.assertEqual(1, attest['verified'])
        self.assertEqual(1, attest['rows'])

    def test_missing_and_ambiguous_originals_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'RETRIEVAL_ATTESTATION_ROW'):
            subject.inspect([row('1')], {}, Lexicon(), subject.target.selector.load_generator())
        text = 'когда мы уже домик сегодня. когда мы уже домик завтра.'
        prepared, refused, attest = subject.inspect([row('1')], {'1':text}, Lexicon(), subject.target.selector.load_generator())
        self.assertEqual([], prepared)
        self.assertEqual({'unmatchedOrAmbiguousOriginal':1}, refused)
        self.assertEqual(0, attest['verified'])


if __name__ == '__main__':
    unittest.main()
