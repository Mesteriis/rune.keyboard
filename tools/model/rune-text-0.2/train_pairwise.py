#!/usr/bin/env python3
"""Train a fused-model LoRA with Rune's bounded average-log-probability objective."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
from typing import Iterator

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
from mlx.utils import tree_flatten, tree_unflatten
import mlx_lm
from mlx_lm import load
from mlx_lm.tuner.trainer import TrainingArgs, train
from mlx_lm.tuner.utils import linear_to_lora_layers
from training_resume import plan as plan_segment
from validation_sampling import balanced_indices


HERE = Path(__file__).resolve().parent


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_base(base: Path, manifest_path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in manifest_path.read_text().splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    actual = {name: sha(base / name) for name in expected}
    if actual != expected:
        raise ValueError("base model digest mismatch")
    return actual


def verify_data(data: Path, config_path: Path, lock_path: Path) -> dict:
    manifest = json.loads((data / "manifest.json").read_text())
    if (manifest.get("scope") != "rune-text-0.2-pairwise-training"
            or manifest.get("usesRevealedHoldoutRows") is not False
            or manifest.get("usesAuthoredCalibrationRows") is not True
            or manifest.get("containsPersonalMessages") is not False
            or manifest.get("configSha256") != sha(config_path)
            or manifest.get("sourceLockSha256") != sha(lock_path)):
        raise ValueError("training data provenance mismatch")
    if any(sha(HERE.parents[2] / name) != digest for name, digest in manifest["sources"].items()):
        raise ValueError("training data generator source drift")
    for name in ("train.jsonl", "valid.jsonl"):
        if sha(data / name) != manifest["outputs"][name]:
            raise ValueError("training data digest mismatch")
    return manifest


def common_prefix(left: list[int], right: list[int]) -> int:
    for index, pair in enumerate(zip(left, right)):
        if pair[0] != pair[1]:
            return index
    return min(len(left), len(right))


class PairDataset:
    def __init__(self, path: Path, tokenizer, maximum_tokens: int):
        self.rows = []
        self.languages = []
        self.sources = []
        self.skipped_zero_span = 0
        self.skipped_overlong = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            chosen = tokenizer.encode(row["prefix"] + row["chosen"], add_special_tokens=True)
            rejected = tokenizer.encode(row["prefix"] + row["rejected"], add_special_tokens=True)
            start = common_prefix(chosen, rejected)
            if max(len(chosen), len(rejected)) > maximum_tokens:
                self.skipped_overlong += 1
                continue
            if start < 1 or start >= min(len(chosen), len(rejected)):
                self.skipped_zero_span += 1
                continue
            self.rows.append((chosen, rejected, start))
            self.languages.append(row["language"])
            self.sources.append(row.get("source", "frequency"))
        if (not self.rows
                or self.skipped_zero_span + self.skipped_overlong > len(self.rows) // 4):
            raise ValueError("too many unusable training pairs")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        return self.rows[index]


def padded(sequences: list[list[int]], maximum: int) -> tuple[np.ndarray, np.ndarray]:
    length = min(max(map(len, sequences)), maximum)
    array = np.zeros((len(sequences), length), dtype=np.int32)
    lengths = np.empty((len(sequences),), dtype=np.int32)
    for index, sequence in enumerate(sequences):
        used = min(len(sequence), maximum)
        array[index, :used] = sequence[:used]
        lengths[index] = used
    return array, lengths


def pair_batches(dataset: PairDataset, batch_size: int, max_seq_length: int,
                 loop: bool = False, seed: int | None = None, comm_group=None,
                 skip_batches: int = 0, **_ignored) -> Iterator[tuple]:
    if comm_group is not None and comm_group.size() != 1:
        raise ValueError("pairwise trainer supports one local worker")
    if len(dataset) < batch_size:
        raise ValueError("dataset is smaller than batch size")
    rng = np.random.default_rng(seed if seed is not None else 0)
    indices = np.arange(len(dataset))
    skipped = 0
    while True:
        rng.shuffle(indices)
        for offset in range(0, len(indices) - batch_size + 1, batch_size):
            if skipped < skip_batches:
                skipped += 1
                continue
            rows = [dataset[int(index)] for index in indices[offset:offset + batch_size]]
            chosen, chosen_lengths = padded([row[0] for row in rows], max_seq_length)
            rejected, rejected_lengths = padded([row[1] for row in rows], max_seq_length)
            starts = np.array([row[2] for row in rows], dtype=np.int32)
            yield (mx.array(chosen), mx.array(np.column_stack((starts, chosen_lengths))),
                   mx.array(rejected), mx.array(np.column_stack((starts, rejected_lengths))))
        if not loop:
            return


def average_log_probability(model, tokens, bounds):
    logits = model(tokens[:, :-1])
    targets = tokens[:, 1:]
    cross_entropy = nn.losses.cross_entropy(logits, targets).astype(mx.float32)
    target_positions = mx.arange(1, targets.shape[1] + 1)
    mask = mx.logical_and(target_positions >= bounds[:, 0:1],
                          target_positions < bounds[:, 1:2])
    counts = mask.sum(axis=1)
    scores = -(cross_entropy * mask).sum(axis=1) / counts
    return scores, counts


def make_loss(temperature: float, chosen_nll_weight: float):
    def pairwise_loss(model, chosen, chosen_bounds, rejected, rejected_bounds):
        chosen_scores, chosen_counts = average_log_probability(model, chosen, chosen_bounds)
        rejected_scores, rejected_counts = average_log_probability(model, rejected, rejected_bounds)
        margin = (chosen_scores - rejected_scores) / temperature
        preference = mx.logaddexp(mx.zeros_like(margin), -margin).mean()
        chosen_nll = -chosen_scores.mean()
        return preference + chosen_nll_weight * chosen_nll, (chosen_counts + rejected_counts).sum()
    return pairwise_loss


def evaluate_accuracy(model, dataset: PairDataset, batch_size: int, maximum_tokens: int,
                      limit_batches: int | None) -> dict:
    correct = 0
    total = 0
    margin_sum = 0.0
    per_language = {language: {"pairs": 0, "correct": 0, "margin": 0.0}
                    for language in sorted(set(dataset.languages))}
    per_source: dict[str, dict] = {}
    limit = None if limit_batches is None else limit_batches * batch_size
    groups = [f"{language}:{source}" for language, source in
              zip(dataset.languages, dataset.sources, strict=True)]
    indices = balanced_indices(groups, limit, seed=0)
    model.eval()
    for offset in range(0, len(indices), batch_size):
        batch_indices = indices[offset:offset + batch_size]
        rows = [dataset[index] for index in batch_indices]
        chosen, chosen_lengths = padded([row[0] for row in rows], maximum_tokens)
        rejected, rejected_lengths = padded([row[1] for row in rows], maximum_tokens)
        starts = np.array([row[2] for row in rows], dtype=np.int32)
        batch = (mx.array(chosen), mx.array(np.column_stack((starts, chosen_lengths))),
                 mx.array(rejected), mx.array(np.column_stack((starts, rejected_lengths))))
        chosen_scores, _ = average_log_probability(model, batch[0], batch[1])
        rejected_scores, _ = average_log_probability(model, batch[2], batch[3])
        margins = chosen_scores - rejected_scores
        mx.eval(margins)
        values = np.array(margins)
        correct += int((values > 0).sum())
        total += len(values)
        margin_sum += float(values.sum())
        for value, index in zip(values, batch_indices, strict=True):
            language = dataset.languages[index]
            source = dataset.sources[index]
            metrics = per_language[language]
            metrics["pairs"] += 1
            metrics["correct"] += int(value > 0)
            metrics["margin"] += float(value)
            source_metrics = per_source.setdefault(
                source, {"pairs": 0, "correct": 0, "margin": 0.0, "languages": {}})
            source_metrics["pairs"] += 1
            source_metrics["correct"] += int(value > 0)
            source_metrics["margin"] += float(value)
            source_language = source_metrics["languages"].setdefault(
                language, {"pairs": 0, "correct": 0, "margin": 0.0})
            source_language["pairs"] += 1
            source_language["correct"] += int(value > 0)
            source_language["margin"] += float(value)
    model.train()
    languages = {language: {"pairs": value["pairs"], "correct": value["correct"],
                 "accuracy": value["correct"] / value["pairs"],
                 "meanMargin": value["margin"] / value["pairs"]}
                 for language, value in per_language.items() if value["pairs"]}
    source_metrics = {
        source: {
            "pairs": value["pairs"], "correct": value["correct"],
            "accuracy": value["correct"] / value["pairs"],
            "meanMargin": value["margin"] / value["pairs"],
            "languages": {
                language: {
                    "pairs": metrics["pairs"], "correct": metrics["correct"],
                    "accuracy": metrics["correct"] / metrics["pairs"],
                    "meanMargin": metrics["margin"] / metrics["pairs"],
                }
                for language, metrics in sorted(value["languages"].items())
            },
        }
        for source, value in sorted(per_source.items())
    }
    return {"pairs": total, "correct": correct, "accuracy": correct / total,
            "meanMargin": margin_sum / total, "languages": languages,
            "sampleSources": source_metrics}


def run(args: argparse.Namespace) -> None:
    base = Path(args.base).resolve(strict=True)
    data = Path(args.data).resolve(strict=True)
    output = Path(args.output).resolve()
    config_path = Path(args.config).resolve(strict=True)
    lock_path = Path(args.lock).resolve(strict=True)
    if output.exists():
        raise ValueError("output directory must be fresh")
    config = json.loads(config_path.read_text())
    lock = json.loads(lock_path.read_text())
    training = dict(config["training"])
    total_iterations = training["iterations"]
    if args.smoke:
        training.update(iterations=2, validationBatches=2, reportEvery=1,
                        evaluateEvery=2, saveEvery=2, gradientAccumulationSteps=1)
        segment = plan_segment(total_iterations, args.completed_iterations, 2,
                               training["gradientAccumulationSteps"])
    else:
        segment = plan_segment(total_iterations, args.completed_iterations,
                               args.segment_iterations, training["gradientAccumulationSteps"])
    if mlx_lm.__version__ != lock["trainingToolchain"]["mlx-lm"]["version"]:
        raise ValueError("mlx-lm version mismatch")
    base_hashes = verify_base(base, (HERE / lock["baseModel"]["sha256Manifest"]).resolve())
    data_manifest = verify_data(data, config_path, lock_path)
    resume = Path(args.resume_adapter).resolve(strict=True) if args.resume_adapter else None
    resume_optimizer = (Path(args.resume_optimizer).resolve(strict=True)
                        if args.resume_optimizer else None)
    if (resume is None) != (args.completed_iterations == 0):
        raise ValueError("resume adapter and positive completed iterations must be provided together")
    if (resume is None) != (resume_optimizer is None):
        raise ValueError("resume adapter and optimizer state must be provided together")
    output.mkdir(parents=True)

    random.seed(config["seed"])
    np.random.seed(config["seed"])
    mx.random.seed(config["seed"])
    model, tokenizer = load(str(base), lazy=True)
    model.freeze()
    lora = config["lora"]
    linear_to_lora_layers(model, lora["numLayers"], {
        "rank": lora["rank"], "scale": lora["scale"], "dropout": lora["dropout"]})
    if resume is not None:
        model.load_weights(str(resume), strict=False)
    trainable = sum(value.size for _, value in tree_flatten(model.trainable_parameters()))
    train_data = PairDataset(data / "train.jsonl", tokenizer, config["maximumSequenceTokens"])
    valid_data = PairDataset(data / "valid.jsonl", tokenizer, config["maximumSequenceTokens"])
    baseline = evaluate_accuracy(model, valid_data, training["batchSize"],
                                 config["maximumSequenceTokens"], training["validationBatches"])
    (output / "baseline.json").write_bytes(canonical(baseline) + b"\n")

    adapter = output / "adapters.safetensors"
    optimizer = optim.AdamW(learning_rate=training["learningRate"])
    if resume_optimizer is not None:
        optimizer.state = tree_unflatten(mx.load(str(resume_optimizer)))
    train(model, optimizer, train_data, valid_data,
          args=TrainingArgs(batch_size=training["batchSize"], iters=segment["segmentIterations"],
              val_batches=training["validationBatches"], steps_per_report=training["reportEvery"],
              steps_per_eval=training["evaluateEvery"], steps_per_save=training["saveEvery"],
              max_seq_length=config["maximumSequenceTokens"], adapter_file=str(adapter),
              grad_accumulation_steps=training["gradientAccumulationSteps"],
              clear_cache_threshold=training["clearCacheThresholdBytes"]),
          loss=make_loss(training["marginTemperature"], training["chosenNllWeight"]),
          iterate_batches=lambda **kwargs: pair_batches(
              **kwargs, seed=config["seed"],
              skip_batches=(segment["completedBefore"]
                            if kwargs["dataset"] is train_data else 0)))
    optimizer_state = output / "optimizer.safetensors"
    mx.save_safetensors(str(optimizer_state), dict(tree_flatten(optimizer.state)))
    final = evaluate_accuracy(model, valid_data, training["batchSize"],
                              config["maximumSequenceTokens"], training["validationBatches"])
    (output / "final.json").write_bytes(canonical(final) + b"\n")
    adapter_config = {
        "model": str(base), "fine_tune_type": "lora", "num_layers": lora["numLayers"],
        "lora_parameters": {"rank": lora["rank"], "scale": lora["scale"],
                            "dropout": lora["dropout"]},
    }
    (output / "adapter_config.json").write_bytes(canonical(adapter_config) + b"\n")
    provenance = {
        "schemaVersion": 1, "scope": "rune-text-0.2-pairwise-adapter",
        "smokeOnly": bool(args.smoke), "configSha256": sha(config_path),
        "sourceLockSha256": sha(lock_path), "dataManifestSha256": sha(data / "manifest.json"),
        "baseFiles": base_hashes, "trainableParameters": trainable,
        "tokenizedRows": {
            "train": len(train_data), "valid": len(valid_data),
            "trainSkippedZeroSpan": train_data.skipped_zero_span,
            "validSkippedZeroSpan": valid_data.skipped_zero_span,
            "trainSkippedOverlong": train_data.skipped_overlong,
            "validSkippedOverlong": valid_data.skipped_overlong,
        },
        "toolchain": {"python": platform.python_version(), "mlx-lm": mlx_lm.__version__},
        "trainingSegment": {
            **segment,
            "resumeAdapterSha256": sha(resume) if resume is not None else None,
            "resumeAdapterFile": resume.name if resume is not None else None,
            "resumeOptimizerSha256": (
                sha(resume_optimizer) if resume_optimizer is not None else None),
            "resumeOptimizerFile": (
                resume_optimizer.name if resume_optimizer is not None else None),
            "resumeProvenanceSha256": (
                sha(resume.parent / "provenance.json")
                if resume is not None and (resume.parent / "provenance.json").is_file() else None),
            "optimizerStateResumed": resume_optimizer is not None,
            "optimizerResetAtResume": False,
        },
        "sources": {str(path.relative_to(HERE.parents[2])): sha(path) for path in
                    (Path(__file__).resolve(), HERE / "training_resume.py",
                     HERE / "validation_sampling.py")},
        "baseline": baseline, "final": final,
        "outputs": {"adapters.safetensors": sha(adapter),
                    "adapter_config.json": sha(output / "adapter_config.json"),
                    "optimizer.safetensors": sha(optimizer_state)},
    }
    (output / "provenance.json").write_bytes(canonical(provenance) + b"\n")
    print(json.dumps({"baseline": baseline, "final": final,
                      "trainingSegment": segment, "smokeOnly": bool(args.smoke)}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default=HERE / "training-config.json")
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--resume-adapter")
    parser.add_argument("--resume-optimizer")
    parser.add_argument("--completed-iterations", type=int, default=0)
    parser.add_argument("--segment-iterations", type=int)
    parser.add_argument("--smoke", action="store_true")
    run(parser.parse_args())
