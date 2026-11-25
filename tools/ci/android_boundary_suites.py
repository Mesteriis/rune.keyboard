#!/usr/bin/env python3
"""Run owned-emulator Android suites with explicit fixture scopes and evidence."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
QA='io.github.mesteriis.rune.keyboard.qa.'
APP_RUNNER='io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner'
GRADLE_RUNNER_ARG='-Pandroid.testInstrumentationRunnerArguments.'
PERSONAL='io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalAdmissionInstrumentedTest'
PERSONAL_METHODS={
    'protectedOriginalIsExplainedInOrdinaryAndRefinementPaths',
    'explicitPairRejectionAndConfirmationAreExplainedWithoutChangingTheirGate',
    'compactPathKeepsProtectedAndPersonalVetoesWithRealRussianResources',
    'resourceFailuresHaveSpecificReasonsAndPreserveGateOrder',
}
EXPORT='io.github.mesteriis.rune.keyboard.smarttyping.tools.QualityExportInstrumentedTest'
LIFECYCLE='io.github.mesteriis.rune.keyboard.smarttyping.experiments.RussianAssetsLifecycleInstrumentedTest'
QUAL_SAFETY=QA+'QualificationPackageSafetyInstrumentedTest'
CONFIRMED=QA+'ConfirmedWordsInstrumentedTest'
CONFIRMED_METHODS={'fullConfirmationReportsLimitOnceAndListCanBeFiltered',
                   'failedRemovalOffersIdempotentRetryAndPreservesPairRejection',
                   'settingsNavigationOpensTheConfirmedWordsList'}
CASE_REJECTION=QA+'CaseRejectionImeInstrumentedTest'
CASE_REJECTION_METHODS={'learnedCaseRejectionSurvivesSymbolsAndColon',
                        'undoLearnsAndLaterManualCaseChoiceStillWorks'}
COMPOSE=QA+'EditingComposeInstrumentedTest'
COMPOSE_METHODS={'composePrivateEmojiDeletionAndContinuation',
                 'composeSelectionCutPasteAndNativeMenuKeepPayloadReadsZero',
                 'composePasteKeepsAdjacentSuffixLiteralAndOwnSpaceRestoresCorrection',
                 'composeVerticalSelectionAndHomeEndUseNativeBoundaries'}
EMOJI_MEMORY=QA+'EmojiMemoryMeasurementInstrumentedTest'
EMOJI_MEMORY_METHOD='observeProcessMemoryBeforeAfterOpeningAndVisitingCategories'
NATIVE_RUNTIME='io.github.mesteriis.rune.runtime.llama.LlamaRuntimeInstrumentedTest'
NATIVE_RUNTIME_METHODS={
    'scoringBeforeLoadAndAfterCancelOrUnloadReturnsTypedFailure',
    'publicScoringRejectsInvalidInputWithoutAModel',
    'nativeScoringIndependentlyValidatesByteArraysAndReturnsNoPartialWire',
    'scoringRacesWithCancelUnloadAndCloseWithoutHanging',
    'nativeLibraryLoadsAndBadFileReturnsTypedFailure',
    'concurrentCancelAndCloseNeverUseADestroyedHandle',
}
# Keep conservative minimums even when comparing the full discovered set:
# they catch accidental filtering shared by discovery and execution.
GENERAL_MIN_REPORTED=300
GENERAL_MIN_EXECUTED=250
GENERAL_SKIP_FILE=Path(__file__).with_name('android-general-skips.json')
GENERAL_REQUIRED={
    *((QA+'ExpandedCandidatesInstrumentedTest',name) for name in (
        'hiddenCandidateCanBeExplicitlySelectedInRealIme',
        'russianMetroIsSelectableFromExpandedSuggestions',
        'typingOutsideExpandedRowClosesItWithoutSelectingOldCandidate',
        'backClosesExpandedRowAndKeepsTypingSession')),
    ('io.github.mesteriis.rune.keyboard.ime.ui.CandidateStripInstrumentedTest',
     'expandedCandidatesStayOverKeysAndCancelHeldTouchOnRefresh'),
    (QA+'TypingDiagnosticsInstrumentedTest','externalSelectionDisableProducesContentFreeMetadataInRealIme'),
    (QA+'TypingDiagnosticsInstrumentedTest','privateExpandedCandidateSelectionDoesNotWriteEnabledDiagnostics'),
    (QA+'EmojiOpeningMeasurementInstrumentedTest','measureFreshPaletteHandlerAndFirstDrawStart'),
    (QA+'EmojiPresentedFrameInstrumentedTest','firstVisibleEmojiHasPixelCopyEvidence'),
    (QA+'EmojiPanelInstrumentedTest','privatePaletteKeepsHeightAndInsertsEmojiWithoutReadingEditor'),
    (QA+'EmojiPanelInstrumentedTest','privateComplexEmojiDeletionNeverReadsEditor'),
    (QA+'EmojiPanelInstrumentedTest','privateWebViewEmojiDeletionAndContinuation'),
    (QA+'EmojiPanelInstrumentedTest','privateEmojiExternalRewriteKeepsEditorText'),
    (QA+'EmojiPanelInstrumentedTest','privateEmojiExternalCursorMoveDoesNotDeleteEmoji'),
    (QA+'EmojiPanelInstrumentedTest','privateEmojiDroppedCompositionKeepsEmojiAndNextInput'),
    (QA+'ImeLifecycleInstrumentedTest','backspaceRepeatStopsWhenImeViewDetaches'),
    (QA+'LiveCandidatesInstrumentedTest','canonicalCaseAutoReplacesOnBoundaryAndBackspaceRestoresOriginal'),
    (QA+'LiveCandidatesInstrumentedTest','russianAlpAbbreviationStaysLowercaseAtAllBoundaries'),
    (QA+'LiveCandidatesInstrumentedTest','russianDomainLabelStaysExactAtAllBoundaries'),
    (QA+'LiveCandidatesInstrumentedTest','russianDomainContinuationRestoresLabelAfterReadyPeriodCorrection'),
    (QA+'LiveCandidatesInstrumentedTest','englishIAfterInternalApostropheIsNotSuggested'),
    (QA+'LiveCandidatesInstrumentedTest','languageSwitchFailureReportsDisabledTarget'),
    *((QA+'EditingPanelInstrumentedTest',name) for name in (
        'publicSelectionNavigationAndCutReachTheEditorWithoutPayloadReads',
        'publicPasteAndFrameworkRestartKeepAdjacentSuffixLiteralUntilOwnSpace',
        'touchPopupEntryAndHeldArrowStopOnCancellation',
        'rawEditorsHideMenuCommandsAndPasswordEditorsHideEntry',
        'multilineArrowsPreserveColumnAndExtendAcrossLineBoundary',
        'restartClearsSelectionModeAndFreshFieldDoesNotInheritTheForeignBoundary',
        'hideAndShowKeepPastedSuffixLiteralUntilOwnBoundary',
        'realServiceRebindCannotCorrectThePastedAdjacentSuffix',
        'realServiceRebindAtStartPreservesForeignTextOnTheRight')),
    (QA+'EditorBoundaryInstrumentedTest','distinctEditorResetsManualShiftAndSymbolsThroughBinder'),
    (QA+'LiveCandidatesInstrumentedTest','immediateBackspaceUndoThenSpaceKeepsOriginalDuringFollowingWord'),
    (QA+'NeighborRecoveryLiveInstrumentedTest','threeNeighborErrorsCorrectWithHiddenStripAndBackspaceRestoresSource'),
    (QA+'NeighborRecoveryLiveInstrumentedTest','twoNeighborErrorsCorrectAndUndoKeepsTheNextWord'),
    (QA+'ReviewedChatProtectionInstrumentedTest','compactChatOriginalIsKeptAtSpace'),
    (QA+'ReviewedChatProtectionInstrumentedTest','contextualChatOriginalIsKeptAtSpace'),
    (QA+'ReviewedChatProtectionInstrumentedTest','protectedOriginalStillAllowsManualSuggestion'),
    (QA+'ReviewedChatProtectionInstrumentedTest','wishesChatOriginalIsKeptAtSpace'),
    (QA+'ReviewedChatProtectionInstrumentedTest','inviteChatOriginalIsKeptAtSpace'),
    *((QA+'ReviewedChatProtectionInstrumentedTest',name) for name in (
        'pairingChatOriginalIsKeptAtSpace', 'toxicChatOriginalIsKeptAtSpace',
        'bannedChatOriginalIsKeptAtSpace', 'colloquialYoOriginalIsKeptAtSpace',
        'slangChatOriginalIsKeptAtSpace', 'protectedSlangAllowsContextualManualSuggestion')),
    *((QA+'MechanicalPunctuationInstrumentedTest',name) for name in (
        'pairOfDotsWaitsForWhitespaceAndNewWordThenUndoesCapsTogether',
        'decimalVersionAndHostnameKeepOwnedBoundariesWithoutLayerChanges',
        'cachedMechanicalTogglePreservesHeldKeyInstancesAndNextInputUndo',
        'commaPopupPunctuationCapsAndImmediateUndoNeverReplayOldWord',
        'commandDotKeepsItsSeparatorAcrossBoundaryAndOrdinaryBackspace',
        'russianColonContinuationAddsSpaceWithoutCapitalization',
        'russianEraAbbreviationKeepsLowercaseInSentenceCapsEditor',
        'russianPeriodContinuationCapitalizesNextSentence')),
}


def general_known_skips():
    data=json.loads(GENERAL_SKIP_FILE.read_text())
    if (not isinstance(data,dict) or set(data)!={'schema','knownSkips'} or
            type(data['schema']) is not int or data['schema'] != 1):
        raise ValueError('GENERAL_SKIP_SCHEMA')
    entries=data['knownSkips']
    if not isinstance(entries,list) or not entries:
        raise ValueError('GENERAL_SKIP_SCHEMA')
    identities=[]
    for entry in entries:
        if (not isinstance(entry,dict) or set(entry)!={'class','method'} or
                not all(isinstance(entry[k],str) and entry[k] for k in ('class','method'))):
            raise ValueError('GENERAL_SKIP_SCHEMA')
        identities.append((entry['class'],entry['method']))
    if identities != sorted(set(identities)):
        raise ValueError('GENERAL_SKIP_SCHEMA')
    return set(identities)


def report(path, scope, expected_identities=None):
    root=ET.parse(path).getroot()
    if root.tag not in ('testsuite','testsuites'):raise ValueError('TEST_REPORT_ROOT')
    counts={key:int(root.attrib[key]) for key in ('tests','failures','errors','skipped')}
    cases=list(root.iter('testcase'))
    if any(value<0 for value in counts.values()) or len(cases)!=counts['tests']:
        raise ValueError('TEST_REPORT_COUNTS')
    identities=set();passed=set();skipped=set();actual={'failures':0,'errors':0,'skipped':0}
    for case in cases:
        identity=(case.get('classname'),case.get('name'))
        if not all(identity) or identity in identities:raise ValueError('TEST_REPORT_IDENTITY')
        identities.add(identity)
        statuses=[child.tag for child in case if child.tag in ('failure','error','skipped')]
        if len(statuses)>1:raise ValueError('TEST_REPORT_STATUS')
        if not statuses:passed.add(identity)
        if 'skipped' in statuses:skipped.add(identity)
        for status in statuses:actual[{'failure':'failures','error':'errors','skipped':'skipped'}[status]]+=1
    if any(counts[key]!=actual[key] for key in actual):raise ValueError('TEST_REPORT_STATUS_COUNTS')
    required={'personal':(PERSONAL,None), 'export-navigation':(EXPORT,'qualityDashboardOwnsNumericExportNavigation'),
              'export-picker':(EXPORT,'realDocumentPickerCancelAndSaveExportOnlyNumericSnapshot'),
              'qualification-lifecycle':(LIFECYCLE,None), 'qualification-safety':(QUAL_SAFETY,None)}
    if scope in required:
        cls,method=required[scope]
        if any(c!=cls or method is not None and m!=method for c,m in identities):raise ValueError('TEST_REPORT_SCOPE')
        if scope=='personal' and not {(PERSONAL, name) for name in PERSONAL_METHODS} <= passed:
            raise ValueError('TEST_REPORT_REQUIRED_CASES')
    elif scope in ('case-rejection','confirmed-words','compose-editor','emoji-memory'):
        cls,methods={'case-rejection':(CASE_REJECTION,CASE_REJECTION_METHODS),
                     'confirmed-words':(CONFIRMED,CONFIRMED_METHODS),
                     'compose-editor':(COMPOSE,COMPOSE_METHODS),
                     'emoji-memory':(EMOJI_MEMORY,{EMOJI_MEMORY_METHOD})}[scope]
        if identities != {(cls, method) for method in methods}:
            raise ValueError('TEST_REPORT_SCOPE')
    elif scope=='general' and any(c in (PERSONAL,EXPORT,LIFECYCLE,QUAL_SAFETY) for c,_ in identities):
        raise ValueError('TEST_REPORT_SCOPE')
    elif scope=='general' and not GENERAL_REQUIRED <= passed:
        raise ValueError('TEST_REPORT_REQUIRED_CASES')
    elif scope=='general' and not skipped <= general_known_skips():
        raise ValueError('TEST_REPORT_UNEXPECTED_SKIP')
    elif scope=='native-runtime' and any(not c.startswith('io.github.mesteriis.rune.runtime.llama.') for c,_ in identities):
        raise ValueError('TEST_REPORT_SCOPE')
    elif scope=='native-runtime' and not {(NATIVE_RUNTIME, name) for name in NATIVE_RUNTIME_METHODS} <= passed:
        raise ValueError('TEST_REPORT_REQUIRED_CASES')
    if expected_identities is not None and identities != expected_identities:
        raise ValueError('TEST_REPORT_DISCOVERY_MISMATCH')
    return counts


def plan(api):
    if api not in ('26','37.0'):raise ValueError('ANDROID_SUITE_API')
    common=['./gradlew','--no-daemon',':app:connectedDebugAndroidTest']
    arg=GRADLE_RUNNER_ARG
    excluded=','.join((PERSONAL,EXPORT,LIFECYCLE,QUAL_SAFETY))
    result=[('general',common+[arg+'runeOwnedEmulator=q4-counters',arg+'notClass='+excluded]),
            ('personal',common+[arg+'runeOwnedEmulator=q3-personal',arg+'class='+PERSONAL]),
            ('case-rejection',common+[arg+'runeSyntheticProfileFixture=true',arg+'class='+CASE_REJECTION]),
            ('confirmed-words',common+[arg+'runeSyntheticProfileFixture=true',
                arg+'class='+','.join(CONFIRMED+'#'+method for method in sorted(CONFIRMED_METHODS))]),
            ('compose-editor',common+[arg+'runeComposeQa=true',arg+'class='+COMPOSE]),
            ('emoji-memory',common+[arg+'runeEmojiMemory=true',
                arg+'class='+EMOJI_MEMORY+'#'+EMOJI_MEMORY_METHOD]),
            ('export-navigation',common+[arg+'runeOwnedEmulator=q8-editor',
                arg+'class='+EXPORT+'#qualityDashboardOwnsNumericExportNavigation'])]
    if api=='26':
        result.append(('export-picker',common+[arg+'runeOwnedEmulator=q4-counters',
            arg+'class='+EXPORT+'#realDocumentPickerCancelAndSaveExportOnlyNumericSnapshot']))
    for name,cls in (('qualification-lifecycle',LIFECYCLE),('qualification-safety',QUAL_SAFETY)):
        result.append((name,['./gradlew','--no-daemon','-PruneNativeQualification=true',
            ':app:connectedDebugAndroidTest',arg+'class='+cls]))
    result.append(('native-runtime',['./gradlew','--no-daemon',':runtime-llama:connectedDebugAndroidTest']))
    for _, command in result:
        if ':app:connectedDebugAndroidTest' in command:
            command.append(arg+'runeCiFailureCapture=true')
    return result


def discovered_cases(raw):
    """Check the runner's log-only start/end stream and terminal summary."""
    if ('INSTRUMENTATION_FAILED' in raw or 'FAILURES!!!' in raw
            or re.findall(r'^INSTRUMENTATION_CODE: (.+)$', raw, re.M) != ['-1']):
        raise ValueError('GENERAL_DISCOVERY_INCOMPLETE')
    status = {}
    started = set()
    finished = set()
    for line in raw.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            key, sep, value = line.removeprefix('INSTRUMENTATION_STATUS: ').partition('=')
            if sep:
                status[key] = value
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            code = line.rsplit(' ', 1)[-1]
            identity = (status.get('class'), status.get('test'))
            if not all(identity) or code not in ('1', '0', '-3', '-4'):
                raise ValueError('GENERAL_DISCOVERY_EVENT')
            if code == '1':
                if identity in started or identity in finished:
                    raise ValueError('GENERAL_DISCOVERY_DUPLICATE')
                started.add(identity)
            else:
                if identity in finished or (identity not in started and code != '-3'):
                    raise ValueError('GENERAL_DISCOVERY_SEQUENCE')
                finished.add(identity)
            status = {}
    counts = re.findall(r'^OK \((\d+) tests?\)$', raw, re.M)
    if not finished or started - finished or counts != [str(len(finished))]:
        raise ValueError('GENERAL_DISCOVERY_INCOMPLETE')
    return finished


