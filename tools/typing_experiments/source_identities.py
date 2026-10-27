"""Explicit public source identity namespaces; no implicit Wikipedia/Tatoeba alias."""
import hashlib
import json
import re
import unicodedata


def unsupported_surface_key(value,language='ru'):
    """Exact unsupported RU word surface only; never a guessed lemma/family."""
    if language!='ru' or not isinstance(value,str):return None
    value=unicodedata.normalize('NFC',value).casefold()
    if not re.fullmatch('[а-яё]{1,32}',value):return None
    return hashlib.sha256(json.dumps(['rune-unsupported-surface-v1','ru',value],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def tatoeba_identity(row):
    source=row.get('sourceRepository')
    if source in (None,'wikimedia/wikipedia'):return None
    if source!='tatoeba' or row.get('language')!='ru':raise ValueError('SOURCE_SENTENCE_SCOPE')
    value=row.get('article')
    if not isinstance(value,str) or not value.startswith('tatoeba:'):raise ValueError('SOURCE_SENTENCE_ID')
    value=value.removeprefix('tatoeba:')
    if not 1<=len(value)<=20 or not value.isascii() or not value.isdecimal() or int(value)<=0:raise ValueError('SOURCE_SENTENCE_ID')
    return ['tatoeba','ru',str(int(value))]
