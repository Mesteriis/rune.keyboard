#!/usr/bin/env python3
"""Build a frozen, family-disjoint final Smart Typing qualification corpus."""
from __future__ import annotations

import argparse
from collections import Counter
import heapq
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unicodedata


HERE = Path(__file__).resolve().parent
EVAL_ROOT = HERE.parent
REPO = HERE.parents[3]
LANGUAGES = ("en", "ru", "es")
FILES = [f"{task}-{language}.jsonl" for task in ("spelling", "punctuation")
         for language in LANGUAGES] + ["protected-tokens.jsonl"]
ALPHABETS = {
    "en": "abcdefghijklmnopqrstuvwxyz",
    "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "es": "abcdefghijklmnñopqrstuvwxyzáéíóúü",
}
WORDS = {language: re.compile(f"[{re.escape(alphabet)}]+", re.IGNORECASE)
         for language, alphabet in ALPHABETS.items()}
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
BOUNDARY = re.compile(r"([.,:]|\s)(\s*)([^\W\d_]+)", re.UNICODE)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def family(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold().replace("ё", "е"))
    return "".join(char for char in value if unicodedata.category(char) != "Mn")


def bounded_prefix(value: str, maximum_bytes: int = 256) -> str:
    value = unicodedata.normalize("NFC", value).lstrip()
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value
    tail = encoded[-maximum_bytes:].decode("utf-8", errors="ignore")
    boundary = re.search(r"\s", tail)
    return tail[boundary.end():] if boundary else ""


def vocabulary(path: Path, language: str) -> set[str]:
    result = set()
    allowed = set(ALPHABETS[language])
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(.+) ([0-9]+)", line)
        if not match:
            raise ValueError(f"malformed frequency row: {path.name}")
        word = unicodedata.normalize("NFC", match.group(1)).casefold()
        if 4 <= len(word) <= 20 and word.isalpha() and all(char in allowed for char in word):
            result.add(word)
    return result


