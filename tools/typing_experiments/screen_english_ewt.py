#!/usr/bin/env python3
"""Aggregate-only exploration of the disclosed EWT training partition; never qualify a rule."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

TRAIN_SHA = 'd68e06122a702464c613076523d56740f047e5bbe89dd90ec32737e04d952143'
TOKEN = re.compile(r'(?<!\w)[Ii](?!\w)', re.UNICODE)


def screen(data):
    text = data.decode('utf-8')
    counts = Counter()
    ids = set()
    in_sentence = False
    for line in text.splitlines():
        if line.startswith('# sent_id = '):
            ident = line.removeprefix('# sent_id = ')
            if not ident or ident in ids: raise ValueError('EWT_SENTENCE_ID')
            ids.add(ident); counts['sentences'] += 1; in_sentence = True
        elif line.startswith('# newdoc id = '):
            counts['documents'] += 1
        elif line.startswith('# text = '):
            if not in_sentence: raise ValueError('EWT_TEXT_WITHOUT_SENTENCE')
            value = line.removeprefix('# text = ')
            for match in TOKEN.finditer(value):
                letter = 'upper' if match.group() == 'I' else 'lower'
                offset = match.end()
                nxt = value[offset:offset + 1]
                prev = value[match.start() - 1:match.start()] if match.start() else ''
                following = ('space' if nxt.isspace() else 'period' if nxt == '.' else
                    'apostrophe' if nxt in ("'", '’') else 'other_proposed' if nxt in ',!?;:' else
                    'end' if not nxt else 'other')
                counts[letter + '_' + following] += 1
                if prev in ("'", '’'):
                    counts[letter + '_preceded_apostrophe'] += 1
        elif line and not line.startswith('#'):
            fields = line.split('\t')
            if len(fields) != 10: raise ValueError('EWT_TOKEN_SHAPE')
            if fields[0].isdigit() and fields[1] in ('I', 'i'):
                counts['annotated_' + ('upper_' if fields[1] == 'I' else 'lower_') + fields[3]] += 1
        elif not line:
            in_sentence = False
    if not ids: raise ValueError('EWT_EMPTY')
    return {'purpose': 'aggregate_discovery_not_qualification', 'counts': dict(sorted(counts.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.train.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != TRAIN_SHA: raise ValueError('EWT_TRAIN_SHA')
    result = screen(data); result['sourceSha256'] = digest
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
