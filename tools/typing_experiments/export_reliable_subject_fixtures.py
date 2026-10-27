"""Authored parity for source-v2 cues; does not redefine frozen model features."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
from contextual_assets import write_index,grammar_payload,GRAMMAR_MAGIC
from right_context_subject_evidence import ReliableRightContextGrammarFeatures,VERSION
from right_context_grammar_features import FEATURE_NAMES,completed_following_words
from right_context_contrast_corpus import PAIRS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'morphology'));from ranker import PymorphyLexicon
    lex=PymorphyLexicon();features=ReliableRightContextGrammarFeatures(lex)
    words=['и','в','по','же','или','как','да','что','это','нет','то','а','но','она','они','модели','девочка']
    suffixes={s for word in words for s in [' '+word+' ',' '+word,' будут '+word+' ',' будет '+word+',',' будут '+word+' имя ']}
    suffixes.update(['',' ','будут ',' будут_тест ',' будут. она ',' будут\nона ',' БУДУТ\tОНИ ',' '*123+'будут ',' е\u0308лки ',' будут 🙂 они '])
    candidates=sorted({w for pair in PAIRS for w in pair}|{'готова','готово','готовы','готов','в','и','неизвестный','готово_имя','ГОТОВА','е\u0308лки'})
    cases=[(suffix,candidate) for suffix in sorted(suffixes) for candidate in candidates]
    queried=set(candidates)|{w for suffix in suffixes for w in completed_following_words(suffix)};keys=sorted({w.lower() for w in queried if lex.analyses(w)})
    grammar=write_index([(w,grammar_payload(lex.analyses(w))) for w in keys],args.output/'grammar.bin',GRAMMAR_MAGIC)
    enc=lambda s:base64.b64encode(s.encode()).decode();payload=''.join('\t'.join([enc(s),enc(c),','.join(map(repr,features.extract(s,c)))])+'\n' for s,c in cases).encode()
    (args.output/'vectors.tsv').write_bytes(payload);(args.output/'hashes.properties').write_text('grammar='+grammar['sha256']+'\n')
    (args.output/'provenance.json').write_text(json.dumps(dict(purpose='AUTHORED_SOURCE_PARITY_ONLY_NOT_QUALIFICATION',version=VERSION,cases=len(cases),features=FEATURE_NAMES,modelFeatureDefinitionsChanged=False,containsOwnerText=False,grammarLicense='CC-BY-SA-3.0',grammarSource='https://opencorpora.org/',dictionary=lex.receipt(),grammar=grammar,vectorSha256=hashlib.sha256(payload).hexdigest(),sourceSha256=hashlib.sha256(Path(__file__).with_name('right_context_subject_evidence.py').read_bytes()).hexdigest(),exporterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),features=len(FEATURE_NAMES))),flush=True)


if __name__=='__main__':main()
