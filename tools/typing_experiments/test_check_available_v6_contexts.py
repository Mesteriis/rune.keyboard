import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import check_available_v6_contexts as subject


class RetainedV6ContextAnchorsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'anchors'
        shutil.copytree(subject.DIRECTORY, self.directory)

    def test_retained_anchors_cover_registered_contexts_without_claiming_corpus(self):
        report = subject.check(self.directory)
        self.assertEqual((3291, 3277, 14, 0, 1),
            (report['targets'], report['uniqueTargets'], report['ambiguousTargets'],
             report['missingTargets'], report['crossPartitionAnchors']))
        self.assertFalse(report['independentQualification'])

    def test_rehashed_mutation_cannot_replace_frozen_anchor_set(self):
        path = self.directory / 'anchors.jsonl'
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        rows[0]['wordStart'] += 1
        raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows).encode()
        path.write_bytes(raw)
        receipt_path = self.directory / 'receipt.json'
        receipt = json.loads(receipt_path.read_bytes())
        receipt['anchorsSha256'] = hashlib.sha256(raw).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_RECEIPT'):
            subject.check(self.directory)

    def test_false_qualification_or_helper_drift_is_refused(self):
        path = self.directory / 'receipt.json'
        receipt = json.loads(path.read_bytes())
        receipt['independentQualification'] = True
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_RECEIPT'):
            subject.check(self.directory)
        shutil.copy(subject.DIRECTORY / 'receipt.json', path)
        real = subject.recovery.articles.sha_file
        def changed(path):
            if Path(path).name == 'recover_available_v6_contexts.py':
                return '0' * 64
            return real(path)
        with mock.patch.object(subject.recovery.articles, 'sha_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_HELPER_BINDING'):
                subject.check(self.directory)


if __name__ == '__main__':
    unittest.main()
