from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import verify_packaged_native as gate

SECTIONS = """There are 5 section headers:
  [ 0] NULL
  [ 1] .text PROGBITS
  [ 2] .rodata PROGBITS
  [ 3] .dynsym DYNSYM
"""


class PackagedNativeTest(unittest.TestCase):
    def test_debug_and_symbol_sections_are_refused_independently(self):
        gate.verify_sections(SECTIONS)
        for name in (".debug_info", ".debug_str", ".zdebug_info", ".symtab", ".gnu_debugdata", ".gnu_debuglink"):
            with self.subTest(name=name), self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_DEBUG_SECTIONS"):
                gate.verify_sections(SECTIONS + f"  [ 4] {name} PROGBITS\n")
        with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_REQUIRED_SECTIONS"):
            gate.verify_sections("not an ELF section table")

    def test_machine_local_paths_are_refused_without_echoing_payload(self):
        gate.verify_paths(b"JNI_OnLoad\x00/data/local/model.gguf\x00")
        for path in (b"/Users/private/build/source.cc", b"/home/private/build/source.cc"):
            with self.assertRaisesRegex(gate.NativePayloadError, "^NATIVE_LOCAL_SOURCE_PATH$"):
                gate.verify_paths(b"ELF\x00" + path + b"\x00")

    def fixture(self, directory, mutate=None, duplicate=False):
        root = Path(directory); stripped = root / "stripped"; apk = root / "test.apk"
        entries = {}
        for abi in gate.ABIS:
            for name in gate.LIBRARIES:
                entry = f"lib/{abi}/{name}"
                data = (abi + name).encode()
                entries[entry] = data
                path = stripped / "out/lib" / abi / name
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        if mutate:
            mutate(entries)
        with warnings.catch_warnings(), zipfile.ZipFile(apk, "w") as archive:
            warnings.simplefilter("ignore", UserWarning)
            for name, data in entries.items(): archive.writestr(name, data)
            if duplicate: archive.writestr(next(iter(entries)), b"duplicate")
            archive.writestr("classes.dex", b"unrelated")
        return apk, stripped

    @patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, SECTIONS, ""))
    def test_exact_four_member_payload_reports_only_fixed_metadata(self, run):
        with tempfile.TemporaryDirectory() as directory:
            apk, stripped = self.fixture(directory)
            report = gate.verify(apk, stripped, Path("readelf"))
            self.assertEqual(4, len(report)); self.assertEqual(4, run.call_count)
            self.assertTrue(all(set(item) == {"entry", "bytes", "sha256"} for item in report))

    @patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, SECTIONS, ""))
    def test_same_sections_but_changed_native_bytes_fail(self, run):
        with tempfile.TemporaryDirectory() as directory:
            apk, stripped = self.fixture(directory, lambda entries: entries.update({next(iter(entries)): b"changed"}))
            with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_STRIPPED_PAYLOAD_MISMATCH"):
                gate.verify(apk, stripped, Path("readelf"))

    @patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, SECTIONS, ""))
    def test_path_audit_is_separate_from_strip_and_payload_identity(self, run):
        with tempfile.TemporaryDirectory() as directory:
            apk, stripped = self.fixture(directory, lambda entries: entries.update({
                next(iter(entries)): b"ELF\x00/Users/private/source.cc\x00"}))
            reference = stripped / "out/lib/arm64-v8a/libc++_shared.so"
            reference.write_bytes(b"ELF\x00/Users/private/source.cc\x00")
            self.assertEqual(4, len(gate.verify(apk, stripped, Path("readelf"))))
            with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_LOCAL_SOURCE_PATH"):
                gate.verify(apk, stripped, Path("readelf"), require_no_local_paths=True)

    @patch.object(gate.subprocess, "run")
    def test_duplicate_missing_extra_or_traversal_members_fail_before_tool_execution(self, run):
        mutations = [lambda entries: entries.pop(next(iter(entries))),
                     lambda entries: entries.update({"lib/arm64-v8a/extra.so": b"extra"}),
                     lambda entries: entries.update({"lib/../../escape.so": b"escape"})]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                apk, stripped = self.fixture(directory, mutate)
                with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_APK_MEMBER_SET"):
                    gate.verify(apk, stripped, Path("readelf"))
        with tempfile.TemporaryDirectory() as directory:
            apk, stripped = self.fixture(directory, duplicate=True)
            with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_APK_MEMBER_SET"):
                gate.verify(apk, stripped, Path("readelf"))
        run.assert_not_called()

    @patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, SECTIONS, ""))
    def test_missing_or_ambiguous_strip_outputs_fail(self, run):
        for duplicate in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                apk, stripped = self.fixture(directory)
                reference = next(stripped.rglob("librune_llama.so"))
                if duplicate:
                    other = stripped / "duplicate" / reference.parent.name / reference.name
                    other.parent.mkdir(parents=True); other.write_bytes(reference.read_bytes())
                else:
                    reference.unlink()
                with self.assertRaisesRegex(gate.NativePayloadError, "NATIVE_STRIPPED_REFERENCE_SET"):
                    gate.verify(apk, stripped, Path("readelf"))

    @patch.object(gate.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "readelf"))
    def test_readelf_failure_cannot_become_pass(self, run):
        with tempfile.TemporaryDirectory() as directory:
            apk, stripped = self.fixture(directory)
            with self.assertRaises(subprocess.CalledProcessError):
                gate.verify(apk, stripped, Path("readelf"))


if __name__ == "__main__":
    unittest.main()
