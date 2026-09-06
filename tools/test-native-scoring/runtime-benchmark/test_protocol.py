import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock
import run as runner
import native_proof
import protocol as p

BASE=Path(__file__).resolve().parent

def fixture(profile=0):
    proof={'schema':1,'build':1,'matched_release':1,'native':[{'id':i,'sha256':[i+1]*8} for i in range(2)]}
    rows=[]
    def add(kind,config=-1,iteration=-1):
        r=[1,kind,profile,len(rows),config,iteration,0,1_000_000,2,0,0,-1,1000,2000,3000,4000,0,0]
        if kind in (1,2,5): r[9:12]=[(2,4,8)[config%3]*2,(2,4,8)[config%3],1]
        if kind==3 and config==1: r[11]=1
        if kind==0:r[16:18]=[36,1]
        if kind==8:r[8:16]=[config+1]*8
        if kind==4:r[6]=1;r[16:18]=[100,10_000_000]
        rows.append(r)
    add(0);add(8,0);add(8,1);add(3,0);add(3,1)
    for kind,config,iteration in p.expected_visits(1)+p.expected_visits(p.REPEATS[profile]):add(kind,config,iteration)
    for i in range(3):add(4,i)
    add(5,0);add(3,2);add(3,3);add(6)
    return rows,proof

def encoded(rows):return '\n'.join(','.join(map(str,r)) for r in rows)+'\n'

