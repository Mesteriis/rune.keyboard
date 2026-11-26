"""Project verified historical corpus rows to control keys."""
from collections import Counter

import control_ledger


def project_corpus_entries(rows, bindings, prefix, language, source_repository=None):
    counts = Counter()
    contexts = {'protected': set(), 'regression': set()}
    surfaces = {'protected': set(), 'regression': set()}
    articles = set()
    for row in rows:
        if row['language'] != language:
            raise ValueError('CONTROL_CORPUS_LANGUAGE')
        kind = 'protected' if row['group'] == 'protected' else 'regression'
        counts[kind] += 1
        contexts[kind].add(control_ledger.key_for(row, kind))
        surfaces[kind].add(control_ledger.surface_key(language, row['typed']))
        mapped = row if source_repository is None else row | {'sourceRepository': source_repository}
        articles.add(control_ledger.article_key(mapped))
    if not articles:
        raise ValueError('CONTROL_CORPUS_EMPTY')
    common = {'language': language, 'bindings': bindings}
    entries = [
        dict(common, id=prefix + kind, kind=kind, rowCount=counts[kind],
             keys=sorted(contexts[kind]), surfaceKeys=sorted(surfaces[kind]))
        for kind in contexts if counts[kind]
    ]
    entries.append(dict(common, id=prefix + 'source', kind='source',
                        rowCount=len(articles), keys=[], articleKeys=sorted(articles)))
    return entries
