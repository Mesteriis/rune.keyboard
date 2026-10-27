"""Exclude whole frozen source contexts for newly added supervised families.

No scores, predictions, expected spellings or individual error rows affect this
filter. All variants and controls of an excluded context leave together.
"""


def exclude_training_contexts(rows, training_families):
    families=set(training_families)
    if not families or any(not isinstance(f,str) or not f for f in families):
        raise ValueError('TRAINING_FAMILY_SCHEMA')
    contexts={}
    for row in rows:
        key=row.get('contextHash');declared=row.get('families');family=row.get('family')
        if (not isinstance(key,str) or not key or not isinstance(declared,list) or not declared
                or any(not isinstance(f,str) or not f for f in declared)
                or not isinstance(family,str) or family not in declared):
            raise ValueError('SOURCE_FAMILY_SCHEMA')
        values=frozenset(declared)
        if key in contexts and contexts[key]!=values:
            raise ValueError('SOURCE_CONTEXT_FAMILY_DIVERGENCE')
        contexts[key]=values
    rejected={key for key,values in contexts.items() if values & families}
    return [row for row in rows if row['contextHash'] not in rejected],dict(
        originalRows=len(rows),keptRows=sum(row['contextHash'] not in rejected for row in rows),
        excludedRows=sum(row['contextHash'] in rejected for row in rows),
        excludedContexts=len(rejected),excludedContextHashes=sorted(rejected))
