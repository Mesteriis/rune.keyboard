#!/usr/bin/env python3
"""Check architecture source namespaces and reviewed orchestration orders."""
from pathlib import Path
import re

from check_learning_disclosures import writer_body as function_body

ROOT = Path(__file__).resolve().parents[1]
BASE = 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/'
ENUMS = {
    'SpellingSource': BASE + 'correction/SpellingQualification.kt',
    'DiagnosticSource': BASE + 'diagnostics/TypingDiagnostics.kt',
}
CONTROLLER = BASE + 'session/TypingSessionController.kt'
PERSONAL = BASE + 'personalization/AndroidTypingPersonalization.kt'
RECOVERY = BASE + 'correction/RecoveryQualification.kt'


def enum_values(source, name):
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    match = re.search(r'\benum\s+class\s+' + re.escape(name) + r'\s*\{([^}]*)}', source, re.S)
    if not match:
        raise ValueError('MISSING_ENUM')
    values = [part.strip() for part in match[1].split(';')[0].split(',') if part.strip()]
    if not values or len(values) != len(set(values)) or any(not re.fullmatch(r'[A-Z][A-Z0-9_]*', v) for v in values):
        raise ValueError('UNREVIEWED_ENUM_SHAPE')
    return values


def ordered(source, patterns):
    matches = []
    for label, pattern in patterns:
        positions = list(re.finditer(pattern, source))
        if len(positions) != 1:
            raise ValueError('UNREVIEWED_BRANCH_SHAPE')
        matches.append((positions[0].start(), label))
    return [label for _, label in sorted(matches)]


def marker(document, key):
    values = re.findall(r'<!-- Q2:' + re.escape(key) + r' ([A-Z0-9_ ]+) -->', document)
    if len(values) != 1:
        raise ValueError('MISSING_ORDER_MARKER')
    return values[0].split()


def inspect(root=ROOT):
    errors = []
    try:
        document = (root / 'docs/ARCHITECTURE.md').read_text()
        for name, path in ENUMS.items():
            actual = enum_values((root / path).read_text(), name)
            match = re.search(r'<!-- Q2:' + name + r':begin -->(.*?)<!-- Q2:' + name + r':end -->', document, re.S)
            rows = re.findall(r'^\| `([A-Z][A-Z0-9_]*)` \|', match[1], re.M) if match else []
            if rows != actual:
                errors.append('SOURCE_NAMESPACE_TABLE ' + name)
        controller = (root / CONTROLLER).read_text()
        personal = (root / PERSONAL).read_text()
        baseline = function_body(controller, 'baselineCandidateSelection').split('val ranking = when', 1)[1]
        actual = ordered(baseline, [
            ('COMMON_CONFUSION', r'commonId\s*>\s*0\s*->'),
            ('CANONICAL_CASE', r'snapshot\.isCanonicalCaseCorrection\(\)\s*->'),
            ('GENERAL_LOCAL', r'localDecision\s*!=\s*null\s*->'),
            ('COMPACT_PUBLIC', r'compactWinner\s*!=\s*null\s*->'),
            ('NEIGHBOR_RECOVERY', r'recoveryWinner\s*!=\s*null\s*->'),
            ('CALIBRATED', r'CalibratedSpellingPolicy\.rank\('),
        ])
        if marker(document, 'BASELINE_ORDER') != actual:
            errors.append('SOURCE_BRANCH_ORDER BASELINE_ORDER')
        contextual = function_body(personal, 'jointAutomaticEvaluation')
        actual = ordered(contextual, [
            ('LEGACY', r'\blegacyJointAutomaticEvaluation\('),
            ('CONTEXTUAL_PUBLIC', r'ContextualCorrectionPolicy\.evaluate\('),
            ('INFINITIVE_REVISION', r'InfinitiveRevisionPolicy\.evaluate\('),
            ('NOUN_CASE_REVISION', r'NounCaseRevisionPolicy\.evaluate\('),
        ])
        if marker(document, 'CONTEXTUAL_ORDER') != actual:
            errors.append('SOURCE_BRANCH_ORDER CONTEXTUAL_ORDER')
        legacy = function_body(personal, 'legacyJointAutomaticEvaluation')
        actual = ordered(legacy, [('JOINT', r'JointCorrectionPolicy\.evaluate\('),
                                  ('JOINT_RESCUE', r'JointRescuePolicy\.evaluate\(')])
        if marker(document, 'LEGACY_ORDER') != actual:
            errors.append('SOURCE_BRANCH_ORDER LEGACY_ORDER')
        flags = {'nounCaseRevision': 'NOUN_CASE_REVISION', 'grammarRevision': 'INFINITIVE_REVISION',
                 'contextualPublic': 'CONTEXTUAL_PUBLIC', 'wordContext': 'WORD_CONTEXT',
                 'jointRescue': 'JOINT_RESCUE', 'jointPublic': 'JOINT',
                 'neighborRecovery': 'NEIGHBOR_RECOVERY', 'compactPublic': 'COMPACT_PUBLIC'}
        for name in ['allowsAutomatic', 'automaticDecision']:
            actual_flags = re.findall(r'selection\.ranking\?\.(\w+)\s*==\s*true', function_body(controller, name))
            actual = [flags[flag] for flag in actual_flags] + ['DEFAULT']
            if marker(document, 'ADMISSION_ORDER') != actual:
                errors.append('SOURCE_BRANCH_ORDER ADMISSION_ORDER/' + name)
        model = re.search(r'const val MODEL_QUALIFIED\s*=\s*(true|false)\b', (root / RECOVERY).read_text())
        if not model or 'RecoveryQualification.MODEL_QUALIFIED=' + model[1] not in document:
            errors.append('MODEL_REFINEMENT_STATUS')
    except (OSError, ValueError, IndexError, KeyError):
        errors.append('UNREADABLE_OR_UNREVIEWED_SOURCE_CONTRACT')
    return errors


if __name__ == '__main__':
    errors = inspect()
    if errors:
        print('\n'.join(errors))
    else:
        counts = {name: len(enum_values((ROOT / path).read_text(), name)) for name, path in ENUMS.items()}
        print(f"Typing source documentation PASS: {counts['SpellingSource']} spelling, {counts['DiagnosticSource']} diagnostic, orchestration orders")
    raise SystemExit(bool(errors))
