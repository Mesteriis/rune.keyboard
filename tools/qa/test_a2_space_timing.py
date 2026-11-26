import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import a2_space_timing as timing


def capture(*slices, end=310_000_000):
    rows = "".join(f"{name},{timestamp},{duration},{owner},{end}\n"
                   for name, timestamp, duration, owner in slices)
    return "name,ts,dur,upid,trace_end\n" + rows


KEY = (timing.KEY, 2_000_000, 0, 1)
REQUEST = (timing.REQUEST, 6_000_000, 0, 1)
RESULT = (timing.RESULT, 25_000_000, 1_000_000, 1)
DEADLINE = (timing.DEADLINE, 260_000_000, 0, 1)


class SpaceTimingTest(unittest.TestCase):
    def test_latency_ends_after_editor_result_processing(self):
        self.assertEqual(("completed", 24_000_000), timing.measure(capture(KEY, REQUEST, RESULT)))
        self.assertEqual(("deadline_missed", None), timing.measure(capture(KEY, REQUEST, DEADLINE)))

    def test_missing_and_censored_are_distinct(self):
        self.assertEqual(("no_admission", None), timing.measure(capture(KEY)))
        self.assertEqual(("no_terminal_marker", None), timing.measure(capture(KEY, REQUEST)))
        self.assertEqual(("incomplete_capture", None), timing.measure(capture(KEY, end=200_000_000)))

    def test_distinguishes_completed_scores_from_error_responses(self):
        for name, outcome in ((timing.CONTEXT_TOO_LONG, "context_too_long"),
                              (timing.SCORING_ERROR, "scoring_error")):
            row = (name, 25_000_000, 1_000_000, 1)
            self.assertEqual((outcome, None), timing.measure(capture(KEY, REQUEST, row)))

    def test_query_excludes_the_legacy_ambiguous_result(self):
        sql = timing.query("io.github.mesteriis.rune.keyboard")
        self.assertNotIn("'Rune#modelSpaceResult'", sql)
        for name in timing.TERMINAL_OUTCOMES:
            self.assertIn(f"'{name}'", sql)

    def test_rejects_ambiguous_or_invalid_slices(self):
        for rows in ((KEY, KEY), (KEY, RESULT), (KEY, REQUEST, RESULT, DEADLINE),
                     (KEY, REQUEST, (timing.RESULT, 5_999_999, 1, 1)),
                     (KEY, REQUEST, (timing.RESULT, 25_000_000, -1, 1)),
                     (KEY, REQUEST, (timing.RESULT, 25_000_000, 0, 2))):
            with self.subTest(rows=rows):
                self.assertEqual(("invalid_capture", None), timing.measure(capture(*rows)))

    def make_plan(self, root, attempts):
        manifest = root / "plan.json"
        processor = root / "processor"
        processor.write_bytes(b"fixture processor")
        rows = []
        for mode, characters in timing.CELLS:
            for number in range(attempts):
                name = f"{mode}-{characters}-{number}.pftrace"
                (root / name).write_text(name)
                rows.append({"mode": mode, "characters": characters, "trace": name})
        manifest.write_text(json.dumps({"schema": 1, "package": sorted(timing.PACKAGES)[0],
                                        "attemptsPerCell": attempts, "attempts": rows}))
        return manifest, processor

    def test_matrix_reports_nearest_rank_and_explicit_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, processor = self.make_plan(Path(directory), 22)

            def read(command, **_):
                index = int(Path(command[2]).stem.rsplit("-", 1)[-1])
                terminal = {20: DEADLINE, 21: (timing.CONTEXT_TOO_LONG, 25_000_000, 1_000_000, 1)}
                rows = (KEY, REQUEST, terminal.get(index, (timing.RESULT, (index + 10) * 1_000_000, 0, 1)))
                return subprocess.CompletedProcess(command, 0, capture(*rows))

            with patch.object(timing.subprocess, "run", side_effect=read):
                report = timing.summarize(manifest, processor)
        self.assertTrue(report["complete"])
        for cell in report["cells"]:
            self.assertEqual((22, 22, 1, 22, 26.0), (
                cell["attempts"], cell["observedAdmissions"], cell["deadlineMisses"],
                cell["deadlineDenominator"], cell["p95Ms"]))
            self.assertEqual(1 / 22, cell["deadlineMissRate"])
            self.assertEqual(1, cell["outcomes"]["context_too_long"])

    def test_missing_capture_never_reduces_the_planned_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, processor = self.make_plan(Path(directory), 1)
            (manifest.parent / "off-300-0.pftrace").unlink()
            with patch.object(timing.subprocess, "run",
                              return_value=subprocess.CompletedProcess([], 0, capture(KEY, REQUEST, RESULT))):
                report = timing.summarize(manifest, processor)
        self.assertFalse(report["complete"])
        self.assertEqual({"missing_capture": 1}, report["cells"][0]["outcomes"])
        self.assertEqual(1, report["cells"][0]["attempts"])
        self.assertIsNone(report["cells"][0]["p95Ms"])
        self.assertIsNone(report["cells"][0]["deadlineMissRate"])

    def test_rejects_reused_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, processor = self.make_plan(Path(directory), 1)
            root = manifest.parent
            (root / "on-300-0.pftrace").write_bytes((root / "off-300-0.pftrace").read_bytes())
            with patch.object(timing.subprocess, "run",
                              return_value=subprocess.CompletedProcess([], 0, capture(KEY, REQUEST, RESULT))):
                with self.assertRaisesRegex(ValueError, "repeated trace bytes"):
                    timing.summarize(manifest, processor)

    def test_rejects_unbalanced_plan_and_capture_outside_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, _ = self.make_plan(Path(directory), 1)
            plan = json.loads(manifest.read_text())
            plan["attempts"][0]["trace"] = "../other.pftrace"
            manifest.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "invalid or repeated capture path"):
                timing.load_plan(manifest)
            plan["attempts"].pop(0)
            manifest.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "incomplete timing plan"):
                timing.load_plan(manifest)


if __name__ == "__main__":
    unittest.main()
