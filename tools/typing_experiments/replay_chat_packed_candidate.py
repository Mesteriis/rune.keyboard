#!/usr/bin/env python3
"""Replay an isolated packed candidate with its real, unchanged qualification gates."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from replay_joint_correction import replay,controller_records

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/FrozenRareWordLexicon.kt'
RARE='smarttyping/lexicon/ru.rare'


def verify_assets(original,copy,candidate):
    originals={p.relative_to(original) for p in original.rglob('*') if p.is_file()}
    copied={p.relative_to(copy) for p in copy.rglob('*') if p.is_file()}
    if originals!=copied:raise ValueError('PACKED_REPLAY_ASSET_SCOPE')
    for relative in originals:
        expected=candidate if relative.as_posix()==RARE else original/relative
        if replay.sha256(copy/relative)!=replay.sha256(expected):raise ValueError('PACKED_REPLAY_ASSET_DRIFT')


def candidate_constants(source,old_hash,new_hash,new_size):
    if not re.fullmatch('[0-9a-f]{64}',old_hash) or not re.fullmatch('[0-9a-f]{64}',new_hash) or type(new_size) is not int or new_size<=0:
        raise ValueError('PACKED_REPLAY_CONSTANTS')
    match=re.search(r'const val ASSET_BYTES = ([0-9_]+)L',source)
    if not match or source.count('const val ASSET_BYTES = ')!=1 or source.count(old_hash)!=1:
        raise ValueError('PACKED_REPLAY_SOURCE')
    return source.replace(match.group(0),f'const val ASSET_BYTES = {new_size}L').replace(old_hash,new_hash)


def run(rows_path,baseline_path,candidate_root,output,java):
    rows_path,baseline_path,candidate_root,output,java=map(lambda p:Path(p).resolve(),(rows_path,baseline_path,candidate_root,output,java))
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('PACKED_REPLAY_OUTPUT')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):raise ValueError('PACKED_REPLAY_JAVA_OPTIONS')
    baseline=json.loads(baseline_path.read_text());candidate_receipt_path=candidate_root/'receipt.json';candidate_receipt=json.loads(candidate_receipt_path.read_text())
    candidate=candidate_root/'candidate.rare';old_asset=replay.ASSETS/RARE
    if (baseline.get('status')!='COMPLETE' or baseline.get('exitCode')!=0 or baseline.get('mode')!='current-product'
            or baseline.get('rowsSha256')!=replay.sha256(rows_path) or candidate_receipt.get('purpose')!='POSTHOC_PACKED_CANDIDATE_NOT_QUALIFICATION'
            or candidate_receipt.get('candidateSha256')!=replay.sha256(candidate) or candidate_receipt.get('baselineSha256')!=replay.sha256(old_asset)
            or candidate_receipt.get('independentQualification') is not False):raise ValueError('PACKED_REPLAY_BINDING')
    replay.verify_bound_files(baseline)
    records=replay.read_jsonl(rows_path);controller=controller_records(records);sources,jars,android=replay.compile_inputs(java)
    assets=sorted(p for p in replay.ASSETS.rglob('*') if p.is_file())
    paths=list(dict.fromkeys([*sources,*jars,android,java,*assets,rows_path,baseline_path,candidate,candidate_receipt_path,Path(__file__),Path(replay.__file__)]))
    bindings={replay.path_key(p):replay.sha256(p) for p in paths}
    modified=candidate_constants(FROZEN.read_text(),candidate_receipt['baselineSha256'],candidate_receipt['candidateSha256'],candidate.stat().st_size)
    output.mkdir(parents=True,mode=0o700);asset_copy=output/'assets';shutil.copytree(replay.ASSETS,asset_copy)
    shutil.copyfile(candidate,asset_copy/RARE)
    verify_assets(replay.ASSETS,asset_copy,candidate)
    frozen_copy=output/'FrozenRareWordLexicon.kt';frozen_copy.write_text(modified)
    frozen_hash=replay.sha256(frozen_copy)
    enc=lambda s:base64.b64encode(s.encode()).decode('ascii')
    with (output/'inputs.tsv').open('x',encoding='ascii') as stream:
        for index,row in enumerate(controller):stream.write('\t'.join([str(index),enc(row['id']),row['split'],row['language'],enc(row['prefix']),enc(row['typed'])])+'\n')
    jar,compile_command=replay.compile_harness(output,java,[frozen_copy if p==FROZEN else p for p in sources],jars,android)
    classpath=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]))
    command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',classpath,
        'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',str(output/'inputs.tsv'),str(asset_copy),'current-product','all']
    with (output/'candidate-observations.jsonl').open('xb') as out,(output/'candidate-observations.log').open('xb') as log:
        result=subprocess.run(command,stdout=out,stderr=log,timeout=1200,check=True)
    replay.verify_bound_files({'files':bindings});replay.verify_bound_files(baseline)
    verify_assets(replay.ASSETS,asset_copy,candidate)
    if replay.sha256(frozen_copy)!=frozen_hash:raise ValueError('PACKED_REPLAY_SOURCE_DRIFT')
    summary=dict(purpose='PACKED_CANDIDATE_WITH_UNCHANGED_QUALIFICATION_NOT_QUALIFICATION',independentQualification=False,
        rowsSha256=replay.sha256(rows_path),candidateSha256=replay.sha256(candidate),baselineSha256=replay.sha256(old_asset),
        observationsSha256=replay.sha256(output/'candidate-observations.jsonl'),frozenSourceSha256=replay.sha256(frozen_copy),
        compiledJarSha256=replay.sha256(jar),bindings=bindings,compileCommand=compile_command,runCommand=command,exitCode=result.returncode)
    (output/'receipt.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n');return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline','candidate-root','output','java'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=run(args.rows,args.baseline,args.candidate_root,args.output,args.java)
    print(json.dumps({'exitCode':result['exitCode'],'independentQualification':False}))

if __name__=='__main__':main()
