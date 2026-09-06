import unittest
from analyze_widths import report


def fixture():
    rows = [f"INSTRUMENTATION_STATUS: candidate_width_measurement=v1 id={i} maximum={w} round={r} "
            f"wall_ns=2000000 cpu_ns=1000000 states=100 verified=8 completion=0 alternatives={w}"
            for i in range(60) for w in (1, 3, 7) for r in range(5)]
    return "\n".join(rows + ["OK (1 test)", "INSTRUMENTATION_CODE: -1"])


class WidthMeasurementTest(unittest.TestCase):
    def test_full_matrix_is_not_energy_qualification(self):
        result = report(fixture())
        self.assertFalse(result["physicalEnergyQualified"])
        for width in result["widths"].values():
            self.assertEqual(300, width["cpu"]["count"])
            self.assertEqual(300, width["totalCpuMillis"])

    def test_bad_status_missing_repeated_bounds_and_nonrepeatability_fail(self):
        text = fixture()
        bad = [text.replace("OK (1 test)", "FAILURES!!!"), "\n".join(text.splitlines()[1:]),
               text + "\n" + text.splitlines()[0], text.replace("states=100", "states=8193"),
               text.replace("maximum=1", "maximum=2"), text.replace("cpu_ns=1000000", "cpu_ns=nan"),
               text.replace("states=100", "states=101", 1), text.replace("alternatives=1", "alternatives=2")]
        for value in bad:
            with self.assertRaises(ValueError):
                report(value)
