"""Freeze small public cross-language feature fixtures from the pinned training inputs."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
from contextual_assets import write_index, grammar_payload, COUNT_MAGIC, GRAMMAR_MAGIC
from grammar_context_features import GrammarContextFeatures, preceding_words
from word_context_features import WordContextFeatures, previous_word


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon(cache_size=16384); grammar = GrammarContextFeatures(lexicon)
    paths = [Path('build/context-ranking-20261025/counts-v3/model-counts.jsonl'),
             Path('build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl')]
    tables = [WordContextFeatures.load(path) for path in paths]
    cases = [
        ('тебе надо ', 'научищься', 'научиться'), ('тебе надо ', 'научищься', 'научишься'),
        ('Том начал немного ', 'злищься', 'злиться'), ('Том начал немного ', 'злищься', 'злишься'),
        ('я не могу тебе ', 'заплатищь', 'заплатить'), ('я не могу тебе ', 'заплатищь', 'заплатишь'),
        ('Том показал мне ', 'фотографие', 'фотографию'), ('Том показал мне ', 'фотографие', 'фотографией'),
        ('они ', 'виновн', 'виновны'), ('они ', 'виновн', 'виновен'),
        ('ты уже ', 'идещь', 'идёшь'), ('мы уже ', 'идем', 'идём'),
        ('в ', 'лес', 'лесу'), ('к новой ', 'книг', 'книге'), ('из ', 'ча', 'чаю'),
        ('о ', 'замк', 'замке'), ('она ', 'стл', 'стала'), ('он ', 'стл', 'стал'),
        ('надо ', 'фывапролдж', 'фывапролдж'), ('надо, ', 'учитса', 'учиться'),
        ('xнадо ', 'учитса', 'учиться'), ('_надо ', 'учитса', 'учиться'),
        ('-надо ', 'учитса', 'учиться'), ('Ⅰнадо ', 'учитса', 'учиться'),
        ('🙂надо ', 'учитса', 'учиться'), ('я\nне могу тебе ', 'платит', 'платить'),
        ('к новои\u0306 ', 'книг', 'книге'), ('к ', 'новои\u0306', 'новои\u0306'),
        ('о ', 'елка', 'елка'), ('о ', 'ёлка', 'ёлка'), ('о ', 'елки', 'елки'),
        ('о ', 'ёлки', 'ёлки'), ('мы ', 'все', 'все'), ('это ', 'всё', 'всё'),
        ('тебе\tнадо\t', 'учитса', 'учиться'),
        ('слово ' * 100 + 'надо ', 'учитса', 'учиться'),
        ('Я\u00a0уже\t', 'ддмой', 'домой'),
    ]
    for table in tables:
        for previous, word in sorted(table.pairs, key=lambda key: -table.pairs[key][0])[:3]:
            cases.extend([(previous + ' ', word, word), (previous + ' ', word, 'фывапролдж')])
    queried_words = {candidate.casefold() for _, _, candidate in cases}
    queried_words.update(word for context, _, _ in cases for word in preceding_words(context))
    records = [(word, grammar_payload(lexicon.analyses(word))) for word in sorted(queried_words)
               if lexicon.analyses(word)]
    locks = {'grammar': write_index(records, args.output / 'grammar.bin', GRAMMAR_MAGIC)['sha256']}
    for name, table in zip(['wiki', 'conversation'], tables, strict=True):
        keys = {(previous_word(context), word.casefold()) for context, original, candidate in cases
                for word in (original, candidate)}
        records = []
        for previous, word in keys:
            if (previous, word) not in table.pairs: continue
            count, documents = table.pairs[previous, word]
            records.append((previous + '\0' + word, struct.pack('<IIII', count, documents,
                                                             table.words[word], table.prefixes[previous])))
        locks[name] = write_index(sorted(records), args.output / (name + '.bin'), COUNT_MAGIC)['sha256']
    def encode(value): return base64.b64encode(value.encode()).decode()
    def numeric(values): return ','.join(repr(value) for value in values)
    with (args.output / 'vectors.tsv').open('w') as stream:
        for context, original, candidate in cases:
            stream.write('\t'.join([encode(context), encode(original), encode(candidate),
                                    numeric(grammar.extract(context, original, candidate)),
                                    *[numeric(t.extract(context, original, candidate)) for t in tables]]) + '\n')
    (args.output / 'hashes.properties').write_text(''.join(f'{key}={value}\n' for key, value in sorted(locks.items())))
    (args.output / 'provenance.json').write_text(json.dumps(dict(
        cases=len(cases), syntheticConstructedContexts=True, containsOwnerText=False,
        sourceHashes={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        dictionary=lexicon.receipt(), grammarFeatureSha256=hashlib.sha256(
            Path('tools/typing_experiments/grammar_context_features.py').read_bytes()).hexdigest(),
        exporterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2) + '\n')
    print('FROZEN_PUBLIC_PARITY_CASES', len(cases))


if __name__ == '__main__': main()
