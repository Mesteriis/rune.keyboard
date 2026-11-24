from pathlib import Path
import tempfile
import unittest

import audit_role_model_transitive_imports as audit


class RoleModelImportScreenTest(unittest.TestCase):
    def test_project_imports_are_screened_without_claiming_dynamic_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.py'
            source.write_text('import local, json\nfrom helper.sub import item\nfrom . import relative\n'
                              'load = __import__("dynamic")\ndef deferred():\n import nested\n')
            missing = audit.missing_for_sources([source], {'local'}, {'local', 'helper', 'dynamic'})
            self.assertEqual(['helper'], missing)
            direct, nested = audit.static_imports_by_scope(source)
            self.assertIn('helper', direct)
            self.assertIn('nested', nested)
            self.assertNotIn('dynamic', direct | nested)


if __name__ == '__main__':
    unittest.main()
