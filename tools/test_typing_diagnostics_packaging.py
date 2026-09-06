import struct
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest
import zipfile
from typing_diagnostics_packaging import defined_dex_classes, forbidden_classes, parse_mapping, verify


def minimal_dex(name):
    encoded = ('L' + name.replace('.', '/') + ';').encode('ascii')
    string_offset, type_offset, class_offset, data_offset = 112, 116, 120, 152
    dex = bytearray(data_offset)
    dex[:8] = b'dex\n035\x00'
    struct.pack_into('<I', dex, 56, 1)
    struct.pack_into('<I', dex, 60, string_offset)
    struct.pack_into('<I', dex, 64, 1)
    struct.pack_into('<I', dex, 68, type_offset)
    struct.pack_into('<I', dex, 96, 1)
    struct.pack_into('<I', dex, 100, class_offset)
    struct.pack_into('<I', dex, string_offset, data_offset)
    struct.pack_into('<I', dex, type_offset, 0)
    struct.pack_into('<I', dex, class_offset, 0)
    dex.extend(bytes([len(encoded)]) + encoded + b'\0')
    return bytes(dex)


class PackagingTest(unittest.TestCase):
    def fixture(self, root, variant='debug', alias=False):
        prefix = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.'
        name = prefix + ('DiagnosticsActivity' if variant == 'debug' else 'NoTypingDiagnostics')
        classes = root / 'classes'
        cls = classes / (name.replace('.', '/') + '.class')
        cls.parent.mkdir(parents=True); cls.write_bytes(b'synthetic inventory entry')
        apks = root / 'apks'; apks.mkdir()
        with zipfile.ZipFile(apks / 'app.apk', 'w') as archive:
            archive.writestr('classes.dex', minimal_dex(name))
        manifest = root / 'AndroidManifest.xml'
        activity = '<activity android:name="' + name + '" android:exported="false" />' if variant == 'debug' else ''
        target = '<activity-alias android:name=".PublicAlias" android:targetActivity="' + prefix + 'DiagnosticsActivity" android:exported="true" />' if alias else ''
        manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="io.github.mesteriis.rune.keyboard"><application>' + activity + target + '</application></manifest>')
        mapping = root / 'mapping.txt'; mapping.write_text('')
        return Namespace(variant=variant, classes=[classes], manifest=manifest, apk_dir=apks,
                         mapping=None if variant == 'debug' else mapping)

    def test_complete_debug_and_final_artifact_sets(self):
        for variant in ('debug', 'release', 'profile'):
            with tempfile.TemporaryDirectory() as folder:
                verify(self.fixture(Path(folder), variant))

    def test_exported_alias_cannot_expose_private_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, '[Aa]lias'):
                verify(self.fixture(Path(folder), alias=True))

    def test_actual_class_definitions_are_decoded(self):
        self.assertEqual({'a.b.C'}, defined_dex_classes(minimal_dex('a.b.C')))

    def test_mapping_reveals_obfuscated_debug_recorder(self):
        original = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder'
        mapping = parse_mapping(original + ' -> a.b.C:\n    void record() -> a\n')
        self.assertEqual([original], forbidden_classes(defined_dex_classes(minimal_dex('a.b.C')), mapping))

    def test_contracts_and_noop_variants_are_permitted(self):
        prefix = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.'
        self.assertEqual([], forbidden_classes({prefix + n for n in
            ('DiagnosticText', 'DiagnosticEvent', 'NoTypingDiagnostics', 'TypingDiagnosticsProvider', 'DiagnosticsSettingsProvider')}))
        self.assertEqual([prefix + 'HiddenWriter'], forbidden_classes({prefix + 'HiddenWriter'}))

    def test_nested_debug_encoder_is_not_a_contract(self):
        name = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider$DiagnosticsEncoding'
        self.assertEqual([name], forbidden_classes({name}))

    def test_only_exact_compiler_helpers_are_permitted(self):
        prefix = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.'
        for name in ('TypingDiagnostics$DefaultImpls', 'DiagnosticsSettingsProvider$$ExternalSyntheticLambda0'):
            self.assertEqual([], forbidden_classes({prefix + name}))
        for name in ('TypingDiagnostics$DefaultImpls$Recorder',
                     'DiagnosticsSettingsProvider$$ExternalSyntheticLambda1',
                     'NoTypingDiagnostics$Recorder', 'DiagnosticEvent$Encoder'):
            self.assertEqual([prefix + name], forbidden_classes({prefix + name}))

    def test_nested_recorder_is_rejected_in_full_pre_r8_and_mapped_dex_admission(self):
        prefix = 'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.'
        original = prefix + 'NoTypingDiagnostics$Recorder'
        for location in ('pre-r8', 'dex'):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder); args = self.fixture(root, 'release')
                if location == 'pre-r8':
                    cls = args.classes[0] / (original.replace('.', '/') + '.class')
                    cls.write_bytes(b'synthetic inventory entry')
                else:
                    args.mapping.write_text(original + ' -> a.b.C:\n')
                    with zipfile.ZipFile(args.apk_dir / 'app.apk', 'w') as archive:
                        archive.writestr('classes.dex', minimal_dex('a.b.C'))
                with self.assertRaisesRegex(ValueError, 'debug diagnostics classes'):
                    verify(args)

    def test_alias_target_is_resolved_in_every_variant_even_if_private(self):
        for variant in ('debug', 'release', 'profile'):
            for target in ('.smarttyping.diagnostics.DiagnosticsActivity',
                           'io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsActivity'):
                with tempfile.TemporaryDirectory() as folder:
                    args = self.fixture(Path(folder), variant)
                    text = args.manifest.read_text().replace('</application>',
                        '<activity-alias android:name=".Alias" android:exported="false" android:targetActivity="' +
                        target + '" /></application>')
                    args.manifest.write_text(text)
                    with self.assertRaisesRegex(ValueError, '[Aa]lias'):
                        verify(args)

    def test_truncated_or_invalid_dex_fails_closed(self):
        for content in (b'', b'not a dex', minimal_dex('a.b.C')[:130]):
            with self.assertRaises(ValueError): defined_dex_classes(content)


if __name__ == '__main__':
    unittest.main()
