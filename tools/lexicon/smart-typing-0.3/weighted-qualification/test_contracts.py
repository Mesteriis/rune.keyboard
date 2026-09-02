"""Promotion interfaces only. No generator, compiler, model, ADB or oracle execution."""
from __future__ import annotations
import ast
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
import archive
import qualify

class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = archive.load(qualify.PACKAGE)
        cls.inputs = archive.read_json(cls.records['fixtures/inputs.json'])
        cls.test_root = Path(os.environ['RUNE_QUAL_TEST_DIR']).resolve()
        cls.test_root.mkdir(parents=True, exist_ok=True)

    def temporary(self):
        return tempfile.TemporaryDirectory(dir=self.test_root)

    def copy_archive(self, root):
        (root/'evidence').mkdir()
        for name in ('original-manifest.json','records.json.gz.b64'):
            shutil.copyfile(qualify.PACKAGE/'evidence'/name,root/'evidence'/name)

    def test_all_41_historical_texts_match_43_artifact_manifest(self):
        self.assertEqual(41,len(self.records))
        self.assertFalse(any(name.startswith('bin/') for name in self.records))
        self.assertEqual(775,len(self.inputs))
        self.assertEqual(720,sum(x['group']==0 for x in self.inputs))
        self.assertEqual(55,sum(x['group']==1 for x in self.inputs))

    def test_replaced_self_consistent_historical_manifest_is_rejected(self):
        with self.temporary() as directory:
            root=Path(directory);self.copy_archive(root)
            p=root/'evidence/original-manifest.json';value=json.loads(p.read_text());value['scope']='different'
            p.write_text(json.dumps(value))
            with self.assertRaisesRegex(archive.Failure,'HISTORICAL_MANIFEST_IDENTITY'):archive.load(root)

    def test_changed_archive_is_rejected(self):
        with self.temporary() as directory:
            root=Path(directory);self.copy_archive(root)
            p=root/'evidence/records.json.gz.b64';data=p.read_text();p.write_text(('A' if data[0]!='A' else 'B')+data[1:])
            with self.assertRaises(archive.Failure):archive.load(root)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(archive.Failure,'DUPLICATE_JSON_KEY'):archive.read_json(b'{"x":1,"x":2}')

    def test_historical_numeric_protocol(self):
        rows=archive.validate_numeric(self.records['reports/actual.tsv'],self.inputs)
        self.assertEqual(775,sum(r[1]==1 for r in rows))
        development=[r for r in rows if r[1]==1 and r[3]==0]
        self.assertEqual(72,sum(r[5]==0 for r in development))
        self.assertEqual(602,sum(r[5]==3 for r in development))
        self.assertEqual(42,sum(r[5]==4 for r in development))
        self.assertEqual(4,sum(r[5]==2 for r in development))

    def test_payload_and_unknown_record_rejected(self):
        raw=self.records['reports/actual.tsv']
        for extra in (b'private-payload\n',b'1\t9\t99\n'):
            with self.assertRaises((archive.Failure,UnicodeError)):archive.validate_numeric(raw+extra,self.inputs)

    def test_wrong_load_missing_done_and_request_duplicate_rejected(self):
        rows=self.records['reports/actual.tsv'].splitlines()
        wrong=rows.copy();wrong[0]=wrong[0].replace(b'121255',b'121256')
        duplicate=rows.copy();index=next(i for i,r in enumerate(rows) if r.startswith(b'1\t1\t1\t'))
        duplicate[index]=duplicate[index].replace(b'1\t1\t1\t',b'1\t1\t0\t',1)
        for altered in (wrong,rows[:-1],duplicate):
            with self.assertRaises(archive.Failure):archive.validate_numeric(b'\n'.join(altered)+b'\n',self.inputs)

    def test_exhaustion_without_veto_rejected(self):
        rows=[x.split(b'\t') for x in self.records['reports/actual.tsv'].splitlines()]
        next(r for r in rows if r[1]==b'1' and r[5]==b'3')[7]=b'0'
        with self.assertRaisesRegex(archive.Failure,'RECORD_VETO'):
            archive.validate_numeric(b'\n'.join(b'\t'.join(r) for r in rows)+b'\n',self.inputs)

    def test_out_of_bounds_counts_rejected(self):
        for column,value in ((9,b'8193'),(10,b'65'),(12,b'8')):
            rows=[x.split(b'\t') for x in self.records['reports/actual.tsv'].splitlines()]
            next(r for r in rows if r[1]==b'1')[column]=value
            with self.assertRaisesRegex(archive.Failure,'RECORD_CAPS'):
                archive.validate_numeric(b'\n'.join(b'\t'.join(r) for r in rows)+b'\n',self.inputs)

    def test_paths_must_be_explicit_repo_relative_ignored_build(self):
        with self.temporary() as directory:
            root=Path(directory)
            for value in ('/tmp/out','../outside','tools/new-output','build'):
                with self.assertRaises(archive.Failure):qualify.build_path(root,value)
            self.assertEqual(root/'build/qualification/run1',qualify.build_path(root,'build/qualification/run1'))

    def test_nested_directory_or_output_leaf_symlink_preserves_sentinel(self):
        with self.temporary() as directory:
            root=Path(directory);outside=root/'outside';outside.mkdir();sentinel=outside/'sentinel';sentinel.write_bytes(b'unchanged')
            (root/'build/qualification/run1/reports').mkdir(parents=True)
            leaf=root/'build/qualification/run1/reports/actual.tsv';leaf.symlink_to(sentinel)
            with self.assertRaisesRegex(archive.Failure,'WRITE_SYMLINK'):qualify.build_path(root,'build/qualification/run1')
            leaf.unlink();nested=root/'build/qualification/run1/bin';nested.symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(archive.Failure,'WRITE_SYMLINK'):qualify.build_path(root,'build/qualification/run1')
            self.assertEqual(b'unchanged',sentinel.read_bytes())

    def test_prepare_requires_all_explicit_inputs(self):
        with self.assertRaises(archive.Failure):qualify.parser().parse_args(['prepare','--build-dir','build/qualification/run1'])
        args=qualify.parser().parse_args(['prepare','--build-dir','build/qualification/run1','--source-build-dir','build/source','--index-dir','build/index','--rank-dir','build/ranks'])
        self.assertEqual('build/source',args.source_build_dir)

    def test_run_requires_explicit_java_and_cache(self):
        with self.assertRaises(archive.Failure):qualify.parser().parse_args(['run','--build-dir','build/qualification/run1'])
        args=qualify.parser().parse_args(['run','--build-dir','build/qualification/run1','--java','java','--gradle-cache','cache'])
        self.assertEqual('java',args.java)

    def test_prepare_input_rejection_writes_nothing(self):
        with self.temporary() as directory:
            root=Path(directory)
            args=qualify.parser().parse_args(['prepare','--build-dir','build/qualification/run1','--source-build-dir','build/source','--index-dir','build/index','--rank-dir','build/ranks'])
            with patch.object(qualify,'external_inputs',side_effect=archive.Failure('INPUT_IDENTITY')):
                with self.assertRaises(archive.Failure):qualify.prepare(args,self.records,root)
            self.assertFalse((root/'build').exists())

    def test_run_interface_uses_explicit_paths_timeout_and_never_overwrites(self):
        with self.temporary() as directory:
            root=Path(directory);home=root/'build/qualification/run1'
            for name in ('reports','bin','fixtures'):(home/name).mkdir(parents=True)
            for name in ('index','ranks'):(root/name).mkdir()
            jars=[]
            for i in range(5):
                p=root/f'tool{i}.jar';p.write_bytes(bytes([i]));jars.append(p)
            artifact=home/'bin/qualification.jar';artifact.write_bytes(b'interface-test-only')
            owner={'production_sources':{'test':'fixed'},'inputs':{'index_dir':'index','rank_dir':'ranks'}}
            qualify.write_json(home/'reports/compiled.json',{'fresh_compilation':True,'sources':owner['production_sources'],'jars':[archive.sha(p) for p in jars],'jar_sha256':archive.sha(artifact)})
            args=qualify.parser().parse_args(['run','--build-dir','build/qualification/run1','--java','java','--gradle-cache','cache'])
            observed=[]
            def simulated_child(command,seconds,output=None):
                observed.append((command,seconds));output.write(self.records['reports/actual.tsv']);return b''
            with patch.object(qualify,'selected',return_value=(home,owner)),patch.object(qualify,'toolchain',return_value=(Path('/test/java'),jars)),patch.object(qualify,'original_source_lock',return_value=owner['production_sources']),patch.object(qualify,'child',side_effect=simulated_child):
                qualify.run_stage(args,self.records,root)
                with self.assertRaisesRegex(archive.Failure,'RUN_ALREADY_EXISTS'):qualify.run_stage(args,self.records,root)
            self.assertEqual(1,len(observed));command,seconds=observed[0]
            self.assertEqual(300,seconds)
            self.assertEqual([home/'fixtures',root/'index',root/'ranks'],command[-3:])
            identity=qualify.json_file(home/'reports/run.json')
            self.assertFalse(identity['comparison_passed'])
            # This writes only a temporary mocked interface result, never measured evidence.

    def test_original_reference_kotlin_and_cpp_remain_verbatim(self):
        for name in ('reference.py','QualificationMain.kt','unit_oracle.cpp'):
            self.assertEqual(self.records['src/'+name],(qualify.PACKAGE/'source'/name).read_bytes())

    def test_analyzer_semantics_change_only_base_parameter(self):
        old=ast.parse(self.records['src/analyze.py']);new=ast.parse((qualify.PACKAGE/'source/analyze.py').read_text())
        old_body=next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name=='main').body
        new_body=next(x for x in new.body if isinstance(x,ast.FunctionDef) and x.name=='main').body
        class Rename(ast.NodeTransformer):
            def visit_Name(self,node):
                if node.id=='BASE':node.id='base'
                return node
        self.assertEqual(ast.dump(Rename().visit(ast.Module(body=old_body,type_ignores=[]))),ast.dump(ast.Module(body=new_body,type_ignores=[])))

    def test_weighted_expected_construction_semantics_preserved(self):
        old=ast.parse(self.records['src/prepare_oracle.py']);new=ast.parse((qualify.PACKAGE/'source/derive_oracle.py').read_text())
        def block(tree,name):
            body=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name).body
            start=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='frequencies')
            end=next(i for i,x in enumerate(body[start:],start) if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='emit' and 'oracle/provenance.json' in ast.dump(x))
            return ast.Module(body=body[start:end],type_ignores=[])
        class Rename(ast.NodeTransformer):
            def visit_Name(self,node):
                node.id={'BASE':'base','WORDS':'wordforms'}.get(node.id,node.id);return node
        self.assertEqual(ast.dump(Rename().visit(block(old,'main'))),ast.dump(block(new,'derive')))

    def test_missing_java_fails_before_child(self):
        args=qualify.parser().parse_args(['compile','--build-dir','build/a/b','--java','missing','--gradle-cache','missing'])
        with patch.object(qualify.shutil,'which',return_value=None),patch.object(qualify.subprocess,'run') as execute:
            with self.assertRaisesRegex(archive.Failure,'JAVA_REQUIRED'):qualify.toolchain(args)
            execute.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
