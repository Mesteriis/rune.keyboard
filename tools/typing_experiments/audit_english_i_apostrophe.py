"""Verify the disclosed, manually reviewed apostrophe cohort against its source."""
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path

import screen_english_i_source as source

REVIEW = Path(__file__).with_name('english_i_apostrophe_review.json')
PURPOSE = 'disclosed agent-reviewed examples; not independent qualification'


def audit(data, review):
    if hashlib.sha256(data).hexdigest() != source.SHA256:
        raise ValueError('EN_I_SOURCE_DIGEST')
    if (not isinstance(review, dict) or set(review) != {'schema', 'sourceSha256', 'purpose', 'rows'} or
            type(review['schema']) is not int or review['schema'] != 1 or
            review['sourceSha256'] != source.SHA256 or review['purpose'] != PURPOSE or
            not isinstance(review['rows'], list) or not review['rows']):
        raise ValueError('EN_I_REVIEW_SCHEMA')
    labels = {}
    for row in review['rows']:
        if (not isinstance(row, dict) or set(row) != {'id', 'offset', 'label'} or
                not isinstance(row['id'], str) or not row['id'].isascii() or not row['id'].isdecimal() or
                type(row['offset']) is not int or row['offset'] < 0 or
                row['label'] not in ('opening_quote_pronoun', 'internal_apostrophe_preserve')):
            raise ValueError('EN_I_REVIEW_ROW')
        key = (str(int(row['id'])), row['offset'])
        if key in labels:
            raise ValueError('EN_I_REVIEW_DUPLICATE')
        labels[key] = row['label']
    seen = set()
    counts = Counter()
    for line in bz2.decompress(data).decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) != 4 or fields[1] != 'eng':
            raise ValueError('EN_I_SOURCE_ROW')
        text = fields[2]
        for match in source.TOKEN.finditer(text):
            offset = match.start()
            if offset == 0 or text[offset - 1] not in "'’":
                continue
            key = (str(int(fields[0])), offset)
            if key in seen or key not in labels:
                raise ValueError('EN_I_REVIEW_COVERAGE')
            seen.add(key)
            label = labels[key]
            if label == 'opening_quote_pronoun':
                if match.group() != 'I' or (offset > 1 and not text[offset - 2].isspace()):
                    raise ValueError('EN_I_REVIEW_CONTEXT')
            elif match.group() != 'i' or offset < 2 or not text[offset - 2].isalpha():
                raise ValueError('EN_I_REVIEW_CONTEXT')
            counts[label] += 1
            counts[label + '_' + source.category(text, match.end())] += 1
    if seen != set(labels):
        raise ValueError('EN_I_REVIEW_COVERAGE')
    return dict(sorted(counts.items()))


if __name__ == '__main__':
    print(json.dumps(audit(source.SOURCE.read_bytes(), json.loads(REVIEW.read_text())), sort_keys=True, indent=2))
