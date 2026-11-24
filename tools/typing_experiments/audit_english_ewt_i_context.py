#!/usr/bin/env python3
"""Aggregate aligned EWT training examples; no source text or labels enter product."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from screen_english_ewt import TOKEN, TRAIN_SHA

PREVIOUS_WORD = re.compile(r'([^\W\d_]+)\s+$', re.UNICODE)


def audit(data):
    counts = Counter(); contexts = defaultdict(set)
    for block in data.decode('utf-8').strip().split('\n\n'):
        lines = block.splitlines()
        texts = [line.removeprefix('# text = ') for line in lines if line.startswith('# text = ')]
        if len(texts) != 1: raise ValueError('EWT_TEXT_COUNT')
        text = texts[0]
        matches = list(TOKEN.finditer(text))
        if not matches: continue
        marked = []
        for line in lines:
            if not line or line.startswith('#'): continue
            fields = line.split('\t')
            if len(fields) != 10: raise ValueError('EWT_TOKEN_SHAPE')
            if fields[0].isdigit() and fields[1] in ('I', 'i'):
                marked.append((fields[1], fields[3]))
        if [m.group() for m in matches] != [word for word, _ in marked]:
            counts['sentences_unaligned'] += 1
            counts['occurrences_unaligned'] += len(matches)
            continue
        counts['sentences_aligned'] += 1
        for match, (_, pos) in zip(matches, marked, strict=True):
            before, after = text[:match.start()], text[match.end():]
            previous = PREVIOUS_WORD.search(before)
            next_char = after[:1]
            boundary = ('space' if next_char.isspace() else 'period' if next_char == '.' else
                        'other_proposed' if next_char and next_char in ',!?;:' else 'apostrophe' if next_char in ("'", '’') else
                        'end' if not next_char else 'other')
            kind = 'pronoun' if pos == 'PRON' else 'other_pos'
            case = 'upper' if match.group() == 'I' else 'lower'
            previous_kind = 'word' if previous else 'other_or_start'
            counts[f'{case}_{kind}_{boundary}_{previous_kind}'] += 1
            # A one-word preceding context cannot distinguish opposite annotated classes.
            if previous and boundary in ('space', 'other_proposed'):
                contexts[previous.group(1).casefold()].add(kind)
    counts['previous_word_collision_types'] = sum(len(labels) > 1 for labels in contexts.values())
    return {'purpose': 'development_context_audit_not_qualification', 'counts': dict(sorted(counts.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); data = args.train.read_bytes()
    if hashlib.sha256(data).hexdigest() != TRAIN_SHA: raise ValueError('EWT_TRAIN_SHA')
    result = audit(data); result['sourceSha256'] = TRAIN_SHA
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
