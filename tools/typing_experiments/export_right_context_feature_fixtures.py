"""Freeze authored Python/Kotlin parity vectors; not model training or qualification."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
from contextual_assets import write_index, grammar_payload, GRAMMAR_MAGIC
from right_context_contrast_corpus import PAIRS, CONTEXTS, WEAK_SUFFIXES
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures, completed_following_words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon(); features = RightContextGrammarFeatures(lexicon)
    suffixes = {s for _, left, right in CONTEXTS for s in (left, right)} | set(WEAK_SUFFIXES)
    suffixes |= {' была ', ' будет она ', ' будет им ', ' стали ', ' будут, она ',
                 ' будут. она ', ' будут\nона ', ' будут1 ', ' будут-то ', ' будутabc ',
                 ' БУДУТ\tОНИ ', 'будут ', ' будут', ' он', ' она',
                 ' ' * 123 + 'будут ', ' слово' * 100 + ' ', ' е\u0308лки ',
                 ' будут 🙂 они ', ' будут\u00a0они ', ' будут\u200bони ', ' \nбудут '}
    candidates = sorted({word for pair in PAIRS for word in pair} |
                        {'виновен', 'виновны', 'стали', 'неизвестноеслово', 'готово_имя', 'готово' * 30, 'е\u0308лки'})
    cases = [(suffix, word) for suffix in sorted(suffixes) for word in candidates]
    queried = {word.lower() for word in candidates if len(word) <= 32}
    queried |= {word for suffix, _ in cases for word in completed_following_words(suffix)}
    # Include NFC-normalized queried candidates as well as following tokens.
    import unicodedata
    queried |= {unicodedata.normalize('NFC', word).lower() for word in candidates if len(word) <= 64}
    records = [(word, grammar_payload(lexicon.analyses(word))) for word in sorted(queried) if lexicon.analyses(word)]
    locked = write_index(records, args.output / 'grammar.bin', GRAMMAR_MAGIC)['sha256']
    def encode(value): return base64.b64encode(value.encode()).decode()
    payload = ''.join('\t'.join([encode(suffix), encode(word), ','.join(map(repr, features.extract(suffix, word)))]) + '\n'
                      for suffix, word in cases).encode()
    (args.output / 'vectors.tsv').write_bytes(payload)
    (args.output / 'hashes.properties').write_text('grammar=' + locked + '\n')
    (args.output / 'provenance.json').write_text(json.dumps(dict(
        schema=1, purpose='AUTHORED_PARITY_ONLY_NOT_QUALIFICATION', cases=len(cases), features=FEATURE_NAMES,
        grammarLicense='CC-BY-SA-3.0', grammarSource='https://opencorpora.org/',
        containsOwnerText=False, includesDisclosedWordAsRegressionOnly=True,
        vectorSha256=hashlib.sha256(payload).hexdigest(), grammarSha256=locked,
        featureSha256=hashlib.sha256(Path(__file__).with_name('right_context_grammar_features.py').read_bytes()).hexdigest(),
        exporterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), dictionary=lexicon.receipt()), indent=2) + '\n')
    print(json.dumps({'cases':len(cases),'features':len(FEATURE_NAMES),'grammarSha256':locked}))


if __name__ == '__main__':
    main()
