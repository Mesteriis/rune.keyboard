# Final native correctness — 2026-09-06

Fresh Release configure/build and all seven CTest cases PASS at1a5826e, 8.24seconds. Exact-model subset: three tests,6.90seconds. No source changed during the run; input-receipt.json binds21 native source/build/patch files and pinned upstream SHA. The full compiler commands and generated CTest commands are retained. The required Python extraction/optimization guard suite also passes8/8; its log and source hashes are retained.

Coverage: scalar teacher-forcing oracle, stable numeric/UTF-8/wire contracts, token/BOS caps, real tokenizer legacy equivalence, eight abort stages, successful reuse, unsupported presets and per-call concurrent cancellation isolation. Unicode preparation, QWEN2 pre-split and BPE checkpoints are reached inside loops. The complete exact-model token stream matches the independently frozen pristine-API golden SHA256 d65c09fdad70f012a0ad17a01d9e0a7c1d891136a69c1977633b9152a7fdea00.

The GGUF is exactly396704416bytes/SHA2567a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4, verified at configure and before each model test. Upstream36b10154383b60eb15baac2c7a40d2a5f784faa7 and tokenizer patch0a043ce8a57b8534ef2f409443d2dd6ecf00042bd9c2b661b31d94618eb4dc95 remain unchanged; only build-directory copies are patched.

android-continuity.json verifies native sources unchanged since the diagnostics checkpoint and byte-identical app APK to the full152 API26/API37 matrices. Prior ordinary Android JNI6/6 evidence is separate; this host run does not claim fresh optional exact-model Android execution, inside-tokenizer Android instrumentation, typing quality, physical latency or battery qualification. Compiled binaries and GGUF stay local; their hashes are recorded.
