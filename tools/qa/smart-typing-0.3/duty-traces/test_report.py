import json
import unittest
import xml.etree.ElementTree as ET

from report import COSTS, COUNTS, PREFIX, read_results


def fixture():
    root = ET.Element("testsuite", name="io.github.mesteriis.rune.keyboard.intelligence.inference.ModelDutyTraceTest",
                      tests="9", failures="0", errors="0", skipped="0")
    lines = []
    for (language, count), (wall, cpu) in COSTS.items():
        ET.SubElement(root, "testcase", name=f"trace[{language}-{count}]")
        row = dict(COUNTS, language=language, candidates=count,
                   usableBefore1000msBoundary=int(wall + 25 <= 1000),
                   simulatedCpuMillis=9355 + 2 * cpu, simulatedWallMillis=275510 + 2 * wall,
                   finalCreditUnits=-7450)
        lines.append(PREFIX + json.dumps(row))
    ET.SubElement(root, "system-out").text = "\n".join(lines)
    return root


class ReportTest(unittest.TestCase):
    def test_complete_simulated_fixture(self):
        self.assertEqual(9, len(read_results(ET.tostring(fixture()))))

    def test_nonpassing_suites(self):
        for field in ("failures", "errors", "skipped"):
            root = fixture(); root.set(field, "1")
            with self.assertRaises(ValueError): read_results(ET.tostring(root))

    def test_hidden_test_failure(self):
        root = fixture(); ET.SubElement(root.find("testcase"), "failure")
        with self.assertRaises(ValueError): read_results(ET.tostring(root))

    def test_missing_or_repeated_configuration(self):
        for duplicate in (False, True):
            root = fixture(); out = root.find("system-out"); lines = out.text.splitlines()
            out.text = "\n".join(lines[:-1] + ([lines[0]] if duplicate else []))
            with self.assertRaises(ValueError): read_results(ET.tostring(root))

    def test_false_counts_timing_or_debt(self):
        for key in ("admitted", "expired", "simulatedCpuMillis", "simulatedWallMillis",
                    "finalCreditUnits", "usableBefore1000msBoundary"):
            root = fixture(); out = root.find("system-out"); lines = out.text.splitlines()
            row = json.loads(lines[0][len(PREFIX):]); row[key] += 1
            lines[0] = PREFIX + json.dumps(row); out.text = "\n".join(lines)
            with self.assertRaises(ValueError): read_results(ET.tostring(root))

    def test_non_numeric_or_extra_payload(self):
        for key, value in (("admitted", True), ("admitted", float("nan")), ("payload", "text")):
            root = fixture(); out = root.find("system-out"); lines = out.text.splitlines()
            row = json.loads(lines[0][len(PREFIX):]); row[key] = value
            lines[0] = PREFIX + json.dumps(row); out.text = "\n".join(lines)
            with self.assertRaises(ValueError): read_results(ET.tostring(root))

    def test_repeated_testcase(self):
        root = fixture(); root.findall("testcase")[1].set("name", root.find("testcase").get("name"))
        with self.assertRaises(ValueError): read_results(ET.tostring(root))


if __name__ == "__main__":
    unittest.main()
