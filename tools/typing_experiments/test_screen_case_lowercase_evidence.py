import struct
import unittest
from unittest.mock import patch
import screen_case_lowercase_evidence as subject


def asset(records):
    data = b''
    offsets = [0]
    for flag, key, value in records:
        key, value = key.encode(), value.encode()
        data += bytes((flag, len(key), len(value))) + key + value
        offsets.append(len(data))
    return b'RNC1' + struct.pack('>I', len(records)) + struct.pack(f'>{len(offsets)}I', *offsets) + data


class CaseEvidenceTest(unittest.TestCase):
    def test_valid_asset_and_reject_corruption(self):
        raw = asset([(1, 'клавы', 'Клавы'), (0, 'читы', 'Читы')])
        self.assertEqual({'клавы'}, subject.parse_case(raw))
        for damaged in (raw[:-1], b'BAD!' + raw[4:], asset([(1, 'читы', 'Читы'), (1, 'клавы', 'Клавы')])):
            with self.subTest(damaged=damaged), self.assertRaises(ValueError):
                subject.parse_case(damaged)

    def test_only_excluded_articles_and_noninitial_case_evidence(self):
        lines = ['1\trus\tКлавы старые.\tuser\n', '2\trus\tНужны клавы.\tuser\n',
                 '3\trus\tЖду Клавы.\tuser\n', '4\trus\tВижу клавы.\tuser\n',
                 '5\trus\tПроверка xклавы и клавы2.\tuser\n']
        def keys_for(rows, kind):
            return {rows[0]['article']}
        with patch.object(subject, 'keys_for', side_effect=keys_for):
            lower, title, rows = subject.scan(lines, {'клавы'}, {'tatoeba:1', 'tatoeba:2', 'tatoeba:3'})
        self.assertEqual({'2'}, lower['клавы'])
        self.assertEqual({'3'}, title['клавы'])
        self.assertEqual(2, rows)

    def test_missing_or_bad_review_is_rejected(self):
        bad = {'schema': 1, 'purpose': subject.PURPOSE, 'cases': [
            {'id': 'x', 'typed': 'missing', 'baseline': 'X', 'label': 'lowercase_preserve'}]}
        with self.assertRaisesRegex(ValueError, 'CASE_SCREEN_REVIEW'):
            subject.summarize({'клавы'}, {}, {}, 0, bad)


if __name__ == '__main__':
    unittest.main()
