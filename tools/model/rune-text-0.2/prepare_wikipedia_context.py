#!/usr/bin/env python3
"""Extract deterministic real-context spelling pairs from pinned Wikipedia parquet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from generate_pairwise_data import LANGUAGES, canonical, family, mutations, sha, valid_word


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
WORDS = {
    language: re.compile(f"[{re.escape(alphabet)}]+", re.IGNORECASE)
    for language, alphabet in {
        "en": "abcdefghijklmnopqrstuvwxyz",
        "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "es": "abcdefghijklmnñopqrstuvwxyzáéíóúü",
    }.items()
}


def bounded_prefix(value: str, maximum_bytes: int) -> str:
    value = unicodedata.normalize("NFC", value).lstrip()
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value
    tail = encoded[-maximum_bytes:].decode("utf-8", errors="ignore")
    boundary = re.search(r"\s", tail)
    return tail[boundary.end():] if boundary else ""


def context_candidates(text: str, language: str, vocabulary: set[str], excluded: set[str],
                       minimum_word: int, maximum_word: int, minimum_context_words: int,
                       maximum_prefix_bytes: int, seed: int) -> list[dict]:
    result: list[dict] = []
    text = unicodedata.normalize("NFC", text)
    for sentence in SENTENCE_BREAK.split(text):
        for ordinal, match in enumerate(WORDS[language].finditer(sentence)):
            if ordinal < minimum_context_words:
                continue
            word = match.group().casefold()
            word_family = family(word)
            if (not valid_word(word, language, minimum_word, maximum_word)
                    or word not in vocabulary or word_family in excluded):
                continue
            prefix = bounded_prefix(sentence[:match.start()], maximum_prefix_bytes)
            if not prefix or not prefix[-1].isspace():
                continue
            identity = hashlib.sha256(
                f"{seed}:{language}:{word_family}:{prefix}".encode("utf-8")).hexdigest()
            result.append({
                "id": f"wikipedia-{language}-{identity[:20]}",
                "language": language,
                "split": "pool",
                "family": word_family,
                "prefix": prefix,
                "chosen": word,
                "source": "wikimedia_wikipedia_20231101",
                "selectionHash": identity,
            })
    return result


def materialize(candidate: dict, vocabulary: set[str], seed: int) -> dict | None:
    variants = mutations(candidate["chosen"], candidate["language"], vocabulary,
                         f"{seed}:wikipedia:{candidate['language']}:{candidate['prefix']}:{candidate['chosen']}")
    if not variants:
        return None
    rejected, category = variants[0]
    return {**candidate, "rejected": rejected,
            "category": f"wikipedia_context:{category}"}


def context_pairs(text: str, language: str, vocabulary: set[str], excluded: set[str],
                  minimum_word: int, maximum_word: int, minimum_context_words: int,
                  maximum_prefix_bytes: int, seed: int) -> list[dict]:
    return [row for candidate in context_candidates(
        text, language, vocabulary, excluded, minimum_word, maximum_word,
        minimum_context_words, maximum_prefix_bytes, seed)
        if (row := materialize(candidate, vocabulary, seed)) is not None]


def read_vocabulary(path: Path, language: str, minimum: int, maximum: int) -> set[str]:
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(.+) ([0-9]+)", line)
        if not match:
            raise ValueError(f"malformed frequency row in {path.name}")
        word = unicodedata.normalize("NFC", match.group(1)).casefold()
        if valid_word(word, language, minimum, maximum):
            result.add(word)
    return result


def read_excluded(corpus: Path) -> dict[str, set[str]]:
    result = {language: set() for language in LANGUAGES}
    for language in LANGUAGES:
        for line in (corpus / f"spelling-{language}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            result[language].add(family(row["family"]))
    return result


def select_unique(rows: list[dict], limit: int) -> list[dict]:
    best: dict[str, dict] = {}
    for row in rows:
        current = best.get(row["family"])
        if current is None or row["selectionHash"] < current["selectionHash"]:
            best[row["family"]] = row
    return sorted(best.values(), key=lambda row: row["selectionHash"])[:limit]


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            row = {key: value for key, value in row.items() if key != "selectionHash"}
            stream.write(canonical(row).decode("utf-8") + "\n")


def run(args: argparse.Namespace) -> None:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required to read the pinned parquet inputs") from error

    config_path = Path(args.config).resolve(strict=True)
    lock_path = Path(args.lock).resolve(strict=True)
    inputs = Path(args.inputs).resolve(strict=True)
    frequencies = Path(args.frequency_inputs).resolve(strict=True)
    corpus = Path(args.excluded_corpus).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists() or not output.is_relative_to(REPO / "build"):
        raise ValueError("output must be a fresh directory below build")
    config = json.loads(config_path.read_text())
    lock = json.loads(lock_path.read_text())
    context_config = config["wikipediaContext"]
    source = lock["wikipediaContext"]
    actual = {name: sha(inputs / name) for name in sorted(source["files"])}
    if actual != {name: item["sha256"] for name, item in sorted(source["files"].items())}:
        raise ValueError("Wikipedia parquet digest mismatch")
    for name, item in source["files"].items():
        if (inputs / name).stat().st_size != item["bytes"]:
            raise ValueError(f"Wikipedia parquet size mismatch: {name}")

    frequency_expected = lock["frequencyWords"]["files"]
    if {name: sha(frequencies / name) for name in sorted(frequency_expected)} != frequency_expected:
        raise ValueError("frequency input digest mismatch")
    excluded = read_excluded(corpus)
    rows: list[dict] = []
    receipts: dict[str, dict] = {}
    for language in LANGUAGES:
        vocabulary = read_vocabulary(frequencies / f"{language}_50k.txt", language,
                                     config["minimumWordCodePoints"], config["maximumWordCodePoints"])
        filename = source["languageFiles"][language]
        best_by_family: dict[str, dict] = {}
        eligible = 0
        parquet_file = parquet.ParquetFile(inputs / filename)
        scanned = 0
        for batch in parquet_file.iter_batches(batch_size=64, columns=["text"]):
            for text in batch.column(0).to_pylist():
                scanned += 1
                candidates = context_candidates(
                    text or "", language, vocabulary, excluded[language],
                    config["minimumWordCodePoints"], config["maximumWordCodePoints"],
                    context_config["minimumContextWords"], context_config["maximumPrefixUtf8Bytes"],
                    config["seed"])
                eligible += len(candidates)
                for candidate in candidates:
                    current = best_by_family.get(candidate["family"])
                    if current is None or candidate["selectionHash"] < current["selectionHash"]:
                        best_by_family[candidate["family"]] = candidate
        selected = []
        for candidate in sorted(best_by_family.values(), key=lambda row: row["selectionHash"]):
            row = materialize(candidate, vocabulary, config["seed"])
            if row is not None:
                selected.append(row)
            if len(selected) == context_config["poolRowsPerLanguage"]:
                break
        if len(selected) != context_config["poolRowsPerLanguage"]:
            raise ValueError(f"insufficient Wikipedia context rows for {language}: {len(selected)}")
        rows.extend(selected)
        receipts[language] = {
            "articlesScanned": scanned,
            "eligibleContexts": eligible,
            "uniqueFamilies": len(best_by_family),
            "selectedRows": len(selected),
        }
    output.mkdir(parents=True)
    write_rows(output / "pairs.jsonl", rows)
    manifest = {
        "schemaVersion": 1,
        "scope": "rune-text-0.2-wikipedia-context-pool",
        "containsPersonalMessages": False,
        "sourceDataset": {
            "repository": source["repository"],
            "snapshot": source["snapshot"],
            "parquetRevision": source["parquetRevision"],
            "licenses": source["licenses"],
            "files": actual,
        },
        "configSha256": sha(config_path),
        "sourceLockSha256": sha(lock_path),
        "excludedCorpusManifestSha256": sha(corpus / "manifest.json"),
        "languages": receipts,
        "rows": len(rows),
        "outputs": {"pairs.jsonl": sha(output / "pairs.jsonl")},
        "sources": {
            str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve()),
            str((HERE / "generate_pairwise_data.py").relative_to(REPO)):
                sha(HERE / "generate_pairwise_data.py"),
        },
    }
    (output / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(json.dumps({language: receipts[language]["selectedRows"] for language in LANGUAGES},
                     sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=HERE / "training-config.json")
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--frequency-inputs", required=True)
    parser.add_argument("--excluded-corpus", default=REPO / "tools/eval/smart-typing-0.3")
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
