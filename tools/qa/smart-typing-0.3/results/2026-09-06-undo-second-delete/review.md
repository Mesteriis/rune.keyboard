# Second Backspace after correction Undo — narrow review

Spec: **PASS**. Code quality: **PASS**. No actionable finding in the two-test delta.

Scope is only the new assertions after the existing successful first Undo in `LiveFakeModelBinderInstrumentedTest` and `LiveCandidatesInstrumentedTest`, plus the existing helpers they use. No production source, fixture behavior, scoring policy or corpus was changed. No tests/build/device/model calls were run by this reviewer.

Identity verified against [inputs.json](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/undo-second-delete-20260906/inputs.json):

- Base `1a5826e12c6ecc036cc0e028c6c44cc927d8375e`.
- Patch SHA256 `2830775fa423e6f4f5ccf11ec086f836bf5c7ddb4fc34ddbd870393c105f5fee`.
- `LiveFakeModelBinderInstrumentedTest.kt`: `638e1ba5728cdc42055058632d29eb1cdb0d93384fb0e6915742b122709f59ef`.
- `LiveCandidatesInstrumentedTest.kt`: `3653c91ce624171952e071508e8533cca6197faa6d42a291979f1f2fc3082e46`.
- Recorded test APK `c163682c2b9182e8ea24d9a224f49e67370934e1f6e4e5e2d2f6bba7c2c59987`; product APK remains `6a7d0d179b5c0446d88991cb14359ca63f97ce570e1ec09e2692667399f721e1`.

[LiveFakeModelBinderInstrumentedTest:36](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveFakeModelBinderInstrumentedTest.kt:36) continues the same live resident-controller/remote-service/remote-editor session from actual model-numeric correction `a hello ` and first Undo `a helllo`. A second actual Delete must produce exactly `a helll`, caret 7, owned span 1–7, exactly one composing write, and no connection/region/finish/commit/raw-key deltas. The editor helper requires settled remote text/selection/span and acknowledged controller selection, then checks zero payload reads. This cannot pass merely by incrementing an in-process write counter or by consuming Undo again without deletion.

[LiveCandidatesInstrumentedTest:46](/Users/avm/projects/Personal/rune-keyboard/app/src/androidTest/java/io/github/mesteriis/rune/keyboard/qa/LiveCandidatesInstrumentedTest.kt:46) continues from packaged canonical-case correction `я Москва ` and first Undo `я москва`. The second real Delete must yield `я москв`, one additional compose call, unchanged commit/region/finish counts, unchanged owned start, end/caret 7, and the existing zero-payload-read assertions. It adds no retry, changes no candidate eligibility, and retains the existing preconditions proving the automatic correction and first Undo actually happened.

These assertions directly address the missing spelling/canonical **correction → Undo → ordinary next deletion** sequence identified in row 6 of the baseline editor audit. They cover a Latin and a Cyrillic final letter. The existing complex-grapheme deletion test remains separate evidence; no new claim about every complex grapheme after every correction is made.

While reviewing, root-owned logs completed: [api26.log](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/undo-second-delete-20260906/api26.log) reports 2/2 in 38.054 s; [api37.log](/Users/avm/projects/Personal/rune-keyboard/build/smart-typing-0.3/undo-second-delete-20260906/api37.log) reports 2/2 in 33.279 s. These are affected-case delta runs, not retroactive additions to the older full152 logs. The numeric scorer remains fake; neither real-GGUF quality nor physical-phone execution is claimed.
