import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from contextual_assets import (write_index, count_records, grammar_payload, analysis_code,
                               COUNT_MAGIC, POS, CASES)


def analysis(**changes):
    return SimpleNamespace(**dict(dict(lemma='учиться', pos='INFN', case=None,
                                      number=None, gender=None, person=None), **changes))


class ContextualAssetsTest(unittest.TestCase):
    def test_front_coding_blocks_and_digest(self):
        records = [(f'слово{i:03}', bytes([i])) for i in range(65)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'words.ctx'
            receipt = write_index(records, path, COUNT_MAGIC)
            data = path.read_bytes()
        self.assertEqual(receipt['records'], 65)
        self.assertEqual(hashlib.sha256(data[:-32]).digest(), data[-32:])
        block, count, blocks, start = struct.unpack_from('<IIII', data, 8)
        self.assertEqual((block, count, blocks, start), (32, 65, 3, 40))
        position = start; previous = b''; actual = []
        for i in range(count):
            prefix, suffix, size = struct.unpack_from('<BBH', data, position)
            if i % 32 == 0: self.assertEqual(prefix, 0)
            previous = previous[:prefix] + data[position + 4:position + 4 + suffix]
            actual.append((previous.decode(), data[position + 4 + suffix:position + 4 + suffix + size]))
            position += 4 + suffix + size
        self.assertEqual(actual, records)
        self.assertEqual(position, len(data) - 32)

    def test_invalid_or_unsorted_records_fail_before_publication(self):
        for records in ([], [('b', b'x'), ('a', b'y')], [('a', b'x'), ('a', b'y')],
                        [('', b'x')], [('a', b'')], [('а' * 128, b'x')]):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'bad.ctx'
                with self.assertRaises(ValueError): write_index(records, path, COUNT_MAGIC)
                self.assertFalse(path.exists())

    def test_count_denominators_are_the_frozen_table_mass(self):
        rows = [('мы', 'идём', 3, 2), ('мы', 'едем', 4, 3), ('вы', 'идём', 2, 1)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'counts.jsonl'
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            result = {key: struct.unpack('<IIII', payload) for key, payload in count_records(path)}
        self.assertEqual(result['мы\0идём'], (3, 2, 5, 7))
        self.assertEqual(result['мы\0едем'], (4, 3, 4, 7))

    def test_ambiguity_count_is_not_lost_when_tags_project_to_the_same_code(self):
        payload = grammar_payload([analysis(lemma='учиться'), analysis(lemma='научиться')])
        self.assertEqual(tuple(payload[:2]), (2, 1))
        code, = struct.unpack('<H', payload[2:])
        self.assertEqual(code & 31, POS.index('INFN'))
        self.assertEqual((code >> 5) & 7, 0)
        self.assertEqual((analysis_code(analysis(case='loc2')) >> 5) & 7, CASES.index('loct'))
        self.assertEqual((analysis_code(analysis(case='voct')) >> 5) & 7, CASES.index('voct'))


if __name__ == '__main__': unittest.main()
