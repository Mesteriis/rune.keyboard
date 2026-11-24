import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_tatoeba_phrase_observed as subject


class ObservedRegistrationTest(unittest.TestCase):
    def test_registered_entries_and_counts_match_fixture(self):
        fixture = subject.load_fixture()
        first, second = subject.entries()
        a = subject.control.load(subject.source.CONTROL)
        b = subject.lexical.load_ledger(subject.source.LEXICAL)
        self.assertEqual([first], [e for e in a['entries'] if e['id'] == subject.ENTRY])
        self.assertEqual([second], [e for e in b['entries'] if e['id'] == subject.ENTRY + '-contexts'])
        self.assertEqual(84306, fixture['variants'])
        self.assertEqual((431, 56), (len(first['keys']), len(second['keys']['context'])))
        self.assertFalse(json.loads(subject.RECEIPT.read_bytes())['independentQualification'])

    def test_fixture_and_receipt_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)/'fixture.json'; receipt = Path(directory)/'receipt.json'
            fixture.write_bytes(subject.FIXTURE.read_bytes()); receipt.write_bytes(subject.RECEIPT.read_bytes()+b' ')
            with mock.patch.object(subject, 'FIXTURE', fixture), mock.patch.object(subject, 'RECEIPT', receipt):
                with self.assertRaisesRegex(ValueError, 'TATOEBA_OBSERVED_FIXTURE'):
                    subject.load_fixture()
            receipt.write_bytes(subject.RECEIPT.read_bytes())
            value = json.loads(fixture.read_bytes()); value['controlKeys'].append(value['controlKeys'][0]); fixture.write_text(json.dumps(value))
            with mock.patch.object(subject, 'FIXTURE', fixture), mock.patch.object(subject, 'RECEIPT', receipt):
                with self.assertRaisesRegex(ValueError, 'TATOEBA_OBSERVED_KEYS'):
                    subject.load_fixture()

    def test_nonidentical_replay_is_rejected_before_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'receipt.json').write_text('{}')
            (root/'run-1.jsonl').write_text('one')
            (root/'run-2.jsonl').write_text('two')
            with self.assertRaisesRegex(ValueError, 'TATOEBA_OBSERVED_REPLAY'):
                subject.extract(root)


if __name__ == '__main__': unittest.main()
