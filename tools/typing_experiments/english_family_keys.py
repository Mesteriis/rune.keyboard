"""Exact English annotated-lemma identities; never infer or qualify families."""
import re
import unicodedata

from holdout_ledger import _digest

SCHEMA = 'ud-annotated-lemma-en-v1'
LEMMA = re.compile(r"[a-z]+(?:'[a-z]+)*\Z")


def key_for(lemma):
    if not isinstance(lemma,str):
        raise ValueError('EN_LEMMA_SCHEMA')
    value=unicodedata.normalize('NFC',lemma).casefold().replace('’',"'")
    if not 1<=len(value)<=32 or not LEMMA.fullmatch(value):
        raise ValueError('EN_LEMMA_SCHEMA')
    return _digest('family',[SCHEMA,value])


def keys_for(values):
    if not isinstance(values,(list,tuple)) or not values:
        raise ValueError('EN_LEMMA_SCHEMA')
    return {key_for(value) for value in values}
