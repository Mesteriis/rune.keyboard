"""Reusable source-bound builder for future independent Russian spelling holdouts."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

import independent_corpus_guard as registry_guard
import joint_public_sources
import prepare_external_spelling_holdout as common


ROOT = Path(__file__).resolve().parents[2]
TYPO_ROWS = 1_000
CORRECT_ROWS = 700


@dataclass(frozen=True)
class HoldoutSpec:
    version: int
    shard: str
    source_sha256: str
    source_bytes: int
    seed: int

    def __post_init__(self) -> None:
        if self.version < 7 or len(self.shard) != 4 or not self.shard.isdigit():
            raise ValueError("HOLDOUT_SPEC")
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
            raise ValueError("SOURCE_SHA256")
        if self.source_bytes <= 0 or self.seed <= 0:
            raise ValueError("SOURCE_SIZE_OR_SEED")

    @property
    def source_path(self) -> str:
        return f"20231101.ru/train/{self.shard}.parquet"


def canonical_family_keys(families):
    if not isinstance(families, list) or not families or any(not isinstance(f, str) or not f.strip() for f in families):
        raise ValueError('FRESH_CANONICAL_FAMILY_SCHEMA')
    return {' '.join(unicodedata.normalize('NFC', family).casefold().split()) for family in families}


def build_rows(spec: HoldoutSpec, pool: list[dict], known: set[str], generator,
               typo_count: int = TYPO_ROWS, correct_count: int = CORRECT_ROWS) -> list[dict]:
    ordered = sorted(pool, key=lambda row: hashlib.sha256(
        f"{spec.seed}:external-holdout:{row['family']}:{row['selectionHash']}".encode()).digest())
    rows: list[dict] = []
    cursor = 0
    seen_canonical = set()
    for cohort, required in (("typo", typo_count), ("correct", correct_count)):
        produced = 0
        while produced < required and cursor < len(ordered):
            item = ordered[cursor]
            cursor += 1
            families = canonical_family_keys(item['sourceEvidence']['families']) if 'sourceEvidence' in item else set()
            if seen_canonical & families:
                continue
            variants = generator.safe_typos(item["word"], "ru", known,
                f"{spec.seed}:holdout:{cohort}:{item['selectionHash']}")
            if not variants:
                continue
            typo, category = variants[0]
            candidates = [" " + typo, " " + item["word"]]
            expected = 1
            if cohort == "correct":
                candidates.reverse()
                expected = 0
            row = {
                "ambiguous": False, "candidates": candidates,
                "category": category if cohort == "typo" else "correct_word",
                "cohort": cohort, "corpusVersion": spec.version,
                "expectedCandidate": expected, "family": item["family"],
                "id": f"ru-holdout-v{spec.version}-{cohort}-{produced:04d}",
                "language": "ru", "noAuto": False, "position": "end",
                "prefix": item["prefix"],
                "source": f"wikimedia-wikipedia-20231101-ru-{spec.shard}-external-v{spec.version}",
                "split": "holdout", "task": "spelling",
                "template": f"holdout-wikipedia-{item['selectionHash']}",
                "typed": typo if cohort == "typo" else item["word"],
                "wordLength": len(item["word"]),
            }
            if cohort == "typo":
                row["expectedSpelling"] = item["word"]
            if "sourceEvidence" in item:
                row.update(item["sourceEvidence"])
            rows.append(row)
            seen_canonical.update(families)
            produced += 1
    if Counter(row["cohort"] for row in rows) != Counter(typo=typo_count, correct=correct_count):
        raise ValueError("INSUFFICIENT_FRESH_HOLDOUT")
    if len({row["family"] for row in rows}) != len(rows):
        raise ValueError("HOLDOUT_FAMILY_OVERLAP")
    return rows


def source_bound_candidates(article, text, known, excluded, seed, generator, lexicon):
    """Attach uniquely matched public source and all dictionary analyses."""
    if not isinstance(article, str) or not article.isascii() or not article.isdecimal() or len(article) > 20:
        raise ValueError('FRESH_SOURCE_ARTICLE')
    if not isinstance(text, str):
        raise ValueError('FRESH_SOURCE_TEXT')
    text = unicodedata.normalize('NFC', text)
    candidates = generator.spelling_candidates(text, 'ru', known, excluded, seed)
    indexed = {}
    for sentence, start in registry_guard.selector_segments(text):
        for ordinal, match in enumerate(generator.WORDS['ru'].finditer(sentence)):
            if ordinal < 4 or not registry_guard.whole_selector_token(text, sentence, start, match, {}):
                continue
            word = match.group().casefold()
            family = generator.family(word)
            prefix = generator.bounded_prefix(sentence[max(0, match.start()-512):match.start()]).rstrip()
            if not prefix:
                continue
            selection = hashlib.sha256(f'{seed}:qualification:ru:{family}:{prefix}'.encode()).hexdigest()
            indexed.setdefault((word, family, prefix, selection), []).append((sentence, start, match))
    result = []
    for item in candidates:
        matches = indexed.get((item['word'], item['family'], item['prefix'], item['selectionHash']), [])
        if len(matches) != 1:
            continue  # Ambiguous source positions cannot certify a proposal.
        sentence, start, match = matches[0]
        families = sorted({analysis.lemma for analysis in lexicon.analyses(item['word'])})
        if not families:
            continue
        evidence = registry_guard.attach_selector_source(
            {'articleId': article, 'expectedSpelling': match.group()}, text, sentence, start, match, {})
        evidence.update(expectedSpelling=item['word'], sourceRepository='wikimedia/wikipedia', families=families)
        result.append(dict(item, sourceEvidence=evidence))
    return result


def require_disjoint_canonical_families(rows):
    seen = set()
    for row in rows:
        families = canonical_family_keys(row['families'])
        if seen & families:
            raise ValueError('FRESH_CANONICAL_FAMILY_OVERLAP')
        seen.update(families)


def prepare_source_resources(snapshot, source, source_sha, frequency, frequency_sha, script, exclusions, bindings):
    inputs = registry_guard.selector_inputs(snapshot, source, source_sha, frequency, frequency_sha, collector=Path(__file__))
    extra = {'script': (script, common.sha256(script))}
    for name in ('prepare_external_spelling_holdout.py', 'joint_public_sources.py',
                 'holdout_ledger.py', 'control_ledger.py', 'public_corpus_preparation_v1.py',
                 'conversation_split_checks.py', 'source_identities.py', 'recover_legacy_families.py'):
        path = Path(__file__).with_name(name)
        extra['helper-' + name] = (path, common.sha256(path))
    for index, path in enumerate(exclusions):
        resolved = path.resolve(strict=True)
        key = str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)
        extra[f'exclusion-{index}'] = (resolved, bindings[key])
    inputs.update(joint_public_sources.snapshot(extra))
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    import ranker
    if Path(ranker.__file__).resolve() != (ROOT / 'tools/morphology/ranker.py').resolve():
        raise ValueError('FRESH_DICTIONARY_HELPER_IDENTITY')
    lexicon = ranker.PymorphyLexicon(cache_size=16384)
    return inputs, lexicon, lexicon.receipt()


def register_source_article(article, seen):
    if (not isinstance(article, str) or not article.isascii() or not article.isdecimal() or
            len(article) > 20 or str(int(article)) in seen):
        raise ValueError('FRESH_SOURCE_ARTICLE')
    seen.add(str(int(article)))


def prepare(spec: HoldoutSpec, script_path: Path, parquet_path: Path, frequency_path: Path,
            exclusions: list[Path], output: Path, *, historical_reproduction: bool = False) -> dict:
    snapshot = registry_guard.begin(historical_reproduction)
    try:
        import pyarrow
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required") from error
    script = script_path.resolve(strict=True)
    source, frequency, output = (parquet_path.resolve(strict=True),
                                 frequency_path.resolve(strict=True), output.resolve())
    if output.exists() or not output.is_relative_to(ROOT / "build"):
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    if source.stat().st_size != spec.source_bytes or common.sha256(source) != spec.source_sha256:
        raise ValueError("PUBLIC_SOURCE_IDENTITY")
    if common.sha256(frequency) != common.FREQUENCY_SHA256:
        raise ValueError("PUBLIC_FREQUENCY_IDENTITY")
    generator = common.load_generator()
    excluded, exclusion_bindings, excluded_rows = common.excluded_families(
        exclusions, generator.family)
    input_snapshot = None
    lexicon = None
    dictionary_receipt = None
    if snapshot is not None:
        input_snapshot, lexicon, dictionary_receipt = prepare_source_resources(
            snapshot, source, spec.source_sha256, frequency, common.FREQUENCY_SHA256,
            script, exclusions, exclusion_bindings)
    known = generator.vocabulary(frequency, "ru")
    best: dict[str, dict] = {}
    articles = 0
    seen_articles = set()
    for batch in parquet.ParquetFile(source).iter_batches(batch_size=128, columns=["id", "text"]):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            articles += 1
            if snapshot is not None:
                register_source_article(article, seen_articles)
                candidates = source_bound_candidates(article, text, known, excluded, spec.seed, generator, lexicon)
            else:
                candidates = generator.spelling_candidates(text or "", "ru", known, excluded, spec.seed)
            for item in candidates:
                current = best.get(item["family"])
                if current is None or item["selectionHash"] < current["selectionHash"]:
                    best[item["family"]] = item
    rows = build_rows(spec, list(best.values()), known, generator)
    if any(generator.family(row["family"]) in excluded for row in rows):
        raise ValueError("EXCLUDED_FAMILY_SELECTED")
    if snapshot is not None:
        require_disjoint_canonical_families(rows)
    registry_receipt = registry_guard.finish(snapshot, rows)
    if snapshot is not None:
        registry_guard.verify_selector_inputs(input_snapshot)
        if lexicon.receipt() != dictionary_receipt:
            raise ValueError('FRESH_DICTIONARY_DRIFT')
    output.mkdir(parents=True)
    rows_path = output / "rows.jsonl"
    with rows_path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(common.canonical(row).decode("utf-8") + "\n")
    manifest = {
        "schemaVersion": 1, "corpusVersion": spec.version,
        "scope": f"independent-ru-spelling-holdout-v{spec.version}",
        "frozenBeforeScoring": True, "containsPersonalMessages": False,
        "labelsRetainedForPythonOnly": True,
        "source": {"repository": common.SOURCE_REPOSITORY,
                   "revision": common.SOURCE_REVISION, "path": spec.source_path,
                   "bytes": spec.source_bytes, "sha256": spec.source_sha256,
                   "license": "CC BY-SA 3.0 and GFDL"},
        "frequency": {"path": str(frequency.relative_to(ROOT)),
                      "sha256": common.FREQUENCY_SHA256},
        "exclusions": {"files": exclusion_bindings, "rows": excluded_rows,
                       "families": len(excluded)},
        "selection": {"seed": spec.seed, "articlesScanned": articles,
                      "eligibleFamilies": len(best)},
        "generatorRuntime": {"pyarrowVersion": pyarrow.__version__},
        "counts": {"typo": TYPO_ROWS, "correct": CORRECT_ROWS, "total": len(rows)},
        "files": {"rows.jsonl": common.sha256(rows_path)},
        "sources": {
            str(script.relative_to(ROOT)): common.sha256(script),
            str(Path(__file__).resolve().relative_to(ROOT)): common.sha256(Path(__file__)),
            str(Path(common.__file__).resolve().relative_to(ROOT)): common.sha256(Path(common.__file__)),
            str(common.GENERATOR.relative_to(ROOT)): common.sha256(common.GENERATOR),
        },
    }
    manifest.update(registry_receipt)
    if snapshot is not None:
        manifest['dictionary'] = dictionary_receipt
        manifest['selectionInputBindings'] = {name: digest for name, (_, digest) in sorted(input_snapshot.items())}
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")
    return manifest