def safe_typos(word: str, language: str, known: set[str], seed: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def add(value: str, category: str) -> None:
        value = unicodedata.normalize("NFC", value)
        if value and value != word and value.casefold() not in known and value not in {
                prior for prior, _ in result}:
            result.append((value, category))

    order = sorted(range(len(word)), key=lambda index: hashlib.sha256(
        f"{seed}:{index}".encode()).digest())
    alphabet = ALPHABETS[language]
    for index in order:
        add(word[:index] + word[index + 1:], "missing_letter")
        if index + 1 < len(word) and word[index] != word[index + 1]:
            add(word[:index] + word[index + 1] + word[index] + word[index + 2:],
                "transposition")
        add(word[:index] + word[index] + word[index:], "repeated_letter")
        replacement = alphabet[(alphabet.index(word[index]) + 7) % len(alphabet)]
        add(word[:index] + replacement + word[index + 1:], "substitution")
    return result


def seen_families(training_data: Path, old_corpus: Path) -> dict[str, set[str]]:
    result = {language: set() for language in LANGUAGES}
    for name in ("train.jsonl", "valid.jsonl"):
        for line in (training_data / name).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            result[row["language"]].add(family(row["family"]))
    for language in LANGUAGES:
        for name in (f"spelling-{language}.jsonl", f"punctuation-{language}.jsonl"):
            for line in (old_corpus / name).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                result[language].add(family(row["family"]))
    return result


def spelling_candidates(text: str, language: str, known: set[str], excluded: set[str],
                        seed: int) -> list[dict]:
    result = []
    text = unicodedata.normalize("NFC", text)
    for sentence in SENTENCE_BREAK.split(text):
        for ordinal, match in enumerate(WORDS[language].finditer(sentence)):
            if ordinal < 4:
                continue
            word = match.group().casefold()
            word_family = family(word)
            if word not in known or word_family in excluded:
                continue
            prefix = bounded_prefix(sentence[max(0, match.start() - 512):match.start()]).rstrip()
            if not prefix:
                continue
            identity = hashlib.sha256(
                f"{seed}:qualification:{language}:{word_family}:{prefix}".encode()).hexdigest()
            result.append({"word": word, "family": word_family, "prefix": prefix,
                           "selectionHash": identity})
    return result


def spelling_rows(pool: list[dict], language: str, known: set[str], seed: int) -> list[dict]:
    counts = {("calibration", "typo"): 1000, ("calibration", "correct"): 700,
              ("holdout", "typo"): 1000, ("holdout", "correct"): 700}
    rows = []
    cursor = 0
    ordered = sorted(pool, key=lambda row: hashlib.sha256(
        f"{seed}:qualification-split:{language}:{row['family']}".encode()).digest())
    for (split, cohort), required in counts.items():
        produced = 0
        while produced < required and cursor < len(ordered):
            item = ordered[cursor]
            cursor += 1
            variants = safe_typos(item["word"], language, known,
                                  f"{seed}:{split}:{cohort}:{item['selectionHash']}")
            if not variants:
                continue
            typed, category = variants[0]
            sid = f"{language}-{split}-v2-{cohort}-{produced:04d}"
            if cohort == "typo":
                candidates = [" " + typed, " " + item["word"]]
                expected = 1
            else:
                candidates = [" " + item["word"], " " + typed]
                expected = 0
            row = {
                "corpusVersion": 2, "id": sid, "language": language, "split": split,
                "family": item["family"], "template": f"{split}-wikipedia-{item['selectionHash']}",
                "prefix": item["prefix"], "source": "wikimedia-wikipedia-20231101-qualification",
                "task": "spelling", "cohort": cohort,
                "typed": typed if cohort == "typo" else item["word"],
                "candidates": candidates, "expectedCandidate": expected,
                "category": category if cohort == "typo" else "correct_word",
                "noAuto": False, "ambiguous": False, "position": "end",
                "wordLength": len(item["word"]),
            }
            if cohort == "typo":
                row["expectedSpelling"] = item["word"]
            rows.append(row)
            produced += 1
        if produced != required:
            raise ValueError(f"insufficient spelling rows for {language}/{split}/{cohort}")
    return rows


PROTECTED_BASE = {
    "calibration": {
        "name": ["Amelia", "Nikita"], "surname": ["Cooper", "Lebedev"],
        "brand": ["OpenStreetMap", "Thunderbird"], "command": ["git switch demo", "rg FIXME src"],
        "camel_case": ["pendingBoundary", "runtimeDigest"],
        "snake_case": ["candidate_limit", "session_nonce"],
        "kebab_case": ["context-window", "model-worker"],
        "identifier_python": ["Path.resolve", "secrets.token_hex"],
        "identifier_cpp": ["std::variant", "std::unique_ptr"],
        "identifier_kotlin": ["EditorCommand", "CoroutineScope"],
        "all_caps": ["GGUF"], "digits": ["API36"],
        "mixed": ["модель-runtime"], "hostname": ["ranking.example"],
    },
    "holdout": {
        "name": ["Harper", "Viktoria"], "surname": ["Murphy", "Belova"],
        "brand": ["Nextcloud", "KeePassXC"], "command": ["git restore file", "rg NOTE app"],
        "camel_case": ["activeRevision", "scoringRequest"],
        "snake_case": ["prefix_bytes", "worker_state"],
        "kebab_case": ["candidate-score", "idle-timeout"],
        "identifier_python": ["Path.unlink", "random.Random"],
        "identifier_cpp": ["std::expected", "std::shared_ptr"],
        "identifier_kotlin": ["InputPolicy", "StateFlow"],
        "all_caps": ["BINDER"], "digits": ["API37"],
        "mixed": ["клавиатура-core"], "hostname": ["lexicon.example"],
    },
}
ORTHOGRAPHY = {
    "calibration": [
        ("fiancee", "fiancée", "en_optional_accent"),
        ("expose", "exposé", "en_optional_accent"),
        ("publico", "público", "es_ambiguous_accent"),
        ("practico", "práctico", "es_ambiguous_accent"),
        ("съемка", "съёмка", "ru_yo_e"),
        ("маневр", "манёвр", "ru_yo_e"),
    ],
    "holdout": [
        ("naive", "naïve", "en_optional_accent"),
        ("creme", "crème", "en_optional_accent"),
        ("termino", "término", "es_ambiguous_accent"),
        ("deposito", "depósito", "es_ambiguous_accent"),
        ("свекла", "свёкла", "ru_yo_e"),
        ("шофер", "шофёр", "ru_yo_e"),
    ],
}
PROTECTED_PREFIX = {
    "en": "Preserve this exact token in example",
    "ru": "Сохраните точный токен в примере",
    "es": "Conserva el token exacto del ejemplo",
}


def one_edit(value: str) -> str:
    for index in range(len(value) - 1, -1, -1):
        if value[index].isalnum():
            return value[:index] + value[index + 1:]
    raise ValueError("protected token has no editable character")


def protected_rows(language: str) -> list[dict]:
    rows = []
    for split in ("calibration", "holdout"):
        entries = [(category, token, None, None)
                   for category, tokens in PROTECTED_BASE[split].items() for token in tokens]
        entries += [("ambiguous_accent", token, alternative, kind)
                    for token, alternative, kind in ORTHOGRAPHY[split]]
        if len(entries) != 30:
            raise ValueError(f"protected seed count is not 30 for {split}: {len(entries)}")
        for token_index, (category, token, alternative, kind) in enumerate(entries):
            for context_index in range(10):
                sid = f"{language}-{split}-v2-protected-{token_index:02d}-{context_index}"
                rival = alternative or one_edit(token)
                row = {
                    "corpusVersion": 2, "id": sid, "language": language, "split": split,
                    "family": f"protected:{category}:{family(token)}",
                    "template": f"{split}-protected-{token_index:02d}-{context_index}",
                    "prefix": f"{PROTECTED_PREFIX[language]} {context_index}",
                    "source": "authored-protected-token-matrix-v2", "task": "spelling",
                    "cohort": "protected", "typed": token,
                    "candidates": [" " + token, " " + rival], "expectedCandidate": 0,
                    "category": category, "noAuto": True, "ambiguous": category == "ambiguous_accent",
                    "position": "end", "wordLength": len(token),
                }
                if alternative:
                    row.update(orthographicPolicy="preserve_ambiguous_diacritic_or_yo_e",
                               orthographicAlternative=alternative, orthographicKind=kind)
                rows.append(row)
    return rows


def punctuation_candidates(text: str, language: str, seed: int) -> list[dict]:
    result = []
    text = unicodedata.normalize("NFC", text)
    for match in BOUNDARY.finditer(text):
        marker, whitespace, observed = match.groups()
        if marker.isspace():
            if marker != " " or whitespace:
                continue
        elif marker in ".,:":
            if not whitespace:
                continue
        else:
            continue
        word = observed.casefold()
        if not 3 <= len(word) <= 20 or not all(char in ALPHABETS[language] for char in word):
            continue
        if marker in ".,:":
            boundary = marker + " "
            prefix_end = match.start(1)
        else:
            boundary = " "
            prefix_end = match.start(1)
        if boundary == ". ":
            if observed[:1] != observed[:1].upper():
                continue
        elif observed != word:
            continue
        prefix = bounded_prefix(text[max(0, prefix_end - 512):prefix_end]).rstrip()
        if not prefix:
            continue
        identity = hashlib.sha256(
            f"{seed}:punctuation:{language}:{boundary}:{prefix}:{word}".encode()).hexdigest()
        result.append({"prefix": prefix, "word": word, "boundary": boundary,
                       "selectionHash": identity})
    return result


def punctuation_rows(pool: list[dict], language: str) -> list[dict]:
    rows = []
    by_boundary = {boundary: [] for boundary in (" ", ", ", ": ", ". ")}
    for row in pool:
        by_boundary[row["boundary"]].append(row)
    for boundary, entries in by_boundary.items():
        entries.sort(key=lambda row: row["selectionHash"])
        if len(entries) < 100:
            raise ValueError(f"insufficient punctuation rows for {language}/{boundary!r}")
        for split, selected in (("calibration", entries[:50]), ("holdout", entries[50:100])):
            for item in selected:
                sid = f"{language}-{split}-v2-punct-{len(rows):04d}"
                boundaries = [" ", ", ", ": ", ". "]
                candidates = [value + (item["word"][:1].upper() + item["word"][1:]
                              if value == ". " else item["word"]) for value in boundaries]
                rows.append({
                    "corpusVersion": 2, "id": sid, "language": language, "split": split,
                    "family": f"punctuation:{item['selectionHash']}",
                    "template": f"{split}-punctuation-{item['selectionHash']}",
                    "prefix": item["prefix"],
                    "source": "wikimedia-wikipedia-20231101-qualification",
                    "task": "punctuation", "cohort": "punctuation",
                    "currentWord": item["word"], "boundaries": boundaries,
                    "candidates": candidates, "expectedCandidate": boundaries.index(boundary),
                    "expectedBoundary": boundary, "ambiguous": boundary == " ",
                    "noAuto": True, "category": "observed_boundary", "position": "boundary",
                })
    return rows


def keep_bounded(heap: list[tuple[int, str, dict]], seen: set[str], row: dict,
                 limit: int = 512) -> None:
    identity = row["selectionHash"]
    if identity in seen:
        return
    rank = int(identity, 16)
    entry = (-rank, identity, row)
    if len(heap) < limit:
        heapq.heappush(heap, entry)
        seen.add(identity)
    elif rank < -heap[0][0]:
        removed = heapq.heapreplace(heap, entry)
        seen.remove(removed[1])
        seen.add(identity)


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda item: (item["split"] != "calibration", item["id"])):
            stream.write(canonical(row).decode("utf-8") + "\n")


