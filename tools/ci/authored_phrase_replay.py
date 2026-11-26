"""Observe disclosed author-written phrase inputs through the current controller."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/eval/smart-typing-0.3/pipeline')]
import final_product_replay as harness
import register_authored_phrase_inputs as source
from phrase_replay_review_screen import ensure_disclosed


def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def evaluate(cases, rows):
    if len(cases) != len(rows): raise ValueError('AUTHORED_REPLAY_COUNT')
    total = dict(phrases=len(rows), words=0, changedPhrases=0, boundaryChanges=0,
                 prefixChanges=0, caseOnlyChanges=0, automaticEdits=0, undoChecked=0, undoFailures=0)
    for (name, phrase), row in zip(cases, rows, strict=True):
        words = phrase.split(' '); stages = row.get('phraseStages')
        if row.get('id') != name or row.get('typed') != phrase or row.get('status') != 'COMPLETE' or not isinstance(stages, list) or len(stages) != len(words):
            raise ValueError('AUTHORED_REPLAY_IDENTITY')
        changed_phrase = False
        for i, (word, stage) in enumerate(zip(words, stages, strict=True)):
            before, after = stage.get('before'), stage.get('after')
            if (stage.get('wordIndex') != i or stage.get('typed') != word or not isinstance(before, str) or
                not isinstance(after, str) or not before.endswith(word) or
                (i == 0 and before != word) or (i and before != stages[i-1]['after'] + word)):
                raise ValueError('AUTHORED_REPLAY_SESSION')
            changed = after != before + ' '; prefix = not after.startswith(before[:-len(word)])
            case_only = changed and after.lower() == (before + ' ').lower()
            if (stage.get('changed'), stage.get('prefixChanged'), stage.get('caseOnly')) != (changed, prefix, case_only):
                raise ValueError('AUTHORED_REPLAY_FLAGS')
            total['words'] += 1; total['boundaryChanges'] += changed; total['prefixChanges'] += prefix
            total['caseOnlyChanges'] += case_only; total['automaticEdits'] += stage.get('automaticEdit') is True
            changed_phrase |= changed
            if i == len(words)-1 and stage.get('automaticEdit') is True:
                total['undoChecked'] += 1
                total['undoFailures'] += stage.get('undoResult') != 'HANDLED' or stage.get('undoExact') is not True
        total['changedPhrases'] += changed_phrase
    if total['undoFailures']: raise ValueError('AUTHORED_REPLAY_UNDO')
    return total


def run(java, output):
    java = Path(java).resolve(strict=True); output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('AUTHORED_REPLAY_OUTPUT')
    source.check(); cases = source.phrases(); sources, jars, android = harness.compile_inputs(java)
    assets = sorted(p for p in (harness.ASSETS / 'smarttyping').rglob('*') if p.is_file())
    files = [*sources, *jars, android, java, java.parent.parent / 'release', *assets,
             source.CONTROL, source.LEXICAL, Path(source.__file__), ROOT / 'tools/ci/register_authored_dialogue.py',
             Path(__file__).resolve(), ROOT / 'tools/ci/phrase_replay_review_screen.py',
             Path(harness.__file__).resolve(), harness.SOURCE_MANIFEST,
             *[source.FIXTURE / n for n in (*source.PINS, 'NOTICE.md')]]
    keys = [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}' for i,p in enumerate(files)]
    before = {k:digest(p) for k,p in zip(keys, files, strict=True)}
    output.mkdir(parents=True)
    jar, _ = harness.compile_harness(output, java, sources, jars, android)
    encode = lambda value: base64.b64encode(value.encode()).decode('ascii')
    inputs = output / 'input.tsv'
    inputs.write_text(''.join('\t'.join((str(i), encode(name), 'holdout', 'ru', encode(''), encode(phrase)))+'\n'
                              for i,(name,phrase) in enumerate(cases)))
    cp = os.pathsep.join(map(str, [jar, jars[1], jars[2], android]))
    command = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-Drune.replay.phrase=true',
               '-Drune.replay.phraseUndo=true', '-cp', cp,
               'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',
               str(inputs), str(harness.ASSETS), 'current-product', 'all']
    results = []
    for i in (1,2):
        with (output / f'run-{i}.jsonl').open('xb') as out, (output / f'run-{i}.log').open('xb') as log:
            subprocess.run(command, cwd=ROOT, stdout=out, stderr=log, check=True, timeout=1200)
        results.append((output / f'run-{i}.jsonl').read_bytes())
    if results[0] != results[1]: raise ValueError('AUTHORED_REPLAY_NONDETERMINISTIC')
    observations = [json.loads(line) for line in results[0].splitlines()]
    metrics = evaluate(cases, observations)
    registered, _ = source.inputs()
    ensure_disclosed(observations, registered)
    if before != {k:digest(p) for k,p in zip(keys, files, strict=True)}: raise ValueError('AUTHORED_REPLAY_DRIFT')
    source.check()
    receipt = dict(scope='disclosed-authored-phrase-diagnostic', independentQualification=False,
                   externalModelCalls=0, metrics=metrics, inputSha256=before,
                   resultSha256=hashlib.sha256(results[0]).hexdigest())
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n')
    print(json.dumps(metrics, sort_keys=True))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--java',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.java,args.output)
