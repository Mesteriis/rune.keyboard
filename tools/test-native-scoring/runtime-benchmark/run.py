#!/usr/bin/env python3
"""Explicit manual instrumentation runner; no build, installation or model transfer."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import protocol

PACKAGE='io.github.mesteriis.rune.runtime.llama.test'
ANNOTATIONS='io.github.mesteriis.rune.runtime.llama.'

def arguments(profile,proof):
    protocol.need(profile in ('pilot','full'),'profile_invalid')
    protocol.need(proof.get('schema')==1 and proof.get('build') in (0,1),'proof_invalid')
    protocol.need(proof['build']==0 or proof.get('matched_release')==1,'release_proof_missing')
    native=proof.get('native',[])
    protocol.need(len(native)==2 and [x.get('id') for x in native]==[0,1],'native_proof_invalid')
    args=['adb','-d','shell','am','instrument','-w','-r','-e','annotation',ANNOTATIONS+'RuntimeBenchmarkOnly',
          '-e','notAnnotation',ANNOTATIONS+'VerifiedModelOnly','-e','runeBenchmarkProfile',profile,
          '-e','runeBenchmarkBuild',str(proof['build'])]
    for entry in native:
        digest=entry.get('sha256',[])
        protocol.need(len(digest)==8 and all(type(x) is int and 0<=x<2**32 for x in digest),'native_proof_invalid')
        args.extend(['-e','runeBenchmarkNative'+str(entry['id']),':'.join(map(str,digest))])
    return args+[PACKAGE+'/androidx.test.runner.AndroidJUnitRunner']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['pilot','full'],required=True)
    parser.add_argument('--proof',type=Path,required=True);parser.add_argument('--rows',type=Path,required=True)
    parser.add_argument('--summary',type=Path,required=True);args=parser.parse_args()
    try:
        protocol.need(not args.rows.exists() and not args.rows.is_symlink() and not args.summary.exists()
                      and not args.summary.is_symlink(),'output_exists')
        proof=json.loads(args.proof.read_text());command=arguments(args.profile,proof)
        try:
            completed=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,
                                     timeout=(600 if args.profile=='pilot' else 1800)+60)
        except subprocess.TimeoutExpired:
            # Best-effort bounded cleanup of only this dedicated instrumentation app.
            subprocess.run(['adb','-d','shell','am','force-stop',PACKAGE],stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,timeout=10)
            raise protocol.Invalid('host_timeout')
        protocol.need(completed.returncode==0,'instrumentation_command_failed')
        numeric=protocol.capture(io.StringIO(completed.stdout));rows=protocol.parse(numeric)
        result=protocol.summarize(rows,proof)
        protocol.need(result['profile']==(0 if args.profile=='pilot' else 1),'profile_mismatch')
        with args.rows.open('x') as output:output.write(numeric)
        with args.summary.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    except Exception as failure:
        print('benchmark_run_error:'+ (str(failure) if isinstance(failure,protocol.Invalid) else 'operation_failed'),file=sys.stderr)
        return 1
    print('benchmark_run_pass');return 0

if __name__=='__main__':sys.exit(main())
