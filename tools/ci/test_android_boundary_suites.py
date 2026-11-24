import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import android_boundary_suites as suites


def fixture(command, count, skipped=0):
    args=' '.join(command)
    if ':runtime-llama:connectedDebugAndroidTest' in args:
        cls=suites.NATIVE_RUNTIME;method=None;count=len(suites.NATIVE_RUNTIME_METHODS)
    elif 'notClass=' in args:
        cls='io.github.mesteriis.rune.keyboard.qa.ExampleTest';method=None
    else:
        value=next(a.split('class=',1)[1] for a in command if 'class=' in a)
        cls,_,method=value.partition('#')
        if ',' in value: method=None
    methods=sorted(suites.CASE_REJECTION_METHODS) if cls==suites.CASE_REJECTION else sorted(suites.CONFIRMED_METHODS) if cls==suites.CONFIRMED else sorted(suites.PERSONAL_METHODS) if cls==suites.PERSONAL else sorted(suites.COMPOSE_METHODS) if cls==suites.COMPOSE else sorted(suites.NATIVE_RUNTIME_METHODS) if cls==suites.NATIVE_RUNTIME else []
    required=sorted(suites.GENERAL_REQUIRED)[:count] if 'notClass=' in args else []
    filler=count-len(required)
    identities=[(cls,method or (methods[i] if i<len(methods) else 'case'+str(i))) for i in range(filler)]+required
    cases=''.join(f'<testcase classname="{klass}" name="{name}">'
                  + ('<skipped/>' if i<skipped else '') + '</testcase>' for i,(klass,name) in enumerate(identities))
    return f'<testsuites tests="{count}" failures="0" errors="0" skipped="{skipped}">{cases}</testsuites>'


