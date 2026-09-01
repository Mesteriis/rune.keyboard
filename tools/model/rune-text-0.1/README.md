# Rune Text 0.1 reproducible build

This recipe converts the immutable `Qwen/Qwen3-0.6B-Base` revision
`da87bfb608c14b7cf20ba1ce41287e8de496c0cd` to F16 and quantizes it to
`Q4_K_M` with llama.cpp revision
`36b10154383b60eb15baac2c7a40d2a5f784faa7`.

Prepare a source directory containing the exact files listed in
`source.sha256`, then run:

```sh
./tools/model/rune-text-0.1/reproduce.sh /absolute/source /absolute/output
```

The command uses two fresh Linux containers, compares the complete outputs,
and emits the artifact SHA-256, byte size, selected GGUF metadata, build
provenance, and Debian/Python SBOMs. Android/Gradle builds never execute this
recipe and never download model or native dependencies.

Publishing `model-rune-text-v0.1.0` is a separate gated operation: both Linux
outputs must match and the unchanged artifact must pass the Fold qualification
matrix documented in `docs/ACCEPTANCE.md`.
