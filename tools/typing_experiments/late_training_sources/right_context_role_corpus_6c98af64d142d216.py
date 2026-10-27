"""Authored-only case-role and singular-gender training contrasts.

Uses the existing training families, never disclosed natural failure sentences.
Unresolved singular gender and ambiguous noun roles retain the previous output.
The eventual replay selector must retrieve every required form without labels.
"""
import hashlib
import json
from grammar_contrast_corpus import shared_variants,one_edit_cost
from right_context_contrast_corpus import PAIRS

_GENDERS = {'masc':('он','был','пришёл','мальчик'),
            'femn':('она','была','пришла','девочка'),
            'neut':('оно','было','исчезло','письмо')}
_DATIVE = frozenset(('верен','полезен','нужен','важен'))


def generate(lexicon, paradigms, *, pairs=PAIRS):
    rows={};skipped=[]
    for masculine,plural in pairs:
        source=[a for a in lexicon.analyses(masculine) if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc']
        lemmas={a.lemma for a in source}
        if len(lemmas)!=1:raise ValueError('ROLE_TRAINING_PARADIGM')
        lemma=next(iter(lemmas))
        if not any(a.pos=='ADJS' and a.number=='plur' and a.lemma==lemma for a in lexicon.analyses(plural)):
            raise ValueError('ROLE_TRAINING_PLURAL_PARADIGM')
        for gender,(pronoun,past,arrival,noun) in _GENDERS.items():
            forms=sorted({w for w in paradigms.get(masculine,()) if any(a.pos=='ADJS' and a.number=='sing' and a.gender==gender and a.lemma==lemma for a in lexicon.analyses(w))})
            if not forms:
                skipped.append(dict(family=lemma,gender=gender,reason='NO_DICTIONARY_FORM'));continue
            singular=masculine if gender=='masc' and masculine in forms else forms[0]
            variants=shared_variants(singular,plural,lexicon,edit_profiles=True)[:2]
            if not variants:
                skipped.append(dict(family=lemma,gender=gender,reason='NO_SHARED_UNKNOWN_CORRUPTION'));continue
            def add(original,applied,target,prefix,suffix,kind,scenario):
                row=dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',language='ru',
                    family=lemma,original=original,applied=applied,expectedApplied=target,
                    leftContext=prefix,rightContext=suffix,candidateForms=[singular,plural],kind=kind,scenario=scenario)
                if kind!='correct_original':row['contrastEditCosts']=[one_edit_cost(original,w) for w in (singular,plural)]
                row['id']='right-role-'+hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
                rows[row['id']]=row
            strong=[('',f' {pronoun} ',singular,'right_pronoun'),
                    ('',f' будет {pronoun} ',singular,'copula_pronoun'),
                    ('',f' {past} ',singular,'gendered_past_copula'),
                    (pronoun+' тогда ',' будет ',singular,'left_pronoun'),
                    ('',f' {noun} ',singular,'right_subject_noun'),
                    ('',' они ',plural,'right_plural_pronoun'),
                    ('',' будут ',plural,'plural_copula'),
                    ('',' были ',plural,'plural_past_copula')]
            strong.append((('ты' if gender!='neut' else 'оно')+' '+arrival+', и теперь ',
                           ' будешь ' if gender!='neut' else ' будет ',singular,'preceding_past_gender'))
            if masculine in _DATIVE:
                strong.extend((pronoun+' ',' '+complement+' ',singular,'ambiguous_complement_with_left_subject')
                              for complement in ('модели','традиции','организации'))
            weak=(' будет ',' будешь ',' буду ',' модели ',' традиции ',' организации ',' будет',' он')
            for prefix,suffix,target,scenario in strong:
                for typo in variants:
                    for applied in (typo,singular,plural):add(typo,applied,target,prefix,suffix,'unknown_original',scenario)
                for original in (singular,plural):add(original,original,original,prefix,suffix,'correct_original',scenario)
            for suffix in weak:
                for typo in variants:
                    for applied in (typo,singular,plural):add(typo,applied,applied,'',suffix,'insufficient_right_evidence','ambiguous_or_unfinished')
    if not rows:raise ValueError('EMPTY_ROLE_CORPUS')
    return list(rows.values()),skipped
