"""Run disclosed Russian multiword regression through one real controller session."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/eval/smart-typing-0.3/pipeline'))
import final_product_replay as harness

# Previously disclosed public regression examples, not independent quality labels.
CASES = (
    ('infinitive-following', 'тебе надо научищься этому', 'тебе надо научиться этому ', False),
    ('noun-following', 'том показал мне фотографие вчера', 'том показал мне фотографию вчера ', False),
    ('infinitive-undo', 'тебе надо научищься', 'тебе надо научиться ', True),
    ('noun-undo', 'том показал мне фотографие', 'том показал мне фотографию ', True),
    ('valid-verb', 'ты уже злишься сегодня', 'ты уже злишься сегодня ', False),
    ('valid-phrase', 'это новая книга', 'это новая книга ', False),
)


def validate(rows):
    if len(rows) != len(CASES): raise ValueError('PHRASE_ROW_COUNT')
    total = dict(prefixChanges=0, caseOnlyChanges=0, boundaryChanges=0, automaticChanges=0, undoChecked=0, undoFailures=0)
    for row, (name, typed, expected, undo) in zip(rows, CASES, strict=True):
        stages = row.get('phraseStages')
        if row.get('status') != 'COMPLETE' or row.get('id') != name or row.get('typed') != typed or not isinstance(stages, list):
            raise ValueError('PHRASE_ROW_IDENTITY')
        words = typed.split(' ')
        if len(stages) != len(words) or any(s.get('wordIndex') != i or s.get('typed') != w for i, (s, w) in enumerate(zip(stages, words, strict=True))):
            raise ValueError('PHRASE_STAGE_IDENTITY')
        if stages[-1].get('after') != expected: raise ValueError('PHRASE_OUTPUT_MISMATCH:' + name)
        if name.startswith('infinitive-') and not any(s.get('grammarRevisionAttempted') is True for s in stages):
            raise ValueError('PHRASE_GRAMMAR_NOT_EXERCISED')
        if name.startswith('noun-') and not any(s.get('nounCaseAttempted') is True for s in stages):
            raise ValueError('PHRASE_NOUN_NOT_EXERCISED')
        for i, stage in enumerate(stages):
            if i and stage.get('before') != stages[i-1].get('after') + words[i]: raise ValueError('PHRASE_SESSION_DIVERGENCE')
            before, after = stage.get('before'), stage.get('after')
            if not isinstance(before, str) or not isinstance(after, str) or not before.endswith(words[i]): raise ValueError('PHRASE_TEXT_SCHEMA')
            if i == 0 and before != words[i]: raise ValueError('PHRASE_SESSION_DIVERGENCE')
            changed = after != before + ' '
            prefix_changed = not after.startswith(before[:-len(words[i])])
            case_only = changed and after.casefold() == (before + ' ').casefold()
            if (stage.get('changed'), stage.get('prefixChanged'), stage.get('caseOnly')) != (changed, prefix_changed, case_only):
                raise ValueError('PHRASE_OBSERVATION_MISMATCH')
            total['prefixChanges'] += prefix_changed; total['caseOnlyChanges'] += case_only
            total['boundaryChanges'] += changed
            total['automaticChanges'] += stage.get('automaticEdit') is True
        if undo:
            if stages[-1].get('automaticEdit') is not True or stages[-1].get('undoResult') != 'HANDLED': raise ValueError('PHRASE_UNDO_NOT_EXERCISED')
            total['undoChecked'] += 1; total['undoFailures'] += stages[-1].get('undoExact') is not True
    if total['prefixChanges'] or total['undoFailures'] or total['undoChecked'] != 2: raise ValueError('PHRASE_INVARIANT_FAILURE')
    return total


def run(output, java):
    output=Path(output).resolve(); java=Path(java).resolve(strict=True)
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_PHRASE_OUTPUT_REQUIRED')
    from register_phrase_replay import CONTROL, LEXICAL, check
    check()
    sources,jars,android=harness.compile_inputs(java)
    assets=sorted(p for p in (harness.ASSETS / 'smarttyping').rglob('*') if p.is_file())
    files=[*sources,*jars,android,java,java.parent.parent/'release',*assets,CONTROL,LEXICAL,ROOT/'tools/ci/register_phrase_replay.py',
           Path(__file__).resolve(),Path(harness.__file__).resolve(),harness.SOURCE_MANIFEST]
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    before={(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}'):digest(p)
            for i,p in enumerate(files)}
    check()
    output.mkdir(parents=True)
    jar,_=harness.compile_harness(output,java,sources,jars,android)
    encode=lambda text:base64.b64encode(text.encode()).decode('ascii')
    inputs=output/'input.tsv';inputs.write_text(''.join('\t'.join((str(i),encode(name),'holdout','ru',encode(''),encode(typed)))+'\n' for i,(name,typed,_,_) in enumerate(CASES)))
    classpath=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]))
    command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-Drune.replay.phrase=true','-Drune.replay.phraseUndo=true',
             '-cp',classpath,'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',
             str(inputs),str(harness.ASSETS),'current-product','all']
    raw=[]
    for number in (1,2):
        with (output/f'run-{number}.jsonl').open('xb') as out,(output/f'run-{number}.log').open('xb') as log:
            subprocess.run(command,cwd=ROOT,stdout=out,stderr=log,timeout=1200,check=True)
        raw.append((output/f'run-{number}.jsonl').read_bytes())
    if raw[0]!=raw[1]:raise ValueError('PHRASE_NOT_DETERMINISTIC')
    rows=[json.loads(line) for line in raw[0].splitlines()]
    metrics=validate(rows)
    after={(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}'):digest(p)
           for i,p in enumerate(files)}
    if before!=after:raise ValueError('PHRASE_INPUT_DRIFT')
    check()
    receipt={'scope':'disclosed-russian-multiword-controller-regression','independentQualification':False,
             'rows':len(rows),'metrics':metrics,'resultSha256':hashlib.sha256(raw[0]).hexdigest(),
             'sourceSha256':digest(harness.HARNESS),'fixtureSha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),
             'inputSha256':before,'externalModelCalls':0}
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--java',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.output,args.java)
