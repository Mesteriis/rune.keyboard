#!/usr/bin/env python3
"""Check source-bound persisted fields, limits and bilingual learning disclosures."""
import ast
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/'
CONTRACTS = {
    'PersonalWord': ('personalization/PersonalTypingModel.kt', {'language', 'word'}),
    'PersonalFeedback': ('personalization/PersonalTypingModel.kt', {'language', 'original', 'replacement', 'accepted', 'rejected'}),
    'PersonalPhrase': ('personalization/PersonalTypingModel.kt', {'language', 'prefix', 'continuation', 'support'}),
    'PersonalTypingSnapshot': ('personalization/PersonalTypingModel.kt', {'feedback', 'confirmed', 'phrases'}),
    'LearningEvidence': ('learning/LearningModel.kt', {'language', 'originalHash', 'expectedHash', 'source', 'pattern', 'holdout', 'trains', 'original', 'expected', 'conflicted'}),
    'LearningSnapshot': ('learning/LearningModel.kt', {'evidence', 'activePolicy', 'rollbackPolicy'}),
    'LearningPatternPolicy': ('learning/LearningModel.kt', {'counts'}),
}
LIMITS = {
    ('personalization/PersonalTypingCodec.kt', 'MAX_FILE_BYTES'): 1048576,
    ('personalization/PersonalTypingModel.kt', 'MAX_CONFIRMED'): 512,
    ('personalization/PersonalTypingModel.kt', 'MAX_FEEDBACK'): 512,
    ('personalization/PersonalTypingModel.kt', 'MAX_PHRASES'): 1024,
    ('personalization/PersonalTypingModel.kt', 'MAX_WORD_CHARS'): 48,
    ('personalization/PersonalTypingModel.kt', 'MAX_COUNT'): 255,
    ('learning/LearningCodec.kt', 'MAX_BYTES'): 524288,
    ('learning/LearningModel.kt', 'MAX_EVIDENCE'): 512,
}
# Reviewed serialized writers; schema edits require renewed disclosure review.
WRITERS = {
    ('personalization/PersonalTypingCodec.kt', 'encode'): 'd19117ba65f652180b89159917f3abc5366cd71797308bd36a80c0166ec26d69',
    ('learning/LearningCodec.kt', 'encode'): '8783fdfd580d4a52bf774b3a3310dcf441fbe9c63864c820d2f45861d5b920b0',
    ('learning/LearningCodec.kt', 'writePolicy'): 'f3b6ba5e25389cf46f6a07e6bcde7a6f861a3876bd590dcb07842925d0eb7846',
}

CONSENT = {
    'values': {
        ('strings.xml', 'settings_personal_learning_summary'): ['confirmed words', 'typed/chosen', 'acceptance counts', 'rejection flags', 'phrase prefixes/continuations', 'language', 'support counts', '1 MiB', 'password', 'incognito', 'keeps the profile', 'including words you did not correct'],
        ('typing_controls_strings.xml', 'settings_collect_examples_summary'): ['original/expected words', 'language', 'hashes', 'feedback source', 'edit type', 'training/holdout/conflict', '512 records', '512 KiB', 'do not encrypt', 'also turn off typo-pattern learning'],
        ('typing_controls_strings.xml', 'settings_typo_patterns_summary'): ['word hashes', 'training/holdout/conflict', 'raw-example collection off', 'do not encrypt', 'active and rollback edit-pattern counts', 'both learning-lab switches'],
        ('learning_strings.xml', 'learning_scope'): ['active and rollback edit-pattern counts', 'per language', 'both example collection and typo-pattern learning', 'password', 'incognito', 'neither encryption nor anonymization'],
    },
    'values-ru': {
        ('strings.xml', 'settings_personal_learning_summary'): ['подтверждённые слова', 'набранных и выбранных', 'числом подтверждений', 'запретом замены', 'начала и продолжения фраз', 'языком', 'частотой', '1 МиБ', 'пароли', 'инкогнито', 'сохраняет профиль', 'включая слова без исправлений'],
        ('typing_controls_strings.xml', 'settings_collect_examples_summary'): ['исходные и ожидаемые слова', 'языком', 'хешами', 'источником', 'типом опечатки', 'обучения, проверочной выборки и конфликта', '512 записей', '512 КиБ', 'не шифруют', 'выключите также обучение типам опечаток'],
        ('typing_controls_strings.xml', 'settings_typo_patterns_summary'): ['хеши слов', 'обучения, проверочной выборки и конфликта', 'при выключенном сборе исходных примеров', 'не шифруют', 'текущие и предыдущие счётчики', 'выключите оба переключателя'],
        ('learning_strings.xml', 'learning_scope'): ['текущие и предыдущие счётчики типов опечаток по языкам', 'выключите оба переключателя', 'пароли', 'инкогнито', 'не являются шифрованием или анонимизацией'],
    },
}


