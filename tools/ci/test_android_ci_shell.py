import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AndroidCiShellTest(unittest.TestCase):
    def test_chrome_routes_run_independently_only_on_api37(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        suites = script[script.index('suite_status=0'):]
        pretend = '''python3() {
  if [ "$1" != tools/ci/android_chrome_editor.py ]; then return 0; fi
  case "$*" in
    *--navigation) echo omnibox; return "$OMNIBOX_STATUS" ;;
    *--password) echo password; return "$PASSWORD_STATUS" ;;
    *) echo textarea; return "$TEXTAREA_STATUS" ;;
  esac
}
./gradlew() { return 0; }
'''
        for api, textarea, omnibox, password, expected in (
                ('26', 9, 11, 13, 0), ('37.0', 9, 0, 0, 9), ('37.0', 0, 11, 0, 11),
                ('37.0', 0, 0, 13, 13), ('37.0', 9, 11, 13, 9)):
            with self.subTest(api=api, textarea=textarea, omnibox=omnibox, password=password):
                job = suites.replace('${{ matrix.api-level }}', api)
                result = subprocess.run(['bash', '-ec', pretend + job], cwd=ROOT, text=True,
                    capture_output=True, env=dict(os.environ, TEXTAREA_STATUS=str(textarea),
                                                  OMNIBOX_STATUS=str(omnibox), PASSWORD_STATUS=str(password)))
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertEqual(['textarea', 'omnibox', 'password'] if api == '37.0' else [], result.stdout.splitlines())
        uploads = workflow.split('- name: Upload instrumentation results', 1)[1]
        for scope in ('omnibox', 'password'):
            self.assertIn(f'build/ci-chrome-{scope}/**', uploads)

    def test_boundary_apks_build_before_emulator_and_install_after_guard(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        setup = workflow.split('      - name: Build Android boundary APKs before emulator startup\n', 1)[1]
        builds = setup.split('\n      - name:', 1)[0]
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        self.assertIn('assembleDebug assembleDebugAndroidTest :runtime-llama:assembleDebugAndroidTest', builds)
        self.assertIn('tools/qa/compose-editor assembleDebug', builds)
        self.assertNotIn(':runtime-llama:assembleDebugAndroidTest', script)
        self.assertNotIn('tools/qa/compose-editor assembleDebug', script)
        guard = script.index('owned_emulator("rune-ci-boundary")')
        install = script.index('adb -s "$compose_serial" install -r tools/qa/compose-editor/build/outputs/apk/debug/RuneComposeEditorQa-debug.apk')
        suites = script.index('python3 tools/ci/android_boundary_suites.py')
        self.assertLess(guard, install)
        self.assertLess(install, suites)

    def test_night_learning_uses_ordinary_apks_and_cannot_skip_boundary_suite(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        setup = workflow.split('      - name: Build Android boundary APKs before emulator startup\n', 1)[1]
        self.assertLess(setup.index('Select night-learning emulator timezone'), setup.index('Run Android boundary suite'))
        builds, night = setup.split('      - name: Select night-learning emulator timezone\n', 1)
        night, boundary = night.split('      - name: Run Android boundary suite\n', 1)
        self.assertIn('        id: boundary-apks\n', builds)
        self.assertIn('avd-name: rune-ci-night-learning', night)
        self.assertIn('android_night_learning.py', night)
        self.assertIn("        if: ${{ !cancelled() && steps.boundary-apks.outcome == 'success' }}\n", boundary)
        self.assertIn('avd-name: rune-ci-boundary', boundary)
        self.assertIn('android_boundary_suites.py', boundary)

    def test_all_direct_adb_actions_use_the_verified_serial(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        self.assertIn('adb -s "$compose_serial" install -r app/build/outputs/apk/debug/app-debug.apk', script)
        self.assertNotIn('installDebug', script)
        self.assertEqual([], re.findall(r'\badb\s+(?!-s\s+"\$compose_serial")', script))

    def test_compose_setup_failures_stop_before_boundary_suite(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        lines = [line[12:] if line.startswith('            ') else line for line in script.splitlines()]
        text = '\n'.join(lines)
        builds = workflow.split('      - name: Build Android boundary APKs before emulator startup\n', 1)[1]
        builds = builds.split('\n      - name:', 1)[0].split('        run: |\n', 1)[1] + '\n'
        start = text.index('compose_serial=')
        end = text.index('\n', text.index('adb -s "$compose_serial" install -r app/build/outputs/apk/debug/app-debug.apk', start))
        setup = builds + text[start:end]
        fake = '''./gradlew() {
  case "$*" in
    *tools/qa/compose-editor*) return "$COMPOSE_STATUS" ;;
    *) return "$BUILD_STATUS" ;;
  esac
}
python3() { if [ "$GUARD_STATUS" -ne 0 ]; then return "$GUARD_STATUS"; fi; printf 'emulator-5554\\n'; }
adb() { return "$INSTALL_STATUS"; }
'''
        for build, compose, guard, install, expected in (
            (9, 0, 0, 0, 9), (0, 10, 0, 0, 10), (0, 0, 8, 0, 8), (0, 0, 0, 7, 7), (0, 0, 0, 0, 0),
        ):
            with self.subTest(build=build, compose=compose, guard=guard, install=install):
                env = dict(os.environ, BUILD_STATUS=str(build), COMPOSE_STATUS=str(compose),
                           GUARD_STATUS=str(guard), INSTALL_STATUS=str(install))
                result = subprocess.run(['bash', '-c', 'set -e\n' + fake + setup + '\nprintf "REACHED\\n"'],
                                        cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertEqual(expected == 0, 'REACHED' in result.stdout)

    def test_each_apk_install_failure_stops_the_setup(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        text = '\n'.join(line[12:] if line.startswith('            ') else line for line in script.splitlines())
        start = text.index('compose_serial=')
        end = text.index('\n', text.index('adb -s "$compose_serial" install -r app/build/outputs/apk/debug/app-debug.apk', start))
        setup = text[start:end]
        fake = '''python3() { printf 'emulator-5554\\n'; }
ADB_CALLS=0
adb() { ADB_CALLS=$((ADB_CALLS + 1)); if [ "$ADB_CALLS" -eq "$FAIL_ON" ]; then return 7; fi; }
'''
        for fail_on in (1, 2, 0):
            with self.subTest(fail_on=fail_on):
                result = subprocess.run(['bash', '-c', 'set -e\n' + fake + setup + '\nprintf "REACHED\\n"'],
                                        cwd=ROOT, env=dict(os.environ, FAIL_ON=str(fail_on)), capture_output=True, text=True)
                self.assertEqual(0 if fail_on == 0 else 7, result.returncode, result.stderr)
                self.assertEqual(fail_on == 0, 'REACHED' in result.stdout)

    def test_logcat_capture_restarts_after_adb_failure(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        capture = next(line.strip().split(' > app/build/ci-device/logcat.txt', 1)[0]
                       for line in script.splitlines() if line.strip().startswith('while true; do adb '))
        fake = '''compose_serial=emulator-5554
calls=0
adb() { calls=$((calls + 1)); echo "attempt $calls"; if [ "$calls" -eq 1 ]; then return 1; fi; }
sleep() { if [ "$calls" -eq 2 ]; then exit 0; fi; }
'''
        result = subprocess.run(['bash', '-c', 'set -e\n' + fake + capture],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['attempt 1', 'attempt 2'], result.stdout.splitlines())

    def test_suite_and_capture_exit_statuses_are_preserved(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        script = workflow.split('          script: |\n', 1)[1].split('\n      - name: Upload instrumentation results', 1)[0]
        lines = [line[12:] if line.startswith('            ') else line for line in script.splitlines()]
        text = '\n'.join(lines)
        capture = text[text.index('capture_ci_failures() {'):text.index('trap capture_ci_failures EXIT') + len('trap capture_ci_failures EXIT')]
        suites = text[text.index('suite_status=0'):]
        fake = '''python3() {
  case "$1" in
    tools/ci/android_boundary_suites.py) echo boundary >> "$TRACE_FILE"; return "$BOUNDARY_STATUS" ;;
    tools/ci/android_synthetic_restart_suites.py) echo restart >> "$TRACE_FILE"; return "$RESTART_STATUS" ;;
    tools/ci/android_editing_process_death.py) echo editing >> "$TRACE_FILE"; return "$EDITING_STATUS" ;;
    tools/ci/android_voice_fixture_suites.py) echo voice >> "$TRACE_FILE"; return "$VOICE_STATUS" ;;
    tools/ci/collect_android_failure_artifacts.py) echo capture >> "$TRACE_FILE"; return "$CAPTURE_STATUS" ;;
    *) return 99 ;;
  esac
}
./gradlew() { echo rebuild >> "$TRACE_FILE"; return "$BUILD_STATUS"; }
'''
        for boundary, build, restart, editing, voice, collector, expected in ((0, 0, 0, 0, 0, 0, 0), (7, 0, 0, 0, 0, 0, 7), (0, 0, 9, 0, 0, 0, 9),
                                                               (7, 0, 9, 0, 0, 3, 7), (0, 0, 0, 0, 0, 3, 3),
                                                               (0, 8, 0, 0, 0, 0, 8), (7, 8, 0, 0, 0, 3, 7),
                                                               (0, 0, 0, 6, 0, 0, 6), (0, 0, 9, 6, 0, 0, 9),
                                                               (0, 0, 0, 0, 5, 0, 5)):
            with self.subTest(boundary=boundary, build=build, restart=restart, editing=editing, voice=voice, collector=collector), tempfile.TemporaryDirectory() as folder:
                trace = Path(folder) / 'trace'
                env = dict(os.environ, TRACE_FILE=str(trace), BOUNDARY_STATUS=str(boundary),
                           BUILD_STATUS=str(build), RESTART_STATUS=str(restart), EDITING_STATUS=str(editing), VOICE_STATUS=str(voice), CAPTURE_STATUS=str(collector))
                result = subprocess.run(['bash', '-c', 'set -e\n' + fake + capture + '\n' + suites],
                                        cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertEqual(expected, result.returncode, result.stderr)
                expected_trace = ['boundary', 'rebuild'] + ([] if build else ['restart', 'editing', 'voice']) + ['capture']
                self.assertEqual(expected_trace, trace.read_text().splitlines())


if __name__ == '__main__':
    unittest.main()
