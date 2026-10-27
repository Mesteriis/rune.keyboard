"""Export exact dictionary-only past-finite analyses as a supplemental index.

The existing compact grammar asset has no tense field. Imperatives also lack a
person tag, so neither absent person nor gender alone can replace tense lookup.
This index preserves the current asset format and changes no installed asset.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
from contextual_assets import write_index,grammar_payload,GRAMMAR_MAGIC

_WORD = re.compile('[а-яё]{1,32}\\Z')


def past_query_keys(dictionary):
    keys=set()
    for word,records in itertools.groupby(dictionary.words.iteritems(),key=lambda row:row[0]):
        if not _WORD.fullmatch(word):continue
        if not any((tag:=dictionary.build_tag_info(*entry)).POS=='VERB' and tag.tense=='past' for _,entry in records):continue
        variants=['']
        for letter in word:
            variants=[prefix+char for prefix in variants for char in ('её' if letter=='ё' else letter)]
        keys.update(variants)
    return keys


def past_records(lexicon):
    lexicon._load();keys=past_query_keys(lexicon._analyzer.dictionary)
    print('PAST_QUERY_KEYS',len(keys),flush=True)
    for index,word in enumerate(sorted(keys)):
        analyses=tuple(a for a in lexicon.analyses(word) if a.pos=='VERB' and a.tense=='past')
        if not analyses:raise ValueError('PAST_DICTIONARY_QUERY_MISSING')
        yield word,grammar_payload(analyses)
        if index and index%25000==0:print('PAST_RECORDS',index,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.json').exists():parser.error('Output and receipt must be new')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'morphology'));from ranker import PymorphyLexicon
    lexicon=PymorphyLexicon(cache_size=16384);receipt=lexicon.receipt()
    result=write_index(past_records(lexicon),args.output,GRAMMAR_MAGIC)
    if lexicon.receipt()!=receipt:raise ValueError('PAST_DICTIONARY_CHANGED')
    result.update(purpose='EXPERIMENTAL_PAST_FINITE_ONLY_NOT_INSTALLED',dictionary=receipt,license='CC-BY-SA-3.0',source='https://opencorpora.org/',exporterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),packedFormatUnchanged=True)
    args.output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