def discover_general(serial, command, output, execute=subprocess.run):
    test_apk = ROOT / 'app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'
    args = ['adb', '-s', serial]
    install = execute(args + ['install', '-t', '-r', str(test_apk)],
                      text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    (output / 'general-discovery-install.log').write_text(install.stdout)
    if install.returncode != 0 or 'Success' not in install.stdout.splitlines():
        raise ValueError('GENERAL_DISCOVERY_INSTALL')
    native = args + ['shell', 'am', 'instrument', '--user', '0', '-w', '-r', '-e', 'log', 'true']
    for value in command:
        if value.startswith(GRADLE_RUNNER_ARG):
            key, argument = value.removeprefix(GRADLE_RUNNER_ARG).split('=', 1)
            native.extend(('-e', key, argument))
    result = execute(native + [APP_RUNNER], text=True, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, timeout=120)
    (output / 'general-discovery.log').write_text(result.stdout)
    if result.returncode != 0:
        raise ValueError('GENERAL_DISCOVERY_ADB')
    identities = discovered_cases(result.stdout)
    (output / 'general-discovered-cases.json').write_text(json.dumps(
        [{'class': cls, 'method': method} for cls, method in sorted(identities)],
        indent=2) + '\n')
    return identities


def run(api,output,execute=subprocess.run,device_guard=None,discover=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    results=[]
    for name,command in plan(api):
        if device_guard is not None:
            device_guard()
        print('ANDROID_SUITE_START',name,flush=True)
        expected = None
        discovery_error = None
        if name == 'general' and discover is not None:
            try:
                expected = discover(command, output)
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                discovery_error = str(error) if isinstance(error, ValueError) else type(error).__name__
                print('ANDROID_GENERAL_DISCOVERY_FAILED', discovery_error, flush=True)
            if device_guard is not None:
                device_guard()
        module='runtime-llama' if name=='native-runtime' else 'app'
        source=ROOT/module/'build/outputs/androidTest-results/connected/debug'
        # Preserve any old results separately so a failed invocation cannot be
        # mistaken for a fresh result from the previous suite.
        if source.exists():shutil.move(str(source),str(output/(name+'-prior-results')))
        with (output/(name+'.log')).open('w') as log:
            result=execute(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if device_guard is not None:
            device_guard()
        evidence=[]
        if source.is_dir():
            preserved=output/(name+'-results')
            shutil.move(str(source),str(preserved))
            for path in preserved.glob('TEST-*.xml'):
                try:
                    evidence.append(report(path,name,expected))
                except (ET.ParseError,ValueError,KeyError) as error:
                    if isinstance(error, ValueError) and str(error) == 'TEST_REPORT_DISCOVERY_MISMATCH':
                        print('ANDROID_GENERAL_REPORT_DISCOVERY_MISMATCH', flush=True)
                    evidence.append({'tests':0,'failures':0,'errors':1,'skipped':0})
        minimum={'personal':4,'export-navigation':1,'export-picker':1,
                 'qualification-lifecycle':1,'qualification-safety':1,'case-rejection':2,'confirmed-words':3,
                 'compose-editor':4}.get(name,1)
        verified=bool(evidence) and sum(x['tests']-x['skipped'] for x in evidence)>=minimum
        if name in ('case-rejection','confirmed-words','compose-editor','emoji-memory'):
            verified=verified and len(evidence)==1 and evidence[0]['skipped']==0
        if name=='general':
            verified=verified and sum(x['tests'] for x in evidence)>=GENERAL_MIN_REPORTED
            verified=verified and sum(x['tests']-x['skipped'] for x in evidence)>=GENERAL_MIN_EXECUTED
            if discover is not None:
                verified=verified and expected is not None and len(evidence)==1
        verified=verified and not any(x['failures'] or x['errors'] for x in evidence)
        results.append({'name':name,'exitCode':result.returncode,'freshResultVerified':verified,'reports':evidence})
        if name == 'general' and discover is not None:
            results[-1]['discovery'] = {'cases': len(expected) if expected is not None else 0,
                                       'error': discovery_error}
        print('ANDROID_SUITE_END',name,result.returncode,'freshResultVerified',verified,flush=True)
    receipt={'schema':1,'api':api,'suites':results,'passed':all(x['exitCode']==0 and x['freshResultVerified'] for x in results)}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return 0 if receipt['passed'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--api',required=True,choices=('26','37.0'));p.add_argument('--output',type=Path,required=True);p.add_argument('--avd-name',required=True)
    args=p.parse_args()
    from android_synthetic_restart_suites import checked_adb, owned_emulator
    serial=owned_emulator(args.avd_name)
    def guard():
        if owned_emulator(args.avd_name) != serial:
            raise ValueError('ANDROID_SUITE_DEVICE_CHANGED')
        navigation_mode = checked_adb(['-s', serial, 'shell', 'getprop', 'qemu.hw.mainkeys'])
        # API 37's 16 KiB system image does not expose this property even when
        # the emulator was started with it; the real-insets test still checks
        # that the navigation exclusion is present.
        if navigation_mode != '0' and not (args.api == '37.0' and navigation_mode == ''):
            raise ValueError('ANDROID_SUITE_SOFTWARE_NAVIGATION_REQUIRED')
    guard()
    def discover(command, output):
        return discover_general(serial, command, output)
    raise SystemExit(run(args.api,args.output,device_guard=guard,discover=discover))

if __name__=='__main__':main()