class ProtocolTest(unittest.TestCase):
    def test_complete_profiles_and_counts(self):
        for profile,count in [(0,27),(1,180)]:
            rows,proof=fixture(profile);summary=p.summarize(p.parse(encoded(rows)),proof)
            self.assertEqual(count,summary['measured_requests'])
            self.assertEqual(count*14//3,sum(c['scored_candidates'] for c in summary['measured_cells']))
            self.assertEqual(3,summary['cancellation']['cancelled'])
    def test_nearest_rank_arithmetic(self):
        self.assertEqual({'count':20,'available_count':20,'missing_count':0,'p50':10,'p95':19,'max':20},p.metric(list(range(1,21))))
        self.assertEqual(3,p.metric([1,2,3])['p95'])
    def test_missing_memory_never_selected_away(self):
        rows,proof=fixture();next(r for r in rows if r[1]==2 and r[4]==0)[12]=-1
        metric=p.summarize(rows,proof)['measured_cells'][0]['metrics']['pss_bytes']
        self.assertEqual(1,metric['missing_count']);self.assertIsNone(metric['p95'])
    def test_missing_duplicate_order_or_terminal_rejected(self):
        rows,proof=fixture()
        for altered in [rows[:-1],rows+[rows[-1]],rows[:8]+rows[9:],rows[:8]+[rows[9],rows[8]]+rows[10:]]:
            with self.assertRaises(p.Invalid):p.summarize(altered,proof)
    def test_native_proof_build_and_hash_required(self):
        rows,proof=fixture()
        for field,value in [('build',0),('matched_release',0),('native',[{'id':0,'sha256':[99]*8},{'id':1,'sha256':[2]*8}])]:
            bad=copy.deepcopy(proof);bad[field]=value
            with self.assertRaises(p.Invalid):p.summarize(rows,bad)
    def test_success_cardinality_and_token_rejected(self):
        for column,value in [(10,8),(9,0),(11,-1),(8,-1)]:
            rows,proof=fixture();next(r for r in rows if r[1]==2 and r[4]==0)[column]=value
            with self.assertRaises(p.Invalid):p.summarize(rows,proof)
    def test_completion_races_are_not_cancelled(self):
        rows,proof=fixture();r=next(r for r in rows if r[1]==4);r[6]=2;r[9:12]=[16,8,1];r[16]=-1
        result=p.summarize(rows,proof)['cancellation']
        self.assertEqual((2,1,1),(result['cancelled'],result['completion_races'],result['completed_before_signal']))
        self.assertIsNone(result['signal_to_end_ns']['p95'])
    def test_explicit_failure_rejected(self):
        rows,proof=fixture();rows[6][1]=7;rows[6][6]=30
        with self.assertRaises(p.Invalid):p.summarize(rows,proof)
    def test_strict_numeric_rows_and_width(self):
        for raw in ['1,text','1,'+'0,'*17,'1,'+','.join(['0']*16),','.join(['1']+[str(2**64)]+['0']*16),','.join(['١']*18),'']:
            with self.assertRaises(p.Invalid):p.parse(raw)
    def test_capture_requires_one_successful_test_and_completion(self):
        rows,_=fixture();lines=['INSTRUMENTATION_STATUS: rune_bench='+x for x in encoded(rows).splitlines()]
        good='\n'.join(lines+['OK (1 test)','INSTRUMENTATION_CODE: -1'])
        self.assertEqual(encoded(rows),p.capture(io.StringIO(good)))
        for bad in [good.replace('OK (1 test)','OK (2 tests)'),good.replace('INSTRUMENTATION_CODE: -1',''),good+'\nFAILURES!!!']:
            with self.assertRaises(p.Invalid):p.capture(io.StringIO(bad))
    def test_cli_redacts_malformed_payload(self):
        with tempfile.TemporaryDirectory(prefix='rune-runtime-benchmark-') as tmp:
            d=Path(tmp);_,proof=fixture();(d/'proof.json').write_text(json.dumps(proof));(d/'rows').write_text('private_payload_token')
            result=subprocess.run([sys.executable,str(BASE/'protocol.py'),'summary','--proof',str(d/'proof.json'),
                '--rows',str(d/'rows'),'--summary',str(d/'summary')],capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode);self.assertNotIn('private_payload_token',result.stdout+result.stderr)
            self.assertFalse((d/'summary').exists())
    def test_runner_explicit_profile_and_expected_native_arguments(self):
        _,proof=fixture()
        for profile in ('pilot','full'):
            args=runner.arguments(profile,proof)
            self.assertEqual(['adb','-d','shell','am','instrument'],args[:5])
            self.assertIn(profile,args)
            self.assertIn('1:1:1:1:1:1:1:1',args)
            self.assertIn('2:2:2:2:2:2:2:2',args)
            self.assertNotIn('VerifiedModelOnly',args)
        for profile in ('',None,'FULL'):
            with self.assertRaises(p.Invalid):runner.arguments(profile,proof)
        bad=copy.deepcopy(proof);bad['native'][0]['sha256'][0]='payload'
        with self.assertRaises(p.Invalid):runner.arguments('pilot',bad)
    def test_runner_timeout_cleanup_is_only_dedicated_test_app(self):
        with tempfile.TemporaryDirectory(prefix='rune-runtime-benchmark-') as tmp:
            d=Path(tmp);_,proof=fixture();(d/'proof').write_text(json.dumps(proof))
            argv=['run.py','--profile','pilot','--proof',str(d/'proof'),'--rows',str(d/'rows'),'--summary',str(d/'summary')]
            with mock.patch.object(sys,'argv',argv), mock.patch.object(runner.subprocess,'run',side_effect=[subprocess.TimeoutExpired('ignored',660),None]) as invoked, mock.patch('sys.stderr',new_callable=io.StringIO) as error:
                self.assertEqual(1,runner.main())
                self.assertEqual(['adb','-d','shell','am','force-stop','io.github.mesteriis.rune.runtime.llama.test'],invoked.call_args_list[1].args[0])
                self.assertEqual(['adb','-d'],invoked.call_args_list[0].args[0][:2])
                self.assertEqual(invoked.call_args_list[0].args[0][:2],invoked.call_args_list[1].args[0][:2])
                self.assertEqual(10,invoked.call_args_list[1].kwargs['timeout'])
                self.assertEqual('benchmark_run_error:host_timeout\n',error.getvalue())
            self.assertFalse((d/'rows').exists());self.assertFalse((d/'summary').exists())
    def test_existing_outputs_rejected_before_adb(self):
        with tempfile.TemporaryDirectory(prefix='rune-runtime-benchmark-') as tmp:
            d=Path(tmp);(d/'summary').write_text('sentinel')
            argv=['run.py','--profile','pilot','--proof',str(d/'missing-proof'),'--rows',str(d/'rows'),'--summary',str(d/'summary')]
            with mock.patch.object(sys,'argv',argv),mock.patch.object(runner.subprocess,'run') as invoked,mock.patch('sys.stderr',new_callable=io.StringIO):
                self.assertEqual(1,runner.main());invoked.assert_not_called()
            self.assertEqual('sentinel',(d/'summary').read_text())
    def test_native_zip_identity_missing_and_mismatch(self):
        with tempfile.TemporaryDirectory(prefix='rune-runtime-benchmark-') as tmp:
            d=Path(tmp)
            def make(name,content,omit=False):
                file=d/name
                with zipfile.ZipFile(file,'w') as z:
                    for i,lib in enumerate(native_proof.LIBRARIES):
                        if not(omit and i==1):z.writestr('lib/arm64-v8a/'+lib,content+bytes([i]))
                return file
            a=make('a.apk',b'fixed');b=make('b.apk',b'fixed');c=make('c.apk',b'changed');missing=make('missing.apk',b'fixed',True)
            self.assertEqual(1,native_proof.proof(a,'release',b)['matched_release'])
            for other in [c,None,missing]:
                with self.assertRaises((ValueError,KeyError)):native_proof.proof(a,'release',other)
            self.assertEqual(0,native_proof.proof(a,'debug')['matched_release'])

if __name__=='__main__':unittest.main(verbosity=2)
