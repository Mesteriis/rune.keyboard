#!/usr/bin/env python3
"""Train the abstaining ranker with exact public morphology/entity retrieval.

This is a new experiment wrapper so previously frozen abstaining policies retain
their original implementation identity. It replaces only group construction;
model fitting, threshold calibration, freeze verification, and fail-closed
promotion decisions remain owned by abstaining_ranker.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import abstaining_ranker as base  # noqa: E402
import rare_word_supplement as rare  # noqa: E402
import rank_refinement as rank  # noqa: E402
sys.path.insert(0, str(ROOT / "tools/morphology"))
from dictionary_index import DictionaryIndex  # noqa: E402


MAX_AUGMENTED_ALTERNATIVES = 64


class Augmenter:
    def __init__(self, morphology: DictionaryIndex, supplement: set[str], ranks: dict[str, int]):
        self.morphology = morphology
        self.supplement = supplement
        self.ranks = ranks

    def apply(self, row: dict, alternatives: list[dict]) -> list[dict] | None:
        if row["language"] != "ru":
            return alternatives
        augmented = rare.augment_candidates(
            row["typed"], alternatives, self.morphology.contains, self.supplement, self.ranks)
        if augmented is not None and len(augmented) > MAX_AUGMENTED_ALTERNATIVES:
            raise ValueError("AUGMENTED_CANDIDATE_BUDGET")
        return augmented


def augmented_base_groups(directory: Path, partition: str, augmenter: Augmenter) -> list[dict]:
    records = rank.verified_groups(directory / f"{partition}.jsonl", partition)
    result = []
    for row, alternatives, _ in records:
        alternatives = augmenter.apply(row, alternatives)
        if alternatives is None:
            continue
        group = base.labelled_group(row, alternatives, "base-augmented")
        if group is not None:
            result.append(group)
    return result


def augmented_product_groups(rows_path: Path, observations_path: Path, split: str,
        augmenter: Augmenter) -> list[dict]:
    rows = [row for row in base.read_jsonl(rows_path) if row["split"] == split]
    observations = base.read_jsonl(observations_path)
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
        local = generation.get("localSearch") or {}
        alternatives = local.get("alternatives") or []
        if (source.get("available") is not True or source.get("present") is True or
                local.get("completion") != "COMPLETE"):
            continue
        alternatives = augmenter.apply(row, alternatives)
        if alternatives is None or not alternatives or not base.gate.structurally_eligible(
                len(alternatives), generation.get("completion")):
            continue
        group = base.labelled_group(row, alternatives, "product-augmented")
        if group is not None:
            result.append(group)
    return result


def install_group_hooks(augmenter: Augmenter) -> None:
    base.base_groups = lambda directory, partition: augmented_base_groups(directory, partition, augmenter)
    base.product_groups = lambda rows, observations, split: augmented_product_groups(
        rows, observations, split, augmenter)


def relative(path: Path) -> str:
    return str(path.resolve(strict=True).relative_to(ROOT))


def train(args: argparse.Namespace, augmenter: Augmenter) -> None:
    install_group_hooks(augmenter)
    base.train_command(args)
    policy_path = Path(args.output).resolve() / "frozen-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    supplement = Path(args.supplement).resolve(strict=True)
    morphology = Path(args.morphology).resolve(strict=True)
    extra = [Path(__file__), Path(rare.__file__), supplement / "manifest.json",
             supplement / "words.txt", supplement / "counts.tsv", morphology]
    policy["admission"] = "complete-source-public-membership-absent-original-aware-augmented-unit-edit"
    policy["candidateRetrieval"] = {
        "kind": "public-morphology-plus-capitalized-entity-unit-edit",
        "maximumAlternatives": MAX_AUGMENTED_ALTERNATIVES,
        "supplement": relative(supplement),
        "morphology": relative(morphology),
    }
    policy["bindings"].update({relative(path): base.sha256(path) for path in extra})
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True, indent=2,
                                      allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"policySha256": base.sha256(policy_path),
                      "retrieval": policy["candidateRetrieval"]}, ensure_ascii=False))


def evaluate(args: argparse.Namespace, policy: dict, augmenter: Augmenter) -> None:
    install_group_hooks(augmenter)
    base.evaluate_command(args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train_parser = commands.add_parser("train")
    train_parser.add_argument("--base-observations", required=True)
    train_parser.add_argument("--product", action="append", type=base.parse_product, required=True)
    train_parser.add_argument("--supplement", type=Path, required=True)
    train_parser.add_argument("--morphology", type=Path, required=True)
    train_parser.add_argument("--output", required=True)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--policy", required=True)
    evaluate_parser.add_argument("--rows", required=True)
    evaluate_parser.add_argument("--observations", required=True)
    evaluate_parser.add_argument("--split", choices=("calibration", "holdout"), default="holdout")
    evaluate_parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = None
    if args.command == "train":
        supplement_path = args.supplement.resolve(strict=True)
        morphology_path = args.morphology.resolve(strict=True)
    else:
        policy = json.loads(Path(args.policy).resolve(strict=True).read_text(encoding="utf-8"))
        retrieval = policy.get("candidateRetrieval") or {}
        if retrieval.get("kind") != "public-morphology-plus-capitalized-entity-unit-edit":
            raise ValueError("AUGMENTED_POLICY_REQUIRED")
        supplement_path = (ROOT / retrieval["supplement"]).resolve(strict=True)
        morphology_path = (ROOT / retrieval["morphology"]).resolve(strict=True)
    supplement, ranks = rare.read_supplement(supplement_path)
    with DictionaryIndex(morphology_path) as morphology:
        augmenter = Augmenter(morphology, supplement, ranks)
        if args.command == "train":
            train(args, augmenter)
        else:
            evaluate(args, policy, augmenter)


if __name__ == "__main__":
    main()
