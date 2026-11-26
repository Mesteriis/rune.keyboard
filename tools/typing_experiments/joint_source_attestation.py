"""Verify joint-row source identities against one independently supplied article.

This bounded primitive neither opens corpora nor qualifies their source files.
Callers must authenticate article IDs, shard bytes and the morphology dictionary.
"""
import hashlib
from pathlib import Path
import re
import unicodedata

from joint_exclusion_inputs import segment_index, source_context_hash, source_segment_hash_at

WORDS=re.compile(r'(?<![\w])[а-яёА-ЯЁ]{3,20}(?![\w])')
SEED='rune-joint-v1-20261025'


def attest_article(article,source,text,rows,generator,lexicon,native_families,partition):
    """Require each row's source window, segment, selection and all lemmas.

    No row contents are returned. The caller must bind this result to the exact
    source file and collect/check all partitions separately before qualification.
    """
    if (not isinstance(article,str) or not article.isascii() or not article.isdecimal() or
            not isinstance(source,str) or Path(source).name!=source or not isinstance(text,str) or
            not isinstance(rows,list) or not rows):
        raise ValueError('JOINT_ARTICLE_SCOPE')
    text=unicodedata.normalize('NFC',text)
    matches={}
    for match in WORDS.finditer(text):
        matches.setdefault(match.group().casefold(),[]).append(match)
    segments=segment_index(text);checked=0
    for row in rows:
        if not isinstance(row,dict) or row.get('article')!=article or row.get('source')!=source:
            raise ValueError('JOINT_ARTICLE_ROW_SCOPE')
        word=row.get('word');prefix=row.get('prefix');family=row.get('family')
        if (not isinstance(word,str) or word!=word.casefold() or not isinstance(prefix,str) or
                not isinstance(family,str) or not family.isdecimal() or
                native_families.get(word)!=family or row.get('split')!=partition(family) or type(row.get('noAuto')) is not bool):
            raise ValueError('JOINT_ARTICLE_ROW_SCHEMA')
        expected=row.get('typed') if row['noAuto'] else word
        cohort=row.get('cohort');typed=row.get('typed')
        if (not isinstance(typed,str) or row.get('expectedSpelling')!=expected or
                (row['noAuto'] and (cohort not in ('correct','protected') or
                    typed!=(word if cohort=='correct' else '@'+word))) or
                (not row['noAuto'] and (cohort!='typo' or typed==word))):
            raise ValueError('JOINT_ARTICLE_LABEL')
        lemmas=sorted({analysis.lemma for analysis in lexicon.analyses(word)})
        if not lemmas or row.get('families')!=lemmas:raise ValueError('JOINT_ARTICLE_LEMMAS')
        identity=hashlib.sha256((SEED+article+word+prefix).encode()).hexdigest()
        if row.get('selectionHash')!=identity:raise ValueError('JOINT_ARTICLE_SELECTION')
        found=False
        for match in matches.get(word,[]):
            actual_prefix=generator.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip()
            if actual_prefix!=prefix:continue
            if (source_context_hash(text,match,generator)==row.get('contextHash') and
                    source_segment_hash_at(text,match,segments)==row.get('sourceSegmentHash')):
                found=True;break
        if not found:raise ValueError('JOINT_ARTICLE_SOURCE_MISMATCH')
        checked+=1
    return {'checkedRows':checked}