def writer_body(source, name):
    match = re.search(r'\bfun\s+' + re.escape(name) + r'\s*\(', source)
    if not match:
        raise ValueError('MISSING_WRITER')
    start = source.index('{', match.end())
    depth = 1
    for index in range(start + 1, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise ValueError('UNTERMINATED_WRITER')


def constructor_fields(source, name):
    match = re.search(r'\bdata\s+class\s+' + re.escape(name) + r'\s*\(', source)
    if not match:
        raise ValueError('MISSING_RECORD')
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        depth += (source[index] == '(') - (source[index] == ')')
        if depth == 0:
            return set(re.findall(r'\b(?:val|var)\s+(\w+)\s*:', source[start:index]))
    raise ValueError('UNTERMINATED_RECORD')


def number(node):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return number(node.left) * number(node.right)
    raise ValueError('UNREVIEWED_LIMIT_EXPRESSION')


def inspect(root=ROOT):
    errors = []
    try:
        guide = (root / 'docs/USER_GUIDE.ru.md').read_text()
        privacy = (root / 'PRIVACY.md').read_text()
        for (path, name), expected in WRITERS.items():
            body = writer_body((root / (BASE + path)).read_text(), name)
            if hashlib.sha256(body.encode()).hexdigest() != expected:
                errors.append('UNREVIEWED_SERIALIZED_WRITER ' + path + '/' + name)
        for name, (path, expected) in CONTRACTS.items():
            actual = constructor_fields((root / (BASE + path)).read_text(), name)
            if actual != expected:
                errors.append('UNREVIEWED_PERSISTED_FIELDS ' + name)
            rows = [line for line in guide.splitlines() if line.startswith('| `' + name + '`')]
            if len(rows) != 1 or any('`' + field + '`' not in rows[0] for field in actual):
                errors.append('GUIDE_PERSISTED_FIELDS ' + name)
        for (path, key), expected in LIMITS.items():
            source = (root / (BASE + path)).read_text()
            match = re.search(r'const val ' + key + r'\s*=\s*([0-9_* \t]+)\s*(?://[^\n]*)?$', source, re.M)
            if not match or number(ast.parse(match[1].strip(), mode='eval').body) != expected:
                errors.append('UNDISCLOSED_STORAGE_LIMIT ' + key)
        for locale, resources in CONSENT.items():
            for (filename, key), markers in resources.items():
                tree = ET.parse(root / 'app/src/main/res' / locale / filename)
                values = [e.text or '' for e in tree.getroot() if e.attrib.get('name') == key]
                if len(values) != 1 or any(marker.casefold() not in values[0].casefold() for marker in markers):
                    errors.append('CONSENT_DISCLOSURE ' + locale + '/' + key)
        for path in ['no_backup/personal-typing/profile.bin', 'no_backup/learning-lab/learning.bin']:
            if path not in guide or path not in privacy:
                errors.append('STORAGE_PATH_DISCLOSURE ' + path)
        if 'Learning lab → Reset examples and patterns' not in privacy or 'Delete personal typing data' not in privacy:
            errors.append('SEPARATE_RESET_DISCLOSURE')
    except (OSError, ValueError, SyntaxError, ET.ParseError):
        errors.append('UNREADABLE_OR_UNREVIEWED_DISCLOSURE_SOURCE')
    return errors


if __name__ == '__main__':
    failures = inspect()
    print('\n'.join(failures) if failures else 'Learning privacy disclosures PASS: seven records, eight limits, EN/RU consent')
    raise SystemExit(bool(failures))
