from pathlib import Path
import tempfile
import unittest

import qualification_artifacts as gate


class ArtifactGateTest(unittest.TestCase):
    def test_source_and_build_recipe_changes_invalidate_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'runtime.cpp').write_text('implementation')
            (root / 'build.gradle.kts').write_text('compiler recipe')
            paths = ['runtime.cpp', 'build.gradle.kts']
            before = gate.fingerprint(root, paths, 'a' * 40)
            self.assertNotEqual(before, gate.fingerprint(root, paths, 'b' * 40))
            for path in paths:
                old = (root / path).read_text()
                (root / path).write_text(old + ' changed')
                self.assertNotEqual(before, gate.fingerprint(root, paths, 'a' * 40))
                (root / path).write_text(old)


if __name__ == '__main__':
    unittest.main()
