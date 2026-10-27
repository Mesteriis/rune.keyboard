#!/usr/bin/env python3
"""Run the opt-in U13 observer on an explicitly named disposable emulator.

Requires an installed debug app/test APK, seeded synthetic fixture, charging and
night clock configured separately. Never installs APKs or forces Doze.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

PACKAGE='io.github.mesteriis.rune.keyboard'
JOB=1381321777
OBSERVER=PACKAGE+'.smarttyping.learning.LearningNightJobFixtureInstrumentedTest#observeJob'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb',required=True,type=Path);parser.add_argument('--serial',required=True)
    parser.add_argument('--expected-avd',required=True);parser.add_argument('--expected',choices=('blocked','promoted'),required=True)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    if not args.serial.startswith('emulator-') or not args.expected_avd.startswith('rune_review_u13_'):
        parser.error('explicit disposable U13 emulator required')
    log=args.output.with_suffix('.instrumentation.log')
    if args.output.exists() or log.exists():parser.error('fresh output required')
    command=[str(args.adb),'-s',args.serial]
    def raw(parameters,timeout=30):
        return subprocess.run(command+parameters,capture_output=True,text=True,timeout=timeout)
    def guard():
        if raw(['shell','getprop','ro.kernel.qemu']).stdout.strip()!='1':raise RuntimeError('EMULATOR_REQUIRED')
        name=raw(['emu','avd','name']).stdout.splitlines()
        if not name or name[0].strip()!=args.expected_avd:raise RuntimeError('AVD_IDENTITY_CHANGED')
    def run(parameters,check=True):
        guard();result=raw(parameters)
        if check and result.returncode:raise RuntimeError('SCOPED_COMMAND_FAILED:'+str(result.returncode))
        return result
    def observe():
        result=run(['shell','run-as',PACKAGE,'cat','cache/review-u13-state.json'],check=False)
        if result.returncode:return {}
        try:return json.loads(result.stdout)
        except json.JSONDecodeError:return {}
    guard();boot=run(['shell','cat','/proc/sys/kernel/random/boot_id']).stdout.strip()
    run(['shell','am','force-stop',PACKAGE])
    run(['shell','run-as',PACKAGE,'rm','-f','cache/review-u13-state.json'])
    invocation=command+['shell','am','instrument','-w','-r','-e','reviewU13','true','-e','reviewU13Expected',args.expected,
        '-e','class',OBSERVER,PACKAGE+'.test/androidx.test.runner.AndroidJUnitRunner']
    with log.open('x') as stream:
        process=subprocess.Popen(invocation,stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                if observe().get('observerReady'):break
                if process.poll() is not None:raise RuntimeError('OBSERVER_TERMINATED_BEFORE_READY')
                time.sleep(.2)
            else:raise RuntimeError('OBSERVER_NOT_READY')
            run(['shell','input','keyevent','KEYCODE_SLEEP'])
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if re.search(r'(?m)^\s*mWakefulness=Asleep\s*$',run(['shell','dumpsys','power']).stdout):break
                time.sleep(.1)
            else:raise RuntimeError('SCREEN_NOT_ASLEEP')
            # -f tests the service's independent runtime guard, not scheduler readiness.
            trigger=run(['shell','cmd','jobscheduler','run','-f','-u','0',PACKAGE,str(JOB)])
            if 'Running job' not in trigger.stdout:raise RuntimeError('JOB_TRIGGER_NOT_ACKNOWLEDGED')
            process.wait(timeout=110)
        finally:
            if process.poll() is None:
                # Drain the bounded observer before returning an uncertain action result.
                try:process.wait(timeout=110)
                except subprocess.TimeoutExpired:
                    run(['shell','am','force-stop',PACKAGE]);process.wait(timeout=15)
    result=observe();runner_ok=process.returncode==0 and 'OK (1 test)' in log.read_text()
    dump=run(['shell','dumpsys','jobscheduler',PACKAGE]).stdout
    blocks=re.split(r'(?m)(?=^\s*JOB #)',dump)
    failures=[]
    for block in blocks:
        if re.search(r'(?m)^\s*JOB #[^\n]*/'+str(JOB)+r':',block) and PACKAGE in block:
            failures.extend(int(v) for v in re.findall(r'Num failures:\s*(\d+)',block))
    boot_unchanged=run(['shell','cat','/proc/sys/kernel/random/boot_id']).stdout.strip()==boot
    report=dict(expected=args.expected,runnerPassed=runner_ok,observations=result,
        currentJobFailureCount=max(failures) if failures else None,bootUnchanged=boot_unchanged,
        dozeForced=False,apkInstallationPerformed=False)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))
    if not runner_ok or not boot_unchanged or not result.get('finished'):raise SystemExit(1)
    if args.expected=='blocked' and not failures:raise RuntimeError('RETRY_NOT_OBSERVED')
    if args.expected=='blocked' and max(failures)<1:raise RuntimeError('RETRY_NOT_OBSERVED')


if __name__=='__main__':main()
