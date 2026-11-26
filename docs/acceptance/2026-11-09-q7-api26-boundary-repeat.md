# Q7: fresh API 26 boundary and restart run

At clean source `f835c4f4`, an isolated ARM64 API 26 emulator ran the Android
boundary suite with the pinned llama.cpp submodule, software navigation
(`qemu.hw.mainkeys=0`), a dedicated ADB server, and Rune selected as the IME.
The initial debug assembly, test APK assembly and installation succeeded.

The boundary runner exited zero and accepted fresh JUnit reports for every
scope. The general report contained 354 tests, 48 skipped, zero failures or
errors: 306 executed. Eight separate scopes ran 19 tests without skips or
failures: personal (4), case rejection (2), confirmed words (3), export
navigation (1), export picker (1), qualification lifecycle (1), qualification
safety (1) and native runtime (6). The personal scope passed the current
required-method identity check.

After restoring ordinary debug APKs, all four synthetic restart phases passed:
case rejection write/reload and confirmed words write/reload. Their runner
also exited zero. The temporary checkout, APKs, emulator and isolated ADB
server were removed; only the aggregate counts above were retained.

An earlier attempt was stopped before completion because its emulator used
hardware navigation; it is not counted. A further earlier run was interrupted
at the owner's pause and is not counted. This run did not execute the complete
workflow shell or its failure-artifact collector, and it does not establish a
hosted x86_64 CI result, API 37 result, physical Fold behavior, or absence of
failures in the skipped scenarios.
