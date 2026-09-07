#!/usr/bin/env python3
"""Replay calibration, freeze finite policy, then independently replay holdout and named acceptance.

This replays already public holdout with unchanged policy; it is not a new unseen
statistical holdout. Only the finite table receives a named-acceptance qualification.
"""
import argparse
import base64
import json
from pathlib import Path
import sys

import final_product_replay as replay
import select_local_policy
import evaluate_local_holdout


NAMED = {
    'en': [('teh', 'the'), ('recieve', 'receive'), ('adress', 'address')],
    'ru': [('автокрекция', 'автокоррекция'), ('арфография', 'орфография'), ('сообшение', 'сообщение'),
           ('реалбно', 'реально'), ('мододец', 'молодец'), ('шоржусь', 'горжусь')],
    'es': [('mensage', 'mensaje'), ('correcion', 'corrección')],
}


def named_rows():
    rows = []
    for lang, mappings in NAMED.items():
        for typed, expected in mappings:
            for token, target, cohort in [(typed, expected, 'typo'), (expected, expected, 'correct'),
                    ('@' + typed, '@' + typed, 'protected'), (typed + '@example.com', typed + '@example.com', 'protected')]:
                rows.append({'id': f'named-{lang}-{len(rows)}', 'split': 'holdout', 'language': lang,
                    'prefix': '', 'typed': token, 'expectedSpelling': target, 'cohort': cohort,
                    'noAuto': cohort != 'typo'})
    return rows


def run(args):
    root = args.output.resolve()
    replay.require(root.is_relative_to(replay.REPO / 'build') and not root.exists(), 'FRESH_BUILD_OUTPUT')
    root.mkdir(parents=True)
    java = args.java.resolve(strict=True)
    sources, jars, android = replay.compile_inputs(java)
    source_files = sources + [Path(__file__), Path(select_local_policy.__file__),
                             Path(evaluate_local_holdout.__file__), replay.SOURCE_MANIFEST]
    bindings = {str(p.relative_to(replay.REPO)): replay.sha256(p) for p in source_files + replay.asset_paths()}
    bindings[str(java)] = replay.sha256(java)
    for p in jars + [android]: bindings[str(p)] = replay.sha256(p)
    replay.write_json(root / 'artifacts.json', bindings)
    jar, compile_command = replay.compile_harness(root, java, sources, jars, android)
    commands = {'compile': compile_command}

    def observe(rows, name):
        replay.write_jsonl(root / f'{name}-rows.jsonl', rows)
        def b64(value): return base64.b64encode(value.encode()).decode()
        inputs = root / f'{name}-inputs.tsv'
        inputs.write_text(''.join('\t'.join([str(i), b64(r['id']), r['split'], r['language'],
            b64(r.get('prefix', '')), b64(r['typed'])]) + '\n' for i, r in enumerate(rows)))
        out = root / f'{name}-observations.jsonl'
        commands[name] = replay.run_harness(root, java, jars, android, jar, inputs, out, 'unavailable')
        return replay.read_jsonl(out)

    # Selection reads only calibration labels. Holdout labels are loaded after config is written.
    manifest = json.loads((replay.CORPUS / 'manifest.json').read_text())
    def corpus(split):
        rows = []
        for name, sha in manifest['files'].items():
            path = replay.CORPUS / name
            replay.require(replay.sha256(path) == sha, 'CORPUS_DRIFT')
            rows += [r for r in replay.read_jsonl(path) if r.get('task') == 'spelling' and r['split'] == split]
        return rows

    calibration = corpus('calibration')
    observed = observe(calibration, 'calibration')
    config = select_local_policy.select(calibration, observed, bindings)
    replay.write_json(root / 'selected-policy.json', config)
    holdout = corpus('holdout')
    observed = observe(holdout, 'holdout')
    report = evaluate_local_holdout.evaluate(config, holdout, observed, bindings)
    named = named_rows()
    observed_named = observe(named, 'named')
    named_report = evaluate_local_holdout.evaluate(config, named, observed_named, bindings)
    for row, observation in zip(named, observed_named, strict=True):
        if row['cohort'] == 'typo':
            replay.require(observation['fullTokenGeneration']['protectedReason'] is None and
                row['expectedSpelling'] in [c['text'] for c in observation['fullTokenGeneration']['alternatives']] and
                observation['boundaryChangedBeyondInsertedSpace'], 'NAMED_TARGET_AND_REPLACEMENT')
    named_report['allLanguagesPass'] = all(v['pass'] for v in named_report['languages'].values())
    replay.require(named_report['allLanguagesPass'], 'NAMED_ACCEPTANCE_FAILED')
    for key, sha in bindings.items():
        replay.require(replay.sha256(Path(key) if Path(key).is_absolute() else replay.REPO / key) == sha, 'SOURCE_DRIFT')
    replay.write_json(root / 'holdout-report.json', report)
    replay.write_json(root / 'named-report.json', named_report)
    replay.write_json(root / 'receipt.json', {'scope': 'finite-common-confusion-qualification',
        'generalLocalEnabled': False, 'newUnseenHoldout': False, 'thresholdsFittedOnHoldout': False,
        'files': {p.name: replay.sha256(p) for p in root.iterdir() if p.is_file()},
        'corpusManifestSha256': replay.sha256(replay.CORPUS / 'manifest.json'), 'commands': commands})
    print(json.dumps({'holdout': report, 'named': named_report}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
