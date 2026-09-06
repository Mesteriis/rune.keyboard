"""Small host-only contracts over preserved numeric records; no timing reruns."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.dont_write_bytecode = True
import bench
import records

class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all = records.historical_records()
        cls.full = bench.read_json(bench.PACKAGE/'manifests/full.json')
        cls.exact = bench.read_json(bench.PACKAGE/'manifests/exact.json')
        cls.quiet = records.cohort(cls.all,'full/device-api26-development-quiet')
        cls.cold = records.cohort(cls.all,'full/device-api26-cold')
        cls.exact02 = records.cohort(cls.all,'exact/device-api26-exact-02')
        cls.decision = bench.read_json(bench.PACKAGE/'evidence/decision.json')
        cls.dex = cls.decision['historical_dex_sha256']['full']
        cls.exact_dex = cls.decision['historical_dex_sha256']['exact_02']

    def test_package_and_manifest_identity(self):
        bench.package_check()
        origins = bench.read_json(bench.PACKAGE/'manifests/source-origins.json')['files']
        for rec in origins:
            self.assertEqual(bench.sha(bench.PACKAGE/rec['path']), rec['sha256'])
        reader = bench.sha(bench.PACKAGE/'source/common/LexiconPrototype.kt')
        self.assertEqual(reader,self.full['source_reader_sha256'])
        self.assertEqual(reader,self.exact['reader_sha256'])

    def test_full_and_cold_complete_preserved_records(self):
        self.assertEqual(records.validate_full(self.quiet,self.full,self.dex)['processes'],9)
        self.assertEqual(records.validate_full(self.cold,self.full,self.dex)['processes'],27)

    def test_exact02_all_repetitions_allocation_unavailable(self):
        parsed = records.validate_exact(self.exact02,self.exact,self.exact_dex)
        self.assertEqual(len(parsed),9)
        samples = [r for p in parsed.values() for repeats in p['samples'].values() for r in repeats]
        self.assertEqual(len(samples),12465)
        self.assertTrue(all(r[2]==-1 for r in samples))
        self.assertTrue(all(p['api']==26 for p in parsed.values()))

    def test_untrusted_full_filename_rejected(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        data['DO_NOT_ECHO_INPUT_MARKER.tsv'] = data.pop(name)
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_missing_full_process_rejected(self):
        data = dict(self.quiet)
        del data[next(p for p in data if p!='verify.tsv')]
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_duplicate_full_process_rejected(self):
        data = dict(self.quiet)
        data['extra.tsv'] = data[next(p for p in data if p!='verify.tsv')]
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_missing_full_row_rejected(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        lines = data[name].splitlines()
        del lines[next(i for i,v in enumerate(lines) if v.startswith('ROW\t'))]
        data[name] = '\n'.join(lines)+'\n'
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_duplicate_full_row_rejected(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        line = next(v for v in data[name].splitlines() if v.startswith('ROW\t'))
        data[name] += line+'\n'
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_mixed_profiles_rejected(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        data[name] = data[name].replace('META\t26\t','META\t37\t',1)
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_capped_failure_must_prohibit_auto(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        lines = data[name].splitlines()
        for i,line in enumerate(lines):
            f = line.split('\t')
            if f[0]=='ROW' and f[4]=='bounded' and f[-1]=='true':
                f[-1]='false';lines[i]='\t'.join(f);break
        else:self.fail('FIXTURE_REQUIRES_CAPPED_ROW')
        data[name]='\n'.join(lines)+'\n'
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_wrong_full_expected_count_rejected(self):
        data = dict(self.quiet)
        name = next(p for p in data if p!='verify.tsv')
        lines = data[name].splitlines()
        i = next(i for i,v in enumerate(lines) if v.startswith('ROW\t'))
        row = lines[i].split('\t');row[1+records.ROW_HEADER.index('expected')]='999999';lines[i]='\t'.join(row)
        data[name]='\n'.join(lines)+'\n'
        with self.assertRaises(ValueError):records.validate_full(data,self.full,self.dex)

    def test_wrong_dex_rejected_both_profiles(self):
        with self.assertRaises(ValueError):records.validate_full(self.quiet,self.full,'0'*64)
        with self.assertRaises(ValueError):records.validate_exact(self.exact02,self.exact,'0'*64)

    def test_exact_missing_process_row_and_bad_label(self):
        data = dict(self.exact02);del data['en.front.tsv']
        with self.assertRaises(ValueError):records.validate_exact(data,self.exact,self.exact_dex)
        raw = self.exact02['en.front.tsv'];module=records.exact_module();group=self.exact['groups'][0]
        lines=raw.splitlines();i=next(i for i,v in enumerate(lines) if v.startswith('ROW\t5\t'))
        with self.assertRaises(ValueError):module.parse('\n'.join(lines[:i]+lines[i+1:]),group,'front',bench.EXACT_HASH)
        row=lines[i].split('\t');row[5]='2';lines[i]='\t'.join(row)
        with self.assertRaises(ValueError):module.parse('\n'.join(lines),group,'front',bench.EXACT_HASH)

    def test_unavailable_optional_samples_cannot_hide_in_median(self):
        module=records.exact_module()
        # The unchanged exact reducer computes this in summarize(); inspect its
        # public output with tiny synthetic strata, not a new measured workload.
        with tempfile.TemporaryDirectory(dir=bench.PROJECT/'build') as tmp:
            home=Path(tmp);(home/'reports').mkdir();(home/'bin').mkdir()
            (home/'reports/frozen-manifest.json').write_text('{}');(home/'bin/benchmark-dex.jar').write_bytes(b'fixture')
            module.ROOT=home
            for values,expected in [([-1,-1,10,30,50],None),([10,20,30,40,50],30)]:
                queries=[{'id':0,'cohort':0,'label':0,'category':'fixture','stratum':'fixture'}]
                data={('en',f):{'api':-1,'samples':{0:[(1,v,v,v) for v in values]}} for f in ('front','trie','delete')}
                report=module.summarize({'groups':[{'language':'en','queries':queries}]},data)
                pool=next(g for g in report['groups'] if g['pool']=='development')
                for result in pool['formats'].values():
                    for name in ('cpu_ns_p95','allocated_bytes_p95','gc_count_p95'):
                        self.assertEqual(result[name],expected)

    def test_original_allocation_preserved_but_never_qualified(self):
        raw=bench.read_json(bench.PACKAGE/'evidence/summary-device-api26-development-quiet.json')
        snapshot=copy.deepcopy(raw);qualified=records.qualified_full(raw)
        self.assertEqual(raw,snapshot)
        self.assertTrue(all(r['reference_allocated_bytes'] is None for g in qualified['comparisons'] for r in g['formats'].values()))
        self.assertEqual(qualified['energy_evidence'],'NOT_MEASURED')
        first=records.cohort(self.all,'exact/device-api26-exact-01')
        negative=sum(int(line.split('\t')[8]) < -1 for raw in first.values() for line in raw.splitlines() if line.startswith('ROW\t'))
        self.assertEqual(negative,45)

    def test_full_p95_and_completion_match_original_records(self):
        for group in self.decision['languages']:
            lang=group['language']
            for fmt in ('front','trie','delete'):
                text=next(raw for name,raw in self.quiet.items() if name.startswith(lang+'.'+fmt+'.'))
                rows=[dict(zip(records.ROW_HEADER,l.split('\t')[1:])) for l in text.splitlines() if l.startswith('ROW\t')]
                reference=[r for r in rows if r['phase']=='reference']
                ids={r['id'] for r in reference}
                medians=[statistics.median(int(r['topn_ns'])/1e6 for r in reference if r['id']==qid) for qid in ids]
                self.assertEqual(sorted(medians)[math.ceil(.95*len(medians))-1],group['full_complete_p95_ms'][fmt])
                complete=sum(r['phase']=='bounded' and r['repeat']=='0' and r['reason']=='NONE' for r in rows)
                self.assertEqual(complete,group['bounded_completion'][fmt]['complete'])
                self.assertLess(complete,240)

    def test_decision_uses_complete_paired_ci_and_exact(self):
        self.assertEqual(self.decision['decision'],'PACKED_TRIE')
        self.assertFalse(self.decision['size_tie_break_invoked'])
        for g in self.decision['languages']:
            for key in ('front minus trie','delete minus trie'):
                self.assertGreater(g['paired_full_delta_ms_ci95'][key][0],0)
            for key in ('front-trie','delete-trie'):
                self.assertGreater(g['exact_development']['paired_p95_delta_ns_ci95'][key][0],0)
        for name,digest in self.decision['source_summaries_sha256'].items():
            self.assertEqual(bench.sha(bench.PACKAGE/'evidence'/name),digest)

    def test_fixed_fixture_ids_and_development_split(self):
        plan=bench.read_json(bench.PACKAGE/'fixtures/development/manifest.json')
        for group in self.exact['groups']:
            lang=group['language'];index=('en','es','ru').index(lang)
            rows=[s.split('\t') for s in (bench.PACKAGE/'fixtures/exact'/f'{lang}.tsv').read_text().splitlines()]
            full=[s.split('\t') for s in (bench.PACKAGE/'fixtures/full'/f'{lang}.development.tsv').read_text().splitlines()]
            dev=[json.loads(s) for s in (bench.PACKAGE/'fixtures/development'/f'{lang}.jsonl').read_text().splitlines()]
            self.assertEqual([int(r[0]) for r in rows],list(range(index*1000,index*1000+277)))
            self.assertEqual([r[3] for r in rows[:240]],[r[1] for r in full])
            self.assertEqual([d['query'] for d in dev],[r[1] for r in full])
            self.assertTrue(all(d['split']=='development' for d in dev))
            self.assertEqual([int(r[2]) for r in rows[240:258]],[1]*18)
            self.assertEqual([int(r[2]) for r in rows[258:276]],[0]*18)
            self.assertEqual(rows[-1][2:4],['2',''])
            for d in dev:
                digest=hashlib.sha256((plan['seed']+'\0'+lang+'\0'+d['source_word']).encode()).digest()
                self.assertLessEqual(digest[0]%10,6)

    def test_build_scope_and_preexisting_leaf_redirect(self):
        with self.assertRaises(ValueError):bench.config.build_root(str(bench.PROJECT))
        with self.assertRaises(ValueError):bench.config.build_root(str(bench.PROJECT/'build'))
        with tempfile.TemporaryDirectory(dir=bench.PROJECT/'build') as tmp:
            root=Path(tmp);outside=root/'outside';outside.mkdir();owned=root/'owned';owned.mkdir()
            sentinel=outside/'value';sentinel.write_text('preserved')
            (owned/'result.json').symlink_to(sentinel)
            with self.assertRaises(ValueError):bench.config.build_root(str(owned))
            self.assertEqual(sentinel.read_text(),'preserved')

    def test_redacted_cli_argument_error(self):
        sentinel='DO_NOT_ECHO_INPUT_MARKER'
        p=subprocess.run([sys.executable,str(bench.PACKAGE/'bench.py'),sentinel],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,2)
        self.assertEqual(p.stdout,'FAIL ARGUMENTS\n')
        self.assertEqual(p.stderr,'')
        self.assertNotIn(sentinel,p.stdout+p.stderr)

    def test_no_machine_identifiers_and_shell_syntax(self):
        for rec in bench.read_json(bench.PACKAGE/'package-manifest.json')['files']:
            if rec['path'].endswith('.gz'):continue
            text=(bench.PACKAGE/rec['path']).read_text(encoding='utf-8')
            for token in ('/Users/','/home/','adb -s ','ANDROID_SERIAL='):
                # This test's literal denylist is not evidence or a machine path.
                if rec['path']!='test_contracts.py':self.assertNotIn(token,text)
        for kind in ('full','exact'):
            result=subprocess.run(['/bin/sh','-n',str(bench.PACKAGE/'source'/kind/'run.sh')],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0)

    def test_pipeline_notices_match_measured_manifest(self):
        for rec in self.full['assets']:
            relative=rec['path']
            if not relative.startswith('notices/'):continue
            if relative=='notices/UPSTREAM-PROTOTYPE-NOTICES.md':path=bench.PACKAGE/'fixtures/UPSTREAM-PROTOTYPE-NOTICES.md'
            elif relative=='notices/output-manifest.json':path=bench.PIPELINE/'frozen-output-manifest.json'
            elif relative=='notices/source-lock.json':path=bench.PIPELINE/'source-lock.json'
            else:path=bench.PIPELINE/relative
            bench.checked(path,rec)

    def test_compiler_command_contract_without_compiling(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=bench.PROJECT/'build') as tmp:
            root=Path(tmp)
            jars=[]
            for i in range(6):
                p=root/f'jar{i}.jar';p.write_bytes(b'fixture');jars.append(p)
            for kind in ('full','exact'):
                for directory in ('bin','src','reports'):(root/kind/directory).mkdir(parents=True)
            calls=[]
            def fake_child(command,**options):
                words=list(map(str,command));calls.append(words)
                flag='--output' if 'com.android.tools.r8.D8' in words else '-d'
                Path(words[words.index(flag)+1]).write_bytes(b'fixture output')
            args=argparse.Namespace()
            with patch.object(bench,'selected',return_value=root), patch.object(bench,'toolchain',return_value=(Path('java17'),jars,Path('android.jar'),Path('d8.jar'))), patch.object(bench,'child',side_effect=fake_child):
                bench.compile_harness(args)
            self.assertEqual(len(calls),6)
            self.assertTrue(all('-XX:ActiveProcessorCount=2' in c and '-Xmx768m' in c for c in calls))
            d8=[c for c in calls if 'com.android.tools.r8.D8' in c]
            self.assertEqual(len(d8),2)
            self.assertTrue(all(c[c.index('--min-api')+1]=='26' for c in d8))
            compiler=[c for c in calls if 'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler' in c]
            self.assertTrue(all(c[c.index('-jvm-target')+1]=='1.8' for c in compiler))
            self.assertEqual(sum(any(x.endswith('/ExactBenchmark.kt') for x in c) for c in compiler),2)
            self.assertEqual(sum(any(x.endswith('/Benchmark.kt') for x in c) for c in compiler),2)

if __name__=='__main__':
    unittest.main(verbosity=2)
