"""Fail closed on disclosed evaluation rows or repeated sentence contexts in training."""
import unicodedata


def context_key(row):
    values = [row.get(name) for name in ('prefix', 'typed', 'expectedSpelling')]
    if any(not isinstance(value, str) for value in values):
        raise ValueError('CONTEXT_ROW_SCHEMA')
    return tuple(' '.join(unicodedata.normalize('NFC', value).casefold().split()) for value in values)


def target_context_key(row):
    prefix, _, target = context_key(row)
    return prefix, target


def check_separation(partitions, disclosed):
    """Sentence identity and left-context/target identity must not cross boundaries."""
    disclosed = tuple(disclosed)
    forbidden_rows = {context_key(row) for row in disclosed}
    forbidden_contexts = {target_context_key(row) for row in disclosed}
    forbidden_sentences = {row['article'] for row in disclosed if row.get('article')}
    seen_contexts, seen_sentences = {}, {}
    for part, rows in partitions.items():
        for row in rows:
            key = context_key(row)
            context = target_context_key(row)
            sentence = row.get('article')
            if (key in forbidden_rows or context in forbidden_contexts or sentence in forbidden_sentences
                    or row.get('purpose') == 'REGRESSION_ONLY_NOT_TRAINING'):
                raise ValueError('DISCLOSED_EVALUATION_REUSED')
            if context in seen_contexts and seen_contexts[context] != part:
                raise ValueError('CONTEXT_SPLIT_OVERLAP')
            if sentence and sentence in seen_sentences and seen_sentences[sentence] != part:
                raise ValueError('SENTENCE_SPLIT_OVERLAP')
            seen_contexts[context] = part
            if sentence:
                seen_sentences[sentence] = part
