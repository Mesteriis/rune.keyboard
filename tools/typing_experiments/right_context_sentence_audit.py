"""Audit new source sentences and all their variants before model scoring.

Previously evaluated families are allowed in this protocol; supervised families,
old articles/contexts and cross-part overlap are not. This is an identity and
label-construction audit, not a cohort-size or model-quality qualification.
"""
from collections import Counter
import hashlib
import re
import unicodedata
from right_context_grammar_features import completed_following_words

_HASH = re.compile('[0-9a-f]{64}\\Z')


def _source_hash(prefix, word, suffix):
    text=' '.join(unicodedata.normalize('NFC',prefix+' '+word+suffix).casefold().split())
    return hashlib.sha256(text.encode()).hexdigest()


def _part(family, seed):
    return 'calibration' if hashlib.sha256((seed+':family:'+family).encode()).digest()[0]%2==0 else 'holdout'


def audit_new_sentences(parts, prior_rows, training_families, *, seed):
    if (not isinstance(parts,dict) or set(parts)!={'calibration','holdout'}
            or any(not isinstance(rows,list) for rows in parts.values()) or not isinstance(seed,str) or not seed):
        raise ValueError('SENTENCE_AUDIT_INPUT')
    if not isinstance(training_families,(list,tuple,set,frozenset)) or not training_families or any(not isinstance(f,str) or not f for f in training_families):
        raise ValueError('SENTENCE_TRAINING_FAMILIES')
    trained=set(training_families);seen_ids=set();facts={};exposed=set();old_articles=set();old_contexts=set()
    for row in prior_rows:
        article=str(row.get('article',''))
        if article.isdigit():old_articles.add(article)
        key=row.get('contextHash')
        if isinstance(key,str) and _HASH.fullmatch(key):old_contexts.add(key)
        if isinstance(row.get('family'),str):exposed.add(row['family'])
        declared=row.get('families',[])
        if isinstance(declared,(list,tuple,set,frozenset)):
            exposed.update(f for f in declared if isinstance(f,str))
    for part,rows in parts.items():
        groups={}
        for row in rows:
            if not isinstance(row,dict):raise ValueError('SENTENCE_ROW_SCHEMA')
            key=row.get('contextHash');family=row.get('family');families=row.get('families');article=row.get('article')
            if (not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen_ids
                    or row.get('split')!=part or row.get('language')!='ru'
                    or not isinstance(key,str) or not _HASH.fullmatch(key)
                    or not isinstance(families,list) or not families or any(not isinstance(f,str) or not f for f in families)
                    or len(families)!=len(set(families)) or not isinstance(family,str) or family not in families
                    or not isinstance(article,str) or not article.isdigit()
                    or any(not isinstance(row.get(k),str) or not row[k] for k in ['word','typed','expectedSpelling','rightContext','group','sideGroup'])
                    or not isinstance(row.get('prefix'),str)
                    or any(type(row.get(k)) is not bool for k in ['noAuto','retainBaseline'])):
                raise ValueError('SENTENCE_ROW_SCHEMA')
            seen_ids.add(row['id']);groups.setdefault(key,[]).append(row)
        for key,variants in groups.items():
            anchor=[r for r in variants if r.get('group')=='typo']
            if len(anchor)!=1:raise ValueError('SENTENCE_SOURCE_ANCHOR')
            anchor=anchor[0];following=completed_following_words(anchor['rightContext'])
            if not following or _source_hash(anchor['prefix'],anchor['word'],anchor['rightContext'])!=key:
                raise ValueError('SENTENCE_SOURCE_IDENTITY')
            expected_groups={'typo','correct','protected','unfinished'}|({'correct_rival'} if anchor.get('rival') else set())
            if Counter(r.get('group') for r in variants)!=Counter(expected_groups):
                raise ValueError('SENTENCE_VARIANT_COVERAGE')
            for row in variants:
                if any(row.get(k)!=anchor.get(k) for k in ['article','prefix','word','rival','family','families','sideGroup']):
                    raise ValueError('SENTENCE_VARIANT_DIVERGENCE')
                group=row['group'];control=group in {'correct','protected','correct_rival'};unfinished=group=='unfinished'
                typed=anchor['word'] if group=='correct' else '@'+anchor['word'] if group=='protected' else anchor['rival'] if group=='correct_rival' else anchor['typed']
                suffix=' '+following[0] if unfinished else anchor['rightContext']
                if (row['typed']!=typed or row['rightContext']!=suffix or row['noAuto']!=control
                        or row['retainBaseline']!=unfinished or row['expectedSpelling']!=(typed if control else anchor['word'])):
                    raise ValueError('SENTENCE_VARIANT_LABEL')
        families={f for row in rows for f in row['families']};articles={r['article'] for r in rows};contexts=set(groups)
        facts[part]=dict(rows=len(rows),contexts=len(contexts),families=len(families),articles=len(articles),
            trainingFamilyOverlap=sorted(families & trained),priorArticleOverlap=sorted(articles & old_articles),
            priorContextOverlap=sorted(contexts & old_contexts),familyPartitionMismatch=sorted(f for f in families if _part(f,seed)!=part),
            previouslyBoundFamilies=len(families & exposed),familiesNotInPriorMetadata=len(families-exposed))
    cal=parts['calibration'];hold=parts['holdout']
    cross=dict(families=sorted({f for r in cal for f in r['families']}&{f for r in hold for f in r['families']}),
               articles=sorted({r['article'] for r in cal}&{r['article'] for r in hold}),
               contexts=sorted({r['contextHash'] for r in cal}&{r['contextHash'] for r in hold}))
    passed=not any(cross.values()) and not any(fact[k] for fact in facts.values() for k in ['trainingFamilyOverlap','priorArticleOverlap','priorContextOverlap','familyPartitionMismatch'])
    return dict(passed=passed,parts=facts,crossPartOverlap=cross,qualityQualificationPerformed=False,
                priorFamilyMetadataIsNotExhaustive=True,earlierEvaluationFamiliesAllowed=True)
