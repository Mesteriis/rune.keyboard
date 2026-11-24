"""Fail-closed diagnostic for Unicode dash boundaries; never admits data."""
import unicodedata

import selector_text_preflight_v2 as previous

# Expose the unchanged source normalizer for the source-bound wrapper.
text_format = previous.text_format


def assess(texts, rows, sources, lexicon, lexical, controls):
    report = previous.assess(texts, rows, sources, lexicon, lexical, controls)
    affected = 0
    for part in previous.previous.PARTS:
        for row in texts[part]:
            source = unicodedata.normalize('NFC', sources[row['articleId']])
            fragment = row['text']
            # The prior assessment verifies that the fragment maps to this source.
            words = list(text_format.WORD.finditer(source))
            for ordinal, _ in enumerate(text_format.WORD.finditer(fragment)):
                match = words[ordinal]
                left = source[match.start()-1:match.start()] if match.start() else ''
                right = source[match.end():match.end()+1]
                if any(char and unicodedata.category(char) == 'Pd' for char in (left, right)):
                    affected += 1
    report['schema'] = 3
    report['textIdentityBlockers']['sourceDashFragments'] = affected
    if affected and report['status'] == 'BLOCKED_COVERAGE':
        report['status'] = 'BLOCKED_TEXT_IDENTITIES'
    return report
