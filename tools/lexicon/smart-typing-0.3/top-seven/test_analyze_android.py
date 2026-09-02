import unittest
from analyze_android import read_measurements, report


def matrix():
    return "\n".join(f"INSTRUMENTATION_STATUS: top_seven_measurement=v1 id={i} strategy={s} round={r} "
                     "wall_ns=2000000 cpu_ns=1000000 states=8192 verified=64 completion=3 alternatives=7"
                     for i in range(60) for s in range(2) for r in range(5))


class AndroidMeasurementContractTest(unittest.TestCase):
    def test_complete_fixed_matrix_retains_suite_failure_and_resource_limits(self):
        value = report(matrix())
        self.assertFalse(value["suite30Passed"])
        self.assertFalse(value["physicalEnergyQualified"])
        self.assertEqual(value["strategies"]["topSeven"]["cpu"]["p95Millis"], 1.0)
        self.assertEqual(value["strategies"]["exhaustive"]["wall"]["count"], 300)

    def test_missing_duplicate_foreign_and_malformed_records_fail(self):
        text = matrix()
        rows = text.splitlines()
        for changed in ["\n".join(rows[:-1]), text + "\n" + rows[0], text.replace("id=59", "id=60"),
                        text.replace("cpu_ns=1000000", "cpu_ns=nan"), text.replace("states=8192", "states=8193")]:
            with self.assertRaises(ValueError):
                read_measurements(changed)


if __name__ == "__main__":
    unittest.main()
