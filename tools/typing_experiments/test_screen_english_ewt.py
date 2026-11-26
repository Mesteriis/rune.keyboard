import unittest
from screen_english_ewt import screen


class ScreenEnglishEwtTest(unittest.TestCase):
    def test_counts_boundaries_and_annotations_without_returning_source_text(self):
        data = ('# newdoc id = a\n# sent_id = a-1\n# text = I said i.e. and Baha\'i, I\'m.\n'
                '1\tI\tI\tPRON\t_\t_\t0\troot\t_\t_\n\n').encode()
        result = screen(data); counts = result['counts']
        self.assertEqual(1, counts['sentences'])
        self.assertEqual(1, counts['annotated_upper_PRON'])
        self.assertEqual(1, counts['lower_period'])
        self.assertEqual(1, counts['lower_preceded_apostrophe'])
        self.assertEqual(1, counts['upper_apostrophe'])
        self.assertNotIn('Baha', str(result))

    def test_rejects_missing_or_duplicate_ids_and_malformed_tokens(self):
        for data in (b'', b'# text = I\n', b'# sent_id = x\n\n# sent_id = x\n', b'# sent_id = x\n1\tbad\n'):
            with self.assertRaises(ValueError): screen(data)


if __name__ == '__main__': unittest.main()
