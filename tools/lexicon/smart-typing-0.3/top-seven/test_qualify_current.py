import os
from pathlib import Path
import subprocess
import sys
import unittest
from qualify_current import excluded_controls


class QualificationContractTest(unittest.TestCase):
    def test_exclusion_reasons_stay_bound_to_their_actual_ids(self):
        rows = [{"id": 771, "query": "\ud800", "cancellation": False},
                {"id": 772, "query": "hello", "cancellation": False},
                {"id": 774, "query": "hello", "cancellation": True}]
        excluded = excluded_controls(rows)
        self.assertEqual(excluded[0]["id"], 771)
        self.assertTrue(excluded[0]["reason"].startswith("unpaired"))
        self.assertEqual(excluded[1], {"id": 774, "reason": "explicit cancellation"})

    def test_optimized_python_cannot_disable_qualification_gates(self):
        result = subprocess.run([sys.executable, "-O", str(Path(__file__).with_name("qualify_current.py")), "--help"],
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"QUALIFICATION_REQUIRES_ASSERTIONS", result.stderr)


if __name__ == "__main__":
    unittest.main()
