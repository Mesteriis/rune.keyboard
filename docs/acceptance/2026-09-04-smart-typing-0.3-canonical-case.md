# Smart Typing 0.3 canonical case checkpoint — 2026-09-04

Lowercase valid words previously stopped at exact lexicon membership, so Rune could not offer the
source spelling `Москва`, `London` or `Juan`. The runtime now performs one bounded exact lookup in a
separate canonical-case asset after ordinary membership succeeds. A matching title-case spelling is
shown beside Original and applies only by explicit tap to the current owned composition. It remains
ineligible for automatic replacement and therefore cannot silently capitalize ambiguous common
words such as English `may`.

RNC1 assets are derived offline from the already pinned and licensed RU/EN/ES surface forms. A key is
included only when its lowercase form has exactly one title-case source spelling; a separate bit
records whether a lowercase source spelling also exists. The three assets contain 20,221 EN, 1,283 ES
and 16,834 RU records and total 1,155,850 bytes before APK compression. Their manifest pins the frozen
surface hashes, builder hash, counts, sizes and output hashes. Runtime loading is lazy on the existing
serial candidate worker. It performs no model binding, network access, editor readback or per-keystroke
scan, and a malformed or mismatched asset fails to Original.

Host coverage verifies deterministic derivation, malformed UTF-8/order/case rejection, exact lookup,
valid-word candidate admission, explicit replacement and the automatic-replacement veto. This
checkpoint does not claim proper-name precision, automatic capitalization qualification, API 26/API
37 instrumentation or physical Fold battery/performance results; those remain release gates.
