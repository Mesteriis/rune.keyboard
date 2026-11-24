from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import android_night_learning as night


class NightLearningTest(unittest.TestCase):
    def test_timezone_places_every_utc_hour_inside_night(self):
        for hour in range(24):
            with self.subTest(hour=hour):
                now = datetime(2026, 11, 23, hour, 59, tzinfo=timezone.utc)
                self.assertIn(now.astimezone(ZoneInfo(night.night_timezone(now))).hour, (2, 3))

    def test_seed_requires_quality_and_count(self):
        seed = {
            "seeded": True, "promotionApproved": True, "heldOut": 20,
            "improvements": 8, "regressions": 0,
        }
        night.verify_seed(seed)
        for key, value in (("heldOut", 19), ("improvements", 0), ("regressions", 1)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "NIGHT_LEARNING_SEED"):
                night.verify_seed({**seed, key: value})

    def test_promotion_requires_night_and_durable_profile_evidence(self):
        observations = dict.fromkeys((
            "finished", "promotingObserved", "activeChanged", "activeMatchesCandidate",
            "rollbackMatchesPrevious", "storeReady", "night", "charging", "screenOff",
        ), True)
        observations["deepIdle"] = False
        report = {
            "observations": observations, "runnerPassed": True,
            "bootUnchanged": True, "dozeForced": False,
        }
        night.verify_promotion(report)
        for key in ("activeMatchesCandidate", "rollbackMatchesPrevious", "screenOff", "deepIdle"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "NIGHT_LEARNING_PROMOTION"):
                night.verify_promotion({**report, "observations": {**observations, key: not observations[key]}})

    def test_existing_rune_installation_is_refused_before_any_mutation(self):
        replies = ["0", "37", "03", "package:" + night.PACKAGE]
        with (
            patch.object(night.shutil, "which", return_value="/usr/bin/adb"),
            patch.object(night, "owned_emulator", return_value="emulator-5582"),
            patch.object(night, "checked_adb", side_effect=replies) as adb,
            self.assertRaisesRegex(ValueError, "NIGHT_LEARNING_REQUIRES_EMPTY_AVD"),
        ):
            night.run("37.0", Path("unused"))
        self.assertEqual(4, adb.call_count)
        self.assertEqual("pm", adb.call_args.args[0][3])

    def test_workflow_uses_separate_fresh_avd_and_uploads_reports(self):
        workflow = (night.ROOT / ".github/workflows/ci.yml").read_text()
        fixture = workflow.split("- name: Run night-learning fixture on a fresh emulator", 1)[1]
        fixture, artifact = fixture.split("- name: Upload instrumentation results", 1)
        self.assertIn("avd-name: " + night.AVD, fixture)
        self.assertIn("-wipe-data -no-snapshot -timezone", fixture)
        self.assertIn("tools/ci/android_night_learning.py", fixture)
        self.assertIn("build/ci-night-learning/**", artifact)


if __name__ == "__main__":
    unittest.main()
