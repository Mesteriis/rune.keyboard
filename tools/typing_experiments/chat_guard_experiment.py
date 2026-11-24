#!/usr/bin/env python3
"""Measure a disclosed in-memory rare-word overlay; never package or qualify it."""
import argparse
import base64
from collections import Counter
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import re

from replay_joint_correction import replay,controller_records

ROOT=Path(__file__).resolve().parents[2]
MARKER='''        val rareWords = if (packagedReaders) PackedRareWordLexicon.openPackaged(
            mapping(rareFile), FrozenRareWordLexicon.ASSET_BYTES) else validatedRareWords
'''


def overlay(source,words):
    if not words or words!=sorted(set(words)) or any(not re.fullmatch('[а-яё]{3,32}',word) for word in words):
        raise ValueError('CHAT_OVERLAY_WORDS')
    if source.count(MARKER)!=1:raise ValueError('CHAT_OVERLAY_SOURCE')
    literal=', '.join('"'+word+'"' for word in words)
    replacement=MARKER.replace('val rareWords =','val baseRareWords =',1)+f'''        val reviewedWords = setOf({literal})
        val rareWords = RareWordLexicon {{ key ->
            if (key in reviewedWords) RareWordMembership(true, true, 1000000)
            else baseRareWords.lookup(key)
        }}
'''
    return source.replace(MARKER,replacement)


def summarize(rows,baseline_path,experimental_path,review):
    selected={item['id'] for item in review['cases'] if item['label']=='preserve'};found=set();counts=Counter()
    with baseline_path.open(encoding='utf-8') as old,experimental_path.open(encoding='utf-8') as new:
        for index,(row,left,right) in enumerate(zip_longest(rows,old,new)):
            if row is None or left is None or right is None:raise ValueError('CHAT_OVERLAY_ROW_COUNT')
            a=json.loads(left);b=json.loads(right)
            if (a.get('id')!=row['id'] or b.get('id')!=f'joint-replay-{index:08d}' or b.get('index')!=index
                    or a.get('status')!='COMPLETE' or b.get('status')!='COMPLETE'
                    or any(a.get(k)!=row[k] or b.get(k)!=row[k] for k in ('split','language','prefix','typed'))):
                raise ValueError('CHAT_OVERLAY_ROW_IDENTITY')
            before=a['beforeBoundary']['text'];after_a=a['afterBoundary']['text'];after_b=b['afterBoundary']['text']
            if before!=b['beforeBoundary']['text'] or not before.casefold().endswith(row['typed'].casefold()):raise ValueError('CHAT_OVERLAY_INPUT')
            for observation,after in ((a,after_a),(b,after_b)):
                if not after.endswith(' ') or type(observation.get('boundaryChangedBeyondInsertedSpace')) is not bool or observation['boundaryChangedBeyondInsertedSpace']!=(after!=before+' '):raise ValueError('CHAT_OVERLAY_EDITOR')
            prefix=before[:-len(row['typed'])];expected=(prefix+row['expectedSpelling']+' ').casefold()
            if after_a!=after_b:counts['changedOutputRows']+=1;counts['changed_'+row['cohort']]+=1
            if row['cohort']=='typo':
                old_ok=after_a.casefold()==expected;new_ok=after_b.casefold()==expected
                counts['typoGain']+=not old_ok and new_ok;counts['typoLoss']+=old_ok and not new_ok
            if row['cohort']=='correct':
                counts['baselineControlChanges']+=after_a!=before+' ';counts['overlayControlChanges']+=after_b!=before+' '
            if b['boundaryChangedBeyondInsertedSpace'] and b.get('restoredBeforeBoundaryExactly') is not True:counts['overlayUndoFailures']+=1
            if row['id'] in selected:
                found.add(row['id']);counts['reviewedRows']+=1;counts['reviewedPreserved']+=after_b.casefold()==(before+' ').casefold()
            counts['rows']+=1
    if found!=selected:raise ValueError('CHAT_OVERLAY_REVIEW_MISSING')
    return dict(sorted(counts.items()))


def run(rows_path,baseline_receipt,baseline_observations,review_path,output,java):
    rows_path,baseline_receipt,baseline_observations,review_path,output,java=map(lambda p:Path(p).resolve(),
        (rows_path,baseline_receipt,baseline_observations,review_path,output,java))
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('CHAT_OVERLAY_OUTPUT')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):raise ValueError('CHAT_OVERLAY_JAVA_OPTIONS')
    baseline=json.loads(baseline_receipt.read_text());review=json.loads(review_path.read_text())
    if (baseline.get('status')!='COMPLETE' or baseline.get('exitCode')!=0 or baseline.get('mode')!='current-product'
            or baseline.get('rowsSha256')!=replay.sha256(rows_path) or baseline.get('observationsSha256')!=replay.sha256(baseline_observations)
            or review.get('purpose')!='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION'):
        raise ValueError('CHAT_OVERLAY_BASELINE')
    replay.verify_bound_files(baseline)
    rows=replay.read_jsonl(rows_path);controller=controller_records(rows)
    words=sorted({item['typed'] for item in review['cases'] if item['label']=='preserve'})
    sources,jars,android=replay.compile_inputs(java)
    paths=list(dict.fromkeys([*sources,*jars,android,java,*sorted(p for p in replay.ASSETS.rglob('*') if p.is_file()),
        rows_path,baseline_receipt,baseline_observations,review_path,Path(__file__),Path(replay.__file__)]))
    bindings={replay.path_key(p):replay.sha256(p) for p in paths}
    source=replay.HARNESS.read_text();modified=overlay(source,words)
    output.mkdir(parents=True,mode=0o700);harness=output/'FinalProductSpellingReplay.kt';harness.write_text(modified)
    enc=lambda s:base64.b64encode(s.encode()).decode('ascii')
    with (output/'inputs.tsv').open('x',encoding='ascii') as stream:
        for index,row in enumerate(controller):
            stream.write('\t'.join([str(index),enc(row['id']),row['split'],row['language'],enc(row['prefix']),enc(row['typed'])])+'\n')
    jar,compile_command=replay.compile_harness(output,java,[harness if p==replay.HARNESS else p for p in sources],jars,android)
    observed=output/'overlay-observations.jsonl'
    run_command=replay.run_harness(output,java,jars,android,jar,output/'inputs.tsv',observed,'current-product')
    counts=summarize(rows,baseline_observations,observed,review)
    replay.verify_bound_files({'files':bindings});replay.verify_bound_files(baseline)
    receipt=dict(purpose='POSTHOC_RARE_WORD_OVERLAY_NOT_QUALIFICATION',independentQualification=False,
        counts=counts,reviewedWords=len(words),rowsSha256=replay.sha256(rows_path),baselineObservationsSha256=replay.sha256(baseline_observations),
        overlayObservationsSha256=replay.sha256(observed),overlayHarnessSha256=replay.sha256(harness),compiledHarnessSha256=replay.sha256(jar),
        reviewSha256=replay.sha256(review_path),bindings=bindings,compileCommand=compile_command,runCommand=run_command,
        caveat='Synthetic rank-1000000 in-memory overlay, chosen after observing these cases. Not a packaged lexicon or independent qualification.')
    (output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline-receipt','baseline-observations','review','output','java'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=run(args.rows,args.baseline_receipt,args.baseline_observations,args.review,args.output,args.java)
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
