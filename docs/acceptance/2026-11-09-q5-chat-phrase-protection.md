# Q5: protection of reviewed public chat originals

Post-hoc inspection of the disclosed Tatoeba full-session baseline found thirteen
source forms used as intentional words in their sentences but automatically
changed: `хотелки`, `скипать`, `усмеяться`, `скипай`, `ебалу`, `анимки`,
`инвент`, `похуй`, `уведы`, `афантазия`, `инвайт`, `пофаниться` and `темпой`.
The existing Russian public-original admission veto now preserves these exact
folded forms. It does not change the frozen dictionary, create a candidate or
change manual candidate selection. The rule is deliberately exact: it does
not infer other inflections. A differently intended use of one of these forms
may now require explicit candidate selection.

The unit regression failed on the previous product source for `хотелки`, then
passed with the change; the full clean-checkout JVM suite passed 1,396 tests
with zero failures, errors or skips, and lint passed. The identical test also
checks that a different unlisted inflection remains eligible for the veto's
normal handling. This is admission-guard evidence, not a claim of full runtime
qualification or a physical-device test.

All 9,543 disclosed phrases were replayed twice with the updated product, with
identical outputs. Boundary changes fell from 169 to 156, with the same 148
case-only changes. A stage-by-stage comparison found exactly the 13 removed
edits, no new edits and no stage with a different edit on both sides. Thirty
later stage texts differ only through their preceding restored word. All 33
final-word Undo checks remained exact; zero prefix changes were observed.
Both typed and resulting contexts were checked against both persistent
registries, with zero new unregistered keys. The [numeric evidence](2026-11-09-q5-chat-phrase-protection-evidence.json)
binds product sources, assets, results and comparison. These are post-hoc
regression controls from an exposed unproofread source, not an independent
accuracy or false-change estimate.

The frozen current and historical product replays also passed on 2,160 and
12,000 rows respectively: zero differing rows and zero tolerated score
differences in each. These regression datasets are not independent qualification.

The original 148 capitalization changes remain, including `клавы → Клавы`
and `читы → Читы`. An earlier blanket lowercase overlay was rejected because
it harmed real name uses; context-sensitive case handling remains open. The two targeted real-IME checks below cover only two of the thirteen forms;
Fold, hosted CI and independent natural qualification remain open. Temporary source,
replay and test build directories were removed after verification.


## Real IME regression

Two new mandatory Android test identities type `твои хотелки` and `апрувни
инвайт` using Rune keys in the remote composing editor. Each waits for the
actual competing suggestion (`хотели` or `инсайт`) before pressing Space,
then verifies the original remains. On a disposable API 37 emulator the first
case reproduced the wrong replacement on the pre-fix product; that deliberate
failure is a negative control. Both new cases passed individually on isolated
ARM64 API 26 and API 37 emulators with exact instrumentation events and zero
skips. The required-case CI report gate includes both identities; its 15 host
tests pass. This is not a complete CI workflow or physical Fold result. The
temporary checkout, APKs, logs and emulators were removed.
