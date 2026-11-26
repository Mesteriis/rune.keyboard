from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest
import a4_abbreviation_review_sample as subject


class AbbreviationReviewSampleTest(unittest.TestCase):
    def test_selects_first_occurrence_and_is_order_independent(self):
        rows = [('8', 'до СПБ. после и спб.'), ('5', 'в спб. далее'), ('2', 'в мск. сегодня')]
        count, sample, excerpts = subject.sample(rows)
        self.assertEqual(3, count)
        self.assertEqual((count, sample, excerpts), subject.sample(reversed(rows)))
        entry = next(x for x in sample if x['article'] == '8')
        self.assertEqual((3, 7), (entry['start'], entry['end']))
        self.assertEqual('upper', entry['case'])
        self.assertNotIn('excerpt', entry)

    def test_rejects_invalid_and_duplicate_articles(self):
        for rows in ([], [('1', 'x'), ('01', 'x')], [('0', 'x')], [('2', None)]):
            with self.assertRaises(ValueError): subject.sample(rows)

    def test_domain_suffix_is_sampled_for_meaning_review(self):
        _, records, _ = subject.sample([('1', 'FORUM.мск. 15 мая')])
        self.assertEqual(1, len(records))
        self.assertEqual('мск', records[0]['form'])
        self.assertEqual('lower', records[0]['case'])

    def test_limits_one_per_article_and_ten_per_form(self):
        rows = [(str(i+1), 'спб. спб.') for i in range(20)]
        count, sample, excerpts = subject.sample(rows)
        self.assertEqual(20, count)
        self.assertEqual(10, len(sample))
        self.assertEqual(10, len({r['article'] for r in sample}))
        self.assertEqual(10, len(excerpts))

    def test_retained_review_is_complete_bound_and_not_qualification(self):
        folder = subject.base.ROOT / 'tools/typing_experiments/a4_controls'
        sample_path = folder / 'wikipedia-0011-review-sample.json'
        labels_path = folder / 'wikipedia-0011-meaning-review.json'
        sample_raw = sample_path.read_bytes(); labels_raw = labels_path.read_bytes()
        self.assertEqual('2ae92996095bd6f8644f80de97858bdaece31caa50336a96585c5522684db1ca',
                         hashlib.sha256(sample_raw).hexdigest())
        self.assertEqual('393a22c912104c52edb6fb7c1c47f6dccb0acec321d4d4983a0fd4c293e18833',
                         hashlib.sha256(labels_raw).hexdigest())
        data, review = json.loads(sample_raw), json.loads(labels_raw)
        self.assertEqual(hashlib.sha256(sample_raw).hexdigest(), review['sampleSha256'])
        self.assertEqual(subject.base.sha(subject.base.LOCK), data['sourceLockSha256'])
        self.assertEqual(subject.base.sha(subject.base.CONTROLS), data['controlsSha256'])
        self.assertEqual(subject.base.sha(Path(subject.__file__)), data['helperSha256'])
        self.assertEqual(subject.base.sha(Path(subject.base.__file__)), data['frequencyHelperSha256'])
        self.assertFalse(data['sourceDecoderAttested'])
        self.assertFalse(data['independentlyQualified'])
        self.assertFalse(review['independentlyQualified'])
        records, labels = data['records'], review['labels']
        self.assertEqual(46, len(records))
        self.assertEqual(list(range(46)), [x['index'] for x in labels])
        self.assertEqual({'abbreviation': 44, 'domain_label': 1, 'uncertain': 1},
                         dict(Counter(x['category'] for x in labels)))
        self.assertEqual({'спб': 10, 'мск': 6, 'адм': 10, 'пгт': 10, 'экон': 10},
                         dict(Counter(x['form'] for x in records)))
        self.assertEqual(len(records), len({(x['form'], x['article']) for x in records}))
        for row in records:
            self.assertEqual({'form', 'article', 'start', 'end', 'case', 'excerptSha256'}, set(row))
            self.assertTrue(row['article'].isascii() and row['article'].isdecimal())
            self.assertGreaterEqual(row['start'], 0)
            self.assertEqual(len(row['form']) + 1, row['end'] - row['start'])
            self.assertIn(row['case'], ('lower', 'upper', 'mixed'))
            self.assertRegex(row['excerptSha256'], r'^[0-9a-f]{64}$')


if __name__ == '__main__': unittest.main()
