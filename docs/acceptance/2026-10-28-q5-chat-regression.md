# Q5: disclosed Russian chat-shaped regression baseline

A pinned public CC0 Tatoeba snapshot is retained with its source lock and
attribution. The generator lowercases and selects only Russian two-to-six-word
phrases with no internal punctuation. It excludes seven otherwise eligible
sentences whose source article is not already in the permanent lexical registry.
It emits 9,543 control phrases and deterministic orthographic candidates:
9,512 doubled consonants, 273 reflexive suffix changes, 1,553 removed signs,
6,357 е/и and 7,092 о/а substitutions; 34,330 rows total. The mix is defined
by applicability, not an estimate of real typing frequencies. Some generated
forms are valid words, so intended corrections are synthetic labels. The
unchanged source controls are not proofread: inspection of the eleven
non-case-only changes found apparent source typos such as `равносесие` as well
as colloquial and out-of-dictionary forms. Consequently a source-control
change is not automatically a false correction.

Two independent generations of rows, label-free inputs and the manifest matched
byte for byte. Regeneration from the retained source snapshot matched them too.
The current product observer completed all 34,330 token cases with opaque IDs
and no target labels. Its bound local replay finished with exit code zero.

Among 9,543 unchanged-source control rows, 41 changed (0.430%); this is a source
change rate, not a measured false-change rate. The descriptive Wilson 95%
interval is 0.317%–0.582%. Thirty were case-only; eleven changed spelling or
other text. There was one control per article cluster, so the article-cluster
count and interval coincide. Neither interval adjusts for correlated sentences
or authors. Across all cases there were zero observed prefix changes and zero
failed exact Undo checks; this token replay does not test multiword revisions.

The [dictionary audit](2026-10-28-q5-chat-dictionary-audit.json) found 9,278
controls with dictionary analyses and 265 without. All 30 changes among the
known controls were case-only; the eleven other changes were among unknown
controls. Dictionary absence does not imply an error: colloquial words, names
and other legitimate forms may be absent. This breakdown cannot resolve user
intent or replace manual control labels.

A [separate case-only review](2026-10-28-q5-chat-case-review.md) classifies all
30 capitalization changes and identifies five lowercase-preservation regression
cases; these are post-hoc judgments, not a population error estimate.

A [post-hoc review](2026-10-28-q5-chat-control-review.md) separates eight
colloquial-word preservation regressions from three possible source typos. It
is deliberately disclosed and is not a population false-change estimate. The
baseline preserves none of the eight reviewed forms; the comparison can be
repeated for a later product build.

The [manifest](2026-10-28-q5-chat-regression-manifest.json),
[aggregate report](2026-10-28-q5-chat-regression-report.json) and
[evidence](2026-10-28-q5-chat-regression-evidence.json) retain numeric results
and source/tool identities. This Russian chat-shaped sample is derived from a
source already used in training/evaluation, not a fresh holdout. It does not
qualify policy, establish natural typing accuracy, or complete Q5: broader
chat-register coverage, phrase/revision replay and any independent evaluation
remain outstanding. No phone, APK, model or runtime policy was changed.
