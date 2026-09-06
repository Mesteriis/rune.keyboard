import unittest

from compare_prefix_reuse import compare


class ComparisonContract(unittest.TestCase):
    def fixture(self):
        lines = ["OK (2 tests)", "INSTRUMENTATION_CODE: -1"]
        for request in range(60):
            for strategy in (0, 1):
                for round_id in range(5):
                    lines.append("INSTRUMENTATION_STATUS: top_seven_measurement=v1 "
                        f"id={request} strategy={strategy} round={round_id} wall_ns=20 cpu_ns=10 "
                        "states=3 verified=1 completion=0 alternatives=1")
        return "\n".join(lines)

    def test_timing_change_with_identical_work_is_accepted(self):
        before = self.fixture()
        report = compare(before, before.replace("cpu_ns=10", "cpu_ns=5"))
        self.assertTrue(report["identicalSearchCountersAndCompletions"])
        self.assertEqual(300, report["strategies"]["topSeven"]["after"]["cpu"]["count"])

    def test_changed_outcome_missing_measurement_or_failed_test_is_rejected(self):
        before = self.fixture()
        for after in (before.replace("states=3", "states=2", 1),
                      before.replace("completion=0", "completion=3", 1),
                      before.replace("OK (2 tests)", "FAILURES!!!"),
                      "\n".join(before.splitlines()[:-1])):
            with self.assertRaises(ValueError):
                compare(before, after)


if __name__ == "__main__":
    unittest.main()
