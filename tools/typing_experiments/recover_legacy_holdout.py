"""Recover source identities from pinned historical Wikipedia holdout selections.

The original selector did not include article IDs in selectionHash. Every
matching article/occurrence is retained, never an arbitrary first match. Frozen
generator bytes are verified before loading; its selector is the authority.
No model, score or new target label participates in recovery.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unicodedata

from holdout_ledger import load_ledger
from right_context_sentence_audit import _source_hash

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = 'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py'
MIXED_GUARD_SHA = 'ed9928d64d80911c0182e03446d710a60abb990cb5fb1cff30730443db773225'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_generator(expected_sha):
    directory = Path(__file__).with_name('frozen_sources')
    manifest = json.loads((directory / 'manifest.json').read_text())
    entry = manifest['sources'].get(expected_sha)
    if not entry or entry['originalPath'] != ORIGINAL:
        raise ValueError('RECOVERY_GENERATOR_NOT_ARCHIVED')
    path = directory / entry['file']
    if path.parent != directory or sha(path) != expected_sha:
        raise ValueError('RECOVERY_GENERATOR_IDENTITY')
    spec = importlib.util.spec_from_file_location('frozen_' + expected_sha, path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    return generator


class LegacySelections:
    def __init__(self, rows, generator, seed, source_sha):
        self.generator = generator; self.seed = seed
        self.mixed_guard = source_sha == MIXED_GUARD_SHA
        self.selected = {}
        for row in rows:
            target = row.get('expectedSpelling')
            if target is None and row.get('cohort') == 'correct':
                target = row['typed']
            if not isinstance(target, str) or not target:
                raise ValueError('RECOVERY_TARGET_MISSING')
            identity = hashlib.sha256(f'{seed}:qualification:ru:{generator.family(target)}:{row["prefix"]}'.encode()).hexdigest()
            if (row['template'] != 'holdout-wikipedia-' + identity
                    or row['family'] != generator.family(target) or identity in self.selected):
                raise ValueError('RECOVERY_SELECTION_IDENTITY')
            self.selected[identity] = dict(id=row['id'], word=target, family=row['family'],
                                          prefix=row['prefix'], selectionHash=identity)
        self.known = {row['word'] for row in self.selected.values()}

    def recover_article(self, article, text):
        if not isinstance(article, str) or not article.isascii() or not article.isdecimal():
            raise ValueError('RECOVERY_ARTICLE_ID')
        text = unicodedata.normalize('NFC', text or '')
        reference = [item for item in self.generator.spelling_candidates(text, 'ru', self.known, set(), self.seed)
                     if item['selectionHash'] in self.selected]
        if not reference:
            return []
        segments = []; start = 0
        for boundary in self.generator.SENTENCE_BREAK.finditer(text):
            segments.append((start, text[start:boundary.start()]))
            start = boundary.end()
        segments.append((start, text[start:]))
        records = []; recovered = []
        for offset, sentence in segments:
            for ordinal, match in enumerate(self.generator.WORDS['ru'].finditer(sentence)):
                if ordinal < 4:
                    continue
                if self.mixed_guard and ((match.start() and sentence[match.start()-1].isalpha())
                        or (match.end() < len(sentence) and sentence[match.end()].isalpha())):
                    continue
                word = match.group().casefold()
                if word not in self.known:
                    continue
                family = self.generator.family(word)
                prefix = self.generator.bounded_prefix(sentence[max(0, match.start()-512):match.start()]).rstrip()
                identity = hashlib.sha256(f'{self.seed}:qualification:ru:{family}:{prefix}'.encode()).hexdigest()
                if identity not in self.selected:
                    continue
                item = dict(word=word, family=family, prefix=prefix, selectionHash=identity)
                if item != {k: self.selected[identity][k] for k in item}:
                    raise ValueError('RECOVERY_MATCH_DIVERGENCE')
                recovered.append(item)
                absolute_start, absolute_end = offset + match.start(), offset + match.end()
                projected_prefix = self.generator.bounded_prefix(text[max(0, absolute_start-256):absolute_start]).rstrip(' \t')
                suffix = text[absolute_end:absolute_end+128]
                records.append(dict(id=self.selected[identity]['id'], selectionHash=identity, article=article,
                    contextHash=_source_hash(projected_prefix, word, suffix)))
        if recovered != reference:
            raise ValueError('RECOVERY_SELECTOR_PARITY')
        return records


def recover(version, parquet_path, output, root=ROOT, ledger_path=None):
    import pyarrow
    import pyarrow.parquet as parquet
    root = Path(root); output = Path(output)
    ledger = load_ledger(ledger_path or root / 'tools/typing_experiments/holdout-ledger.json')
    entry = next(e for e in ledger['entries'] if e['id'] == f'public-spelling-v{version}')
    directory = root / f'build/typing-ranker-v2/external-holdout-v{version}-ru{version+5:04d}'
    manifest_path = directory / 'manifest.json'; rows_path = directory / 'rows.jsonl'
    if any(sha(root / p) != h for p, h in entry['bindings'].items()):
        raise ValueError('RECOVERY_CORPUS_BINDING')
    manifest = json.loads(manifest_path.read_text())
    if (sha(parquet_path) != manifest['source']['sha256']
            or Path(parquet_path).stat().st_size != manifest['source']['bytes']):
        raise ValueError('RECOVERY_PUBLIC_SOURCE_IDENTITY')
    generator_sha = manifest['sources'][ORIGINAL]
    generator = load_generator(generator_sha)
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    selections = LegacySelections(rows, generator, manifest['selection']['seed'], generator_sha)
    output.mkdir(parents=True, exist_ok=False)
    records = []; scanned = 0
    for batch in parquet.ParquetFile(parquet_path).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            records.extend(selections.recover_article(str(article), text))
            scanned += 1
        if scanned % 4096 == 0:
            print(json.dumps(dict(version=version, scanned=scanned, matchedOccurrences=len(records))), flush=True)
    path = output / 'identities.jsonl'
    path.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in sorted(records, key=lambda r: (r['id'], r['article'], r['contextHash']))))
    matched = Counter(r['id'] for r in records)
    missing = sorted({r['id'] for r in rows} - matched.keys())
    report = dict(purpose='HISTORICAL_PUBLIC_IDENTITY_RECOVERY_NOT_MODEL_EVALUATION', version=version,
        source=manifest['source'], corpusRows=len(rows), sourceArticlesScanned=scanned,
        recoveredRows=len(matched), matchedOccurrences=len(records), uniqueArticles=len({r['article'] for r in records}),
        rowsInMultipleOccurrences=sum(n > 1 for n in matched.values()), missingRows=missing,
        sourceGeneratorSha256=generator_sha, corpusSha256=sha(rows_path), corpusManifestSha256=sha(manifest_path),
        identitiesSha256=sha(path), recoverySourceSha256=sha(Path(__file__)), pyarrowVersion=pyarrow.__version__,
        allRowsRecovered=not missing, modelCalls=0,
        projection='right-context-source-hash-v1: whole-article 256-char prefix input / 128-char suffix')
    (output / 'receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    if missing:
        raise ValueError('RECOVERY_INCOMPLETE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', type=int, required=True, choices=range(7, 13))
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, help='Original bootstrap ledger for independent recovery rebuilds')
    args = parser.parse_args()
    recover(args.version, args.parquet, args.output, ledger_path=args.ledger)


if __name__ == '__main__':
    main()
