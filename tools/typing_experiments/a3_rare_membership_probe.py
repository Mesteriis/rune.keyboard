#!/usr/bin/env python3
"""Measure dictionary membership of disclosed rare keys; no name labels."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import a3_case_sidecar_audit as audit
import build_chat_rare_candidate as packed
import pack_rare_word_lexicon as packer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/eval/smart-typing-0.3/pipeline'))
import final_product_replay as harness


def inputs(rare, lowercase):
    return sorted({w for w in rare if re.fullmatch('[а-яё]{3,4}', w)} - set(lowercase))


def run(sidecar, java, output):
    sidecar = sidecar.resolve(strict=True); java = java.resolve(strict=True); root = output.resolve()
    if root.exists() or not root.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')):
        raise ValueError('UNDECLARED_JAVA_OPTIONS')
    sidefile = sidecar / 'words.tsv'; side_receipt = sidecar / 'receipt.json'
    meta = json.loads(side_receipt.read_text())
    if (meta.get('purpose') != 'disclosed_lowercase_source_screen_not_qualification' or
            meta.get('wordsSha256') != packer.sha256(sidefile) or
            meta.get('extractorSha256') != packer.sha256(ROOT / 'tools/typing_experiments/a3_lowercase_sidecar.py') or
            packer.sha256(audit.RARE) != audit.RARE_SHA): raise ValueError('A3_SOURCE_IDENTITY')
    words = inputs(packed.unpack(audit.RARE), (line.split('\t')[0] for line in sidefile.read_text().splitlines()))
    if not words: raise ValueError('A3_EMPTY')
    sources, jars, android = harness.compile_inputs(java)
    probe = ROOT / 'tools/typing_experiments/A3RareMembershipProbe.kt'
    assets = sorted(p for p in harness.ASSETS.rglob('*') if p.is_file())
    paths = list(dict.fromkeys([*sources, *jars, android, java, *assets, probe, Path(__file__),
                               Path(packed.__file__), Path(audit.__file__), sidefile, side_receipt]))
    before = {harness.path_key(p): harness.sha256(p) for p in paths}
    root.mkdir(parents=True, mode=0o700)
    wordfile = root / 'words.txt'; wordfile.write_text(''.join(w + '\n' for w in words))
    jar, _ = harness.compile_harness(root, java, [*sources, probe], jars, android)
    cp = os.pathsep.join(map(str, (jar, jars[1], jars[2], android)))
    command = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-cp', cp,
               'io.github.mesteriis.rune.keyboard.smarttyping.session.A3RareMembershipProbe',
               str(harness.ASSETS), str(wordfile)]
    with (root / 'probe.log').open('x') as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    if before != {harness.path_key(p): harness.sha256(p) for p in paths}: raise ValueError('A3_INPUT_DRIFT')
    summary = {'purpose': 'disclosed_rare_membership_not_name_qualification', 'inputs': len(words),
               'inputSha256': harness.sha256(wordfile), 'jarSha256': harness.sha256(jar),
               'result': (root / 'probe.log').read_text().strip(), 'exitCode': completed.returncode,
               'bindings': before}
    (root / 'receipt.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
    print(summary['result'])


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sidecar', 'java', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(); run(args.sidecar, args.java, args.output)
