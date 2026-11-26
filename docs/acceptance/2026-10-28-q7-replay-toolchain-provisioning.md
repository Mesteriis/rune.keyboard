# Q7: provision the pinned replay compiler inputs

Published main CI run 40680972358 stopped at `PINNED_KOTLIN_CACHE` before its
replay. The published log does not name the missing or ambiguous artifact, so
it cannot prove a more specific cause. The host's Gradle cache happened to be
complete locally; a successful warm-cache run alone did not address that failure.

CI now runs a standalone Gradle project before replay. It resolves exactly the
five coordinates in the existing reproduction-toolchain manifest from Maven
Central without transitive dependencies, then checks every actual JAR's name,
size and SHA-256. This is CI-only and adds no Android application dependency.
The replay loader now respects `GRADLE_USER_HOME`, falling back to the usual
home cache, and names a failing artifact while retaining the exact hash and
single-match checks.

An initially empty, isolated Gradle home successfully resolved all five JARs and
passed their identity checks. With that same new cache, the actual CI replay
completed both deterministic comparisons: 2,160 rows matched projection
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`, and
12,000 rows matched
`b7b49f16aed912ea4c80d811c834f059dc1ac47f6b655e9798923651ec47f512`.
In a separate copied project, mutating the compiler digest caused the resolver
to fail with `REPLAY_TOOLCHAIN_IDENTITY:kotlin-compiler-embeddable`. Replay
loader tests cover the alternate Gradle home, duplicate matching artifacts and
modified bytes. Their module ran 24 tests successfully with one explicit
conditional Kotlin-ready skip; the real replay above is a separate execution.
The full stdlib inventory additionally passed 772 tests in 153 modules with no
skips; its receipt is under `build/review-hosted-ci-audit/toolchain-stdlib/`.

Raw resolver, negative-control and replay logs remain under
`build/review-hosted-ci-audit/`. These are local results, not a hosted rerun or
proof that all other hosted CI failures are resolved. No model, keyboard policy,
APK or phone was changed.
