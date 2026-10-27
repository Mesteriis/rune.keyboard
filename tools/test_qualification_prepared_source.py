import hashlib
import subprocess
import unittest

import qualification_artifacts as qualification
import fdroid_prepared_source as prepared
import test_fdroid_prepared_source as fixtures


class QualificationPreparedSourceTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PreparedSourceTest()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.repo = self.fixture.repo
        self.git = self.fixture.git
        self.commit = self.fixture.commit
        module = self.fixture.fixture.submodule()
        parent = self.repo / 'runtime-llama/src/main/cpp'; parent.mkdir(parents=True)
        self.git(self.repo, 'mv', 'module', 'runtime-llama/src/main/cpp/llama.cpp')
        self.module = parent / 'llama.cpp'
        self.git(self.module, 'config', 'user.name', 'Fixture')
        self.git(self.module, 'config', 'user.email', 'fixture@example.invalid')
        self.git(self.module, 'config', 'commit.gpgsign', 'false')
        self.wrappers = ['examples/llama.android/gradlew', 'examples/llama.android/gradle/wrapper/gradle-wrapper.jar']
        for name in self.wrappers:
            path = self.module / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'fixture wrapper')
        (self.module / 'runtime.cpp').write_text('compiled source')
        self.commit(self.module); self.commit(self.repo)
        self.fixture.policy()
        for name in self.wrappers:
            self.fixture.changes.append(dict(path='runtime-llama/src/main/cpp/llama.cpp/' + name,
                action='delete', beforeSha256=hashlib.sha256((self.module / name).read_bytes()).hexdigest()))
        self.fixture.write_policy(); self.commit(self.repo)

    def test_prepared_wrapper_deletions_pass_without_weakening_default_runtime_check(self):
        qualification.check_runtime_source(self.repo)
        self.fixture.transform()
        with self.assertRaises(subprocess.CalledProcessError): qualification.check_runtime_source(self.repo)
        qualification.check_runtime_source(self.repo, prepared.PREPARER)

    def test_even_committed_preparation_policy_cannot_allow_compiled_submodule_changes(self):
        path = self.module / 'runtime.cpp'
        self.fixture.changes.append(dict(path='runtime-llama/src/main/cpp/llama.cpp/runtime.cpp', action='replace',
            beforeSha256=hashlib.sha256(path.read_bytes()).hexdigest(), afterSha256=hashlib.sha256(b'unqualified runtime').hexdigest()))
        self.fixture.write_policy(); self.commit(self.repo)
        self.fixture.transform(); path.write_bytes(b'unqualified runtime')
        self.assertTrue(prepared.check_prepared(self.repo)['passed'])
        with self.assertRaisesRegex(ValueError, '^QUALIFICATION_PREPARED_RUNTIME_DIRTY$'):
            qualification.check_runtime_source(self.repo, prepared.PREPARER)

    def test_global_prepared_checkpoint_is_required_before_runtime_exception(self):
        self.fixture.transform(); (self.repo / 'extra.txt').write_text('unreviewed')
        with self.assertRaisesRegex(ValueError, 'RELEASE_PREPARED_SOURCE_DELTA'):
            qualification.check_runtime_source(self.repo, prepared.PREPARER)

    def test_unknown_preparer_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'QUALIFICATION_PREPARED_SOURCE_UNSUPPORTED'):
            qualification.check_runtime_source(self.repo, 'unknown')


if __name__ == '__main__':
    unittest.main()
