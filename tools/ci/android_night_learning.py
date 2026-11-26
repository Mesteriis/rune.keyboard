#!/usr/bin/env python3
"""Verify the synthetic night-learning lifecycle on a separate, empty CI AVD."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

from android_synthetic_restart_suites import (
    PACKAGE,
    ROOT,
    checked_adb,
    owned_emulator,
    verified_instrumentation,
)


AVD = "rune-ci-night-learning"
LEARNING = PACKAGE + ".smarttyping.learning."
FIXTURE = LEARNING + "LearningNightJobFixtureInstrumentedTest"
RUNNER = PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner"


def night_timezone(now):
    # Regional IDs are recognized by the emulator. Spread candidates across
    # the UTC offsets so the emulator can start with an hour of night left.
    zones = (
        "Asia/Tokyo", "Pacific/Tarawa", "Pacific/Honolulu", "Pacific/Pitcairn",
        "Pacific/Galapagos", "America/Puerto_Rico", "America/Noronha",
        "Africa/Abidjan", "Africa/Johannesburg", "Asia/Dubai", "Asia/Dhaka",
        "Asia/Singapore", "Pacific/Guam",
    )
    return next(zone for zone in zones if now.astimezone(ZoneInfo(zone)).hour in (2, 3))


def verify_seed(seed):
    if not (
        seed.get("seeded") is True
        and seed.get("promotionApproved") is True
        and seed.get("heldOut", 0) >= 20
        and seed.get("improvements", 0) > 0
        and seed.get("regressions") == 0
    ):
        raise ValueError("NIGHT_LEARNING_SEED")


def verify_promotion(report):
    observations = report.get("observations", {})
    required = (
        "finished", "promotingObserved", "activeChanged", "activeMatchesCandidate",
        "rollbackMatchesPrevious", "storeReady", "night", "charging", "screenOff",
    )
    if not (
        report.get("runnerPassed") is True
        and report.get("bootUnchanged") is True
        and report.get("dozeForced") is False
        and observations.get("deepIdle") is False
        and all(observations.get(key) is True for key in required)
    ):
        raise ValueError("NIGHT_LEARNING_PROMOTION")


def run(api, output):
    adb_binary = shutil.which("adb")
    if not adb_binary:
        raise ValueError("NIGHT_LEARNING_ADB")
    serial = owned_emulator(AVD)

    def adb(*args):
        if owned_emulator(AVD) != serial:
            raise ValueError("NIGHT_LEARNING_DEVICE_CHANGED")
        return checked_adb(["-s", serial, *args])

    def instrument(cls, method, name):
        text = adb(
            "shell", "am", "instrument", "--user", "0", "-w", "-r",
            "-e", "reviewU13", "true", "-e", "class", f"{cls}#{method}", RUNNER,
        )
        (output / (name + ".log")).write_text(text + "\n")
        if not verified_instrumentation(text, cls, method):
            raise ValueError("NIGHT_LEARNING_INSTRUMENTATION_" + name)

    if adb("shell", "am", "get-current-user") != "0":
        raise ValueError("NIGHT_LEARNING_USER")
    if adb("shell", "getprop", "ro.build.version.sdk") != api.split(".")[0]:
        raise ValueError("NIGHT_LEARNING_API")
    if adb("shell", "date", "+%H") not in ("01", "02", "03", "04"):
        raise ValueError("NIGHT_LEARNING_TIME_WINDOW")
    if "package:" + PACKAGE in adb("shell", "pm", "list", "packages", "--user", "0", PACKAGE):
        raise ValueError("NIGHT_LEARNING_REQUIRES_EMPTY_AVD")

    output.mkdir(parents=True, exist_ok=False)
    adb("emu", "power", "ac", "on")
    adb("emu", "power", "capacity", "95")
    adb("shell", "wm", "dismiss-keyguard")
    for path in (
        "app/build/outputs/apk/debug/app-debug.apk",
        "app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk",
    ):
        adb("install", "--user", "0", str(ROOT / path))

    instrument(
        LEARNING + "LearningJobSchedulerInstrumentedTest",
        "schedulesNightWorkerWithEverySystemConstraint", "scheduler",
    )
    instrument(FIXTURE, "seedFixture", "seed")
    seed = json.loads(adb("shell", "run-as", PACKAGE, "cat", "cache/review-u13-state.json"))
    (output / "seed.json").write_text(json.dumps(seed, indent=2) + "\n")
    verify_seed(seed)
    night = output / "night.json"
    subprocess.run([
        sys.executable, str(ROOT / "tools/qa/review-night-learning.py"), "--adb", adb_binary,
        "--serial", serial, "--expected-avd", AVD, "--expected", "promoted", "--output", str(night),
    ], check=True)
    if not verified_instrumentation(
        night.with_suffix(".instrumentation.log").read_text(), FIXTURE, "observeJob"
    ):
        raise ValueError("NIGHT_LEARNING_INSTRUMENTATION_observeJob")
    verify_promotion(json.loads(night.read_text()))

    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")
    instrument(
        LEARNING + "LearningLabProgressInstrumentedTest",
        "showsEligibleThresholdProgressAndActualRefusalReason", "learning-lab",
    )
    (output / "receipt.json").write_text(json.dumps({"api": api, "passed": True, "cases": 4}) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", choices=("26", "37.0"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.api, args.output)


if __name__ == "__main__":
    main()
