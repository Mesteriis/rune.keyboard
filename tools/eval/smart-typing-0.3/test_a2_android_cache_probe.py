from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import a2_android_cache_probe as subject


class AndroidCacheProbeBuildTest(unittest.TestCase):
    def test_elf_requires_arm64_little_endian_executable(self):
        valid=bytearray(64);valid[:6]=b'\x7fELF\x02\x01'
        struct.pack_into('<HH',valid,16,3,183)
        subject.validate_executable(valid)
        for offset,value in ((4,1),(5,2),(16,1),(18,62)):
            bad=bytearray(valid);bad[offset]=value
            with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'A2_ANDROID_ELF_IDENTITY'):
                subject.validate_executable(bad)
        with self.assertRaisesRegex(ValueError,'A2_ANDROID_ELF_IDENTITY'):
            subject.validate_executable(b'bad')

    def test_wrong_compiler_fails_before_output_is_created(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();output=root/'build/probe'
            for variant in ('Debug', 'RelWithDebInfo'):
                native=root/'runtime-llama/.cxx'/variant/'example/arm64-v8a';native.mkdir(parents=True)
                with self.subTest(variant=variant), mock.patch.object(subject,'ROOT',root):
                    with self.assertRaisesRegex(ValueError,'A2_ANDROID_COMPILER'):
                        subject.build(native,root/'wrong-clang',output)
                self.assertFalse(output.exists())

    def test_other_native_builds_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();native=root/'runtime-llama/.cxx/Release/example/arm64-v8a';native.mkdir(parents=True)
            with mock.patch.object(subject,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'A2_ANDROID_NATIVE_SCOPE'):
                    subject.build(native,root/'aarch64-linux-android26-clang++',root/'build/probe')


if __name__=='__main__':unittest.main()
