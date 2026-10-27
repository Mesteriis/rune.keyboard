"""Score-blind neighboring-word extraction and per-article cohort selection.

Non-overlapping pair matches miss a predicate in 'теперь готов был'. Selecting
one globally prioritized case per article can then erase every positive cohort
in articles that also contain a negative. Keep one case per group in one owned
part; retain family separation from the caller's fixed family partition.
"""
import hashlib
import re

_PAIR = re.compile(r'(?=(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?P<right>[а-яё]{1,32})(?![\w-]))')
_HASH = re.compile('[0-9a-f]{64}\\Z')


def adjacent_russian_pairs(folded_text):
    """Return overlapping bounded word pairs with exact source capture offsets."""
    return _PAIR.finditer(folded_text)


def choose_article_contexts(choices, *, article, seed):
    if not isinstance(article,str) or not article.isdigit() or not isinstance(seed,str) or not seed:
        raise ValueError('ARTICLE_SELECTION_IDENTITY')
    if not choices:return []
    for row in choices:
        if (row.get('article')!=article or row.get('part') not in {'calibration','holdout'}
                or not isinstance(row.get('sideGroup'),str) or not row['sideGroup']
                or any(not isinstance(row.get(k),str) or not _HASH.fullmatch(row[k]) for k in ['selectionHash','contextHash'])):
            raise ValueError('ARTICLE_SELECTION_SCHEMA')
    preferred='calibration' if hashlib.sha256((seed+':article:'+article).encode()).digest()[0]%2==0 else 'holdout'
    available={row['part'] for row in choices};owner=preferred if preferred in available else next(iter(available))
    groups={}
    for row in choices:
        if row['part']!=owner:continue
        group=row['sideGroup'];key=(row['selectionHash'],row['contextHash'])
        if group not in groups or key<(groups[group]['selectionHash'],groups[group]['contextHash']):groups[group]=row
    return [groups[group] for group in sorted(groups)]
