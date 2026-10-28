#!/usr/bin/env python3
"""Train and evaluate a compact ranker that can explicitly choose the original word.

The train command may read only disclosed public train/development observations.  It freezes a
candidate and zero-regression thresholds before the evaluate command can read an external
holdout.  Evaluation is fail-closed and exits non-zero when promotion is refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from catboost import CatBoostRanker, Pool

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import neural_refinement as neural  # noqa: E402
import rank_refinement as rank  # noqa: E402
sys.path.insert(0, str(ROOT / "tools/eval/smart-typing-0.3/pipeline"))
import evaluate_compact_autocorrection as gate  # noqa: E402


SCHEMA = 1
SEED = 19092026
SPLIT_SEED = "abstaining-ranker-20260919-v1"
WEIGHTS = (1, 3, 6)
MINIMUM_ADDITIONS = 100
CONTEXT_MODEL = ROOT / "app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin"
REJECTED_CASES = frozenset({
    "ru-holdout-v2-correct-0158",
    "ru-holdout-v2-typo-0697",
    "ru-holdout-v4-correct-0451",
    "ru-holdout-v4-typo-0461",
})


def sha256(path: Path | str) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_jsonl(path: Path | str) -> list[dict]:
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")


def original_candidate(row: dict) -> dict:
    return {
        "text": row["typed"], "canonicalKey": row["typed"].casefold(),
        "unitDistance": 0, "frequencyRank": 2_147_483_647,
        "editCost": 0.0, "isFallback": False,
    }


def expected_word(row: dict) -> str:
    return row.get("expectedSpelling", row["typed"]).casefold()


def labelled_group(row: dict, alternatives: list[dict], source: str) -> dict | None:
    candidates = [original_candidate(row)] + [candidate for candidate in alternatives
        if candidate["text"].casefold() != row["typed"].casefold()]
    if len(candidates) < 2:
        return None
    expected = expected_word(row)
    matches = [index for index, candidate in enumerate(candidates)
               if candidate["text"].casefold() == expected]
    target = matches[0] if row["cohort"] == "typo" and not row["noAuto"] and matches else 0
    return {"row": row, "candidates": candidates, "target": target,
            "expectedAvailable": target != 0, "source": source}


def base_groups(directory: Path, partition: str) -> list[dict]:
    records = rank.verified_groups(directory / f"{partition}.jsonl", partition)
    result = []
    for row, alternatives, _ in records:
        group = labelled_group(row, alternatives, "base")
        if group is not None:
            result.append(group)
    return result


def structurally_eligible(observation: dict, alternatives: list[dict]) -> bool:
    generation = observation.get("fullTokenGeneration") or {}
    local = generation.get("localSearch") or {}
    return (local.get("completion") == "COMPLETE" and alternatives and
            gate.structurally_eligible(len(alternatives), generation.get("completion")))


def product_groups(rows_path: Path, observations_path: Path, split: str) -> list[dict]:
    rows = [row for row in read_jsonl(rows_path) if row["split"] == split]
    observations = read_jsonl(observations_path)
    if ([row["id"] for row in rows] != [item.get("id") for item in observations] or
            any(item.get("split") != split or item.get("status") != "COMPLETE"
                for item in observations)):
        raise ValueError("OBSERVATION_IDENTITY")
    result = []
    for row, observation in zip(rows, observations, strict=True):
        if row["language"] != "ru" or observation.get("localDecision") is not None:
            continue
        source = observation.get("compactSourceMorphology") or {}
        generation = observation.get("fullTokenGeneration") or {}
        alternatives = (generation.get("localSearch") or {}).get("alternatives") or []
        if (source.get("available") is not True or source.get("present") is True or
                not structurally_eligible(observation, alternatives)):
            continue
        group = labelled_group(row, alternatives, "product")
        if group is not None:
            result.append(group)
    return result


def is_development(identifier: str) -> bool:
    if identifier in REJECTED_CASES:
        return False
    value = hashlib.sha256(f"{SPLIT_SEED}:{identifier}".encode()).hexdigest()
    return int(value[:8], 16) % 5 == 0


def split_product(groups: list[dict]) -> tuple[list[dict], list[dict]]:
    identifiers = [group["row"]["id"] for group in groups]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("DUPLICATE_PRODUCT_ROW")
    training = [group for group in groups if not is_development(group["row"]["id"])]
    development = [group for group in groups if is_development(group["row"]["id"])]
    eligible_rejections = REJECTED_CASES.intersection(identifiers)
    if not eligible_rejections.issubset({group["row"]["id"] for group in training}):
        raise ValueError("REJECTED_CASE_NOT_TRAINING")
    if not training or not development:
        raise ValueError("EMPTY_PRODUCT_PARTITION")
    return training, development


def fit(groups: list[dict], path: Path) -> None:
    features, labels, group_ids = [], [], []
    for group_id, group in enumerate(groups):
        row, candidates, target = group["row"], group["candidates"], group["target"]
        features.extend(rank.features(row["prefix"], row["typed"], candidate)
                        for candidate in candidates)
        labels.extend(int(index == target) for index in range(len(candidates)))
        group_ids.extend([group_id] * len(candidates))
    model = CatBoostRanker(iterations=128, depth=5, learning_rate=.05,
        loss_function="PairLogitPairwise", random_seed=SEED, thread_count=2,
        verbose=False, allow_writing_files=False)
    model.fit(Pool(np.asarray(features, dtype=np.float32), np.asarray(labels),
                   group_id=np.asarray(group_ids)))
    rank.export_tree(model, path, rank.FEATURES)


def combined_score(blob: bytes, context_model: neural.Model, row: dict, candidate: dict) -> float:
    raw = rank.tree_score(blob, rank.features(row["prefix"], row["typed"], candidate))
    return .8 * math.tanh(raw / 4) + neural.context_score(
        context_model, row["prefix"], candidate["text"])


def unthresholded_metrics(path: Path, groups: list[dict], context_model: neural.Model) -> dict:
    blob = path.read_bytes()
    selected = correct = wrong = abstained = 0
    for group in groups:
        row, candidates, target = group["row"], group["candidates"], group["target"]
        scores = [combined_score(blob, context_model, row, candidate)
                  for candidate in candidates]
        top = max(range(len(scores)), key=lambda index: (scores[index], -index))
        if top == 0:
            abstained += 1
        else:
            selected += 1
            correct += int(target != 0 and top == target)
            wrong += int(target == 0 or top != target)
    return {"groups": len(groups), "selected": selected, "correct": correct,
            "wrong": wrong, "abstained": abstained,
            "precision": correct / selected if selected else None}


def threshold_records(path: Path, groups: list[dict], context_model: neural.Model) -> list[dict]:
    blob = path.read_bytes()
    records = []
    for group in groups:
        row = group["row"]
        alternatives = group["candidates"][1:]
        scores = [combined_score(blob, context_model, row, candidate)
                  for candidate in alternatives]
        order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        top_index = order[0]
        original_score = combined_score(blob, context_model, row, group["candidates"][0])
        second = scores[order[1]] if len(order) > 1 else -math.inf
        top = alternatives[top_index]
        correct = (row["cohort"] == "typo" and not row["noAuto"] and
                   top["text"].casefold() == expected_word(row))
        records.append({
            "id": row["id"], "family": row["family"], "cohort": row["cohort"],
            "topScore": scores[top_index], "margin": scores[top_index] - max(original_score, second),
            "candidate": top["text"], "correct": correct,
            "control": row["cohort"] in {"correct", "protected"},
        })
    return records


def parse_product(value: str) -> tuple[Path, Path, str]:
    fields = value.split("::")
    if len(fields) != 3 or fields[2] not in {"calibration", "holdout"}:
        raise argparse.ArgumentTypeError("product input must be ROWS::OBSERVATIONS::SPLIT")
    return Path(fields[0]).resolve(strict=True), Path(fields[1]).resolve(strict=True), fields[2]


def train_command(args: argparse.Namespace) -> None:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    base = Path(args.base_observations).resolve(strict=True)
    base_train, base_dev = base_groups(base, "train"), base_groups(base, "dev")
    products = []
    for rows, observations, split in args.product:
        products.extend(product_groups(rows, observations, split))
    product_train, product_dev = split_product(products)
    context_model = neural.load_model(CONTEXT_MODEL)
    variants = {}
    for weight in WEIGHTS:
        path = output / f"ranker-w{weight}.bin"
        fit(base_train + product_train * weight, path)
        records = threshold_records(path, product_dev, context_model)
        policy, additions = gate.calibrate(records, MINIMUM_ADDITIONS)
        variants[str(weight)] = {
            "path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size,
            "baseDev": unthresholded_metrics(path, base_dev, context_model),
            "productDev": unthresholded_metrics(path, product_dev, context_model),
            "thresholds": policy,
            "additions": {key: value for key, value in additions.items() if key != "selectedIds"},
        }
    selected_weight = max(WEIGHTS, key=lambda weight: (
        variants[str(weight)]["additions"]["correctAdditions"],
        variants[str(weight)]["baseDev"]["correct"], -variants[str(weight)]["bytes"], -weight))
    selected = variants[str(selected_weight)]
    inputs = [Path(__file__), Path(rank.__file__), Path(neural.__file__),
              ROOT / "tools/eval/smart-typing-0.3/pipeline/evaluate_compact_autocorrection.py",
              CONTEXT_MODEL, base / "train.jsonl", base / "dev.jsonl", base / "manifest.json"]
    for rows, observations, _ in args.product:
        inputs += [rows, observations]
    policy = {
        "schemaVersion": SCHEMA, "stage": "frozen-before-external-holdout",
        "model": {"path": selected["path"], "sha256": selected["sha256"],
                  "bytes": selected["bytes"]},
        "contextModel": {"path": str(CONTEXT_MODEL.relative_to(ROOT)),
                         "sha256": sha256(CONTEXT_MODEL)},
        "minimumScore": selected["thresholds"]["minimumScore"],
        "minimumMargin": selected["thresholds"]["minimumMargin"],
        "minimumAdditions": MINIMUM_ADDITIONS,
        "admission": "local-complete-source-morphology-absent-original-aware",
        "zeroNewIncorrectRequired": True, "zeroNewControlChangesRequired": True,
        "selectedProductWeight": selected_weight,
        "bindings": {str(path.resolve().relative_to(ROOT)): sha256(path) for path in inputs},
        "partitions": {
            "baseTrain": len(base_train), "baseDev": len(base_dev),
            "productTrain": [group["row"]["id"] for group in product_train],
            "productDev": [group["row"]["id"] for group in product_dev],
            "rejectedCases": sorted(REJECTED_CASES),
        },
        "selection": {"variants": variants, "selectedWeight": selected_weight},
    }
    write_json(output / "frozen-policy.json", policy)
    print(json.dumps({"selectedWeight": selected_weight, "modelSha256": selected["sha256"],
                      "additions": selected["additions"]}, ensure_ascii=False))


def verify_policy(policy: dict) -> tuple[Path, neural.Model]:
    if policy.get("schemaVersion") != SCHEMA or policy.get("stage") != "frozen-before-external-holdout":
        raise ValueError("INVALID_FROZEN_POLICY")
    for relative, digest in policy.get("bindings", {}).items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"FROZEN_INPUT_DRIFT:{relative}")
    model_path = ROOT / policy["model"]["path"]
    if (model_path.stat().st_size != policy["model"]["bytes"] or
            sha256(model_path) != policy["model"]["sha256"]):
        raise ValueError("FROZEN_MODEL_DRIFT")
    context_path = ROOT / policy["contextModel"]["path"]
    if sha256(context_path) != policy["contextModel"]["sha256"]:
        raise ValueError("FROZEN_CONTEXT_DRIFT")
    return model_path, neural.load_model(context_path)


def evaluate_command(args: argparse.Namespace) -> None:
    policy_path = Path(args.policy).resolve(strict=True)
    policy = json.loads(policy_path.read_text())
    model_path, context_model = verify_policy(policy)
    rows_path, observations_path = Path(args.rows).resolve(strict=True), Path(args.observations).resolve(strict=True)
    if sha256(rows_path) in policy["bindings"].values() or sha256(observations_path) in policy["bindings"].values():
        raise ValueError("HOLDOUT_REUSES_TRAINING_INPUT")
    groups = product_groups(rows_path, observations_path, args.split)
    records = threshold_records(model_path, groups, context_model)
    additions = gate.threshold_metrics(records, policy["minimumScore"], policy["minimumMargin"])
    rows, observations = read_jsonl(rows_path), read_jsonl(observations_path)
    active = gate.active_metrics(rows, observations, args.split)
    proposed = gate.combined_metrics(active, additions)
    decision = gate.promotion_decision(active, proposed, additions["additions"],
                                       policy["minimumAdditions"])
    report = {
        "schemaVersion": SCHEMA, "stage": "external-holdout-promotion-decision",
        "policySha256": sha256(policy_path),
        "bindings": {str(rows_path.relative_to(ROOT)): sha256(rows_path),
                     str(observations_path.relative_to(ROOT)): sha256(observations_path)},
        "holdout": {"records": len(records),
                    "additions": {key: value for key, value in additions.items()
                                  if key != "selectedIds"},
                    "active": active, "proposed": proposed, "decision": decision},
    }
    write_json(Path(args.output), report)
    print(json.dumps(report["holdout"], ensure_ascii=False))
    if not decision["promotionApproved"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train_parser = commands.add_parser("train")
    train_parser.add_argument("--base-observations", required=True)
    train_parser.add_argument("--product", action="append", type=parse_product, required=True)
    train_parser.add_argument("--output", required=True)
    train_parser.set_defaults(run=train_command)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--policy", required=True)
    evaluate_parser.add_argument("--rows", required=True)
    evaluate_parser.add_argument("--observations", required=True)
    evaluate_parser.add_argument("--split", choices=("calibration", "holdout"), default="holdout")
    evaluate_parser.add_argument("--output", required=True)
    evaluate_parser.set_defaults(run=evaluate_command)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
