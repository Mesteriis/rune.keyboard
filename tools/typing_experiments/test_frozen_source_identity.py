import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from frozen_source_identity import read_frozen_source


class FrozenSourceIdentityTest(unittest.TestCase):
    def fixture(self,root):
        name='tools/typing_experiments/producer.py';current=root/name
        current.parent.mkdir(parents=True)
        archive=current.parent/'frozen_sources';archive.mkdir()
        raw=b'original historical source\n';digest=hashlib.sha256(raw).hexdigest()
        current.write_bytes(raw);(archive/'producer_old.py').write_bytes(raw)
        manifest={'sources':{digest:{'originalPath':name,'file':'producer_old.py'}}}
        (archive/'manifest.json').write_text(json.dumps(manifest))
        return name,current,archive,raw,digest,manifest

    def test_current_or_archived_exact_source_is_returned_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);name,current,archive,raw,digest,_=self.fixture(root)
            self.assertEqual(raw,read_frozen_source(root,name,digest))
            current.write_bytes(b'new maintained implementation')
            self.assertEqual(raw,read_frozen_source(root,name,digest))
            current.unlink()
            self.assertEqual(raw,read_frozen_source(root,name,digest))
            (archive/'producer_old.py').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_IDENTITY'):read_frozen_source(root,name,digest)

    def test_matching_bytes_cannot_substitute_another_original_path_or_escape_archive(self):
        for change in ('origin','escape','missing'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);name,current,archive,_,digest,manifest=self.fixture(root)
                current.write_bytes(b'new')
                if change=='origin':manifest['sources'][digest]['originalPath']='other.py'
                if change=='escape':manifest['sources'][digest]['file']='../producer.py'
                if change=='missing':manifest['sources']={}
                (archive/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_ORIGIN'):read_frozen_source(root,name,digest)

    def test_symlink_file_or_parent_is_rejected(self):
        for location in ('current','archive-parent','archive-file'):
            with self.subTest(location=location),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);name,current,archive,raw,digest,_=self.fixture(root)
                if location=='current':
                    current.unlink();current.symlink_to(archive/'producer_old.py')
                elif location=='archive-file':
                    current.write_bytes(b'new');(archive/'producer_old.py').unlink()
                    (archive/'other.py').write_bytes(raw);(archive/'producer_old.py').symlink_to(archive/'other.py')
                else:
                    current.write_bytes(b'new');archive.rename(root/'moved');archive.symlink_to(root/'moved')
                with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_SYMLINK'):read_frozen_source(root,name,digest)

    def test_malformed_requests_fail_before_any_read(self):
        for name,digest in [('../producer.py','a'*64),('/producer.py','a'*64),('x\\y.py','a'*64),
                            ('x//y.py','a'*64),('producer.py','bad')]:
            with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_REQUEST'):read_frozen_source('/absent',name,digest)


if __name__=='__main__':unittest.main()
