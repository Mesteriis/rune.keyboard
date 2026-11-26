import contextlib
import io
from pathlib import Path
import sys
import tempfile
from temporary_test_build import temporary_build_directory
import unittest
import hashlib

ROOT=Path(__file__).resolve().parents[2]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools/ci'))
    import word_evaluation_smoke as smoke
finally:sys.path[:]=old_path


class WordEvaluationDriverTest(unittest.TestCase):
    def test_captured_source_identity_uses_only_exact_safe_archive(self):
        from captured_source_identity import ARCHIVES,read
        (name,digest),archive_name=next(iter(ARCHIVES.items()))
        archived=(ROOT/'tools/ci/fixtures/captured-sources'/archive_name).read_bytes()
        self.assertEqual(digest,hashlib.sha256(archived).hexdigest())
        with tempfile.TemporaryDirectory() as folder:
            repo=Path(folder);current=repo/name;current.parent.mkdir(parents=True);current.write_bytes(b'current source changed')
            archive=repo/'tools/ci/fixtures/captured-sources'/archive_name;archive.parent.mkdir(parents=True);archive.write_bytes(archived)
            self.assertEqual(archived,read(repo,name,digest))
            archive.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'CAPTURE_SOURCE_ARCHIVE_IDENTITY'):read(repo,name,digest)
            with self.assertRaisesRegex(ValueError,'CAPTURE_SOURCE_REQUEST'):read(repo,'../outside',digest)
            with self.assertRaisesRegex(ValueError,'CAPTURE_SOURCE_IDENTITY'):read(repo,name,'0'*64)
            current.unlink();current.symlink_to(archive)
            with self.assertRaisesRegex(ValueError,'CAPTURE_SOURCE_SYMLINK'):read(repo,name,digest)
            current.unlink();current.write_bytes(archived);archive.unlink()
            self.assertEqual(archived,read(repo,name,digest))

    def test_both_capture_manifests_resolve_exact_source_bytes(self):
        import json
        from captured_source_identity import read
        for fixture in ('word-ranking-bounded-capture.json', 'retrieval-bounded-capture.json'):
            value = json.loads((ROOT / 'tools/ci/fixtures' / fixture).read_bytes())
            for name, digest in value['sourceFiles'].items():
                with self.subTest(fixture=fixture, name=name):
                    self.assertEqual(digest, hashlib.sha256(read(ROOT, name, digest)).hexdigest())

    def test_real_driver_preserves_cohorts_binds_all_inputs_and_refuses_disclosed_acceptance(self):
        with temporary_build_directory(ROOT) as folder,contextlib.redirect_stdout(io.StringIO()):
            result=smoke.run(Path(folder)/'output')
        self.assertTrue(result['packagedFilesUnchanged']);word=result['extraComparison']
        self.assertEqual((4,3,1),(word['mainRows'],word['typoRows'],word['controls']))
        self.assertEqual((4,4,4),(word['previousRows'],word['extraRows'],word['legacyRows']))
        self.assertFalse(word['accepted']);self.assertTrue(word['secondDisclosureRejected'])
        self.assertGreater(word['inputMutationRejections'],150)
        self.assertEqual(word['capturedFiles'],word['inputMutationRejections'])


if __name__=='__main__':unittest.main()
