# A1 and Q7 Android boundary checks

The resident Rune IME test enters `baha'i` in the separate QA editor.
It enters the apostrophe with a down-flick on the English `k` key,
so the test keeps the letters layout and the same editor connection.
It checks that the suggestion strip omits `I`, commits a space, and
then checks that a separate `i` offers the manual `I` suggestion.
The fixture confirms zero editor payload reads. The general CI suite
requires this test identity in its fresh report.

The local instrumentation selection also includes the existing English
manual-selection and Spanish-layout controls, canonical casing with
Backspace, Russian immediate Undo followed by the next word, and the
three contextual punctuation tests. The latter three failed on both
Android jobs at published commit `2c1ff975`. Their independent-controller
fixture was subsequently repaired in `4aa961c3`.
[Published CI run](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358)
[Fixture repair](2026-10-28-hosted-ci-independent-controller.md)

The isolated offline build produced debug APK SHA-256
`55f1f5d2441bcb9d26f2ec83dcef5138eb5f3f06411236ddadee8e77a500fc6e`
and instrumentation APK SHA-256
`a228390ed568b32004b849c8761bf7959cb000886a037dbbc8045894ee33ec4b`.
All 27 Python Android suite-runner tests passed.

| Owned ARM64 emulator | Page size | Executed | Failures or skips | Instrumentation log SHA-256 |
| --- | ---: | ---: | ---: | --- |
| API 26 | 4,096 | 8 | 0 | `234a4fda3c6955ac9a648cfd4a8ab3162385b12cf2840ee7d62e6351ad270e0a` |
| API 37 | 16,384 | 8 | 0 | `bcc1a6375dcdfafbc608336ede100e2f953b94ae15ed4c1ba2d1d46f8bf950f1` |

The first setup attempts ended before any tests. Android 26 lacked
`getconf`, so page size was read from `/proc/self/smaps` on the successful
run. The retry used a free emulator port after the original port was
unavailable. The final runs produced eight start and eight success events
on each API. The disposable emulators, isolated ADB server, APKs and
temporary build folders were removed.

The eight-method selection leaves the complete hosted Android jobs and
physical Fold acceptance open. Automatic English pronoun conversion and
its independent qualification remain open.