class BoundarySuitePlanTest(unittest.TestCase):
    def test_log_only_discovery_requires_complete_unique_cases(self):
        def event(method, status):
            return ('INSTRUMENTATION_STATUS: class=ExampleTest\n'
                    f'INSTRUMENTATION_STATUS: test={method}\n'
                    f'INSTRUMENTATION_STATUS_CODE: {status}\n')

        complete = (event('one', 1) + event('one', 0) + event('two', 1) + event('two', 0)
                    + 'OK (2 tests)\nINSTRUMENTATION_CODE: -1\n')
        self.assertEqual({('ExampleTest', 'one'), ('ExampleTest', 'two')},
                         suites.discovered_cases(complete))
        for altered in (complete.replace(event('two', 0), ''),
                        complete.replace('test=two', 'test=one'),
                        complete.replace('OK (2 tests)', 'OK (1 test)'),
                        complete.removesuffix('INSTRUMENTATION_CODE: -1\n')):
            with self.subTest(altered=altered), self.assertRaisesRegex(ValueError, 'GENERAL_DISCOVERY'):
                suites.discovered_cases(altered)

    def test_report_rejects_missing_or_substituted_non_required_method_above_floor(self):
        complete = fixture(dict(suites.plan('26'))['general'], 369)
        expected = {(case.get('classname'), case.get('name'))
                    for case in ET.fromstring(complete).iter('testcase')}
        ordinary = f'<testcase classname="{suites.QA}ExampleTest" name="case0"></testcase>'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xml'
            path.write_text(complete)
            self.assertEqual(369, suites.report(path, 'general', expected)['tests'])
            for altered in (complete.replace(ordinary, '').replace('tests="369"', 'tests="368"'),
                            complete.replace('name="case0"', 'name="unrelated"')):
                path.write_text(altered)
                self.assertGreater(suites.report(path, 'general')['tests'], suites.GENERAL_MIN_REPORTED)
                with self.assertRaisesRegex(ValueError, 'TEST_REPORT_DISCOVERY_MISMATCH'):
                    suites.report(path, 'general', expected)

    def test_discovery_failure_is_saved_and_does_not_stop_remaining_suites(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(suites, 'ROOT', Path(folder)):
            output = Path(folder) / 'run'
            cases = []

            def discover(command, destination):
                self.assertEqual(dict(suites.plan('26'))['general'], command)
                self.assertEqual(output, destination)
                raise ValueError('GENERAL_DISCOVERY_INCOMPLETE')

            def execute(command, **_):
                cases.append(command)
                return SimpleNamespace(returncode=0)

            self.assertEqual(1, suites.run('26', output, execute=execute, discover=discover))
            result = json.loads((output / 'receipt.json').read_text())['suites'][0]
            self.assertEqual({'cases': 0, 'error': 'GENERAL_DISCOVERY_INCOMPLETE'}, result['discovery'])
            self.assertEqual(len(suites.plan('26')), len(cases))

    def test_native_runtime_requires_each_core_case_to_pass(self):
        command = dict(suites.plan('26'))['native-runtime']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'result.xml'
            complete = fixture(command, 6)
            path.write_text(complete)
            suites.report(path, 'native-runtime')
            for name in suites.NATIVE_RUNTIME_METHODS:
                with self.subTest(name=name):
                    path.write_text(complete.replace('name="'+name+'"', 'name="unrelated"'))
                    with self.assertRaisesRegex(ValueError, 'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path, 'native-runtime')
                    path.write_text(complete.replace('name="'+name+'"></testcase>',
                        'name="'+name+'"><skipped/></testcase>').replace('skipped="0"', 'skipped="1"'))
                    with self.assertRaisesRegex(ValueError, 'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path, 'native-runtime')

    def test_general_requires_all_editing_panel_scenarios(self):
        cls = suites.QA + 'EditingPanelInstrumentedTest'
        methods = {
            'publicSelectionNavigationAndCutReachTheEditorWithoutPayloadReads',
            'publicPasteAndFrameworkRestartKeepAdjacentSuffixLiteralUntilOwnSpace',
            'touchPopupEntryAndHeldArrowStopOnCancellation',
            'rawEditorsHideMenuCommandsAndPasswordEditorsHideEntry',
            'multilineArrowsPreserveColumnAndExtendAcrossLineBoundary',
            'restartClearsSelectionModeAndFreshFieldDoesNotInheritTheForeignBoundary',
            'hideAndShowKeepPastedSuffixLiteralUntilOwnBoundary',
            'realServiceRebindCannotCorrectThePastedAdjacentSuffix',
            'realServiceRebindAtStartPreservesForeignTextOnTheRight',
        }
        self.assertTrue({(cls, method) for method in methods} <= suites.GENERAL_REQUIRED)

    def test_general_rejects_missing_or_skipped_expanded_candidate_regressions(self):
        methods = {
            (suites.QA + 'ExpandedCandidatesInstrumentedTest', 'hiddenCandidateCanBeExplicitlySelectedInRealIme'),
            (suites.QA + 'ExpandedCandidatesInstrumentedTest', 'russianMetroIsSelectableFromExpandedSuggestions'),
            (suites.QA + 'ExpandedCandidatesInstrumentedTest', 'typingOutsideExpandedRowClosesItWithoutSelectingOldCandidate'),
            (suites.QA + 'ExpandedCandidatesInstrumentedTest', 'backClosesExpandedRowAndKeepsTypingSession'),
            ('io.github.mesteriis.rune.keyboard.ime.ui.CandidateStripInstrumentedTest',
             'expandedCandidatesStayOverKeysAndCancelHeldTouchOnRefresh'),
        }
        complete = fixture(dict(suites.plan('26'))['general'], 369)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xml'
            path.write_text(complete)
            self.assertEqual(369, suites.report(path, 'general')['tests'])
            for cls, name in sorted(methods):
                case = f'<testcase classname="{cls}" name="{name}"></testcase>'
                self.assertIn(case, complete)
                for status, altered in (
                    ('missing', complete.replace(case, '').replace('tests="369"', 'tests="368"')),
                    ('skipped', complete.replace(case, case.replace('</testcase>', '<skipped/></testcase>'))
                                        .replace('skipped="0"', 'skipped="1"')),
                ):
                    with self.subTest(method=name, status=status):
                        path.write_text(altered)
                        with self.assertRaisesRegex(ValueError, 'TEST_REPORT_REQUIRED_CASES'):
                            suites.report(path, 'general')

    def test_personal_suite_requires_each_admission_scenario(self):
        names = [
            'protectedOriginalIsExplainedInOrdinaryAndRefinementPaths',
            'explicitPairRejectionAndConfirmationAreExplainedWithoutChangingTheirGate',
            'compactPathKeepsProtectedAndPersonalVetoesWithRealRussianResources',
            'resourceFailuresHaveSpecificReasonsAndPreserveGateOrder',
        ]
        def xml(methods, skipped=None):
            cases = ''.join(f'<testcase classname="{suites.PERSONAL}" name="{name}">'
                            + ('<skipped/>' if name == skipped else '') + '</testcase>' for name in methods)
            return f'<testsuite tests="{len(methods)}" failures="0" errors="0" skipped="{int(skipped is not None)}">{cases}</testsuite>'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.xml'
            path.write_text(xml(names))
            suites.report(path, 'personal')
            for missing in names:
                with self.subTest(missing=missing):
                    path.write_text(xml([n for n in names if n != missing] + ['unrelatedScenario']))
                    with self.assertRaisesRegex(ValueError, 'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path, 'personal')
                    path.write_text(xml(names, skipped=missing))
                    with self.assertRaisesRegex(ValueError, 'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path, 'personal')

    def test_owned_scopes_and_qualification_are_separate(self):
        for api in ('26','37.0'):
            plan=dict(suites.plan(api));general=' '.join(plan['general'])
            for name in (suites.PERSONAL,suites.EXPORT,suites.LIFECYCLE,suites.QUAL_SAFETY):
                self.assertIn(name,general)
            self.assertIn('notClass=',general)
            self.assertIn('runeOwnedEmulator=q3-personal',' '.join(plan['personal']))
            self.assertIn('runeSyntheticProfileFixture=true',' '.join(plan['case-rejection']))
            self.assertIn(suites.CASE_REJECTION,' '.join(plan['case-rejection']))
            self.assertIn('runeSyntheticProfileFixture=true',' '.join(plan['confirmed-words']))
            for method in suites.CONFIRMED_METHODS:
                self.assertIn(suites.CONFIRMED+'#'+method,' '.join(plan['confirmed-words']))
            self.assertIn('runeComposeQa=true',' '.join(plan['compose-editor']))
            self.assertIn(suites.COMPOSE,' '.join(plan['compose-editor']))
            self.assertIn('-Pandroid.testInstrumentationRunnerArguments.runeEmojiMemory=true', plan['emoji-memory'])
            self.assertIn('-Pandroid.testInstrumentationRunnerArguments.class=' +
                          suites.EMOJI_MEMORY + '#' + suites.EMOJI_MEMORY_METHOD, plan['emoji-memory'])
            self.assertNotIn('runeEmojiMemory=', general)
            self.assertIn('runeOwnedEmulator=q8-editor',' '.join(plan['export-navigation']))
            self.assertIn('-PruneNativeQualification=true',plan['qualification-lifecycle'])
            self.assertIn(suites.LIFECYCLE,' '.join(plan['qualification-lifecycle']))
            self.assertIn(suites.QUAL_SAFETY,' '.join(plan['qualification-safety']))
            self.assertEqual(api=='26','export-picker' in plan)
            self.assertIn('native-runtime',plan)
            for command in plan.values():
                if ':app:connectedDebugAndroidTest' in command:
                    self.assertIn('-Pandroid.testInstrumentationRunnerArguments.runeCiFailureCapture=true', command)
        with self.assertRaisesRegex(ValueError,'ANDROID_SUITE_API'):suites.plan('30')

    def test_failure_is_retained_and_remaining_suites_run(self):
        calls=[]
        def fake(command,**kwargs):
            calls.append(command);kwargs['stdout'].write('fake output\n')
            return SimpleNamespace(returncode=1 if len(calls)==1 else 0)
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(suites,'ROOT',Path(folder)):
            output=Path(folder)/'run'
            self.assertEqual(1,suites.run('26',output,execute=fake))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertFalse(receipt['passed']);self.assertEqual(len(suites.plan('26')),len(calls))
            self.assertEqual(1,receipt['suites'][0]['exitCode'])
            self.assertTrue(all(not x['freshResultVerified'] for x in receipt['suites']))
            self.assertEqual('fake output\n',(output/'general.log').read_text())
            with self.assertRaises(FileExistsError):suites.run('26',output,execute=fake)

    def test_cli_rejects_multiple_devices_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            adb = root / 'adb'
            adb.write_text('#!/bin/sh\nprintf "List of devices attached\\n'
                           'emulator-5554\\tdevice\\nemulator-5556\\tdevice\\n"\n')
            adb.chmod(0o755)
            output = root / 'results'
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ.get('PATH', ''))
            result = subprocess.run([sys.executable, str(Path(suites.__file__).resolve()),
                                     '--api', '37.0', '--output', str(output),
                                     '--avd-name', 'rune-ci-boundary'],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('RESTART_REQUIRES_ONE_DEVICE', result.stderr)
            self.assertFalse(output.exists())

    def test_cli_rejects_missing_software_navigation_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            adb = root / 'adb'
            adb.write_text('#!/bin/sh\ncase "$*" in\n'
                '  devices) printf "List of devices attached\\nemulator-5554\\tdevice\\n";;\n'
                '  *ro.kernel.qemu) echo 1;;\n'
                '  *ro.hardware) echo ranchu;;\n'
                '  *emu\\ avd\\ name) printf "rune-ci-boundary\\nOK\\n";;\n'
                '  *qemu.hw.mainkeys) echo 1;;\n'
                '  *) exit 1;;\nesac\n')
            adb.chmod(0o755)
            output = root / 'results'
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ.get('PATH', ''))
            result = subprocess.run([sys.executable, str(Path(suites.__file__).resolve()),
                                     '--api', '26', '--output', str(output),
                                     '--avd-name', 'rune-ci-boundary'],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('ANDROID_SUITE_SOFTWARE_NAVIGATION_REQUIRED', result.stderr)
            self.assertFalse(output.exists())

    def test_cli_accepts_verified_software_navigation(self):
        import android_synthetic_restart_suites as restart
        args = ['android_boundary_suites.py', '--api', '26', '--output', 'unused',
                '--avd-name', 'rune-ci-boundary']
        with mock.patch.object(sys, 'argv', args), \
             mock.patch.object(restart, 'owned_emulator', return_value='emulator-5554'), \
             mock.patch.object(restart, 'checked_adb', return_value='0') as checked, \
             mock.patch.object(suites, 'run', return_value=0) as run:
            with self.assertRaises(SystemExit) as result:
                suites.main()
        self.assertEqual(0, result.exception.code)
        checked.assert_called_once_with(['-s', 'emulator-5554', 'shell', 'getprop', 'qemu.hw.mainkeys'])
        run.assert_called_once()

    def test_cli_allows_unexposed_property_only_on_api37(self):
        import android_synthetic_restart_suites as restart
        for api, expected in [('26', 'error'), ('37.0', 'allowed')]:
            with self.subTest(api=api):
                args = ['android_boundary_suites.py', '--api', api, '--output', 'unused',
                        '--avd-name', 'rune-ci-boundary']
                with mock.patch.object(sys, 'argv', args), \
                     mock.patch.object(restart, 'owned_emulator', return_value='emulator-5554'), \
                     mock.patch.object(restart, 'checked_adb', return_value=''), \
                     mock.patch.object(suites, 'run', return_value=0) as run:
                    if expected == 'error':
                        with self.assertRaisesRegex(ValueError, 'ANDROID_SUITE_SOFTWARE_NAVIGATION_REQUIRED'):
                            suites.main()
                        run.assert_not_called()
                    else:
                        with self.assertRaises(SystemExit) as result:
                            suites.main()
                        self.assertEqual(0, result.exception.code)
                        run.assert_called_once()

    def test_cli_rejects_hardware_keys_on_api37(self):
        import android_synthetic_restart_suites as restart
        args = ['android_boundary_suites.py', '--api', '37.0', '--output', 'unused',
                '--avd-name', 'rune-ci-boundary']
        with mock.patch.object(sys, 'argv', args), \
             mock.patch.object(restart, 'owned_emulator', return_value='emulator-5554'), \
             mock.patch.object(restart, 'checked_adb', return_value='1'), \
             mock.patch.object(suites, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'ANDROID_SUITE_SOFTWARE_NAVIGATION_REQUIRED'):
                suites.main()
            run.assert_not_called()

    def test_device_guard_rejects_changes_during_suite(self):
        calls = []
        checks = []
        def guard():
            checks.append(True)
            if len(checks) == 2:
                raise ValueError('ANDROID_SUITE_DEVICE_CHANGED')
        def fake(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(suites, 'ROOT', Path(folder)):
            with self.assertRaisesRegex(ValueError, 'ANDROID_SUITE_DEVICE_CHANGED'):
                suites.run('37.0', Path(folder) / 'run', execute=fake, device_guard=guard)
            self.assertFalse((Path(folder) / 'run' / 'receipt.json').exists())
        self.assertEqual(2, len(checks))
        self.assertEqual(1, len(calls))

    def test_old_results_cannot_be_mistaken_for_a_new_run(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(suites,'ROOT',Path(folder)):
            stale=Path(folder)/'app/build/outputs/androidTest-results/connected/debug'
            stale.mkdir(parents=True)
            (stale/'TEST-old.xml').write_text('<testsuite tests="500" failures="0" errors="0" skipped="0"/>')
            output=Path(folder)/'run'
            self.assertEqual(1,suites.run('37.0',output,execute=lambda *a,**k:SimpleNamespace(returncode=0)))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertFalse(receipt['suites'][0]['freshResultVerified'])
            self.assertTrue((output/'general-prior-results/TEST-old.xml').exists())

    def test_each_suite_must_publish_fresh_nonempty_junit_results(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(suites,'ROOT',Path(folder)):
            def fake(command,**kwargs):
                module='runtime-llama' if ':runtime-llama:connectedDebugAndroidTest' in command else 'app'
                result=Path(folder)/module/'build/outputs/androidTest-results/connected/debug'
                result.mkdir(parents=True)
                count=300 if 'notClass=' in ' '.join(command) else 4 if 'q3-personal' in ' '.join(command) else 2 if suites.CASE_REJECTION in ' '.join(command) else 4 if suites.COMPOSE in ' '.join(command) else 3 if suites.CONFIRMED in ' '.join(command) else 1
                (result/'TEST-device.xml').write_text(fixture(command,count))
                return SimpleNamespace(returncode=0)
            output=Path(folder)/'run'
            self.assertEqual(0,suites.run('26',output,execute=fake))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertTrue(receipt['passed'])
            self.assertTrue(all(s['freshResultVerified'] for s in receipt['suites']))

    def test_truncated_general_suite_cannot_pass(self):
        for count, skipped in ((1, 0), (299, 0), (300, 51)):
            with self.subTest(count=count, skipped=skipped), tempfile.TemporaryDirectory() as folder, mock.patch.object(suites,'ROOT',Path(folder)):
                def fake(command,**kwargs):
                    module='runtime-llama' if ':runtime-llama:connectedDebugAndroidTest' in command else 'app'
                    result=Path(folder)/module/'build/outputs/androidTest-results/connected/debug'
                    result.mkdir(parents=True)
                    n, s=(count, skipped) if 'notClass=' in ' '.join(command) else (4 if 'q3-personal' in ' '.join(command) else 2 if suites.CASE_REJECTION in ' '.join(command) else 4 if suites.COMPOSE in ' '.join(command) else 3 if suites.CONFIRMED in ' '.join(command) else 1, 0)
                    (result/'TEST-device.xml').write_text(fixture(command,n,s))
                    return SimpleNamespace(returncode=0)
                output=Path(folder)/'run'
                self.assertEqual(1,suites.run('26',output,execute=fake))
                receipt=json.loads((output/'receipt.json').read_text())
                self.assertFalse(receipt['suites'][0]['freshResultVerified'])
                self.assertTrue(all(s['freshResultVerified'] for s in receipt['suites'][1:]))

    def test_general_requires_previously_failed_cases_to_execute(self):
        for cls, method in (
            ('TypingDiagnosticsInstrumentedTest', 'externalSelectionDisableProducesContentFreeMetadataInRealIme'),
            ('TypingDiagnosticsInstrumentedTest', 'privateExpandedCandidateSelectionDoesNotWriteEnabledDiagnostics'),
            ('EmojiPanelInstrumentedTest', 'privatePaletteKeepsHeightAndInsertsEmojiWithoutReadingEditor'),
            ('EmojiPanelInstrumentedTest', 'privateComplexEmojiDeletionNeverReadsEditor'),
            ('EmojiPanelInstrumentedTest', 'privateWebViewEmojiDeletionAndContinuation'),
            ('EmojiPanelInstrumentedTest', 'privateEmojiExternalRewriteKeepsEditorText'),
            ('EmojiPanelInstrumentedTest', 'privateEmojiExternalCursorMoveDoesNotDeleteEmoji'),
            ('EmojiPanelInstrumentedTest', 'privateEmojiDroppedCompositionKeepsEmojiAndNextInput'),
            ('ImeLifecycleInstrumentedTest', 'backspaceRepeatStopsWhenImeViewDetaches'),
            ('LiveCandidatesInstrumentedTest', 'canonicalCaseAutoReplacesOnBoundaryAndBackspaceRestoresOriginal'),
            ('LiveCandidatesInstrumentedTest', 'languageSwitchFailureReportsDisabledTarget'),
        ):
            self.assertIn((suites.QA+cls, method), suites.GENERAL_REQUIRED)
        command=dict(suites.plan('26'))['general']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.xml'
            complete=fixture(command,300)
            path.write_text(complete)
            self.assertEqual(300,suites.report(path,'general')['tests'])
            for cls,method in suites.GENERAL_REQUIRED:
                with self.subTest(method=method):
                    target=f'<testcase classname="{cls}" name="{method}"></testcase>'
                    self.assertIn(target,complete)
                    path.write_text(complete.replace(target,target.replace(method,method+'Missing')))
                    with self.assertRaisesRegex(ValueError,'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path,'general')
                    path.write_text(complete.replace('skipped="0"','skipped="1"').replace(target,target.replace('</testcase>','<skipped/></testcase>')))
                    with self.assertRaisesRegex(ValueError,'TEST_REPORT_REQUIRED_CASES'):
                        suites.report(path,'general')

    def test_general_rejects_unexpected_skip_even_above_execution_floor(self):
        command=dict(suites.plan('26'))['general']
        complete=fixture(command,300)
        filler=f'<testcase classname="{suites.QA}ExampleTest" name="case0"></testcase>'
        cls,method=next(iter(suites.general_known_skips()))
        allowed=f'<testcase classname="{cls}" name="{method}"><skipped/></testcase>'
        unexpected=f'<testcase classname="{suites.QA}ExampleTest" name="case0"><skipped/></testcase>'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.xml'
            path.write_text(complete.replace('skipped="0"','skipped="1"').replace(filler,allowed))
            self.assertEqual(1,suites.report(path,'general')['skipped'])
            path.write_text(complete.replace('skipped="0"','skipped="1"').replace(filler,unexpected))
            with self.assertRaisesRegex(ValueError,'TEST_REPORT_UNEXPECTED_SKIP'):
                suites.report(path,'general')

    def test_general_skip_inventory_rejects_duplicate_or_invalid_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'skips.json'
            for entries in ([{'class':'c','method':'m'}]*2, [{'class':'c'}], []):
                path.write_text(json.dumps({'schema':1,'knownSkips':entries}))
                with mock.patch.object(suites,'GENERAL_SKIP_FILE',path):
                    with self.assertRaisesRegex(ValueError,'GENERAL_SKIP_SCHEMA'):
                        suites.general_known_skips()

    def test_invalid_or_all_skipped_results_cannot_pass(self):
        for xml in ('<testsuites tests="4" failures="0" errors="0" skipped="4"/>',
                    '<testsuites tests="-1" failures="0" errors="0" skipped="0"/>',
                    '<testsuites tests="4"/>', '<broken'):
            with self.subTest(xml=xml), tempfile.TemporaryDirectory() as folder, mock.patch.object(suites,'ROOT',Path(folder)):
                def fake(command,**kwargs):
                    module='runtime-llama' if ':runtime-llama:connectedDebugAndroidTest' in command else 'app'
                    result=Path(folder)/module/'build/outputs/androidTest-results/connected/debug'
                    result.mkdir(parents=True);(result/'TEST-device.xml').write_text(xml)
                    return SimpleNamespace(returncode=0)
                self.assertEqual(1,suites.run('37.0',Path(folder)/'run',execute=fake))

    def test_case_rejection_requires_both_methods_without_skips(self):
        command = dict(suites.plan('37.0'))['case-rejection']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xml'
            path.write_text(fixture(command, 2))
            self.assertEqual(2, suites.report(path, 'case-rejection')['tests'])
            path.write_text(fixture(command, 1))
            with self.assertRaisesRegex(ValueError, 'TEST_REPORT_SCOPE'):
                suites.report(path, 'case-rejection')
            path.write_text(fixture(command, 2, skipped=1))
            self.assertEqual(1, suites.report(path, 'case-rejection')['skipped'])

    def test_compose_scope_requires_all_four_exact_methods(self):
        command = dict(suites.plan('37.0'))['compose-editor']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xml'
            complete = fixture(command, 4)
            path.write_text(complete)
            self.assertEqual(4, suites.report(path, 'compose-editor')['tests'])
            for method in suites.COMPOSE_METHODS:
                with self.subTest(method=method):
                    path.write_text(complete.replace(f'name="{method}"', 'name="otherMethod"'))
                    with self.assertRaisesRegex(ValueError, 'TEST_REPORT_SCOPE'):
                        suites.report(path, 'compose-editor')

    def test_confirmed_words_requires_exact_methods(self):
        command = dict(suites.plan('37.0'))['confirmed-words']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xml'
            path.write_text(fixture(command, 3))
            self.assertEqual(3, suites.report(path, 'confirmed-words')['tests'])
            path.write_text(fixture(command, 2))
            with self.assertRaisesRegex(ValueError, 'TEST_REPORT_SCOPE'):
                suites.report(path, 'confirmed-words')

    def test_emoji_memory_requires_the_exact_observer(self):
        command = dict(suites.plan('26'))['emoji-memory']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'TEST-device.xml'
            path.write_text(fixture(command, 1))
            self.assertEqual(1, suites.report(path, 'emoji-memory')['tests'])
            path.write_text(fixture(command, 1).replace(suites.EMOJI_MEMORY_METHOD, 'anotherTest'))
            with self.assertRaisesRegex(ValueError, 'TEST_REPORT_SCOPE'):
                suites.report(path, 'emoji-memory')

    def test_synthetic_scope_skip_fails_the_routed_run(self):
        for target, target_class in [('case-rejection', suites.CASE_REJECTION),
                                     ('confirmed-words', suites.CONFIRMED),
                                     ('compose-editor', suites.COMPOSE),
                                     ('emoji-memory', suites.EMOJI_MEMORY)]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder, mock.patch.object(suites, 'ROOT', Path(folder)):
                def fake(command, **kwargs):
                    module = 'runtime-llama' if ':runtime-llama:connectedDebugAndroidTest' in command else 'app'
                    result = Path(folder) / module / 'build/outputs/androidTest-results/connected/debug'
                    result.mkdir(parents=True)
                    args = ' '.join(command)
                    count = 300 if 'notClass=' in args else 4 if 'q3-personal' in args else 2 if suites.CASE_REJECTION in args else 4 if suites.COMPOSE in args else 3 if suites.CONFIRMED in args else 1
                    (result / 'TEST-device.xml').write_text(fixture(command, count, skipped=1 if target_class in args else 0))
                    return SimpleNamespace(returncode=0)
                output = Path(folder) / 'run'
                self.assertEqual(1, suites.run('37.0', output, execute=fake))
                receipt = json.loads((output / 'receipt.json').read_text())
                scope = next(item for item in receipt['suites'] if item['name'] == target)
                self.assertFalse(scope['freshResultVerified'])
                self.assertEqual(1, scope['reports'][0]['skipped'])

    def test_report_refuses_header_only_mismatched_status_and_wrong_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'report.xml'
            wrong_scope=fixture(suites.plan('26')[0][1],1)
            samples=(
                '<testsuites tests="1" failures="0" errors="0" skipped="0"/>',
                wrong_scope.replace('</testcase>','<failure/></testcase>'),
                fixture(suites.plan('26')[1][1],4).replace(
                    f'name="{sorted(suites.PERSONAL_METHODS)[1]}"',
                    f'name="{sorted(suites.PERSONAL_METHODS)[0]}"'),
                fixture(suites.plan('26')[1][1],4).replace('skipped="0"','skipped="1"'),
                wrong_scope,
            )
            for value in samples:
                with self.subTest(value=value[:100]):
                    p.write_text(value)
                    with self.assertRaises(ValueError):suites.report(p,'personal')
            p.write_text(fixture(suites.plan('26')[1][1],4))
            with self.assertRaisesRegex(ValueError,'TEST_REPORT_SCOPE'):suites.report(p,'general')

if __name__=='__main__':unittest.main()
