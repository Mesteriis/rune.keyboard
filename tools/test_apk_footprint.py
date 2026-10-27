from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import apk_footprint as footprint


class ApkFootprintTest(unittest.TestCase):
    def budgets(self):
        value = copy.deepcopy(footprint.load_budgets(footprint.BUDGETS))
        value.update(maxApkBytes=1_000_000, maxUncompressedBytes=10_000,
                     maxContainerBytes=100_000)
        value['baseline']['apkBytes'] = 100
        value['categories'] = dict.fromkeys(footprint.GROUPS, 2_000)
        value['nativeByAbi'] = dict.fromkeys(footprint.ABIS, 1_000)
        return value

    def apk(self, directory, extra=None, compression=zipfile.ZIP_STORED):
        path = Path(directory) / 'fixture.apk'
        entries = {'lib/arm64-v8a/librune_llama.so': b'arm',
                   'lib/arm64-v8a/libc++_shared.so': b'cpp',
                   'lib/x86_64/librune_llama.so': b'x86',
                   'lib/x86_64/libc++_shared.so': b'cpp',
                   'assets/smarttyping/lexicon/en.trie': b'lexicon',
                   'assets/smarttyping/experiments/context.bin': b'context',
                   'res/drawable/icon.png': b'image', 'classes.dex': b'dex',
                   'classes2.dex': b'dex2', 'assets/emoji/catalog-v1.tsv': b'emoji'}
        entries.update(extra or {})
        with zipfile.ZipFile(path, 'w', compression=compression) as archive:
            for name, value in entries.items(): archive.writestr(name, value)
        return path

    def test_all_entries_are_accounted_and_metadata_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory)
            report = footprint.measure(path, self.budgets())
            self.assertTrue(report['passed'])
            self.assertEqual(7, report['categories']['lexicon']['uncompressedBytes'])
            self.assertEqual(7, report['categories']['dex']['uncompressedBytes'])
            self.assertEqual(5, report['categories']['other']['uncompressedBytes'])
            self.assertEqual({'arm64-v8a': 6, 'x86_64': 6}, report['nativeByAbi'])
            self.assertEqual(report['apkBytes'], report['compressedBytes'] + report['containerBytes'])
            self.assertEqual(report, footprint.measure(path, self.budgets()))
            self.assertNotIn(str(path), json.dumps(report))

    def test_compressed_oversized_asset_fails_even_when_apk_total_is_small(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory, {'assets/smarttyping/lexicon/growth.trie': b'0' * 20_000}, zipfile.ZIP_DEFLATED)
            report = footprint.measure(path, self.budgets())
            self.assertLess(report['apkBytes'], self.budgets()['maxApkBytes'])
            self.assertFalse(report['passed'])
            self.assertIn('UNCOMPRESSED_TOTAL', report['violations'])
            self.assertIn('CATEGORY_LEXICON', report['violations'])

    def test_each_category_and_each_native_abi_has_an_independent_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory)
            report = footprint.measure(path, self.budgets())
            for group in footprint.GROUPS:
                budgets = self.budgets()
                budgets['categories'][group] = report['categories'][group]['uncompressedBytes'] - 1
                self.assertEqual(['CATEGORY_' + group.upper()], footprint.measure(path, budgets)['violations'])
            for abi in footprint.ABIS:
                budgets = self.budgets(); budgets['nativeByAbi'][abi] = 5
                self.assertEqual(['NATIVE_' + abi], footprint.measure(path, budgets)['violations'])

    def test_apk_and_container_limits_are_inclusive_and_detect_appended_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory)
            budgets = self.budgets(); original = footprint.measure(path, budgets)
            budgets['maxApkBytes'] = original['apkBytes']
            budgets['maxContainerBytes'] = original['containerBytes']
            self.assertTrue(footprint.measure(path, budgets)['passed'])
            with path.open('ab') as stream: stream.write(b'x')
            self.assertEqual(['APK_TOTAL', 'ZIP_CONTAINER'], footprint.measure(path, budgets)['violations'])

    def test_duplicate_unsafe_and_nonempty_directory_members_refuse(self):
        for extra in ({'../escape': b'x'}, {'/absolute': b'x'}, {'assets\\hidden': b'x'}, {'assets/': b'payload'}):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(footprint.FootprintError):
                    footprint.measure(self.apk(directory, extra), self.budgets())
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory)
            with warnings.catch_warnings(), zipfile.ZipFile(path, 'a') as archive:
                warnings.simplefilter('ignore', UserWarning); archive.writestr('classes.dex', b'again')
            with self.assertRaisesRegex(footprint.FootprintError, 'DUPLICATE_APK_MEMBER'):
                footprint.measure(path, self.budgets())

    def test_unknown_or_missing_native_architecture_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(footprint.FootprintError, 'NATIVE_ABI_OR_MEMBER'):
                footprint.measure(self.apk(directory, {'lib/armeabi-v7a/other.so': b'x'}), self.budgets())
            path = Path(directory) / 'no-native.apk'
            with zipfile.ZipFile(path, 'w') as archive: archive.writestr('classes.dex', b'dex')
            with self.assertRaisesRegex(footprint.FootprintError, 'NATIVE_ABI_SET'):
                footprint.measure(path, self.budgets())

    def test_apk_mutation_between_zip_measurement_and_hash_cannot_publish_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.apk(directory)
            digest = hashlib.sha256()
            class ChangedDuringHash:
                changed = False
                def update(self, chunk):
                    digest.update(chunk)
                    if not self.changed:
                        with path.open('ab') as stream: stream.write(b'x')
                        self.changed = True
                def hexdigest(self): return digest.hexdigest()
            with patch.object(footprint.hashlib, 'sha256', return_value=ChangedDuringHash()):
                with self.assertRaisesRegex(footprint.FootprintError, 'APK_CHANGED_DURING_MEASUREMENT'):
                    footprint.measure(path, self.budgets())

    def test_agp_metadata_selects_signed_or_unsigned_file_without_stale_globs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); metadata = root / 'output-metadata.json'
            path = self.apk(root); (root / 'stale.apk').write_bytes(b'stale')
            value = dict(variantName='release', elements=[dict(type='SINGLE', filters=[], outputFile=path.name)])
            metadata.write_text(json.dumps(value))
            self.assertEqual(path, footprint.release_apk(root))
            value['elements'][0]['outputFile'] = '../outside.apk'; metadata.write_text(json.dumps(value))
            with self.assertRaisesRegex(footprint.FootprintError, 'RELEASE_APK_NAME'):
                footprint.release_apk(root)
            value['elements'] = []; metadata.write_text(json.dumps(value))
            with self.assertRaisesRegex(footprint.FootprintError, 'RELEASE_SINGLE_APK_REQUIRED'):
                footprint.release_apk(root)

    def test_budget_schema_rejects_duplicate_keys_unknown_components_and_bool_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budgets.json'
            mutations = [lambda b: b.update(schema=True), lambda b: b.update(maxApkBytes=True),
                         lambda b: b['baseline'].update(commit=1),
                         lambda b: b['categories'].update(hidden=100),
                         lambda b: b['nativeByAbi'].pop('arm64-v8a')]
            for mutate in mutations:
                value = self.budgets(); mutate(value); path.write_text(json.dumps(value))
                with self.assertRaises(footprint.FootprintError): footprint.load_budgets(path)
            path.write_text('{"schema":1,"schema":1}')
            with self.assertRaisesRegex(footprint.FootprintError, 'DUPLICATE_JSON_KEY'):
                footprint.load_budgets(path)

    def test_cli_writes_failed_budget_report_and_removes_stale_report_on_structural_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = self.apk(root, {'assets/extra': b'x' * 2_001})
            budgets = root / 'budgets.json'; budgets.write_text(json.dumps(self.budgets()))
            report = root / 'report.json'
            cmd = [sys.executable, str(Path(footprint.__file__)), '--apk', str(path), '--budgets', str(budgets), '--report', str(report)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(1, result.returncode); self.assertIn('FOOTPRINT_BUDGET:CATEGORY_OTHER', result.stderr)
            self.assertFalse(json.loads(report.read_text())['passed'])
            self.assertEqual(hashlib.sha256(budgets.read_bytes()).hexdigest(), json.loads(report.read_text())['budgetSha256'])
            path.write_bytes(b'not a ZIP')
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(1, result.returncode); self.assertFalse(report.exists())
            self.assertNotIn(str(path), result.stderr)

    def test_report_cannot_overwrite_the_apk_or_budget_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); apk = self.apk(root)
            budgets = root / 'budgets.json'; budgets.write_text(json.dumps(self.budgets()))
            for target in (apk, budgets):
                original = target.read_bytes()
                result = subprocess.run([sys.executable, str(Path(footprint.__file__)), '--apk', str(apk),
                                         '--budgets', str(budgets), '--report', str(target)],
                                        capture_output=True, text=True)
                self.assertEqual(1, result.returncode)
                self.assertIn('REPORT_OVERLAPS_INPUT', result.stderr)
                self.assertEqual(original, target.read_bytes())


if __name__ == '__main__':
    unittest.main()
