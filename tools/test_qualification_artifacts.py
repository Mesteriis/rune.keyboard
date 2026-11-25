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

    def test_exact_app_instrumentation_update_preserves_qualified_recipe(self):
        catalog = Path(__file__).resolve().parents[1] / gate.RUNTIME_CATALOG
        updated = catalog.read_bytes()
        qualified = updated.replace(b'uiautomator = "2.4.1"', b'uiautomator = "2.4.0"')
        self.assertNotEqual(updated, qualified)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            copy = root / gate.RUNTIME_CATALOG
            copy.parent.mkdir()
            copy.write_bytes(qualified)
            qualified_id = gate.fingerprint(root, [gate.RUNTIME_CATALOG], 'a' * 40)
            copy.write_bytes(updated)
            self.assertEqual(qualified_id, gate.fingerprint(root, [gate.RUNTIME_CATALOG], 'a' * 40))
            copy.write_bytes(updated.replace(b'agp = "9.2.1"', b'agp = "9.2.2"'))
            self.assertNotEqual(qualified_id, gate.fingerprint(root, [gate.RUNTIME_CATALOG], 'a' * 40))


if __name__ == '__main__':
    unittest.main()
