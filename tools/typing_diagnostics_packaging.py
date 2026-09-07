#!/usr/bin/env python3
"""Check pre-R8 declarations and mapped final DEX, not an original-name APK grep."""
import argparse
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

PREFIX = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.'
CONTRACTS = {'DiagnosticKind', 'DiagnosticReason', 'DiagnosticSource', 'DiagnosticCompletion', 'DiagnosticEvent', 'DiagnosticText',
             'TypingDiagnostics', 'NoTypingDiagnostics', 'TypingDiagnosticsProvider',
             'DiagnosticsSettingsProvider'}
# Observed in the pinned compiler's pre-R8 classes and mapped final DEX respectively.
# No prefix/wildcard allowance: a nested recorder or a new helper requires review.
COMPILER_HELPERS = {'TypingDiagnostics$DefaultImpls',
                    'DiagnosticsSettingsProvider$$ExternalSyntheticLambda0'}
ANDROID = '{http://schemas.android.com/apk/res/android}'


def parse_mapping(text):
    return {renamed: original for original, renamed in
            re.findall(r'^([^\s#].*?) -> ([^\s:]+):$', text, re.M)}


def forbidden_classes(names, mapping=None):
    mapping = mapping or {}
    originals = {mapping.get(name, name) for name in names}
    return sorted(name for name in originals if name.startswith(PREFIX) and
                  name.removeprefix(PREFIX) not in CONTRACTS | COMPILER_HELPERS)


def defined_dex_classes(data):
    if len(data) < 112 or not re.fullmatch(rb'dex\n0\d\d\x00', data[:8]):
        raise ValueError('Missing or unsupported DEX header')

    def uint(offset):
        if offset < 0 or offset + 4 > len(data): raise ValueError('DEX offset outside file')
        return struct.unpack_from('<I', data, offset)[0]

    def table(size_offset, item_size):
        count, offset = uint(size_offset), uint(size_offset + 4)
        if offset + count * item_size > len(data): raise ValueError('DEX table outside file')
        return count, offset

    strings_count, strings = table(56, 4)
    types_count, types = table(64, 4)
    count, classes = table(96, 32)
    names = set()
    for index in range(count):
        type_index = uint(classes + index * 32)
        if type_index >= types_count: raise ValueError('DEX class type outside table')
        string_index = uint(types + type_index * 4)
        if string_index >= strings_count: raise ValueError('DEX string outside table')
        offset = uint(strings + string_index * 4)
        for _ in range(5):
            if offset >= len(data): raise ValueError('DEX string length missing')
            byte = data[offset]; offset += 1
            if byte < 128: break
        else: raise ValueError('DEX string length overflow')
        end = data.find(b'\0', offset)
        if end < 0: raise ValueError('Unterminated DEX class descriptor')
        descriptor = data[offset:end].decode('utf-8', errors='strict')
        if not descriptor.startswith('L') or not descriptor.endswith(';'):
            raise ValueError('Invalid defined class descriptor')
        names.add(descriptor[1:-1].replace('/', '.'))
    return names


def class_inventory(paths):
    names = set()
    for path in paths:
        if path.is_dir():
            names.update(str(p.relative_to(path))[:-6].replace('/', '.') for p in path.rglob('*.class'))
        elif path.is_file() and zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as jar:
                names.update(name[:-6].replace('/', '.') for name in jar.namelist() if name.endswith('.class'))
        else: raise ValueError('Missing pre-R8 class artifact: ' + str(path))
    if not names: raise ValueError('Empty pre-R8 class inventory')
    return names


def verify(args):
    names = class_inventory(args.classes)
    manifest = ET.parse(args.manifest).getroot()
    package = manifest.get('package', '')
    components = []
    def component_name(name):
        if not name: return ''
        if name.startswith('.'): return package + name
        return package + '.' + name if '.' not in name else name

    for element in manifest.iter():
        if element.tag not in ('activity', 'activity-alias', 'service', 'receiver', 'provider'): continue
        name = component_name(element.get(ANDROID + 'name', ''))
        if element.tag == 'activity-alias' and component_name(
                element.get(ANDROID + 'targetActivity', '')).startswith(PREFIX):
            raise ValueError('Diagnostics activity alias target forbidden: ' + name)
        if name.startswith(PREFIX): components.append((name, element))
    apks = sorted(args.apk_dir.glob('*.apk'))
    if not apks: raise ValueError('Final APK artifact missing')
    if args.variant == 'debug':
        expected = PREFIX + 'DiagnosticsActivity'
        if expected not in names: raise ValueError('Debug diagnostics activity class missing')
        if len(components) != 1 or components[0][0] != expected:
            raise ValueError('Unexpected debug diagnostics manifest components')
        element = components[0][1]
        if element.get(ANDROID + 'exported') != 'false' or element.find('intent-filter') is not None:
            raise ValueError('Debug diagnostics must be private without intent filters')
    else:
        if components: raise ValueError('Diagnostics component packaged in ' + args.variant)
        if args.mapping is None or not args.mapping.is_file():
            raise ValueError('Obfuscation mapping required for final variant')
        violations = forbidden_classes(names)
        if violations: raise ValueError('Pre-R8 debug diagnostics classes: ' + ', '.join(violations))
    mapping = parse_mapping(args.mapping.read_text()) if args.mapping else {}
    dex_names = set()
    for apk in apks:
        with zipfile.ZipFile(apk) as archive:
            dex_files = [name for name in archive.namelist() if re.fullmatch(r'classes\d*\.dex', name)]
            if not dex_files: raise ValueError('Final APK has no DEX files')
            for name in dex_files: dex_names.update(defined_dex_classes(archive.read(name)))
            if args.variant != 'debug' and any('typing-diagnostics' in name for name in archive.namelist()):
                raise ValueError('Diagnostic data file packaged in final APK')
    if args.variant != 'debug':
        violations = forbidden_classes(dex_names, mapping)
        if violations: raise ValueError('Final DEX debug diagnostics classes: ' + ', '.join(violations))
    print(f'typing diagnostics packaging PASS: {args.variant}, {len(names)} pre-R8 classes, {len(dex_names)} DEX classes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', required=True, choices=('debug', 'release', 'profile'))
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--apk-dir', required=True, type=Path)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--classes', action='append', type=Path, required=True)
    try: verify(parser.parse_args())
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile, ET.ParseError) as error:
        raise SystemExit(str(error)) from error
