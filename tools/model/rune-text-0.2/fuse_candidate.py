#!/usr/bin/env python3
"""Fuse a qualified host-side adapter into one ordinary Hugging Face model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARCHITECTURE_KEYS = (
    "model_type", "hidden_size", "intermediate_size", "num_hidden_layers",
    "num_attention_heads", "num_key_value_heads", "vocab_size", "head_dim",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def files(directory: Path) -> dict[str, str]:
    return {str(path.relative_to(directory)): sha(path) for path in sorted(directory.rglob("*"))
            if path.is_file() and ".cache" not in path.parts}


def completed_training(provenance: dict, config: dict) -> bool:
    segment = provenance.get("trainingSegment")
    return (segment is None or (
        segment.get("completedAfter") == config["training"]["iterations"]
        and segment.get("remainingAfter") == 0))


def run(args: argparse.Namespace) -> None:
    base = Path(args.base).resolve(strict=True)
    adapter = Path(args.adapter).resolve(strict=True)
    output = Path(args.output).resolve()
    config_path = Path(args.config).resolve(strict=True)
    lock_path = Path(args.lock).resolve(strict=True)
    python = Path(args.python).absolute()
    if not python.is_file():
        raise ValueError("training interpreter does not exist")
    if output.exists() or not output.is_relative_to(REPO / "build"):
        raise ValueError("output must be a fresh directory below build")
    config = json.loads(config_path.read_text())
    provenance = json.loads((adapter / "provenance.json").read_text())
    if (provenance.get("scope") != "rune-text-0.2-pairwise-adapter"
            or provenance.get("smokeOnly") is not False
            or provenance.get("configSha256") != sha(config_path)
            or provenance.get("sourceLockSha256") != sha(lock_path)
            or not completed_training(provenance, config)
            or sha(adapter / "adapters.safetensors") != provenance["outputs"]["adapters.safetensors"]
            or sha(adapter / "adapter_config.json") != provenance["outputs"]["adapter_config.json"]
            or ("optimizer.safetensors" in provenance["outputs"]
                and sha(adapter / "optimizer.safetensors")
                != provenance["outputs"]["optimizer.safetensors"])):
        raise ValueError("adapter is not an exact completed candidate run")
    if any(sha(REPO / name) != digest for name, digest in provenance["sources"].items()):
        raise ValueError("training source drift")
    output.mkdir(parents=True)
    fused = output / "fused"
    command = [str(python), "-m", "mlx_lm.fuse", "--model", str(base),
               "--adapter-path", str(adapter), "--save-path", str(fused)]
    with (output / "fuse.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
    base_config = json.loads((base / "config.json").read_text())
    fused_config = json.loads((fused / "config.json").read_text())
    architecture = {key: base_config.get(key) for key in ARCHITECTURE_KEYS}
    if architecture != {key: fused_config.get(key) for key in ARCHITECTURE_KEYS}:
        raise ValueError("fused model changed the runtime architecture")
    fused_files = files(fused)
    weight_files = [name for name in fused_files if name.endswith(".safetensors")]
    if not weight_files or any("adapter" in name.casefold() for name in fused_files):
        raise ValueError("fused output is not a standalone model")
    manifest = {
        "schemaVersion": 1, "scope": "rune-text-0.2-fused-candidate",
        "configSha256": sha(config_path), "sourceLockSha256": sha(lock_path),
        "adapterProvenanceSha256": sha(adapter / "provenance.json"),
        "architecture": architecture, "runtimeAdapter": False,
        "command": ["python", "-m", "mlx_lm.fuse", "--model", "<base>",
                    "--adapter-path", "<adapter>", "--save-path", "<fused>"],
        "files": fused_files,
        "weightBytes": sum((fused / name).stat().st_size for name in weight_files),
        "fuseLogSha256": sha(output / "fuse.log"),
        "sources": {str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve())},
    }
    (output / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(json.dumps({"architecture": architecture, "weightBytes": manifest["weightBytes"]}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--config", default=HERE / "training-config.json")
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    run(parser.parse_args())
