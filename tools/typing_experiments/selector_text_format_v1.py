"""Conservative source-bound check for invisible joins in selected text."""
import re
import unicodedata

WORD = re.compile('[а-яё]+', re.IGNORECASE)


def inspect(source, fragment):
    if not isinstance(source, str) or not isinstance(fragment, str) or not fragment:
        raise ValueError('SELECTOR_TEXT_SOURCE_MISMATCH')
    source = unicodedata.normalize('NFC', source)
    words = list(WORD.finditer(source))
    clean = ' '.join(WORD.findall(source.lower()))
    if ([word.group().lower() for word in words] != WORD.findall(source.lower()) or
            not clean.startswith(fragment)):
        raise ValueError('SELECTOR_TEXT_SOURCE_MISMATCH')
    truncated = len(fragment) < len(clean) and fragment[-1].isalpha() and clean[len(fragment)].isalpha()
    count = 0
    for ordinal, _ in enumerate(WORD.finditer(fragment)):
        if ordinal >= len(words):
            raise ValueError('SELECTOR_TEXT_SOURCE_MISMATCH')
        match = words[ordinal]
        before = source[match.start()-1:match.start()] if match.start() else ''
        after = source[match.end():match.end()+1]
        if any(char and unicodedata.category(char) == 'Cf' for char in (before, after)):
            count += 1
    return {'formatFragments': count, 'truncated': truncated}