def run(args: argparse.Namespace) -> None:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required for qualification corpus generation") from error
    lock_path = Path(args.lock).resolve(strict=True)
    lock = json.loads(lock_path.read_text())
    inputs = Path(args.inputs).resolve(strict=True)
    frequencies = Path(args.frequency_inputs).resolve(strict=True)
    training_data = Path(args.training_data).resolve(strict=True)
    old_corpus = Path(args.old_corpus).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists() or not (output.is_relative_to(REPO / "build")
                               or output == HERE / "corpus"):
        raise ValueError("qualification output must be fresh")
    actual_sources = {name: sha(inputs / name) for name in sorted(lock["files"])}
    if actual_sources != {name: value["sha256"] for name, value in sorted(lock["files"].items())}:
        raise ValueError("qualification Wikipedia digest mismatch")
    if any((inputs / name).stat().st_size != value["bytes"]
           for name, value in lock["files"].items()):
        raise ValueError("qualification Wikipedia size mismatch")
    expected_frequencies = lock["frequencyWords"]
    if {name: sha(frequencies / name) for name in sorted(expected_frequencies)} != expected_frequencies:
        raise ValueError("qualification frequency digest mismatch")
    excluded = seen_families(training_data, old_corpus)
    all_rows = []
    source_receipts = {}
    selection = lock["articleSelection"]
    for language in LANGUAGES:
        known = vocabulary(frequencies / f"{language}_50k.txt", language)
        best_words: dict[str, dict] = {}
        punctuation_heaps = {boundary: [] for boundary in (" ", ", ", ": ", ". ")}
        punctuation_seen = {boundary: set() for boundary in punctuation_heaps}
        articles = 0
        selected_articles = 0
        parquet_file = parquet.ParquetFile(inputs / lock["languageFiles"][language])
        for batch in parquet_file.iter_batches(batch_size=64, columns=["id", "text"]):
            for article_id, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
                articles += 1
                rank = int.from_bytes(hashlib.sha256(
                    f"{selection['seed']}:{language}:{article_id}".encode()).digest()[:8], "big")
                if rank % selection["modulus"] != selection["residue"]:
                    continue
                selected_articles += 1
                for item in spelling_candidates(text or "", language, known, excluded[language], 3042026):
                    current = best_words.get(item["family"])
                    if current is None or item["selectionHash"] < current["selectionHash"]:
                        best_words[item["family"]] = item
                for item in punctuation_candidates(text or "", language, 3042026):
                    keep_bounded(punctuation_heaps[item["boundary"]],
                                 punctuation_seen[item["boundary"]], item)
        punctuation_pool = [entry[2] for heap in punctuation_heaps.values() for entry in heap]
        language_spelling = spelling_rows(list(best_words.values()), language, known, 3042026)
        language_protected = protected_rows(language)
        language_punctuation = punctuation_rows(punctuation_pool, language)
        all_rows += language_spelling + language_protected + language_punctuation
        source_receipts[language] = {
            "articlesScanned": articles, "articlesSelected": selected_articles,
            "eligibleSpellingFamilies": len(best_words),
            "punctuationObservationsRetained": len(punctuation_pool),
        }
    evaluator_spec = importlib.util.spec_from_file_location("final_qualification_evaluator",
                                                            EVAL_ROOT / "evaluate.py")
    evaluator = importlib.util.module_from_spec(evaluator_spec)
    evaluator_spec.loader.exec_module(evaluator)
    validation = evaluator.validate(all_rows)
    output.mkdir(parents=True)
    for language in LANGUAGES:
        write_rows(output / f"spelling-{language}.jsonl",
                   [row for row in all_rows if row["language"] == language
                    and row["task"] == "spelling" and row["cohort"] != "protected"])
        write_rows(output / f"punctuation-{language}.jsonl",
                   [row for row in all_rows if row["language"] == language and row["task"] == "punctuation"])
    write_rows(output / "protected-tokens.jsonl",
               [row for row in all_rows if row.get("cohort") == "protected"])
    manifest = {
        "schemaVersion": 1, "corpusVersion": 2,
        "scope": "smart-typing-0.3-final-qualification-v2",
        "frozenBeforeScoring": True, "containsPersonalMessages": False,
        "usesRevealedHoldoutRows": False,
        "source": {"repository": lock["repository"], "snapshot": lock["snapshot"],
                   "parquetRevision": lock["parquetRevision"], "licenses": lock["licenses"],
                   "files": actual_sources, "articleSelection": selection},
        "sourceReceipts": source_receipts,
        "trainingData": {name: sha(training_data / name)
                         for name in ("manifest.json", "train.jsonl", "valid.jsonl")},
        "oldCorpusManifestSha256": sha(old_corpus / "manifest.json"),
        "validation": validation,
        "files": {name: sha(output / name) for name in FILES},
        "sources": {str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve()),
                    str(lock_path.relative_to(REPO)): sha(lock_path),
                    str((EVAL_ROOT / "evaluate.py").relative_to(REPO)): sha(EVAL_ROOT / "evaluate.py")},
    }
    (output / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    counts = Counter((row["language"], row["split"],
                      "negative" if row.get("cohort") in ("correct", "protected") else row["cohort"])
                     for row in all_rows)
    print(json.dumps({"rows": len(all_rows), "counts": {"/".join(key): value
                     for key, value in sorted(counts.items())}}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--frequency-inputs", required=True)
    parser.add_argument("--training-data", required=True)
    parser.add_argument("--old-corpus", default=EVAL_ROOT)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
