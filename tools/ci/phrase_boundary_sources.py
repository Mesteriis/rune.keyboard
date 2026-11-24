"""Attribute disclosed phrase boundary edits using metadata-only diagnostics."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

import phrase_replay_review_screen as screen


def summarize(cases, observations):
    if len(cases) != len(observations):
        raise ValueError('BOUNDARY_SOURCE_COUNT')
    sources = Counter()
    for (case, _), row in zip(cases, observations, strict=True):
        if row.get('id') != case['id']:
            raise ValueError('BOUNDARY_SOURCE_IDENTITY')
        for stage in row['phraseStages']:
            events = stage.get('boundaryDiagnostics')
            if not isinstance(events, list):
                raise ValueError('BOUNDARY_SOURCE_MISSING')
            applied = [e for e in events if e.get('reason') == 'AUTO_REPLACE']
            if stage['automaticEdit']:
                if len(applied) != 1 or not isinstance(applied[0].get('source'), str) or applied[0]['source'] in ('', 'NONE'):
                    raise ValueError('BOUNDARY_SOURCE_APPLICATION')
                if stage is row['phraseStages'][-1] and case['label'] == 'preserve':
                    sources[applied[0]['source']] += 1
            elif applied:
                raise ValueError('BOUNDARY_SOURCE_STALE_APPLICATION')
    return dict(sorted(sources.items()))


def run(java, output):
    previous = os.environ.get('JAVA_TOOL_OPTIONS')
    if previous and 'rune.replay.boundaryDiagnostics' in previous:
        raise ValueError('BOUNDARY_SOURCE_OPTION_CONFLICT')
    os.environ['JAVA_TOOL_OPTIONS'] = ((previous or '') + ' -Drune.replay.boundaryDiagnostics=true').strip()
    try:
        screen.run(java, output)
    finally:
        if previous is None:
            os.environ.pop('JAVA_TOOL_OPTIONS', None)
        else:
            os.environ['JAVA_TOOL_OPTIONS'] = previous
    output = Path(output)
    raw = (output / 'run-1.jsonl').read_bytes()
    counts = summarize(screen.inputs(), [json.loads(line) for line in raw.splitlines()])
    receipt = {'scope': 'disclosed-posthoc-preservation-controls', 'independentQualification': False,
               'sources': counts, 'resultSha256': hashlib.sha256(raw).hexdigest(),
               'analyzerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output / 'boundary-sources.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.output)
