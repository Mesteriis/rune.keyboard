#!/usr/bin/env python3
"""Build and probe a public Russian rare-name supplement.

Only pinned public Wikipedia shards are accepted. The extractor retains normalized
capitalized Cyrillic forms and aggregate counts, never article text. Candidate
probing enumerates the complete bounded unit-edit neighborhood and performs exact
membership checks; it does not inject an expected answer.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
WORD = re.compile(r"(?<![А-Яа-яЁё-])([А-ЯЁ][а-яё]{2,31})(?![А-Яа-яЁё-])")
CANONICAL = re.compile(r"[а-яё]{3,32}\Z")
ALPHABET = tuple("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
KEYBOARD_ROWS = ("йцукенгшщзхъ", "фывапролджэ", "ячсмитьбю")
KEYBOARD_OFFSETS = (0, 1, 2)
PINNED_SOURCES = {
    "ru-0007.parquet": "39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88",
    "ru-0008.parquet": "9df744fb888585b0db5cacf605f8a8ba8562828a0c240106c70d716738e41e87",
    "ru-0009.parquet": "bf3781c558a3a2b8125e567f060895ead704577943832e6047bcc71f202975fd",
}


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def capitalized_forms(text: str):
    normalized = unicodedata.normalize("NFC", text or "")
    for match in WORD.finditer(normalized):
        preceding = normalized[:match.start()].rstrip()
        if not preceding or preceding[-1] in ".!?\n":
            continue
        yield match.group(1).lower()


def select_words(totals: dict[str, int], article_counts: dict[str, int],
        minimum_occurrences: int, minimum_articles: int) -> list[str]:
    if minimum_occurrences < 1 or minimum_articles < 1:
        raise ValueError("INVALID_THRESHOLDS")
    return sorted(word for word, count in totals.items()
                  if count >= minimum_occurrences and article_counts.get(word, 0) >= minimum_articles)


def canonical_word(word: str) -> str | None:
    value = unicodedata.normalize("NFC", word).lower()
    return value if CANONICAL.fullmatch(value) else None


def one_edit_variants(word: str) -> set[str]:
    source = canonical_word(word)
    if source is None:
        return set()
    result: set[str] = set()
    for index in range(len(source)):
        result.add(source[:index] + source[index + 1:])
        for letter in ALPHABET:
            if letter != source[index]:
                result.add(source[:index] + letter + source[index + 1:])
        if index + 1 < len(source) and source[index] != source[index + 1]:
            result.add(source[:index] + source[index + 1] + source[index] + source[index + 2:])
    for index in range(len(source) + 1):
        for letter in ALPHABET:
            result.add(source[:index] + letter + source[index:])
    result.discard(source)
    return {value for value in result if CANONICAL.fullmatch(value)}


def membership_candidates(word: str, dictionary_contains, supplement: set[str]) -> list[str]:
    source = canonical_word(word)
    if source is None or dictionary_contains(source) or source in supplement:
        return []
    return sorted(value for value in one_edit_variants(source)
                  if dictionary_contains(value) or value in supplement)


def adjacent(first: str, second: str) -> bool:
    for row_a, value_a in enumerate(KEYBOARD_ROWS):
        column_a = value_a.find(first)
        if column_a < 0:
            continue
        for row_b, value_b in enumerate(KEYBOARD_ROWS):
            column_b = value_b.find(second)
            if column_b < 0:
                continue
            dx = abs(2 * column_a + KEYBOARD_OFFSETS[row_a] -
                     2 * column_b - KEYBOARD_OFFSETS[row_b])
            dy = abs(row_a - row_b)
            return (dy == 0 and dx == 2) or (dy == 1 and dx <= 1)
    return False


def initial_edit_cost(source: str, target: str) -> float:
    if len(source) != len(target):
        return 1.0
    differences = [index for index, (left, right) in enumerate(zip(source, target)) if left != right]
    if (len(differences) == 2 and differences[1] == differences[0] + 1 and
            source[differences[0]] == target[differences[1]] and
            source[differences[1]] == target[differences[0]]):
        return 1.25
    if len(differences) == 1:
        index = differences[0]
        return .75 if adjacent(source[index], target[index]) else 1.0
    raise ValueError("NOT_UNIT_EDIT")


def augment_candidates(word: str, existing: list[dict], dictionary_contains,
        supplement: set[str], supplement_ranks: dict[str, int]) -> list[dict] | None:
    source = canonical_word(word)
    if source is None:
        return list(existing)
    if dictionary_contains(source) or source in supplement:
        return None
    result = list(existing)
    present = {item["text"].casefold() for item in result}
    additions = []
    for value in membership_candidates(source, dictionary_contains, supplement):
        if value in present:
            continue
        additions.append({
            "text": value,
            "canonicalKey": value,
            "terminalKey": value,
            "unitDistance": 1,
            "frequencyRank": 50_000 + supplement_ranks.get(value, 1_000_000),
            "editCost": initial_edit_cost(source, value),
            "isFallback": False,
        })
    additions.sort(key=lambda item: (item["editCost"], item["frequencyRank"], item["text"]))
    return result + additions


def read_supplement(directory: Path) -> tuple[set[str], dict[str, int]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    words_path, counts_path = directory / "words.txt", directory / "counts.tsv"
    if (manifest.get("schemaVersion") != 1 or manifest.get("containsPrivateText") is not False or
            file_hash(words_path) != manifest.get("files", {}).get("words.txt") or
            file_hash(counts_path) != manifest.get("files", {}).get("counts.tsv")):
        raise ValueError("SUPPLEMENT_IDENTITY")
    words = words_path.read_text(encoding="utf-8").splitlines()
    if words != sorted(set(words)) or any(canonical_word(word) != word for word in words):
        raise ValueError("SUPPLEMENT_WORDS")
    word_set = set(words)
    ranks = {}
    for rank, line in enumerate(counts_path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] not in word_set or fields[0] in ranks:
            raise ValueError("SUPPLEMENT_COUNTS")
        if int(fields[1]) < manifest["minimumOccurrences"] or int(fields[2]) < manifest["minimumArticles"]:
            raise ValueError("SUPPLEMENT_COUNTS")
        ranks[fields[0]] = rank
    if set(ranks) != word_set:
        raise ValueError("SUPPLEMENT_COUNTS")
    return word_set, ranks


def extract(parquets: list[Path], output: Path, minimum_occurrences: int,
        minimum_articles: int) -> dict:
    import pyarrow.parquet as parquet

    if output.exists() or not output.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    if len(parquets) != len(PINNED_SOURCES):
        raise ValueError("PINNED_SOURCE_SET_REQUIRED")
    bindings = {}
    for path in parquets:
        path = path.resolve(strict=True)
        expected = PINNED_SOURCES.get(path.name)
        actual = file_hash(path)
        if expected is None or actual != expected or path.name in bindings:
            raise ValueError("PUBLIC_PARQUET_IDENTITY")
        bindings[path.name] = {"path": str(path.relative_to(ROOT)), "sha256": actual,
                               "bytes": path.stat().st_size}
    if set(bindings) != set(PINNED_SOURCES):
        raise ValueError("PINNED_SOURCE_SET_REQUIRED")

    totals: Counter[str] = Counter()
    article_counts: Counter[str] = Counter()
    articles = 0
    for path in sorted(parquets, key=lambda item: item.name):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=["text"]):
            for text in batch.column(0).to_pylist():
                forms = list(capitalized_forms(text or ""))
                totals.update(forms)
                article_counts.update(set(forms))
                articles += 1
    words = select_words(totals, article_counts, minimum_occurrences, minimum_articles)
    output.mkdir(parents=True)
    words_path = output / "words.txt"
    counts_path = output / "counts.tsv"
    words_path.write_text("".join(word + "\n" for word in words), encoding="utf-8")
    counts_path.write_text("".join(
        f"{word}\t{totals[word]}\t{article_counts[word]}\n"
        for word in sorted(words, key=lambda value: (-totals[value], value))), encoding="utf-8")
    manifest = {
        "schemaVersion": 1,
        "containsPrivateText": False,
        "sources": bindings,
        "articlesScanned": articles,
        "minimumOccurrences": minimum_occurrences,
        "minimumArticles": minimum_articles,
        "words": len(words),
        "transformation": "NFC lowercase mid-sentence capitalized Cyrillic forms, 3-32 letters",
        "scriptSha256": file_hash(Path(__file__)),
        "files": {words_path.name: file_hash(words_path), counts_path.name: file_hash(counts_path)},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-occurrences", type=int, default=3)
    parser.add_argument("--minimum-articles", type=int, default=2)
    args = parser.parse_args()
    result = extract(args.parquet, args.output, args.minimum_occurrences, args.minimum_articles)
    print(json.dumps({key: result[key] for key in ("articlesScanned", "words")}, sort_keys=True))


if __name__ == "__main__":
    main()
