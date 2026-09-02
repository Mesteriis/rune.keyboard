"""Offline regression tests; no download, native rebuild or full expansion."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import expand_affixes
import fetch_sources
import finalize_inputs
import pipeline_config
import verify_outputs


class SourcePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=pipeline_config.build_root()/'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base/'package'
        self.root = self.base/'build'
        self.package.mkdir()
        self.root.mkdir()
        self.payload = b'one 10\ntwo 5\n'
        self.record = {'path': 'sources/frequency/en_50k.txt', 'reuse': '../implicit/en_50k.txt',
                       'url': 'https://example.invalid/pinned/0123456789/en_50k.txt',
                       'revision': '0123456789', 'sha256': hashlib.sha256(self.payload).hexdigest(),
                       'bytes': len(self.payload)}
        self.lock = self.package/'source-lock.json'
        self.lock.write_text(json.dumps([self.record])+'\n')
        self.stack = self.enterContext(ExitStack())
        self.stack.enter_context(patch.object(fetch_sources, 'PACKAGE', self.package))
        self.stack.enter_context(patch.object(pipeline_config, 'LOCK_SHA256', hashlib.sha256(self.lock.read_bytes()).hexdigest()))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def download(self, content: bytes):
        def run(command: list[str], **kwargs) -> None:
            self.assertEqual(command[-3], self.record['url'])
            self.assertEqual(command[-2], '-o')
            self.assertIn('--proto-redir', command)
            Path(command[-1]).write_bytes(content)
        return run

    def test_absent_lock_cannot_bootstrap_from_unpinned_inputs(self) -> None:
        self.lock.rename(self.package/'source-inputs.json')
        with patch.object(fetch_sources.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Missing immutable'):
                fetch_sources.acquire(self.root, allow_fetch=True)
            run.assert_not_called()
        self.assertFalse(self.lock.exists())

    def test_changed_url_revision_or_reuse_fails_before_loader(self) -> None:
        for key in ('url', 'revision', 'reuse'):
            with self.subTest(field=key), patch.object(fetch_sources.subprocess, 'run') as run:
                self.lock.write_text(json.dumps([dict(self.record, **{key: 'changed'})]))
                with self.assertRaisesRegex(ValueError, 'Frozen source-lock'):
                    fetch_sources.acquire(self.root, allow_fetch=True)
                run.assert_not_called()

    def test_missing_input_without_fetch_fails_closed(self) -> None:
        with patch.object(fetch_sources.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Missing pinned input'):
                fetch_sources.acquire(self.root)
            run.assert_not_called()

    def test_legacy_reuse_field_is_not_an_implicit_cache(self) -> None:
        legacy = self.base/'implicit/en_50k.txt'
        legacy.parent.mkdir()
        legacy.write_bytes(self.payload)
        with self.assertRaisesRegex(ValueError, 'Missing pinned input'):
            fetch_sources.acquire(self.root)

    def test_explicit_cache_is_checked_offline(self) -> None:
        cache = self.base/'cache'
        target = cache/self.record['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(self.payload)
        with patch.object(fetch_sources.subprocess, 'run') as run:
            fetch_sources.acquire(self.root, cache)
            run.assert_not_called()
        self.assertEqual((self.root/self.record['path']).read_bytes(), self.payload)

    def test_bad_cache_is_not_replaced_by_network(self) -> None:
        cache = self.base/'cache'
        target = cache/self.record['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'wrong')
        with patch.object(fetch_sources.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                fetch_sources.acquire(self.root, cache, True)
            run.assert_not_called()

    def test_fetch_exact_url_preserves_lock_and_publishes_verified_bytes(self) -> None:
        before = self.lock.read_bytes()
        with patch.object(fetch_sources.subprocess, 'run', side_effect=self.download(self.payload)) as run:
            fetch_sources.acquire(self.root, allow_fetch=True)
            run.assert_called_once()
        self.assertEqual(self.lock.read_bytes(), before)
        self.assertEqual((self.root/self.record['path']).read_bytes(), self.payload)

    def test_bad_download_is_not_published(self) -> None:
        with patch.object(fetch_sources.subprocess, 'run', side_effect=self.download(b'wrong')):
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                fetch_sources.acquire(self.root, allow_fetch=True)
        self.assertFalse((self.root/self.record['path']).exists())
        self.assertEqual(list(self.root.rglob('*.partial')), [])

    def test_existing_bad_input_is_not_overwritten(self) -> None:
        target = self.root/self.record['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'wrong')
        with patch.object(fetch_sources.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                fetch_sources.acquire(self.root, allow_fetch=True)
            run.assert_not_called()
        self.assertEqual(target.read_bytes(), b'wrong')

    def test_paths_and_symlinks_cannot_escape_build_root(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            pipeline_config.safe_path(self.root, '../outside')
        (self.root/'link').symlink_to(self.package, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            pipeline_config.safe_path(self.root, 'link/source-lock.json')
        with self.assertRaisesRegex(ValueError, 'dedicated child'):
            pipeline_config.build_root(str(pipeline_config.PACKAGE))
        with self.assertRaisesRegex(ValueError, 'dedicated child'):
            pipeline_config.build_root(str(pipeline_config.PROJECT/'build'))

    def test_public_expand_rejects_missing_inputs_before_transform(self) -> None:
        result = subprocess.run([sys.executable, str(pipeline_config.PACKAGE/'pipeline.py'),
                                 '--build-dir', str(self.root), 'expand'],
                                capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root/'reports/finite-expansion.log').exists())
        self.assertFalse((self.root/'outputs/ru.words.txt').exists())

    def test_generated_manifest_cannot_omit_transformation_provenance(self) -> None:
        (self.root/'output-manifest.json').write_text(json.dumps({'transformation_sources': []}))
        with patch.object(verify_outputs, 'ROOT', self.root), patch.object(verify_outputs, 'verify_frozen', return_value=24), \
                patch.object(verify_outputs.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'provenance is incomplete'):
                verify_outputs.main()
            run.assert_called_once()

    def prepare_archive(self) -> tuple[Path, bytes, dict]:
        revision = '5ef55f9c42730ebe4394a78b77855468a6f15dd2'
        archive = self.root/f'downloads/scowl-{revision}.tar.gz'
        archive.parent.mkdir()
        (self.root/'notices').mkdir()
        notice = b'Complete multi-source copyright fixture\n'
        with tarfile.open(archive, 'w:gz') as handle:
            member = tarfile.TarInfo(f'wordlist-{revision}/scowl/Copyright')
            member.size = len(notice)
            handle.addfile(member, io.BytesIO(notice))
        return archive, notice, {'path': str(archive.relative_to(self.root)), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}

    def test_scowl_notice_requires_only_verified_archive(self) -> None:
        archive, notice, record = self.prepare_archive()
        with patch.object(finalize_inputs, 'ROOT', self.root), patch.object(finalize_inputs, 'load_lock', return_value=[record]):
            finalize_inputs.copy_scowl_notice()
        self.assertEqual((self.root/'notices/SCOWL-Copyright.txt').read_bytes(), notice)
        self.assertFalse((self.root/'sources').exists())

    def test_scowl_tampered_archive_is_rejected(self) -> None:
        archive, _, record = self.prepare_archive()
        with archive.open('ab') as handle:
            handle.write(b'changed')
        with patch.object(finalize_inputs, 'ROOT', self.root), patch.object(finalize_inputs, 'load_lock', return_value=[record]):
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                finalize_inputs.copy_scowl_notice()

    def test_normalization_keeps_diacritics_and_yo(self) -> None:
        self.assertEqual(finalize_inputs.normalize('NIN\u0303O'), 'niño')
        self.assertEqual(finalize_inputs.normalize('Café'), 'café')
        self.assertEqual(finalize_inputs.normalize('ЁЛКА'), 'ёлка')
        self.assertNotEqual(finalize_inputs.normalize('всё'), finalize_inputs.normalize('все'))

    def test_frequency_collision_keeps_both_source_rows(self) -> None:
        source = self.root/'sources/frequency/es_50k.txt'
        source.parent.mkdir(parents=True)
        source.write_text('a\u0301 10\ná 5\n', encoding='utf-8')
        (self.root/'outputs').mkdir()
        with patch.object(finalize_inputs, 'ROOT', self.root), patch.object(expand_affixes, 'ROOT', self.root):
            result = finalize_inputs.frequency_component('es')
        self.assertEqual(result['source_rows'], 2)
        self.assertEqual(result['normalized_key_collision_groups'], 1)
        self.assertEqual((self.root/'outputs/frequency/es.tsv').read_text(), 'key\tsource_rank\tsource_word\tsource_count\ná\t1\ta\u0301\t10\ná\t2\tá\t5\n')

    def test_finite_profile_rejects_unsupported_directives_before_native_call(self) -> None:
        aff = self.root/'unsupported.aff'
        aff.write_text('SET UTF-8\nCOMPOUNDRULE 1\n')
        with patch.object(expand_affixes, 'native_flags') as native:
            with self.assertRaisesRegex(ValueError, 'Unsupported affix directives'):
                expand_affixes.read_rules(aff, self.root/'unused.dic', [], 'fixture')
            native.assert_not_called()

    def test_rule_does_not_fullstrip_or_exceed_codepoint_limit(self) -> None:
        rule = expand_affixes.Rule('SFX', 1, False, 'x', 'y', (), re.compile('x$'))
        self.assertIsNone(rule.apply('x'))
        self.assertEqual(rule.apply('ax'), 'ay')
        too_long = expand_affixes.Rule('PFX', 1, False, '', 'zz', (), re.compile('^.*'))
        self.assertIsNone(too_long.apply('a'*31))



class PromotionBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=pipeline_config.build_root()/'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base/'selected-build'
        self.root.mkdir()
        self.outside = self.base/'outside-selected-build'
        self.outside.mkdir()
        self.sentinel = self.outside/'sentinel'
        self.sentinel.write_bytes(b'outside bytes must survive\n')

    def public_stage(self, stage: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(pipeline_config.PACKAGE/'pipeline.py'),
                               '--build-dir', str(self.root), stage],
                              capture_output=True, text=True,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))

    def test_public_stages_reject_existing_writable_leaf_redirects_before_any_write(self) -> None:
        cases = [('reports/finite-expansion.log', 'expand'),
                 ('output-manifest.json', 'finalize'),
                 ('outputs/ru.words.txt', 'expand'),
                 ('outputs/frequency/es.tsv', 'finalize'),
                 ('bin/spell_oracle', 'host'),
                 ('reports/host-build-reproduce.log', 'host')]
        for relative, stage in cases:
            with self.subTest(path=relative, stage=stage):
                leaf = self.root/relative
                leaf.parent.mkdir(parents=True, exist_ok=True)
                leaf.symlink_to(self.sentinel)
                result = self.public_stage(stage)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Build symlink escapes selected directory', result.stderr)
                self.assertEqual(self.sentinel.read_bytes(), b'outside bytes must survive\n')
                self.assertFalse((self.root/'.gitignore').exists())
                leaf.unlink()

    def test_public_host_rejects_nested_host_tools_directory_redirect(self) -> None:
        (self.root/'bin').mkdir()
        (self.root/'bin/host-tools').symlink_to(self.outside, target_is_directory=True)
        result = self.public_stage('host')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Build symlink escapes selected directory: bin/host-tools', result.stderr)
        self.assertEqual(self.sentinel.read_bytes(), b'outside bytes must survive\n')
        self.assertEqual(sorted(p.name for p in self.outside.iterdir()), ['sentinel'])
        self.assertFalse((self.root/'.gitignore').exists())

    def test_readonly_host_tool_links_and_internal_archive_links_survive_prepare(self) -> None:
        tool = self.outside/'gnu-tool-fixture'
        tool.write_bytes(b'#!/bin/sh\nexit 0\n')
        tool.chmod(0o755)
        host = self.root/'bin/host-tools'
        host.mkdir(parents=True)
        for name in ('find', 'grep'):
            (host/name).symlink_to(tool)
        archive = self.root/'sources/archive'
        archive.mkdir(parents=True)
        (archive/'data').write_bytes(b'archive member')
        (archive/'relative-link').symlink_to('data')
        (archive/'internal-directory-link').symlink_to(self.root/'sources', target_is_directory=True)
        pipeline_config.prepare(self.root)
        self.assertEqual(tool.read_bytes(), b'#!/bin/sh\nexit 0\n')
        for name in ('find', 'grep'):
            self.assertTrue((host/name).is_symlink())
        self.assertTrue((archive/'relative-link').is_symlink())
        self.assertEqual((archive/'relative-link').read_bytes(), b'archive member')

    def test_host_tool_exception_rejects_directory_and_indirect_writable_alias(self) -> None:
        host = self.root/'bin/host-tools'
        host.mkdir(parents=True)
        (host/'find').symlink_to(self.outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Invalid read-only host tool link'):
            pipeline_config.prepare(self.root)
        (host/'find').unlink()
        tool = self.outside/'tool'
        tool.write_bytes(b'#!/bin/sh\n')
        tool.chmod(0o755)
        (host/'find').symlink_to(tool)
        (self.root/'reports').mkdir()
        (self.root/'reports/finite-expansion.log').symlink_to(host/'find')
        with self.assertRaisesRegex(ValueError, 'Build symlink escapes'):
            pipeline_config.prepare(self.root)
        self.assertEqual(tool.read_bytes(), b'#!/bin/sh\n')
        self.assertFalse((self.root/'.gitignore').exists())

    def test_self_consistent_frozen_manifest_replacement_fails_before_prepare_writes(self) -> None:
        package = self.base/'package'
        package.mkdir()
        original = (pipeline_config.PACKAGE/'frozen-output-manifest.json').read_bytes()
        frozen_path = package/'frozen-output-manifest.json'
        frozen_path.write_bytes(original)
        self.assertEqual(pipeline_config.load_frozen_manifest(package), json.loads(original))
        for change in ('output', 'notices'):
            with self.subTest(change=change):
                frozen = json.loads(original)
                if change == 'output':
                    record = frozen['languages'][0]['canonical_keys']
                    record.update(sha256=hashlib.sha256(b'replacement\n').hexdigest(), bytes=12, rows=1)
                    replacement = self.root/record['path']
                    replacement.parent.mkdir(parents=True, exist_ok=True)
                    replacement.write_bytes(b'replacement\n')
                else:
                    frozen['notices'] = frozen['notices'][:-1]
                frozen_path.write_text(json.dumps(frozen))
                with patch.object(pipeline_config, 'PACKAGE', package):
                    with self.assertRaisesRegex(ValueError, 'Frozen output-manifest SHA-256 mismatch'):
                        pipeline_config.prepare(self.root)
                    with self.assertRaisesRegex(ValueError, 'Frozen output-manifest SHA-256 mismatch'):
                        verify_outputs.verify_frozen(self.root)
                self.assertFalse((self.root/'.gitignore').exists())
                self.assertFalse((self.root/'notices').exists())
        frozen_path.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing immutable frozen-output'):
            pipeline_config.load_frozen_manifest(package)


if __name__ == '__main__':
    unittest.main()
