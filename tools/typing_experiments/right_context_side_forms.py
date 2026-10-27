"""Dictionary-derived contrast tools for following-context falsification cohorts.

Reads only a hash-locked existing grammar asset. Candidate neighborhoods and
corruptions are chosen without ranker scores or runtime admission assumptions.
"""
import hashlib
import re
import struct
from grammar_contrast_corpus import one_edit_words, shared_variants, one_edit_cost

_WORD = re.compile('[а-яё]{1,32}\\Z')


def grammar_word_sets(blob, expected_sha256):
    if (not 64 <= len(blob) <= 128 * 1024 * 1024 or hashlib.sha256(blob).hexdigest() != expected_sha256
            or blob[:8] != b'RUGRM001' or hashlib.sha256(blob[:-32]).digest() != blob[-32:]):
        raise ValueError('SIDE_GRAMMAR_IDENTITY')
    width, count, blocks, start = struct.unpack_from('<IIII', blob, 8)
    if width != 32 or not 1 <= count <= 8_000_000 or blocks != (count + 31) // 32 or start != 24 + 4 * (blocks + 1) or start >= len(blob) - 32:
        raise ValueError('SIDE_GRAMMAR_HEADER')
    offsets = struct.unpack_from('<' + 'I' * (blocks + 1), blob, 24)
    if offsets[0] != 0 or offsets[-1] + start != len(blob) - 32 or any(a >= b for a,b in zip(offsets,offsets[1:])):
        raise ValueError('SIDE_GRAMMAR_OFFSETS')
    position = start; previous = b''; predicates = set(); nominatives = set()
    for index in range(count):
        if position + 4 > len(blob) - 32:
            raise ValueError('SIDE_GRAMMAR_RECORD')
        prefix, suffix, size = struct.unpack_from('<BBH', blob, position)
        if (prefix > len(previous) or suffix == 0 or not 4 <= size <= 1024 or position + 4 + suffix + size > len(blob) - 32
                or index % 32 == 0 and (prefix != 0 or position != start + offsets[index // 32])):
            raise ValueError('SIDE_GRAMMAR_RECORD')
        key = previous[:prefix] + blob[position+4:position+4+suffix]
        if index and key <= previous:
            raise ValueError('SIDE_GRAMMAR_ORDER')
        payload = blob[position+4+suffix:position+4+suffix+size]
        analyses = payload[1]
        if not 1 <= payload[0] <= 8 or analyses == 0 or size != 2 + 2 * analyses:
            raise ValueError('SIDE_GRAMMAR_PAYLOAD')
        codes = struct.unpack_from('<' + 'H' * analyses, payload, 2)
        word = key.decode('utf-8')
        if _WORD.fullmatch(word):
            if all(code & 31 == 3 and (code >> 8) & 3 in (1,2) for code in codes):predicates.add(word)
            if any(code & 31 in (1,9) and (code >> 5) & 7 == 1 for code in codes):nominatives.add(word)
        previous = key;position += 4 + suffix + size
    if position != len(blob) - 32:
        raise ValueError('SIDE_GRAMMAR_TRAILING')
    return predicates, nominatives


def non_predicate_contrast(word, lexicon, predicates):
    source = lexicon.analyses(word)
    if not source or any(a.pos == 'ADJS' for a in source) or len({a.lemma for a in source}) != 1:
        return None
    for rival in sorted(one_edit_words(word) & predicates):
        tags = lexicon.analyses(rival)
        if (not tags or any(a.pos != 'ADJS' for a in tags) or len({a.lemma for a in tags}) != 1
                or len({a.number for a in tags}) != 1):continue
        variants = shared_variants(word, rival, lexicon, edit_profiles=True)
        if variants:
            return dict(word=word, rival=rival, typed=variants[0], family=next(iter({a.lemma for a in source})),
                        rivalFamily=next(iter({a.lemma for a in tags})),
                        editCosts=[one_edit_cost(variants[0],w) for w in (word,rival)])
    return None
