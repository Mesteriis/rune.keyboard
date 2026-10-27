"""Explicit public source identity namespaces; no implicit Wikipedia/Tatoeba alias."""
def tatoeba_identity(row):
    source=row.get('sourceRepository')
    if source in (None,'wikimedia/wikipedia'):return None
    if source!='tatoeba' or row.get('language')!='ru':raise ValueError('SOURCE_SENTENCE_SCOPE')
    value=row.get('article')
    if not isinstance(value,str) or not value.startswith('tatoeba:'):raise ValueError('SOURCE_SENTENCE_ID')
    value=value.removeprefix('tatoeba:')
    if not 1<=len(value)<=20 or not value.isascii() or not value.isdecimal() or int(value)<=0:raise ValueError('SOURCE_SENTENCE_ID')
    return ['tatoeba','ru',str(int(value))]
