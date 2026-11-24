# U9: exploratory emoji panel memory observations

On 2026-10-28, commit `1dbd7c44` was built as a debug APK and measured on one disposable API 26 arm64 Pixel 7 emulator. Three separate instrumentation invocations opened the actual IME in the QA editor, opened the emoji panel, visited each category and returned to letters. Each invocation passed its category-selection and nonempty-grid checks. The test is opt-in via `runeEmojiMemory=true` and rejects non-emulator hardware.

Process PSS in KiB, reported by `Debug.getMemoryInfo`:

| Invocation | Before opening | First category | After visiting categories | After closing |
| --- | ---: | ---: | ---: | ---: |
| 1 | 32,293 | 44,228 | 57,340 | 57,715 |
| 2 | 33,451 | 45,355 | 56,180 | 55,866 |
| 3 | 33,389 | 46,381 | 56,388 | 56,115 |

The first snapshot followed a five-second delay; the other snapshots followed one second after each action. Categories were selected, but their entire contents were not scrolled through. No forced garbage collection was performed. PSS remained higher in the immediate post-close snapshot; this does not establish a leak, a causal breakdown, or steady-state memory. The debug build, instrumentation, emulator and activity transitions affect the numbers. These runs do not isolate the lazy catalog change, constitute a release-build memory budget, or prove Fold behavior. A controlled before/after comparison, lifecycle investigation, and physical-device measurements remain open.

Raw local logs are `build/review-u9-memory-20261028/memory{,2,3}.log` (SHA-256 respectively `626f6d0ffc8b2a95aa70ce17cf92438cd6515109165748b8e97e837b3550501d`, `e4912277b04aa1569a11dcb57eded6c4858e5342ac6395004f7aed74ef98b7ce`, `6c25986429f6607585fa156057aabe3a20a37f7bed9e634b9b2c878acc9d2d5b`). The debug APK SHA-256 was `abe9c82a6419d7395750b4e7124c9068c1c0a4c2bb5df7009fbf3b4ef75dec43`; the test APK was `4e7f669227939c19627efda7d56666f29f33274db30c76aece066a948a355189`. The task-owned emulator was stopped and its AVD deleted after the observations. No physical device was accessed for this measurement.

## Follow-up: GC request and reopening

The view explicitly retains `EmojiPanelView` across layer changes. Its palette retains recent emoji, the lazily loaded catalog and glyph-support cache; removing that view on every close would also discard those recents and cold-start work. Retention by design does not quantify its contribution to PSS.

A second fresh API 26 emulator ran three separate invocations with the same debug APK and an extended test APK (`1029e64d699e601718130c289a368bd43f4efb1ab7d7bb1d426e86e85ddeb704`). After closing, the test requested `Runtime.gc()`, waited two seconds, took another snapshot, reopened the panel, verified a populated grid and took a final snapshot. All three invocations passed.

| Invocation | Before, KiB PSS | After close | After GC request | After reopen |
| --- | ---: | ---: | ---: | ---: |
| 1 | 33,537 | 57,575 | 54,055 | 54,812 |
| 2 | 34,026 | 56,993 | 54,253 | 54,626 |
| 3 | 34,113 | 58,557 | 54,053 | 54,579 |

The Java used-heap readings after the GC request were about 2.9 MB, while native allocated-heap readings were about 26.7 MB; these counters are not a partition of PSS. A GC request does not guarantee a complete collection or establish why native allocations remain. No conclusion about a leak, a production memory regression, or the cost of any individual cache follows from these observations. The next meaningful comparison needs controlled release-like runs and attribution before changing the retention policy.

The follow-up logs are `build/review-u9-memory-followup-20261028/memory{1,2,3}.log`, SHA-256 respectively `a873fca287d51060b416268a50b117833c9dba68981bebe922d24e3c9632079a`, `2fab35d56b553913b2e4a58042f60bb373cae7ab10d5899e21e8553ce2375caa`, and `10f0ff0002de4bfa1469b9d7ff6713a2c543f8343fffcc0e42aead2b3aa568ab`. The owned emulator was stopped and deleted.

## Current release-like profile on API 26

