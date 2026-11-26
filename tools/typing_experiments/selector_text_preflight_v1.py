"""Fail-closed text-exposure assessment; this module never admits a corpus.

The caller must separately authenticate immutable source and proposal bytes.
Historical selectors and their bound helpers are intentionally unchanged.
"""
from collections import Counter
import unicodedata

import control_ledger as control
from audit_selector_text_exposure import PARTS, WORD, audit
from independent_corpus_guard import selector_segments
from public_corpus_preparation_v1 import preflight as word_preflight


def _joins(char):
    return bool(char) and (char.isalnum() or char == '_' or char in '-‐‑–' or
                           unicodedata.category(char).startswith('M'))


def source_fragment(source, start, end):
    """Conservatively reject token parts, including internally joined apostrophes."""
    left, right = source[start-1:start] if start else '', source[end:end+1]
    if _joins(left) or _joins(right):
        return True
    apostrophes = "'’ʼ"
    return ((left in apostrophes and bool(left) and start >= 2 and _joins(source[start-2:start-1])) or
            (right in apostrophes and bool(right) and _joins(source[end+1:end+2])))


def assess(texts, rows, sources, lexicon, lexical, controls):
    """Check disclosed identities in actual emitted text, retaining all blockers.

    This assesses a supplied in-memory snapshot. It is not proof of source
    authenticity, label quality, completeness, or permission to publish.
    """
    if not isinstance(texts, dict) or set(texts) != set(PARTS):
        raise ValueError('TEXT_PREFLIGHT_PARTITIONS')
    if any(not isinstance(texts[part], list) or not texts[part] for part in PARTS):
        raise ValueError('TEXT_PREFLIGHT_EMPTY_PARTITION')
    ids = []
    for part in PARTS:
        for row in texts[part]:
            if (not isinstance(row, dict) or set(row) != {'articleId', 'text'} or
                    not isinstance(row['articleId'], str) or not row['articleId'].isascii() or
                    not row['articleId'].isdecimal()):
                raise ValueError('TEXT_PREFLIGHT_RECORD')
            ids.append(row['articleId'])
    if len(ids) != len(set(ids)):
        raise ValueError('TEXT_PREFLIGHT_DUPLICATE_ARTICLE')
    # Existing audit validates source/fragment correspondence and both ledgers.
    report = audit(texts, rows, sources, lexicon, lexical, controls)
    word_rows = [row for part in PARTS for row in rows[part]]
    word_check = word_preflight(word_rows, 'spelling', lexical, controls, 'new-families') if word_rows else None
    additional = {kind: set() for kind in ('protected', 'punctuation')}
    fragments = Counter()
    for part in PARTS:
        for row in texts[part]:
            source = unicodedata.normalize('NFC', sources[row['articleId']] or '')
            fragment = row['text']
            words = list(WORD.finditer(source))
            clean = list(WORD.finditer(fragment))
            source_clean = ' '.join(WORD.findall(source.lower()))
            if [m.group().lower() for m in words] != WORD.findall(source.lower()):
                # The underlying audit also reports this; do not guess offsets.
                continue
            segments = list(selector_segments(source))
            segment_index = 0
            for ordinal, match in enumerate(clean):
                if (match.end() == len(fragment) and len(fragment) < len(source_clean)
                        and source_clean[len(fragment)].isalpha()):
                    continue
                if ordinal >= len(words):
                    raise ValueError('TEXT_PREFLIGHT_SOURCE_MAPPING')
                original = words[ordinal]
                if original.group().lower() != match.group():
                    raise ValueError('TEXT_PREFLIGHT_SOURCE_MAPPING')
                if source_fragment(source, original.start(), original.end()):
                    fragments['sourceTokenFragments'] += 1
                while segment_index + 1 < len(segments) and segments[segment_index+1][1] <= original.start():
                    segment_index += 1
                segment, start = segments[segment_index]
                offset = original.start() - start
                if offset < 0 or segment[offset:offset+len(original.group())] != original.group():
                    raise ValueError('TEXT_PREFLIGHT_SEGMENT_MAPPING')
                contexts = ((fragment[max(0, match.start()-128):match.start()].lstrip(), match.group()),
                            (segment[max(0, offset-128):offset].lstrip(), original.group()))
                for prefix, target in contexts:
                    # Empty contexts cannot be punctuation/protected keys in this schema.
                    if not prefix:
                        continue
                    additional['protected'].add(control.key_for(dict(language='ru',prefix=prefix,typed=target),'protected'))
                    additional['punctuation'].add(control.key_for(dict(language='ru',prefix=prefix,currentWord=target,expectedBoundary=' '),'punctuation'))
    extra_overlap = {kind: len(keys & {key for entry in controls['entries'] if entry['kind'] == kind
                                     for key in entry['keys']}) for kind, keys in additional.items()}
    historical = (sum(report['lexicalOverlaps'].values()) + report['controlArticleOverlaps'] +
                  report['controlSurfaceOverlaps'] + report['controlContextOverlaps'] +
                  report['sourceControlContextOverlaps'] + sum(extra_overlap.values()))
    if word_check:
        historical += (sum(word_check['lexicalOverlaps'].values()) + sum(word_check['controlOverlaps'].values()) +
                       word_check['unsupportedTargetOverlaps'] + word_check['englishSourceSurfaceOverlaps'])
    integrity = (report['unresolvedSurfaces'] + report['truncatedInsideWord'] +
                 report['unmappedSourceFragments'] + fragments['sourceTokenFragments'])
    if word_check:
        integrity += len(word_check['identityErrors']) + len(word_check['unsupportedLexicalLanguages'])
    cross = sum(report['crossPartitionOverlaps'].values())
    return dict(schema=1, status='BLOCKED_OVERLAP' if historical or cross else
                'BLOCKED_TEXT_IDENTITIES' if integrity else 'BLOCKED_COVERAGE',
                sourceIdentityVerified=False, sourceLabelsQualified=False,
                independentQualification=False, publicationPermitted=False,
                historicalOverlapCount=historical, crossPartitionOverlapCount=cross,
                textIdentityBlockers=dict(unresolvedSurfaces=report['unresolvedSurfaces'],
                    truncatedInsideWord=report['truncatedInsideWord'],
                    unmappedSourceFragments=report['unmappedSourceFragments'],
                    sourceTokenFragments=fragments['sourceTokenFragments']),
                additionalControlOverlaps=extra_overlap, wordRowPreflight=word_check, exposure=report)
