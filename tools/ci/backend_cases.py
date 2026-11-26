"""Live dictionary contracts, loaded only by the required-backend gate."""
from pathlib import Path
import hashlib
import itertools
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/morphology'))
from ranker import PymorphyLexicon, PINNED, decide
from test_ranker import candidate, generation


class LivePymorphyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lexicon = PymorphyLexicon(cache_size=2)

    def test_dictionary_inflections_and_all_ambiguous_lemmas(self):
        for word, case in [('шкафов', 'gent'), ('шкафом', 'ablt'), ('шкафе', 'loct')]:
            analyses = self.lexicon.analyses(word)
            self.assertTrue(any(a.lemma == 'шкаф' and a.pos == 'NOUN' and a.case == case for a in analyses))
        self.assertTrue({'сталь', 'стать'} <= {a.lemma for a in self.lexicon.analyses('стали')})

    def test_guesses_and_unsupported_tokens_never_become_evidence(self):
        for word in ('фывапролджэщзхъ', 'шкафоф', 'шкаф1', 'cлово', ''):
            self.assertEqual((), self.lexicon.analyses(word))

    def test_context_decisions_use_real_dictionary_analyses(self):
        for word, prefix, original in [('шкафов', 'несколько', 'шкафоф'),
                                       ('шкафе', 'в новом', 'шкафоф'),
                                       ('пойдём', 'давай', 'пойдемм'),
                                       ('дней', 'несколько', 'днец')]:
            with self.subTest(word=word, prefix=prefix):
                result = decide(generation(candidate(word), original=original), prefix, self.lexicon)
                self.assertEqual(word, result.word)
                self.assertEqual('context_supported', result.reason)
        for prefix in ('', 'несколько.', 'несколько\n'):
            self.assertIsNone(decide(generation(), prefix, self.lexicon).word)
        cancelled = generation(); cancelled['completion'] = 'CANCELLED'
        self.assertIsNone(decide(cancelled, 'несколько', self.lexicon).word)

    def test_case_normalization_and_bounded_live_lookup_cache(self):
        first = self.lexicon.analyses('шкафов')
        self.assertEqual(first, self.lexicon.analyses('ШКАФОВ'))
        for word in ('дом', 'шкаф', 'стол'):
            self.assertTrue(self.lexicon.analyses(word))
        self.assertLessEqual(len(self.lexicon._cache), 2)
        self.assertEqual(first, self.lexicon.analyses('шкафов'))

    def test_receipt_binds_installed_dictionary_and_code(self):
        receipt = self.lexicon.receipt()
        self.assertTrue(receipt['dictionaryOnly'])
        self.assertEqual(PINNED, {name: value['version'] for name, value in receipt['packages'].items()})
        for value in receipt['packages'].values():
            self.assertTrue(value['files'])
            self.assertTrue(all(len(digest) == 64 for digest in value['files'].values()))
            self.assertTrue(all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in value['files']))

    def test_historical_neighbor_partition_family_overlap(self):
        """Disclose dictionary-family overlap; this is not a qualification gate."""
        folder = ROOT / 'tools/typing_experiments/neighbor-history-v1'
        manifest_bytes = (folder / 'manifest.json').read_bytes()
        self.assertEqual('2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e',
                         hashlib.sha256(manifest_bytes).hexdigest())
        manifest = json.loads(manifest_bytes)
        partitions = {}
        lexicon = PymorphyLexicon(cache_size=4096)
        for part in ('train', 'calibration', 'holdout'):
            path = folder / (part + '.jsonl')
            content = path.read_bytes()
            self.assertEqual(manifest['files'][path.name], hashlib.sha256(content).hexdigest())
            rows = [json.loads(line) for line in content.splitlines()]
            self.assertTrue(all(row['split'] == part for row in rows))
            words = {row['word'] for row in rows}
            lemmas = {}
            for word in words:
                analyses = lexicon.analyses(word)
                self.assertTrue(analyses)
                for analysis in analyses:
                    lemmas.setdefault(analysis.lemma, set()).add(word)
            partitions[part] = {'articles': {r['article'] for r in rows},
                                'native': {r['family'] for r in rows},
                                'words': words, 'lemmas': lemmas}
        for left, right in itertools.combinations(partitions, 2):
            for axis in ('articles', 'native', 'words'):
                self.assertFalse(partitions[left][axis] & partitions[right][axis])
            overlap = partitions[left]['lemmas'].keys() & partitions[right]['lemmas'].keys()
            self.assertEqual({'чёртов'} if (left, right) == ('train', 'holdout') else set(), overlap)
        self.assertEqual({'чертовым'}, partitions['train']['lemmas']['чёртов'])
        self.assertEqual({'чёртовой'}, partitions['holdout']['lemmas']['чёртов'])
