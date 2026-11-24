# Q5 explicit rejection of automatic capitalization

With personal learning enabled and its store ready, explicitly undoing a
lowercase-to-titlecase automatic correction now retains a rejection scoped to
the normalized word and language. On a later occurrence the personal veto
blocks that automatic case transition. It does not protect the word against
unrelated spelling corrections and does not remove the title-case suggestion:
the user may still select it explicitly. The rejection applies across contexts,
not only in the sentence where Undo happened. The existing privacy and learning
settings continue to gate recording and use; password and incognito fields are
not new learning sources. A full 512-entry case-rejection table fails closed for
new automatic case changes until the personal profile is reset.

The personal snapshot codec reads legacy RPT1. With no case rejections it still
writes RPT1; with at least one it writes RPT2 and adds a bounded language/word
list. Existing confirmations, feedback pairs and phrases are preserved. Old
Rune versions cannot read RPT2: their existing store load fails closed rather
than intentionally rewriting that profile. Downgrading after an RPT2 write can
therefore make personalization unavailable until a compatible version is used;
no downgrade/reinstall was performed on the owner's phone. This is a material
rollback compatibility limit, not a lossless old-version migration claim.

The old implementation failed a new focused test because case-folding discarded
the rejection. The corrected model/codec/admission tests cover direction,
language, bounds, full capacity, reset, malformed/truncated files, V1 bytes and
V1/V2 round trips. A controller test exercises actual boundary correction,
Undo, serialized reload, subsequent veto, explicit suggestion selection and an
unrelated proper-name correction through the personal admission policy. This
controller fixture uses a test bridge; it does not claim a real IME Undo gesture.

Full JVM: 1,368 tests, zero failures/errors/skips; debug lint, IME boundary and
forbidden-runtime-dependency gates passed. On disposable API 26 and 37 emulators,
a real Android personal store/bridge saved a synthetic V1 profile, did not
record while learning was disabled, persisted the case rejection with other
records unchanged, and reloaded it after an actual process restart: two targeted
methods passed per API with zero ignored. The fixtures were explicitly gated to
task-owned emulators. A full-capacity test initially exposed an attempted
48-character case pattern; the final implementation rejects over-32-code-point
case evidence safely and the final test passes.

The current-product parity gate completed two deterministic runs of both Q7
corpora: 2,160 and 12,000 rows match their existing projections. This exercises
ordinary behavior without a learned case rejection; it does not measure personal
learning effectiveness or establish a new population accuracy rate. The final
debug APK SHA-256 is
`486afbd68d53ffae492885e92b38fb0562d3e35b5fc012bd83c3a53d78826681`;
the final instrumentation APK SHA-256 is
`cbe64c082fd7aad006602d65239ad8086d03efe0ef968f19dc6d95b57b05b8b6`.
Raw test/replay logs remain in ignored `build/q5-case-personal-*`. The owner is
currently testing an earlier APK on Fold; it was not interrupted or updated.

After commit `90caa96`, a clean-source run of `:app:privacyGateRelease` and
`:app:privacyGateProfile` passed. The source check reported that exact clean
commit. The local raw log SHA-256 is
`63584efd56aa8f595358e39715b326e850dfc681d02530fbe8a31ed24376bc78`;
the resulting release APK SHA-256 is
`50986559235895d248ff939d015c989155a53c91cfd8f23254ef8db35c217bc7`.
This is local build validation, not a release or Fold installation.

## Real IME follow-up

On the same production debug APK, a later synthetic real-IME test passed once
on each task-owned API 26 and API 37 emulator, with zero ignored tests. It typed
Russian text into the QA editor, observed the actual `Москва` suggestion and
automatic boundary replacement, invoked Backspace Undo, waited for the personal
store to persist the rejection, typed the same word again and verified that the
case change was not selected or applied automatically. A third occurrence was
explicitly changed to `Москва` through the still-visible suggestion. The test
restored the emulator's prior personal-model snapshot and settings, and both
emulators were stopped. This supersedes the earlier limitation that no real IME
Undo gesture was exercised; it does not establish physical Fold behavior.

The follow-up test APK SHA-256 is
`f797b3df95d5e57e4862608eb7dd199559a83fa6f31c963ad44a0f8efe3c01d1`.
The API 26 and API 37 raw log SHA-256 values are respectively
`71fb01f1c687da3fc8688e3ad9b8c7c01b9eb73b75251591a13d9c8c0a9fba9b` and
`14746ce6d7925dfc168ad2ba6ace19b532ba4f541dc612f67ec344f8e0ec0856`.
The first test build failed due to a wrong instrumentation-arguments API; the
corrected build and both final tests passed. The owner phone was not used.

## Reviewed lowercase forms

The existing controller test now exercises `клавы`, `читы` and `моника` in
addition to `клава`. For each word it injects the corresponding canonical
candidate, applies the case change, undoes it, serializes and restores the
personal model, and checks that the next automatic case change is vetoed.
It also checks explicit selection of the capitalized candidate and an unrelated
`Москва` correction. On a temporary clean checkout of `cc73d7b7`, the targeted
JVM test passed with zero failures, errors or skips; the modified test source
SHA-256 was `9f6f9dfc9c11c72a16ea8ed4f4c4a3d303225eef164cab9b78436272e6ceddd8`.
The checkout and build were removed.

This controller fixture supplies canonical candidates directly and uses a
test personalization bridge. It does not establish candidate generation from
the packaged assets, a real IME gesture for these three words, or Fold behavior.
Personal learning must be enabled, and the unwanted first change still occurs
before the user undoes it. Q5's automatic context and independent qualification
remain open; no product behavior was changed.

## Reviewed forms through the real IME

The existing synthetic real-IME test now repeats the complete flow for
`москва`, `клавы`, `читы` and `моника`: it waits for the actual packaged
canonical suggestion, confirms automatic capitalization, invokes Backspace,
waits for the personal rejection to persist, verifies later lowercase input
and explicitly selects the capitalized suggestion. The fixture resets its
synthetic profile between words and restores the prior emulator profile and
preferences on exit. It is gated to an explicitly opted-in emulator.

On separately created ARM64 API 26 and API 37 (16 KiB) emulators, the expanded
method passed once on each with exact instrumentation start/success events and
no skips. Both temporary clean checkouts used `93360fc2` with the modified test
source SHA-256 `9dd92b1f3699165146505306d798c2f44b07864e0911dc798c25893cec525f7c`.
Both builds produced the same debug APK SHA-256
`0e28137a75315b32266872c5eb1356926d733deda761d415983d2a1468957b56` and
instrumentation APK SHA-256
`82daa42496da2358af5136b84a5d2d2636b244927fb7a295288668ab49ab2456`.
The API 26 and API 37 instrumentation transcripts had SHA-256
`f132257d407476bf0cf4b02171ed4a9cb4c4f238758cd42ed32650a2bd661e7f` and
`0e8e6f1984d2e85536d0df5e269491d219572eadaafebe8c6e687296f4a5d79c`.
Emulators, checkouts, APKs and logs were removed; no Fold was used. The method
is already included in the dedicated synthetic-profile CI scope, but hosted
CI has not run this expanded version. Personal learning remains opt-in, and
this does not prevent the first unwanted capitalization or resolve ambiguity.
