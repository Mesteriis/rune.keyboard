#!/usr/bin/env python3
"""Finite RU/ES profile: native flags, Unicode affixes, <=32 codepoints, native acceptance."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from pipeline_config import PACKAGE, build_root

ROOT = build_root()
MAX_CODEPOINTS = 32


@dataclass(frozen=True)
class Rule:
    kind: str
    flag: int
    cross: bool
    strip: str
    add: str
    continuation: tuple[int, ...]
    condition: re.Pattern[str]

    def apply(self, word: str) -> str | None:
        # FULLSTRIP is not enabled by either pinned dictionary.
        if len(word) <= len(self.strip) or not self.condition.search(word):
            return None
        if self.kind == 'PFX':
            if not word.startswith(self.strip):
                return None
            result = self.add + word[len(self.strip):]
        else:
            if not word.endswith(self.strip):
                return None
            result = word[:len(word)-len(self.strip)] + self.add
        return result if 0 < len(result) <= MAX_CODEPOINTS else None


def native_flags(aff: Path, dic: Path, strings: set[str], language: str) -> dict[str, tuple[int, tuple[int, ...]]]:
    ordered = sorted(strings - {''})
    result = subprocess.run([str(ROOT/'bin/spell_oracle'), str(aff), str(dic), '--flags'],
                            input='\n'.join(ordered)+'\n', text=True, encoding='utf-8',
                            capture_output=True, check=True)
    decoded = {'': (0, ())}
    for line in result.stdout.splitlines():
        single, vector, original = line.split('\t')
        decoded[original] = (int(single), tuple(map(int, vector.split(','))) if vector else ())
    if set(decoded) != set(ordered) | {''}:
        raise ValueError('Native flag decoder did not return every requested flag')
    (ROOT/f'reports/{language}-native-flags.tsv').write_text(
        'single_flag\tflag_vector\tsource_text\n'+result.stdout, encoding='utf-8')
    return decoded


def read_dictionary(dic: Path) -> list[tuple[str, str]]:
    lines = dic.read_text(encoding='utf-8').splitlines()
    entries = []
    for line in lines[1:]:
        # These exact inputs have no morphology fields or escaped slash entries.
        line = line.strip()
        if not line:
            continue
        if any(c.isspace() for c in line) or '\\' in line:
            raise ValueError(f'Unsupported dictionary syntax: {line!r}')
        word, _, flags = line.partition('/')
        entries.append((word, flags))
    if len(entries) != int(lines[0]):
        raise ValueError(f'Dictionary count mismatch: {dic.name}')
    return entries


def read_rules(aff: Path, dic: Path, entries: list[tuple[str, str]], language: str) -> tuple[list[Rule], dict, Counter]:
    lines = [line.strip().split() for line in aff.read_text(encoding='utf-8').splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    allowed = {'SET', 'FLAG', 'TRY', 'MAP', 'REP', 'PFX', 'SFX'}
    directives = Counter(row[0] for row in lines)
    if set(directives) - allowed:
        raise ValueError(f'Unsupported affix directives: {set(directives)-allowed}')
    strings = {flags for _, flags in entries}
    for row in lines:
        if row[0] in {'PFX', 'SFX'}:
            strings.add(row[1])
            if len(row) == 5:
                strings.add(row[3].partition('/')[2])
    decoded = native_flags(aff, dic, strings, language)
    rules = []
    index = 0
    while index < len(lines):
        row = lines[index]
        directive = row[0]
        index += 1
        if directive == 'SET':
            if row != ['SET', 'UTF-8']:
                raise ValueError('Unsupported dictionary encoding')
        elif directive == 'FLAG':
            if row != ['FLAG', 'UTF-8']:
                raise ValueError('Unsupported flag encoding')
        elif directive == 'TRY':
            if len(row) != 2:
                raise ValueError('Malformed TRY')
        elif directive in {'MAP', 'REP'}:
            count = int(row[1])
            block = lines[index:index+count]
            if len(block) != count or any(r[0] != directive for r in block):
                raise ValueError(f'Malformed {directive} table')
            index += count  # Suggestion-only tables do not generate lexical affixes.
        else:
            if len(row) != 4 or row[2] not in {'Y', 'N'}:
                raise ValueError('Malformed affix header')
            count = int(row[3])
            block = lines[index:index+count]
            if len(block) != count:
                raise ValueError('Truncated affix table')
            for item in block:
                if len(item) != 5 or item[:2] != row[:2]:
                    raise ValueError('Malformed affix rule')
                condition = item[4]
                if any(c in condition for c in '\\$*+?{}()|'):
                    raise ValueError('Unsupported affix condition grammar')
                add, _, continuation = item[3].partition('/')
                rules.append(Rule(directive, decoded[item[1]][0], row[2] == 'Y',
                                  '' if item[2] == '0' else item[2], '' if add == '0' else add,
                                  decoded[continuation][1],
                                  re.compile('^'+condition if directive == 'PFX' else condition+'$')))
            index += count
    if any(r.continuation for r in rules if r.kind == 'PFX'):
        raise ValueError('Prefix continuation is outside this finite profile')
    # A continuation chain may have only one further suffix in these exact sources.
    continuation_flags = {f for r in rules for f in r.continuation}
    if any(r.continuation for r in rules if r.kind == 'SFX' and r.flag in continuation_flags):
        raise ValueError('Continuation depth exceeds the explicit two-suffix profile')
    return rules, decoded, directives


def generate(entries: list[tuple[str, str]], rules: list[Rule], decoded: dict) -> set[str]:
    prefix, suffix = defaultdict(list), defaultdict(list)
    for rule in rules:
        (prefix if rule.kind == 'PFX' else suffix)[rule.flag].append(rule)
    words = set()
    for root, raw_flags in entries:
        if not 0 < len(root) <= MAX_CODEPOINTS:
            continue
        flags = decoded[raw_flags][1]
        p_rules = [rule for flag in flags for rule in prefix[flag]]
        s_rules = [rule for flag in flags for rule in suffix[flag]]
        words.add(root)
        starts = [(root, False)]
        for rule in p_rules:
            value = rule.apply(root)
            if value:
                words.add(value)
                if rule.cross:
                    starts.append((value, True))
        for start, prefixed in starts:
            for rule in s_rules:
                if prefixed and not rule.cross:
                    continue
                first = rule.apply(start)
                if first is None:
                    continue
                derived = [(first, rule.cross)]
                for flag in rule.continuation:
                    for second in suffix[flag]:
                        if prefixed and not second.cross:
                            continue
                        value = second.apply(first)
                        if value:
                            derived.append((value, rule.cross and second.cross))
                        # Also enumerate a prefix between the two suffixes.
                        # The native acceptance pass resolves any ordering-specific mismatch.
                        if not prefixed and rule.cross and second.cross:
                            for p_rule in p_rules:
                                middle = p_rule.apply(first) if p_rule.cross else None
                                value = second.apply(middle) if middle else None
                                if value:
                                    words.add(value)
                for value, cross in derived:
                    words.add(value)
                    if not prefixed and cross:
                        for p_rule in p_rules:
                            if p_rule.cross:
                                p_value = p_rule.apply(value)
                                if p_value:
                                    words.add(p_value)
    return words


def file_record(path: Path) -> dict:
    data = path.read_bytes()
    scope = {} if path.is_relative_to(ROOT) else {'scope': 'tool'}
    relative = path.relative_to(ROOT) if not scope else path.relative_to(PACKAGE)
    return {**scope, 'path': str(relative), 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'rows': data.count(b'\n')}


def write_words(path: Path, words: set[str]) -> dict:
    path.write_text(''.join(word+'\n' for word in sorted(words)), encoding='utf-8')
    return file_record(path)


def run_oracle(aff: Path, dic: Path, words: set[str], language: str, tag: str) -> tuple[set[str], int]:
    input_path = ROOT/f'reports/{language}-{tag}-input.txt'
    write_words(input_path, words)
    output_path = ROOT/f'reports/{language}-{tag}-oracle.tsv'
    with input_path.open('rb') as source, output_path.open('wb') as output:
        subprocess.run([str(ROOT/'bin/spell_oracle'), str(aff), str(dic)], stdin=source,
                       stdout=output, check=True)
    accepted, rejected = set(), 0
    with output_path.open(encoding='utf-8') as source:
        for line in source:
            if line.startswith('1\t'):
                accepted.add(line[2:].rstrip('\n'))
            elif line.startswith('0\t'):
                rejected += 1
            else:
                raise ValueError('Invalid oracle response')
    if len(accepted)+rejected != len(words):
        raise ValueError('Oracle count mismatch')
    return accepted, rejected


def expand(language: str, stem: str) -> dict:
    aff, dic = [ROOT/f'sources/libreoffice/{stem}.{suffix}' for suffix in ['aff', 'dic']]
    entries = read_dictionary(dic)
    rules, decoded, directives = read_rules(aff, dic, entries, language)
    candidates = generate(entries, rules, decoded)
    accepted, rejected = run_oracle(aff, dic, candidates, language, 'finite')
    surfaces = {unicodedata.normalize('NFC', word) for word in accepted}
    keys = {unicodedata.normalize('NFC', word.lower()) for word in surfaces}
    result = {'language': language, 'profile': 'finite-affixes-v1-max32-no-implicit-compounds',
              'dictionary_entries': len(entries), 'rules': len(rules),
              'directives': dict(sorted(directives.items())), 'enumerated_candidates': len(candidates),
              'oracle_accepted': len(accepted), 'oracle_rejected': rejected,
              'surface_forms': write_words(ROOT/f'outputs/{language}.surface-forms.txt', surfaces),
              'canonical_keys': write_words(ROOT/f'outputs/{language}.words.txt', keys),
              'nfc_changed': sum(word != unicodedata.normalize('NFC', word) for word in accepted),
              'case_changed': sum(word != word.lower() for word in surfaces),
              'non_bmp_flag_strings': sum(any(ord(c)>65535 for c in flag) for flag in decoded)}
    frequency = {line.rsplit(' ', 1)[0] for line in
                 (ROOT/f'sources/frequency/{language}_50k.txt').read_text(encoding='utf-8').splitlines()}
    known, _ = run_oracle(aff, dic, frequency, language, 'frequency')
    missing = known - accepted
    result['known_frequency_words'] = len(known)
    result['missing_frequency_words'] = write_words(ROOT/f'reports/{language}-finite-missing-known.txt', missing)
    legacy_path = ROOT/f'reports/{language}-unmunch-raw.txt'
    if legacy_path.exists():
        legacy = {line for line in legacy_path.read_text(encoding='utf-8').splitlines()
                  if '/' not in line and '|' not in line and 0 < len(line) <= MAX_CODEPOINTS}
        extra, _ = run_oracle(aff, dic, legacy-accepted, language, 'legacy-extra')
        result['accepted_unmunch_not_enumerated'] = write_words(ROOT/f'reports/{language}-legacy-extra-accepted.txt', extra)
    print(language, json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    report = [expand('ru', 'ru_RU/ru_RU'), expand('es', 'es/es_ES')]
    (ROOT/'reports/finite-expansion.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
