"""Exercise the actual CMake native source guard with real isolated Git repositories."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SUBMODULE = 'runtime-llama/src/main/cpp/llama.cpp'
NATIVE = 'runtime-llama/src/main/cpp'
PIN = '36b10154383b60eb15baac2c7a40d2a5f784faa7'
PREPARER = 'fdroidserver-2.4.5'


class PreparedNativeSourceTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='rune native source ')
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.repo = self.base / 'repo'; self.repo.mkdir()
        (self.repo / '.gitignore').write_text('__pycache__/\n')
        self.git(self.repo, 'init', '-q')
        for key, value in [('user.name', 'Native source fixture'), ('user.email', 'fixture@example.invalid'),
                           ('commit.gpgsign', 'false')]: self.git(self.repo, 'config', key, value)
        self.git(self.repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(REPO / SUBMODULE), SUBMODULE)
        self.module = self.repo / SUBMODULE
        self.assertEqual(PIN, self.git(self.module, 'rev-parse', 'HEAD').decode().strip())
        for name in ['tools/qualification_artifacts.py', 'tools/release_source_check.py', 'tools/fdroid_prepared_source.py',
                     NATIVE + '/PrepareLlamaSource.cmake', NATIVE + '/CMakeLists.txt', NATIVE + '/patches/tokenizer-abort.patch']:
            path = self.repo / name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(REPO / name, path)
        for name in ['runtime-llama/build.gradle.kts', 'gradle/libs.versions.toml',
                     'tools/eval/smart-typing-0.3/scoring.cpp', 'tools/eval/smart-typing-0.3/scoring.h']:
            path = self.repo / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('synthetic identity fixture\n')
        app = self.repo / 'app/build.gradle.kts'; app.parent.mkdir(exist_ok=True); app.write_bytes(b'original synthetic build script\n')
        descriptor = self.repo / 'app/src/main/assets/model/rune-text-0.1.json'; descriptor.parent.mkdir(parents=True)
        descriptor.write_text(json.dumps({'runtimeApi': 1, 'sha256': 'a' * 64}))
        # This fixture's identity is computed from its source files, with no model download or weight access.
        import sys
        sys.path.insert(0, str(REPO / 'tools'))
        import qualification_artifacts
        self.addCleanup(lambda: sys.path.remove(str(REPO / 'tools')))
        identity = qualification_artifacts.inspect(self.repo)['runtimeBuildId']
        contract = self.repo / 'app/src/main/java/io/github/mesteriis/rune/keyboard/intelligence/ipc/ScoringContract.kt'
        contract.parent.mkdir(parents=True)
        contract.write_text('const val RUNTIME_API = 1\nconst val MODEL_SHA256 = "' + 'a' * 64 +
                            '"\nconst val RUNTIME_BUILD_ID = "' + identity + '"\n')
        self.changes = [dict(path='app/build.gradle.kts', action='replace',
            beforeSha256=hashlib.sha256(app.read_bytes()).hexdigest(), afterSha256=hashlib.sha256(b'prepared synthetic build script\n').hexdigest())]
        for name in ['gradlew', 'gradlew.bat', 'gradle/wrapper/gradle-wrapper.jar',
                     'tools/typing_experiments/baseline/ru-ranker.bin']:
            path = self.repo / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic removable fixture')
        for name in ['gradlew', 'gradlew.bat', 'gradle/wrapper/gradle-wrapper.jar',
                     'tools/typing_experiments/baseline/ru-ranker.bin', SUBMODULE + '/examples/llama.android/gradlew',
                     SUBMODULE + '/examples/llama.android/gradle/wrapper/gradle-wrapper.jar']:
            self.changes.append(dict(path=name, action='delete', beforeSha256=hashlib.sha256((self.repo/name).read_bytes()).hexdigest()))
        self.write_policy(); self.commit()
        sdk = os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME')
        sdk_cmake = Path(sdk) / 'cmake/3.31.6/bin/cmake' if sdk else None
        self.cmake = os.environ.get('RUNE_TEST_CMAKE') or (str(sdk_cmake) if sdk_cmake and sdk_cmake.is_file() else shutil.which('cmake'))
        self.assertTrue(self.cmake, 'CMake >=3.31.6 is required')
        script = self.base / 'probe.cmake'
        script.write_text('cmake_minimum_required(VERSION 3.31.6)\n'
            'include("${ROOT}/runtime-llama/src/main/cpp/PrepareLlamaSource.cmake")\n'
            'prepare_rune_llama_source("${ROOT}" "${ROOT}/runtime-llama/src/main/cpp/patches/tokenizer-abort.patch")\n'
            'if(EXISTS "${RUNE_LLAMA_SOURCE}/examples/llama.android/gradlew" OR\n'
            '   EXISTS "${RUNE_LLAMA_SOURCE}/examples/llama.android/gradle/wrapper/gradle-wrapper.jar" OR\n'
            '   EXISTS "${CMAKE_CURRENT_BINARY_DIR}/rune-llama-upstream.tar")\n'
            '  message(FATAL_ERROR "Generated source reintroduced example wrappers")\nendif()\n')
        self.script = script

    def git(self, root, *args):
        p = subprocess.run(['git', '-C', str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(0, p.returncode, 'Native fixture Git operation failed')
        return p.stdout

    def write_policy(self):
        p = self.repo / 'fdroid/prepared-source-policy.json'; p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({'schema': 1, 'preparer': PREPARER, 'changes': self.changes}))

    def commit(self):
        self.git(self.repo, 'add', '--all'); self.git(self.repo, 'commit', '-qm', 'Synthetic native guard fixture')

    def prepare(self):
        (self.repo / 'app/build.gradle.kts').write_bytes(b'prepared synthetic build script\n')
        for row in self.changes:
            if row['action'] == 'delete': (self.repo / row['path']).unlink()

    def cmake_probe(self, mode, success, marker=None):
        output = self.base / ('output-' + str(len(list(self.base.glob('output-*'))))); output.mkdir()
        p = subprocess.run([self.cmake, '-DROOT=' + str(self.repo), '-DRUNE_PREPARED_SOURCE=' + mode,
                            '-P', str(self.script)], cwd=output, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        if success: self.assertEqual(0, p.returncode, p.stdout.decode(errors='replace'))
        else:
            self.assertNotEqual(0, p.returncode)
            self.assertIn(marker.encode(), p.stdout)

    def test_pristine_and_exact_prepared_sources_and_generated_copy_sanitation(self):
        self.cmake_probe('', True)
        self.prepare(); self.cmake_probe(PREPARER, True)
        self.cmake_probe('', False, 'llama.cpp source must be pristine')

    def test_compiled_submodule_edit_cannot_be_admitted_by_a_future_policy(self):
        path = self.module / 'src/llama.cpp'; before = path.read_bytes(); after = before + b'\n// unqualified native fixture\n'
        self.changes.append(dict(path=SUBMODULE + '/src/llama.cpp', action='replace',
            beforeSha256=hashlib.sha256(before).hexdigest(), afterSha256=hashlib.sha256(after).hexdigest()))
        self.write_policy(); self.commit(); self.prepare(); path.write_bytes(after)
        self.cmake_probe(PREPARER, False, 'Prepared runtime source failed the reviewed checkpoint')

    def test_unlisted_changes_and_unknown_mode_fail_closed(self):
        self.prepare(); extra = self.repo / 'unreviewed.cpp'; extra.write_text('// unreviewed')
        self.cmake_probe(PREPARER, False, 'Prepared runtime source failed the reviewed checkpoint')
        extra.unlink(); self.cmake_probe('unsupported', False, 'Unsupported prepared runtime source mode')

    def test_pristine_mode_still_rejects_untracked_submodule_code(self):
        (self.module / 'unreviewed.cpp').write_text('// unreviewed')
        self.cmake_probe('', False, 'llama.cpp source must be pristine')


if __name__ == '__main__':
    unittest.main()
