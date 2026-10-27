"""Authored Python/Kotlin role parity, with explicit past-tense dictionary data."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
from contextual_assets import write_index,grammar_payload,GRAMMAR_MAGIC
from right_context_grammar_features import completed_following_words
from right_context_role_features import FEATURE_NAMES,RightContextRoleFeatures,preceding_clause_words


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'morphology'));from ranker import PymorphyLexicon
    lex=PymorphyLexicon();features=RightContextRoleFeatures(lex)
    lefts=['','она ','ты пришла, и теперь ','он пришёл, и теперь ','оно остыло, и теперь ',
      'она пришла, иди теперь ','она пришла, были теперь ','она пришла, будем теперь ',
      'ты пришла. теперь ','ты пришла\nтеперь ','prefix_пришла ','prefix-пришла ',
      'она пришла','она прише\u0308л, теперь ','🙂'*70+'она пришла, теперь ',
      'пришла '+'снова '*24,'а'*130+' ','я'+' '*121+'пришла ','пришла,\tтеперь ']
    rights=['',' модели ',' девочка ',' мальчик ',' письмо ',' она ',' они ',' была ',' было ',
      ' будешь ',' будут ',' будешь она ',' будут и ',' модели',' будут_тест ',' и ',' в ',' по ']
    candidates=['готов','готова','готово','готовы','верен','верна','важен','важна','силён',
      'зал','вагон','иди','неизвестноеслово','готово_имя','ГОТОВА','е\u0308лки']
    cases=[(left,right,candidate) for left in lefts for right in rights for candidate in candidates]
    queried=set(candidates)|{w for left in lefts for w in preceding_clause_words(left)}|{w for right in rights for w in completed_following_words(right)}
    words=sorted({w.lower() for w in queried if lex.analyses(w)})
    grammar=write_index([(w,grammar_payload(lex.analyses(w))) for w in words],args.output/'grammar.bin',GRAMMAR_MAGIC)
    past=write_index([(w,grammar_payload(tags)) for w in words if (tags:=tuple(a for a in lex.analyses(w) if a.pos=='VERB' and a.tense=='past'))],args.output/'past.bin',GRAMMAR_MAGIC)
    enc=lambda s:base64.b64encode(s.encode()).decode();payload=''.join('\t'.join([enc(left),enc(right),enc(candidate),','.join(map(repr,features.extract(left,right,candidate))),enc(' '.join(preceding_clause_words(left))) or '-'])+'\n' for left,right,candidate in cases).encode()
    (args.output/'vectors.tsv').write_bytes(payload);(args.output/'hashes.properties').write_text('grammar='+grammar['sha256']+'\npast='+past['sha256']+'\n')
    provenance=dict(purpose='AUTHORED_PARITY_ONLY_NOT_TRAINING_OR_QUALIFICATION',cases=len(cases),features=FEATURE_NAMES,containsOwnerText=False,grammarLicense='CC-BY-SA-3.0',grammarSource='https://opencorpora.org/',dictionary=lex.receipt(),grammar=grammar,past=past,vectorSha256=hashlib.sha256(payload).hexdigest(),featureSha256=hashlib.sha256(Path(__file__).with_name('right_context_role_features.py').read_bytes()).hexdigest(),exporterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),features=len(FEATURE_NAMES))),flush=True)


if __name__=='__main__':main()
