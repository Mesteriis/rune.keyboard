"""Replay disclosed Tatoeba phrases as full controller sessions, not qualification."""
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
import register_tatoeba_phrase_inputs as source
from authored_phrase_replay import evaluate
import control_ledger as control
import holdout_ledger as lexical


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(java, output):
    java = Path(java).resolve(strict=True); output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('TATOEBA_REPLAY_OUTPUT')
    a = control.load(source.CONTROL); b = lexical.load_ledger(source.LEXICAL)
    first, second = source.entries(b)
    if ([e for e in a['entries'] if e['id'] == source.ENTRY] != [first] or
            [e for e in b['entries'] if e['id'] == source.ENTRY + '-contexts'] != [second]):
        raise ValueError('TATOEBA_REPLAY_INPUT_REGISTRATION')
    cases = source.cases(b); sources, jars, android = harness.compile_inputs(java)
    assets = sorted(p for p in (harness.ASSETS / 'smarttyping').rglob('*') if p.is_file())
    registered_files = [ROOT / path for path in first['bindings']]
    files = [*sources, *jars, android, java, java.parent.parent / 'release', *assets,
             source.CONTROL, source.LEXICAL, *registered_files, Path(__file__).resolve(),
             ROOT / 'tools/ci/authored_phrase_replay.py', Path(harness.__file__).resolve(), harness.SOURCE_MANIFEST]
    keys = [str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}' for i, p in enumerate(files)]
    before = {k: digest(p) for k, p in zip(keys, files, strict=True)}
    if len(before) != len(files):
        raise ValueError('TATOEBA_REPLAY_DUPLICATE_BINDING')
    output.mkdir(parents=True, mode=0o700)
    jar, _ = harness.compile_harness(output, java, sources, jars, android)
    enc = lambda text: base64.b64encode(text.encode()).decode('ascii')
    inputs = output / 'input.tsv'
    inputs.write_text(''.join('\t'.join((str(i), enc(name), 'holdout', 'ru', enc(''), enc(phrase))) + '\n'
                              for i, (name, phrase) in enumerate(cases)))
    cp = os.pathsep.join(map(str, [jar, jars[1], jars[2], android]))
    command = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-Drune.replay.phrase=true',
               '-Drune.replay.phraseUndo=true', '-cp', cp,
               'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',
               str(inputs), str(harness.ASSETS), 'current-product', 'all']
    for number in (1, 2):
        print('TATOEBA_REPLAY_START', number, flush=True)
        with (output / f'run-{number}.jsonl').open('xb') as out, (output / f'run-{number}.log').open('xb') as log:
            subprocess.run(command, cwd=ROOT, stdout=out, stderr=log, check=True, timeout=3600)
        print('TATOEBA_REPLAY_END', number, flush=True)
    raw = (output / 'run-1.jsonl').read_bytes()
    if raw != (output / 'run-2.jsonl').read_bytes():
        raise ValueError('TATOEBA_REPLAY_NONDETERMINISTIC')
    observations = [json.loads(line) for line in raw.splitlines()]
    metrics = evaluate(cases, observations)
    if before != {k: digest(p) for k, p in zip(keys, files, strict=True)}:
        raise ValueError('TATOEBA_REPLAY_DRIFT')
    receipt = dict(schema=1, scope='disclosed-tatoeba-full-session-diagnostic',
                   independentQualification=False, sourceLabelsQualified=False, externalModelCalls=0,
                   observedContextsRegistered=False, metrics=metrics, inputSha256=before,
                   inputTsvSha256=digest(inputs), resultSha256=hashlib.sha256(raw).hexdigest())
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(metrics, sort_keys=True), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--java', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); run(args.java, args.output)