On source `e8b39054`, offline Gradle built the release-shrunk, non-debuggable
profile IME and a separate debug qualification editor. Their SHA-256 values
matched the installed APKs on a disposable ARM64 API 26 emulator with 2 GiB
RAM. The hashes were respectively
`ebc28b1bd169f17a52fd4017c42f0772ead5b449fd8ef78844d5475716768035` and
`cb6dc039049f227f03e8082b90bccb780d43cd918d51e0e73bf01303b764437c`.
Speed compilation of the profile APK succeeded. Each sample switched to the
system IME, force-stopped the profile process, verified the PID had exited,
opened the separate empty QA editor and selected Rune. All samples between
opening and reopening used the same new profile PID.

ADB taps used coordinates checked on the 1080 × 2400 emulator screen. The
measurement harness compared a fixed keyboard crop to observed letters,
symbols and populated Emoji reference crops. All recorded sample crops
matched exactly. The host checked `dumpsys meminfo` for the profile PID
about five seconds after stable letters, about 1.2 seconds after opening,
about 1.2 and 10.2 seconds after closing, and about 1.2 seconds after
reopening. No garbage collection or full-category traversal was requested.

| Stage | Three profile PSS samples, KiB | Median, KiB |
| --- | --- | ---: |
| Before opening | 18,229 / 19,811 / 20,013 | 19,811 |
| First category | 30,321 / 30,320 / 30,430 | 30,321 |
| After closing at about 1 s | 29,706 / 29,665 / 29,787 | 29,706 |
| After closing at about 10 s | 29,622 / 29,581 / 29,699 | 29,622 |
| After reopening | 30,137 / 30,118 / 30,210 | 30,137 |

After ten seconds the per-run increase over baseline was 11,393, 9,770
and 9,686 KiB. In a fourth diagnostic cycle, total PSS rose from 17,886
to 28,774 KiB on the same before-to-close comparison. Android reported
9,129 KiB of that increase in Native Heap, 768 KiB in font mappings,
and 351 KiB in Dalvik Heap. These are whole-process accounting categories.
They leave allocation ownership, longer-term retention, presented-frame
latency and physical Fold budgets open.

Two setup probes stopped before recording samples. The first used a user
flag that the API 26 IME command does not support. The second found that
the accessibility dump contains only the editor window even while the
profile IME is shown. The successful run verified user 0 separately and
used pixel checks for IME layer identity. All four measured cycles exited
zero. The isolated emulator, ADB server, APKs, screenshots and logs were
removed.

## Paired check of the retained panel reference

At `3543eafa`, the ordinary profile APK was compared with a disposable
profile build at `5864aca2`. The diagnostic variant's only source change
set `emojiPanel = null` in the non-Emoji layout branch after removing the
old views. That removes RuneKeyboardView's strong reference and also
discards the panel's local recent-emoji state. The test typed no emoji.
The ordinary and diagnostic profile APK SHA-256 values were
`0b8968a0b51a1648f168c945cb128788fde7d78372513882f74a36d8492524c4` and
`d6683797a512eaccc6d5500c0b5850d0b46c9656eb316aac26f03290711f7698`.
The separate qualification editor SHA-256 was
`6f05e8e7b796d7da6f7e98afe751320f9669a39c058c6204e5c7b71e4a2408ca`.

A single disposable API 26 ARM64 emulator with 2 GiB RAM ran three
adjacent pairs. Each sample freshly installed the selected profile APK,
verified the installed hash, ran speed compilation, then opened the
empty QA editor. The keyboard pixel crop matched its reference at all
five measured stages in every sample. No GC request was issued.

| Run | Retained reference | PSS before, KiB | PSS at 10 s after close, KiB | PSS increase, KiB | Native Heap PSS increase, KiB |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Yes | 18,188 | 29,057 | 10,869 | 9,314 |
| 2 | No | 19,886 | 28,506 | 8,620 | 9,255 |
| 3 | No | 18,256 | 28,822 | 10,566 | 9,645 |
| 4 | Yes | 19,918 | 28,830 | 8,912 | 9,147 |
| 5 | Yes | 19,837 | 29,026 | 9,189 | 9,375 |
| 6 | No | 19,537 | 29,202 | 9,665 | 9,921 |

The medians for Native Heap PSS increase were 9,314 KiB with the
reference retained and 9,645 KiB with it cleared. Clearing this
reference did not reduce the observed Native Heap retention in this
series. The sample does not establish whether the detached view was
collected or which native allocations account for the increase. The
diagnostic change was discarded. The six measurement cycles exited
zero and the isolated emulator and task artifacts were removed.
