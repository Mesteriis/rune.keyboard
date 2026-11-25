#!/usr/bin/env bash
set -e

api_level=${1:?expected Android API level}

# Refuse before installing or changing IME settings if ADB sees an
# unexpected device or the emulator identity is not the CI AVD.
PYTHONPATH=tools/ci python3 -c 'from android_synthetic_restart_suites import owned_emulator; owned_emulator("rune-ci-boundary")'

capture_ci_failures() {
  suite_exit=$?
  trap - EXIT
  set +e
  python3 tools/ci/collect_android_failure_artifacts.py --avd-name rune-ci-boundary --output app/build/ci-device/failure-artifacts
  capture_exit=$?
  if [ "$capture_exit" -ne 0 ]; then
    echo "Android failure-artifact collection failed: $capture_exit" >&2
    if [ "$suite_exit" -eq 0 ]; then suite_exit=$capture_exit; fi
  fi
  if [ -n "${logcat_pid:-}" ]; then
    kill "$logcat_pid" 2>/dev/null
    wait "$logcat_pid" 2>/dev/null
  fi
  exit "$suite_exit"
}
trap capture_ci_failures EXIT

compose_serial="$(PYTHONPATH=tools/ci python3 -c 'from android_synthetic_restart_suites import owned_emulator; print(owned_emulator("rune-ci-boundary"))')"
adb -s "$compose_serial" install -r tools/qa/compose-editor/build/outputs/apk/debug/RuneComposeEditorQa-debug.apk
adb -s "$compose_serial" install -r app/build/outputs/apk/debug/app-debug.apk
mkdir -p app/build/ci-device
while true; do adb -s "$compose_serial" logcat -v threadtime || true; sleep 1; done > app/build/ci-device/logcat.txt 2>&1 &
logcat_pid=$!
adb -s "$compose_serial" shell settings put secure show_ime_with_hard_keyboard 1
for attempt in $(seq 1 15); do if adb -s "$compose_serial" shell ime enable io.github.mesteriis.rune.keyboard/.ime.RuneInputMethodService; then break; fi; if [ "$attempt" -eq 15 ]; then exit 1; fi; sleep 2; done
adb -s "$compose_serial" shell ime set io.github.mesteriis.rune.keyboard/.ime.RuneInputMethodService
adb -s "$compose_serial" shell am start -W -n io.github.mesteriis.rune.keyboard/.qa.ImeQaActivity
# The disposable AVD has distinct q3/q4/q8 and separate-package fixtures.
# Run every scope separately and retain each fresh XML report and log.
suite_status=0
python3 tools/ci/android_boundary_suites.py --api "$api_level" --output app/build/ci-device/boundary-suites --avd-name rune-ci-boundary || suite_status=$?
# Qualification suites build a different debug application ID into the
# same output paths. Restore both ordinary APKs before restart tests.
restart_build_status=0
./gradlew --no-daemon assembleDebug assembleDebugAndroidTest || restart_build_status=$?
if [ "$restart_build_status" -ne 0 ]; then
  if [ "$suite_status" -eq 0 ]; then suite_status=$restart_build_status; fi
else
  python3 tools/ci/android_synthetic_restart_suites.py --avd-name rune-ci-boundary --output build/ci-synthetic-restart || {
    restart_status=$?
    if [ "$suite_status" -eq 0 ]; then suite_status=$restart_status; fi
  }
  python3 tools/ci/android_editing_process_death.py --avd-name rune-ci-boundary --output build/ci-editing-process-death || {
    editing_status=$?
    if [ "$suite_status" -eq 0 ]; then suite_status=$editing_status; fi
  }
  python3 tools/ci/android_voice_fixture_suites.py --avd-name rune-ci-boundary --output build/ci-voice-fixture || {
    voice_status=$?
    if [ "$suite_status" -eq 0 ]; then suite_status=$voice_status; fi
  }
  if [ "$api_level" = '37.0' ]; then
    python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-boundary --output build/ci-chrome-editor || {
      chrome_status=$?
      if [ "$suite_status" -eq 0 ]; then suite_status=$chrome_status; fi
    }
    python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-boundary --output build/ci-chrome-omnibox --navigation || {
      chrome_status=$?
      if [ "$suite_status" -eq 0 ]; then suite_status=$chrome_status; fi
    }
    python3 tools/ci/android_chrome_editor.py --avd-name rune-ci-boundary --output build/ci-chrome-password --password || {
      chrome_status=$?
      if [ "$suite_status" -eq 0 ]; then suite_status=$chrome_status; fi
    }
  fi
fi
exit "$suite_status"
