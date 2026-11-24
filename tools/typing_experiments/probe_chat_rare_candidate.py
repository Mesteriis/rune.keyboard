#!/usr/bin/env python3
"""Execute the production packed-word reader and qualification gates on a candidate."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from replay_joint_correction import replay

ROOT=Path(__file__).resolve().parents[2]
PROBE=ROOT/'tools/typing_experiments/ChatRareCandidateProbe.kt'
BASE=ROOT/'app/src/main/assets/smarttyping/lexicon/ru.rare'


def run(candidate_root,output,java):
    candidate_root,output,java=map(lambda p:Path(p).resolve(),(candidate_root,output,java))
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('RARE_PROBE_OUTPUT')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):raise ValueError('RARE_PROBE_JAVA_OPTIONS')
    candidate=candidate_root/'candidate.rare';receipt_path=candidate_root/'receipt.json';words=candidate_root/'source/words.txt'
    base_words=candidate_root/'base-source/words.txt';base_pack=candidate_root/'original-pack-receipt.json'
    receipt=json.loads(receipt_path.read_text())
    base_receipt=json.loads(base_pack.read_text())
    if (receipt.get('purpose')!='POSTHOC_PACKED_CANDIDATE_NOT_QUALIFICATION' or receipt.get('independentQualification') is not False
            or receipt.get('candidateSha256')!=replay.sha256(candidate) or receipt.get('baselineSha256')!=replay.sha256(BASE)
            or receipt.get('previousWords')!=288246 or receipt.get('addedWords')!=7
            or base_receipt.get('sha256')!=receipt['baselineSha256'] or base_receipt.get('sourceWordsSha256')!=replay.sha256(base_words)
            or receipt.get('candidate',{}).get('sourceWordsSha256')!=replay.sha256(words)):raise ValueError('RARE_PROBE_RECEIPT')
    sources,jars,android=replay.compile_inputs(java)
    paths=list(dict.fromkeys([*sources,*jars,android,java,BASE,candidate,receipt_path,base_pack,base_words,words,PROBE,Path(__file__),Path(replay.__file__)]))
    bindings={replay.path_key(path):replay.sha256(path) for path in paths}
    output.mkdir(parents=True,mode=0o700)
    jar,compile_command=replay.compile_harness(output,java,[*sources,PROBE],jars,android)
    classpath=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]))
    command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',classpath,
        'io.github.mesteriis.rune.keyboard.smarttyping.correction.ChatRareCandidateProbe',str(BASE),str(candidate),str(base_words),str(words),receipt['candidateSha256']]
    with (output/'probe.log').open('x') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=300,check=True)
    values=json.loads((output/'probe.log').read_text())
    if values!={'originalWordsChecked':288246,'addedWordsChecked':7,'oldRanksPreserved':True,'corruptRefused':True,'changedFingerprintRefusals':6}:
        raise ValueError('RARE_PROBE_RESULT')
    replay.verify_bound_files({'files':bindings})
    summary=dict(purpose='PACKED_CANDIDATE_PROBE_NOT_QUALIFICATION',independentQualification=False,results=values,
        candidateSha256=receipt['candidateSha256'],baseSha256=receipt['baselineSha256'],probeSha256=replay.sha256(PROBE),
        compiledJarSha256=replay.sha256(jar),bindings=bindings,compileCommand=compile_command,runCommand=command,exitCode=result.returncode)
    (output/'receipt.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n');return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate-root','output','java'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(run(args.candidate_root,args.output,args.java)['results']))

if __name__=='__main__':main()
