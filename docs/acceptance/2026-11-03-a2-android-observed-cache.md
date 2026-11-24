# A2: observed cache reuse in an Android native scorer copy

A separate ARM64 Android executable was built from the same scorer source and
Android debug-build llama/ggml static libraries used by the runtime. A generated
copy of `scoring.cpp` adds the existing host probe's numeric counter immediately
after the cache-removal branch; the original scorer and production JNI library
are not modified. The builder verifies the Android ABI and API, exact llama
revision and tokenizer patch metadata, upstream source-tree state and listed
inputs before and after compilation, and verifies that the output is an ARM64
ELF. It binds the already-built archives; it does not independently rebuild
them or prove the packaged JNI binary equals this diagnostic executable. A second build after
strengthening the builder produced the identical executable SHA-256:
`c520fc75e0d68d5f132d21d48ab363d19051991193b81186e98e20ede1fc5827`.
The generated observed scorer SHA-256 is
`c6a90f6dd4e9292733553b05d7d1229bb82ca9acea155d5c330a91eeb954a068`.

The exact Rune Text 0.1 model and executable were verified on each temporary
emulator. On API 26 ARM64 and API 37 ARM64 with 16 KiB pages, the existing
three synthetic requests each produced the same numerical observation:

| Prefix stage | Retained tokens |
| --- | ---: |
| First request | 0 |
| Extended prefix, unchanged window start | 69 |
| Window shifted | 1 |

For all six candidate comparisons per device, the warm and newly created cold
scorers had identical token counts and maximum score delta **0**. Both probe logs
have SHA-256 `f23e35d953f920c8ffc3e28d44529e0ec0bfaa107dbf9991a0b5729337143bec`.
The prior Android public-JNI test separately checked the same score parity, but
has no counter. These combined observations support native cache reuse in the
instrumented Android scorer copy; they do **not** directly measure the
production JNI library, full IME controller, physical Fold, performance, or
independent language quality. The feature remains disabled.

The builder is [a2_android_cache_probe.py](../../tools/eval/smart-typing-0.3/a2_android_cache_probe.py);
it only builds a diagnostic executable and never invokes ADB. Its ignored
build receipt binds the actual compiler, static archives, patched headers,
source and output hashes. Four host tests pass for the builder and the original
counter instrumentation. The synthetic contexts were already registered by
the preceding Android score-parity change. The temporary AVDs and isolated ADB
server were deleted after testing; no physical device was touched. Hosted CI
and A2's independent quality and Fold acceptance remain open.
