"""Authored, paired noun/predicate training using real dictionary corruptions.

A shared unknown input has both noun and short-adjective targets in distinct
explicit contexts. Noun labels are training competition, never permission for
this predicate-only runtime source to edit nouns. No natural evaluation text.
"""
import hashlib
import json
from grammar_contrast_corpus import shared_variants, one_edit_cost
from right_context_timeline_calibration import completed_prefixes

PAIRS = (
    ('зол','зал','наш ',' будет открыт '),
    ('зол','пол','этот ',' был мокрым '),
    ('силён','салон','этот ',' будет закрыт '),
    ('слаб','штаб','этот ',' был открыт '),
    ('верен','ветер','сильный ',' будет завтра '),
    ('важен','вагон','этот ',' будет новым '),
    ('щедр','кедр','этот ',' будет высоким '),
)


def generate(lexicon, *, pairs=PAIRS):
    rows={};skipped=[]
    for adjective,noun,noun_prefix,noun_suffix in pairs:
        adjective_tags=tuple(lexicon.analyses(adjective));noun_tags=tuple(lexicon.analyses(noun))
        adjective_lemmas={a.lemma for a in adjective_tags if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc'}
        if (len(adjective_lemmas)!=1 or not noun_tags
                or not any(a.pos=='NOUN' and a.case=='nomn' and a.number=='sing' and a.gender=='masc' for a in noun_tags)):
            raise ValueError('OTHER_PART_DICTIONARY_CONTRAST')
        family=next(iter(adjective_lemmas));families=sorted({a.lemma for a in adjective_tags+noun_tags})
        variants=[v for v in shared_variants(adjective,noun,lexicon,edit_profiles=True) if 3<=len(v)<=32]
        if not variants:
            skipped.append(dict(adjective=adjective,noun=noun,reason='NO_ELIGIBLE_SHARED_UNKNOWN'));continue
        def add(original,applied,target,prefix,suffix,kind,scenario):
            row=dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',language='ru',family=family,
                contrastFamilies=families,original=original,applied=applied,expectedApplied=target,
                leftContext=prefix,rightContext=suffix,candidateForms=[adjective,noun],kind=kind,scenario=scenario)
            if kind!='correct_original':row['contrastEditCosts']=[one_edit_cost(original,w) for w in (adjective,noun)]
            row['id']='right-other-part-'+hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
            rows[row['id']]=row
        contexts=[(prefix,noun_suffix,noun,'noun_subject_before_copula') for prefix in
                  (noun_prefix,'вот '+noun_prefix,'наконец '+noun_prefix,'кажется, '+noun_prefix)]
        contexts.extend((prefix,suffix,adjective,'predicate_with_left_pronoun')
                        for prefix in ('он ','тогда он ','к вечеру он ','потом он ')
                        for suffix in (' был ',' будет '))
        for prefix,suffix,target,scenario in contexts:
            for _,completed in completed_prefixes(suffix):
                for typo in variants:
                    for applied in (typo,adjective,noun):add(typo,applied,target,prefix,completed,'unknown_original',scenario)
                for original in (adjective,noun):add(original,original,original,prefix,completed,'correct_original',scenario)
        for suffix in (' будет ',' был ',' модели ',' будет'):
            for typo in variants:
                for applied in (typo,adjective,noun):add(typo,applied,applied,'',suffix,'insufficient_right_evidence','other_part_ambiguous')
    if not rows:raise ValueError('EMPTY_OTHER_PART_CORPUS')
    return list(rows.values()),skipped
