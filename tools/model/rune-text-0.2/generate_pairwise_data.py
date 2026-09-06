#!/usr/bin/env python3
"""Build disjoint, deterministic spelling preference pairs from pinned word lists."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import unicodedata


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVALUATOR = REPO / "tools/eval/smart-typing-0.3/evaluate.py"
LANGUAGES = ("en", "ru", "es")
ALPHABETS = {
    "en": "abcdefghijklmnopqrstuvwxyz",
    "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "es": "abcdefghijklmnñopqrstuvwxyzáéíóúü",
}
PREFIXES = {
    "en": ("The next word is", "Write the word", "The label reads", "The text contains", "We entered", "Please check"),
    "ru": ("Следующее слово", "Напишите слово", "На этикетке указано", "Текст содержит", "Мы ввели", "Проверьте слово"),
    "es": ("La siguiente palabra es", "Escribe la palabra", "La etiqueta dice", "El texto contiene", "Hemos escrito", "Comprueba la palabra"),
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def family(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.casefold().replace("ё", "е"))
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def read_existing_families(corpus: Path) -> set[str]:
    result: set[str] = set()
    for language in LANGUAGES:
        path = corpus / f"spelling-{language}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            result.add(f"{language}:{family(row['family'])}")
    return result


def valid_word(word: str, language: str, minimum: int, maximum: int) -> bool:
    if not minimum <= len(word) <= maximum or word != word.lower() or not word.isalpha():
        return False
    allowed = set(ALPHABETS[language])
    return all(char in allowed for char in word)


def load_words(path: Path, language: str, minimum: int, maximum: int,
               excluded: set[str]) -> tuple[list[str], set[str]]:
    words: list[str] = []
    vocabulary: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(.+) ([0-9]+)", line)
        if not match:
            raise ValueError(f"malformed frequency row in {path.name}")
        word = unicodedata.normalize("NFC", match.group(1))
        if valid_word(word, language, minimum, maximum):
            vocabulary.add(word.casefold())
            key = f"{language}:{family(word)}"
            if key not in excluded:
                excluded.add(key)
                words.append(word)
    return words, vocabulary


def mutations(word: str, language: str, vocabulary: set[str], seed: str) -> list[tuple[str, str]]:
    possible: list[tuple[str, str]] = []

    def add(value: str, category: str) -> None:
        value = unicodedata.normalize("NFC", value)
        if (value and value != word and value.casefold() not in vocabulary
                and all(value != prior for prior, _ in possible)):
            possible.append((value, category))

    alphabet = ALPHABETS[language]
    order = list(range(len(word)))
    random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16)).shuffle(order)
    for index in order:
        add(word[:index] + word[index + 1:], "missing_letter")
        add(word[:index] + word[index] + word[index:], "repeated_letter")
        if index + 1 < len(word) and word[index] != word[index + 1]:
            add(word[:index] + word[index + 1] + word[index] + word[index + 2:], "transposition")
        replacement = alphabet[(alphabet.index(word[index]) + 1) % len(alphabet)]
        add(word[:index] + replacement + word[index + 1:], "substitution")
        insertion = alphabet[(index * 11 + len(word)) % len(alphabet)]
        add(word[:index] + insertion + word[index:], "extra_letter")
    return possible


def stable_words(words: list[str], language: str, seed: int) -> list[str]:
    return sorted(words, key=lambda word: hashlib.sha256(
        f"{seed}:{language}:{family(word)}".encode()).digest())


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical(row).decode() + "\n")


def build_rows(words: list[str], language: str, vocabulary: set[str], split: str,
               per_word: int, seed: int) -> list[dict]:
    result: list[dict] = []
    for ordinal, word in enumerate(words):
        variants = mutations(word, language, vocabulary, f"{seed}:{language}:{split}:{word}")
        if len(variants) < per_word:
            raise ValueError(f"not enough safe mutations for {language}/{word}")
        prefix = PREFIXES[language][ordinal % len(PREFIXES[language])]
        for variant, (rejected, category) in enumerate(variants[:per_word]):
            result.append({
                "id": f"{language}-{split}-{ordinal:05}-{variant}",
                "language": language,
                "split": split,
                "family": family(word),
                "prefix": prefix,
                "chosen": " " + word,
                "rejected": " " + rejected,
                "category": category,
                "source": "frequency",
            })
    return result


def product_pairs(corpus_rows: list[dict], generated: list[dict], seed: int,
                  training_percent: int, training_repeat: int) -> tuple[list[dict], list[dict]]:
    if not 1 <= training_percent <= 99 or training_repeat < 1:
        raise ValueError("invalid product calibration split")
    by_id = {item["id"]: item for item in generated}
    if len(by_id) != len(generated) or set(by_id) != {row["id"] for row in corpus_rows}:
        raise ValueError("product calibration ids do not match corpus")
    eligible: dict[str, list[dict]] = {language: [] for language in LANGUAGES}
    for row in corpus_rows:
        item = by_id[row["id"]]
        if item["original"] != row["typed"]:
            raise ValueError("product calibration original mismatch")
        alternatives = item.get("alternatives", [])
        if not alternatives:
            continue
        expected = row.get("expectedSpelling")
        if row["cohort"] == "typo":
            if row["noAuto"]:
                continue
            matches = [value for value in alternatives if value["text"] == expected]
            if len(matches) != 1:
                continue
            chosen = expected
            rejected = [item["original"], *(value["text"] for value in alternatives
                                             if value["text"] != expected)]
            category = "product_candidate:" + row["category"]
        else:
            chosen = item["original"]
            rejected = [value["text"] for value in alternatives]
            category = "product_original:" + row["category"]
        if not rejected or any(value == chosen for value in rejected):
            raise ValueError("invalid product calibration candidate set")
        eligible[row["language"]].append({
            "row": row, "chosen": chosen, "rejected": rejected, "category": category})
    train_rows: list[dict] = []
    valid_rows: list[dict] = []
    for language, entries in eligible.items():
        families = sorted({family(value["row"]["family"]) for value in entries},
            key=lambda value: hashlib.sha256(f"{seed}:product:{language}:{value}".encode()).digest())
        cut = max(1, len(families) * training_percent // 100)
        train_families = set(families[:cut])
        for entry in entries:
            row = entry["row"]
            split = "train" if family(row["family"]) in train_families else "valid"
            repeats = training_repeat if split == "train" else 1
            for repeat in range(repeats):
                for rival, rejected in enumerate(entry["rejected"]):
                    target = {
                        "id": f"product-{row['id']}-{repeat}-{rival}",
                        "language": language,
                        "split": split,
                        "family": family(row["family"]),
                        "prefix": row["prefix"] + " ",
                        "chosen": entry["chosen"],
                        "rejected": rejected,
                        "category": entry["category"],
                        "source": "product_calibration",
                    }
                    (train_rows if split == "train" else valid_rows).append(target)
    return train_rows, valid_rows


def load_product_calibration(export: Path, corpus: Path, maximum_alternatives: int) -> tuple[list[dict], list[dict], dict]:
    receipt_path = export / "provenance.json"
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get("maximumAlternatives") != maximum_alternatives
            or receipt.get("sourceOverrides") != {}
            or receipt.get("harnessWidthArgument") is not True
            or receipt.get("corpusManifest") != sha(corpus / "manifest.json")
            or receipt.get("candidates") != sha(export / "candidates.jsonl")):
        raise ValueError("product calibration export provenance mismatch")
    if any(sha(REPO / name) != digest for name, digest in receipt["sources"].items()):
        raise ValueError("product calibration production source drift")
    generated = [json.loads(line) for line in
                 (export / "candidates.jsonl").read_text(encoding="utf-8").splitlines()]
    spec = importlib.util.spec_from_file_location("rune_training_corpus", EVALUATOR)
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    all_rows = evaluator.load_corpus(corpus)
    evaluator.validate(all_rows)
    rows = [row for row in all_rows if row["split"] == "calibration"
            and row["task"] == "spelling"]
    if len(rows) != 6000 or len(generated) != len(rows):
        raise ValueError("product calibration row count mismatch")
    return rows, generated, receipt


def load_context_pool(directory: Path, config_path: Path, lock_path: Path) -> tuple[list[dict], dict]:
    manifest_path = directory / "manifest.json"
    pairs_path = directory / "pairs.jsonl"
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get("scope") != "rune-text-0.2-wikipedia-context-pool"
            or manifest.get("configSha256") != sha(config_path)
            or manifest.get("sourceLockSha256") != sha(lock_path)
            or manifest.get("outputs", {}).get("pairs.jsonl") != sha(pairs_path)
            or manifest.get("containsPersonalMessages") is not False):
        raise ValueError("Wikipedia context pool provenance mismatch")
    if any(sha(REPO / name) != digest for name, digest in manifest.get("sources", {}).items()):
        raise ValueError("Wikipedia context pool source drift")
    rows = [json.loads(line) for line in pairs_path.read_text(encoding="utf-8").splitlines()]
    if (len(rows) != manifest.get("rows") or len({row["id"] for row in rows}) != len(rows)
            or len({(row.get("language"), row.get("family")) for row in rows}) != len(rows)):
        raise ValueError("Wikipedia context pool row count, ids, or families mismatch")
    if any(row.get("split") != "pool" or row.get("source") != "wikimedia_wikipedia_20231101"
           or row.get("language") not in LANGUAGES for row in rows):
        raise ValueError("invalid Wikipedia context pool row")
    return rows, manifest


def split_context_pool(pool: list[dict], existing_train: list[dict], existing_valid: list[dict],
                       seed: int, train_per_language: int,
                       valid_per_language: int) -> tuple[list[dict], list[dict], dict]:
    occupied = {(row["language"], row["family"]) for row in existing_train + existing_valid}
    output_train: list[dict] = []
    output_valid: list[dict] = []
    receipt: dict[str, dict] = {}
    for language in LANGUAGES:
        eligible = [row for row in pool
                    if row["language"] == language and (language, row["family"]) not in occupied]
        eligible.sort(key=lambda row: hashlib.sha256(
            f"{seed}:wikipedia-split:{language}:{row['family']}".encode()).digest())
        required = train_per_language + valid_per_language
        if len(eligible) < required:
            raise ValueError(f"insufficient disjoint Wikipedia contexts for {language}: {len(eligible)}")
        selected_train = eligible[:train_per_language]
        selected_valid = eligible[train_per_language:required]
        for split, rows, target in (("train", selected_train, output_train),
                                    ("valid", selected_valid, output_valid)):
            for row in rows:
                item = dict(row)
                item["split"] = split
                target.append(item)
        receipt[language] = {
            "poolRows": sum(row["language"] == language for row in pool),
            "eligibleAfterExistingFamilies": len(eligible),
            "trainingRows": len(selected_train),
            "validationRows": len(selected_valid),
            "trainingFamiliesSha256": hashlib.sha256(canonical(
                [row["family"] for row in selected_train])).hexdigest(),
            "validationFamiliesSha256": hashlib.sha256(canonical(
                [row["family"] for row in selected_valid])).hexdigest(),
        }
    return output_train, output_valid, receipt


def run(args: argparse.Namespace) -> None:
    config_path = Path(args.config).resolve(strict=True)
    lock_path = Path(args.lock).resolve(strict=True)
    inputs = Path(args.inputs).resolve(strict=True)
    corpus = Path(args.excluded_corpus).resolve(strict=True)
    calibration_export = Path(args.calibration_export).resolve(strict=True)
    context_pool = Path(args.context_pool).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists() or not output.is_relative_to(REPO / "build"):
        raise ValueError("output must be a fresh directory below build")
    config = json.loads(config_path.read_text())
    lock = json.loads(lock_path.read_text())
    if config["baseRevision"] != lock["baseModel"]["revision"]:
        raise ValueError("base revision mismatch")
    expected = lock["frequencyWords"]["files"]
    actual = {name: sha(inputs / name) for name in sorted(expected)}
    if actual != expected:
        raise ValueError("frequency input digest mismatch")
    excluded = read_existing_families(corpus)
    source_corpus_files = [corpus / f"spelling-{language}.jsonl" for language in LANGUAGES]
    train_rows: list[dict] = []
    valid_rows: list[dict] = []
    split_receipt: dict[str, dict] = {}
    for language in LANGUAGES:
        words, vocabulary = load_words(inputs / f"{language}_50k.txt", language,
            config["minimumWordCodePoints"], config["maximumWordCodePoints"], excluded)
        words = stable_words(words, language, config["seed"])
        train_count = config["trainWordsPerLanguage"]
        valid_count = config["validationWordsPerLanguage"]
        if len(words) < train_count + valid_count:
            raise ValueError(f"insufficient disjoint words for {language}")
        train_words = words[:train_count]
        valid_words = words[train_count:train_count + valid_count]
        train_rows += build_rows(train_words, language, vocabulary, "train",
                                 config["mutationsPerTrainWord"], config["seed"])
        valid_rows += build_rows(valid_words, language, vocabulary, "valid",
                                 config["mutationsPerValidationWord"], config["seed"])
        split_receipt[language] = {
            "eligibleWords": len(words),
            "trainWords": len(train_words),
            "validationWords": len(valid_words),
            "trainFamiliesSha256": hashlib.sha256(canonical([family(x) for x in train_words])).hexdigest(),
            "validationFamiliesSha256": hashlib.sha256(canonical([family(x) for x in valid_words])).hexdigest(),
        }
    product_config = config["productCalibration"]
    product_corpus_rows, generated, product_receipt = load_product_calibration(
        calibration_export, corpus, product_config["maximumAlternatives"])
    product_train, product_valid = product_pairs(product_corpus_rows, generated, config["seed"],
        product_config["trainingFamilyPercent"], product_config["trainingRepeat"])
    train_rows += product_train
    valid_rows += product_valid
    context_rows, context_manifest = load_context_pool(context_pool, config_path, lock_path)
    context_config = config["wikipediaContext"]
    context_train, context_valid, context_receipt = split_context_pool(
        context_rows, train_rows, valid_rows, config["seed"],
        context_config["trainingRowsPerLanguage"], context_config["validationRowsPerLanguage"])
    train_rows += context_train
    valid_rows += context_valid
    if {(row["language"], row["family"]) for row in train_rows} & {
            (row["language"], row["family"]) for row in valid_rows}:
        raise ValueError("train/validation family overlap")
    output.mkdir(parents=True)
    write_rows(output / "train.jsonl", train_rows)
    write_rows(output / "valid.jsonl", valid_rows)
    manifest = {
        "schemaVersion": 1,
        "scope": "rune-text-0.2-pairwise-training",
        "containsPersonalMessages": False,
        "usesRevealedHoldoutRows": False,
        "usesAuthoredCalibrationRows": True,
        "configSha256": sha(config_path),
        "sourceLockSha256": sha(lock_path),
        "frequencyInputs": actual,
        "excludedCorpus": {str(path.relative_to(REPO)): sha(path) for path in source_corpus_files},
        "productCalibration": {
            "receiptSha256": sha(calibration_export / "provenance.json"),
            "candidatesSha256": sha(calibration_export / "candidates.jsonl"),
            "trainingRows": len(product_train), "validationRows": len(product_valid),
        },
        "wikipediaContext": {
            "manifestSha256": sha(context_pool / "manifest.json"),
            "pairsSha256": sha(context_pool / "pairs.jsonl"),
            "source": context_manifest["sourceDataset"],
            "splits": context_receipt,
            "trainingRows": len(context_train), "validationRows": len(context_valid),
        },
        "sources": {
            **context_manifest["sources"],
            str(EVALUATOR.relative_to(REPO)): sha(EVALUATOR),
            str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve()),
        },
        "splits": split_receipt,
        "rows": {"train": len(train_rows), "valid": len(valid_rows)},
        "outputs": {"train.jsonl": sha(output / "train.jsonl"), "valid.jsonl": sha(output / "valid.jsonl")},
    }
    (output / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(json.dumps(manifest["rows"], sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=HERE / "training-config.json")
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--excluded-corpus", default=REPO / "tools/eval/smart-typing-0.3")
    parser.add_argument("--calibration-export", required=True)
    parser.add_argument("--context-pool", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
