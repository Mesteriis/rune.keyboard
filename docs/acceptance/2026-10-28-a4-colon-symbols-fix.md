# A4: correction before colon from the symbols layer

The [reproduced failure](2026-10-28-a4-colon-symbols-failure.md) was addressed
by retaining an owned candidate-capable word on entry to the first symbols page.
Only `:` can consume the ready decision there; another text symbol first
invalidates the owned word, and the usual cursor, editor, language and page
invalidations remain. The coordinator retains a ready decision for this action
only with an active eligible editor, no selection and an owned candidate.
Feature and personal protection policy remain effective during that short
transition. In-flight work is cancelled; this does not wait for a new candidate.

On API 26 and API 37 arm64 disposable emulators, three real-IME tests per API
passed: `инн:` remains lowercase, `смотруть:` becomes `смотреть:` and Backspace
restores `смотруть`, and entering `1` after `?123` retains the original word.
All checks use the separate QA editor and verify zero content-read counters.
The earlier ignored colon test is active again. Both emulators were stopped and
deleted. The API 26 log SHA-256 is
`41abe99b709828554f83519d2eb4322fedb494960d40e8e5a9f6c858b92b8781`; API 37 is
`0c6c52db47d9caf15c0654a34aab3d12f770628646d01a8c29c6b5e05d1dc0ac`.
They are `build/review-a4-colon-fix2-api26-20261028/colon-final.log` and
`build/review-a4-colon-fix-api37-20261028/colon-final.log`. Debug APK SHA-256:
`f0b21c3c3e832290aa5db23478895d3b1f8762051ecf8296ad01593954751c98`.

All 1,376 JVM tests passed, including candidate-owner invalidation, protected
ASCII and non-colon controls. The two-pass 2,160-row and 12,000-row Q7 space
replays matched their existing baselines. These checks do not prove all possible
editor/layer transitions or physical Fold behavior. A4 still requires its Fold
acceptance; the 140 disclosed controls are regression data, not an independent
natural holdout.

The clean-source release privacy gate passed at `795db1b`. After that commit,
all three 140-row control replays were regenerated and the source/asset-bound
category gate passed; its output is
`build/review-a4-colon-current-gate-20261028.json`. The independent Fold
acceptance remains outstanding.

## Personal rejection on the live IME

An additional emulator-only synthetic profile fixture installed an explicit
personal rejection of `москва` → `Москва`, enabled personal learning and typed
the word in the separate QA editor. The title-case suggestion was present but
not selected for automatic replacement. After `?123` and `:`, the field retained
`я москва:`. This passed once each on API 26 and API 37; the test restores the
fixture's original personal snapshot, and both task-owned AVDs were deleted.
The raw logs are `build/review-a4-personal-colon-api{26,37}-20261028/personal-colon.log`,
with SHA-256 respectively `a60b9a688146e86c98629fdedc516913e7f71f48bfae34ed0918cda3868fc88d`
and `053c89e679363655008026bb3b34fd64bbf4da8a02a1d8072c9ba0d5bdee74f1`.
This demonstrates the seeded case-rejection path, not every personal or editor
transition. The instrumentation APK SHA-256 was
`2ce4fe49017a436ef5ad8ee21a222421d3f2171466935c326764e056d219b3c9`.

## Switching editor with a retained candidate

On API 26 and API 37, a real-IME test typed `смотруть`, waited for `смотреть`,
and switched to symbols before launching a new QA editor. It separately tested
an editor with `IME_FLAG_NO_PERSONALIZED_LEARNING` and one with
`TYPE_TEXT_FLAG_NO_SUGGESTIONS`. In each new editor the old candidate disappeared,
typing `:` produced exactly `:`, and fixture content-read counters stayed zero.
Each API ran the one method containing both scenarios successfully; the owned
emulators were then deleted. The first API 26 attempt failed because the empty
field exposed its hint as accessibility text; removing that invalid empty-field
assertion and asserting the actual colon resolved the fixture issue. The failed
raw log SHA-256 is `260f6f7cf04428282fe7d1131d8446667b9c8165c20ac4a9b6873aeb92849d58`.
Passing logs under `build/review-a4-editor-transition-api26-20261028/editor-transition2.log`
and `build/review-a4-editor-transition-api37-20261028/editor-transition.log`
have SHA-256 `f6838fc201b2c1c96288bd1d5c594b54126d8c169a6f9a07531247ba897157a4`
and `49f2760a67ebc2192d55ffec853a07cabf48acce199731701880a5108f6e5ee6`.
This covers those two editor transitions, not every third-party editor or Fold.

## Offline WebView editor

The `:qa_editor` offline WebView was used as an independent real Android
`InputConnection` on disposable API 26 and API 37 arm64 emulators. In each,
Rune typed `смотруть`, exposed the `смотреть` suggestion, switched to symbols,
inserted `:`, produced `смотреть:`, then restored `смотруть` with Backspace.
The actual WebView field was checked at each step, with zero content-read
counters. One instrumentation method passed per API; the task-owned emulators
were stopped and deleted. This is an offline WebView fixture, not a claim about
all browser versions or Fold.

Logs `build/review-a4-web-colon-api{26,37}-20261028/web-colon.log` have SHA-256
`5f14d7620f9f5d33e09dfb01c562c8e2f116b32102a83850d2af76ce985e673c` and
`1262300e2620d96709cbcd7b3b5bc5a720f13dbfb95b354a385aeb2a39a7e42b`.
The instrumentation APK SHA-256 was
`b8aa21ffad9e9a15d5df73fd53f71fdeeda1a6f5388755431e779f1c11189f89`.
