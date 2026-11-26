from pathlib import Path
import shutil
import tempfile
import unittest

import verify_historical_role_trainers as trainers


class HistoricalRoleTrainersTest(unittest.TestCase):
    def test_missing_and_modified_source_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target_dir = root / 'tools/typing_experiments/frozen_sources'
            target_dir.mkdir(parents=True)
            for digest in trainers.SOURCES:
                name = 'role_train_' + digest[:16] + '.py'
                shutil.copyfile(trainers.ROOT / 'tools/typing_experiments/frozen_sources' / name, target_dir / name)
            self.assertEqual(3, trainers.verify(root))
            target = target_dir / ('role_train_' + trainers.SOURCES[0][:16] + '.py')
            target.write_bytes(target.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ROLE_TRAINER_DRIFT'):
                trainers.verify(root)
            target.unlink()
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ROLE_TRAINER_MISSING'):
                trainers.verify(root)


if __name__ == '__main__':
    unittest.main()
