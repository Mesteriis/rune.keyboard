"""Experimental whole-word context features; no product policy or private text."""
from collections import Counter
import json
import math
import re

FEATURE_NAMES = ('pair_count', 'pair_documents', 'word_conditioned_pair',
                 'prefix_conditioned_pair', 'gain_over_original_pair', 'pair_available')


def previous_word(context):
    match = re.search(r'(?:^|\s)([а-яё]{1,20})\s*$', context.casefold())
    return match.group(1) if match else None


class WordContextFeatures:
    def __init__(self, rows):
        self.pairs = {}
        self.words, self.prefixes = Counter(), Counter()
        for previous, word, count, documents in rows:
            if (previous, word) in self.pairs or type(count) is not int or type(documents) is not int or not 1 <= documents <= count:
                raise ValueError('INVALID_CONTEXT_COUNTS')
            self.pairs[previous, word] = count, documents
            self.words[word] += count
            self.prefixes[previous] += count

    @classmethod
    def load(cls, path):
        with path.open() as stream:
            return cls(json.loads(line) for line in stream if line.strip())

    def extract(self, context, original, candidate):
        previous = previous_word(context)
        count, documents = self.pairs.get((previous, candidate.casefold()), (0, 0))
        original_count = self.pairs.get((previous, original.casefold()), (0, 0))[0]
        scale = math.log1p(10000)
        return [min(math.log1p(count) / scale, 1), min(math.log1p(documents) / scale, 1),
                count / (1 + self.words[candidate.casefold()]),
                count / (1 + self.prefixes[previous]),
                max(-1, min(1, (math.log1p(count) - math.log1p(original_count)) / scale)),
                float(count > 0)]


def score_breakdown(rank, neural, context_model, tree_blob, context, original, candidates):
    """Use the frozen 95-feature scorer; this does not add the experimental features."""
    result = []
    for candidate in candidates:
        raw = rank.tree_score(tree_blob, rank.features(context, original, candidate))
        tree = .8 * math.tanh(raw / 4)
        character = neural.context_score(context_model, context, candidate['text'])
        result.append(dict(text=candidate['text'], tree=tree, characterContext=character, total=tree + character))
    return result
