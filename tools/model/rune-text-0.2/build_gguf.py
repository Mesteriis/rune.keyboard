#!/usr/bin/env python3
"""Convert a fused Rune Text 0.2 candidate and quantize it with pinned llama.cpp."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ASSET = "rune-text-v1-0.2.0-q4_k_m.gguf"
MAXIMUM_ARTIFACT_BYTES = 420_000_000
CONVERTER_PACKAGES = ("torch", "transformers", "tokenizers", "sentencepiece")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_logged(command: list[str], log: Path, timeout: int) -> None:
    with log.open("xb") as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def converter_toolchain(python: Path) -> dict[str, str]:
    program = """
import json, platform
import sentencepiece, tokenizers, torch, transformers
print(json.dumps({
    "python": ".".join(platform.python_version_tuple()[:2]),
    "torch": torch.__version__.split("+")[0],
    "transformers": transformers.__version__,
    "tokenizers": tokenizers.__version__,
    "sentencepiece": sentencepiece.__version__,
}, sort_keys=True))
"""
    completed = subprocess.run(
        [str(python), "-c", program], capture_output=True, text=True,
        check=True, timeout=60)
    return json.loads(completed.stdout)


def run(args: argparse.Namespace) -> None:
    fused_root = Path(args.fused).resolve(strict=True)
    fused = fused_root / "fused"
    llama = Path(args.llama).resolve(strict=True)
    converter_python = Path(args.converter_python).absolute()
    if not converter_python.is_file():
        raise ValueError("converter interpreter does not exist")
    output = Path(args.output).resolve()
    lock_path = Path(args.lock).resolve(strict=True)
    converter_lock_path = Path(args.converter_lock).resolve(strict=True)
    config_path = Path(args.config).resolve(strict=True)
    if output.exists() or not output.is_relative_to(REPO / "build"):
        raise ValueError("output must be a fresh directory below build")
    lock = json.loads(lock_path.read_text())
    actual_converter_toolchain = converter_toolchain(converter_python)
    if actual_converter_toolchain != json.loads(converter_lock_path.read_text()):
        raise ValueError("converter toolchain does not match converter lock")
    fused_manifest = json.loads((fused_root / "manifest.json").read_text())
    if (fused_manifest.get("scope") != "rune-text-0.2-fused-candidate"
            or fused_manifest.get("runtimeAdapter") is not False
            or fused_manifest.get("configSha256") != sha(config_path)
            or fused_manifest.get("sourceLockSha256") != sha(lock_path)):
        raise ValueError("fused candidate provenance mismatch")
    if any(sha(REPO / name) != digest for name, digest in fused_manifest["sources"].items()):
        raise ValueError("fusing source drift")
    for name, digest in fused_manifest["files"].items():
        if sha(fused / name) != digest:
            raise ValueError("fused candidate digest mismatch")
    revision = subprocess.check_output(["git", "-C", str(llama), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(llama), "status", "--porcelain"], text=True)
    if revision != lock["converter"]["revision"] or dirty:
        raise ValueError("llama.cpp checkout is not the pinned clean revision")

    output.mkdir(parents=True)
    build = output / "llama-build"
    cmake = ["cmake", "-S", str(llama), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
             "-DBUILD_SHARED_LIBS=OFF", "-DGGML_NATIVE=OFF", "-DGGML_OPENMP=OFF",
             "-DGGML_BACKEND_DL=OFF", "-DGGML_CPU_ALL_VARIANTS=OFF",
             "-DGGML_CPU_KLEIDIAI=OFF", "-DGGML_LLAMAFILE=OFF",
             "-DLLAMA_BUILD_COMMON=ON", "-DLLAMA_BUILD_TOOLS=ON",
             "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF",
             "-DLLAMA_BUILD_SERVER=OFF", "-DLLAMA_CURL=OFF"]
    run_logged(cmake, output / "cmake-configure.log", 300)
    run_logged(["cmake", "--build", str(build), "--target", "llama-quantize", "--parallel", "2"],
               output / "cmake-build.log", 1200)
    quantizer = build / "bin" / "llama-quantize"
    if not quantizer.is_file():
        raise ValueError("llama-quantize was not built")
    f16 = output / "rune-text-v1-0.2.0-f16.gguf"
    converter = llama / "convert_hf_to_gguf.py"
    run_logged([str(converter_python), str(converter), str(fused), "--outfile", str(f16), "--outtype", "f16"],
               output / "convert.log", 1200)
    f16_digest = sha(f16)
    f16_bytes = f16.stat().st_size
    artifact = output / ASSET
    run_logged([str(quantizer), str(f16), str(artifact), "Q4_K_M"],
               output / "quantize.log", 1200)
    artifact_digest = sha(artifact)
    artifact_bytes = artifact.stat().st_size
    metadata_process = subprocess.run(
        ["python3", str(REPO / "tools/model/rune-text-0.1/read_gguf_metadata.py"), str(artifact)],
        capture_output=True, text=True, check=True, timeout=60)
    metadata = json.loads(metadata_process.stdout)
    if (metadata.get("gguf.version") != 3 or metadata.get("general.architecture") != "qwen3"
            or metadata.get("general.file_type") != 15 or artifact_bytes > MAXIMUM_ARTIFACT_BYTES):
        raise ValueError("candidate GGUF violates the runtime artifact contract")
    (output / "gguf-metadata.json").write_bytes(canonical(metadata) + b"\n")
    provenance = {
        "schemaVersion": 1, "scope": "rune-text-0.2-q4-k-m-candidate",
        "releaseQualified": False, "publishable": False,
        "fusedManifestSha256": sha(fused_root / "manifest.json"),
        "configSha256": sha(config_path), "sourceLockSha256": sha(lock_path),
        "converterRevision": revision, "quantization": "Q4_K_M",
        "converterToolchain": actual_converter_toolchain,
        "converterToolchainLockSha256": sha(converter_lock_path),
        "f16": {"sha256": f16_digest, "bytes": f16_bytes, "retained": False},
        "artifact": {"name": ASSET, "sha256": artifact_digest, "bytes": artifact_bytes},
        "metadata": metadata,
        "logs": {name: sha(output / name) for name in (
            "cmake-configure.log", "cmake-build.log", "convert.log", "quantize.log")},
        "sources": {str(Path(__file__).resolve().relative_to(REPO)): sha(Path(__file__).resolve())},
    }
    (output / "provenance.json").write_bytes(canonical(provenance) + b"\n")
    f16.unlink()
    shutil.rmtree(build)
    print(json.dumps(provenance["artifact"], sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fused", required=True)
    parser.add_argument("--llama", required=True)
    parser.add_argument("--converter-python", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default=HERE / "training-config.json")
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--converter-lock", default=HERE / "converter-toolchain-lock.json")
    run(parser.parse_args())
