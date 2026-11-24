"""Versioned, fail-closed text assessment with Unicode format-character checks.

The v1 implementation remains intact for historical source bindings. This
additional diagnostic never admits a corpus or certifies source identity.
"""
import selector_text_preflight_v1 as previous
import selector_text_format_v1 as text_format


def assess(texts, rows, sources, lexicon, lexical, controls):
    report = previous.assess(texts, rows, sources, lexicon, lexical, controls)
    affected = 0
    for part in previous.PARTS:
        for row in texts[part]:
            affected += text_format.inspect(sources[row['articleId']], row['text'])['formatFragments']
    report['schema'] = 2
    report['textIdentityBlockers']['sourceFormatFragments'] = affected
    if affected and report['status'] == 'BLOCKED_COVERAGE':
        report['status'] = 'BLOCKED_TEXT_IDENTITIES'
    return report
