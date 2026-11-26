# Q2: local documentation and source acceptance

Q2 is verified locally against the original documentation/privacy/source scope.
The current app, release and data/model acceptance boundaries remain distinct.
This closes this card; it does not close the complete review.

| Requirement | Current evidence |
| --- | --- |
| Persisted words/phrases, hashes, counters/flags, limits, sensitive/incognito exclusions and separate resets are disclosed. | [Learning disclosure](2026-10-28-q2-learning-privacy.md): EN/RU consent, guide/privacy text, seven records and three writers; see the current-source follow-up below for the added case-rejection fields and checks. The API26 node/layout proof predates that change. |
| Architecture describes actual model calls, scheduler responsibilities and all source/order branches. | [Source cascade](2026-10-28-q2-source-cascade-notices.md): 13 SpellingSource / 14 DiagnosticSource values, named ranking/admission/event routes and disabled refinement; current checker passes. |
| Unreleased records the changes without a release bump. | CHANGELOG.md has Unreleased; app version remains 0.4.2 / code 8. No tag, push, workflow dispatch or publication was performed. |
| Current guide/schema/count/resource facts and links are synchronized. | [Guide facts](2026-10-28-q2-guide-facts.md), [README sources](2026-10-28-q2-readme-sources.md) and [guide/navigation](2026-10-28-q2-guide-navigation.md): 18 switches, schema 9, separate 48/24-character model windows, actual sizes, historic metric labels, 160 focused JVM tests and source/link regression checks. |
| Declared local provenance and README source paths exist in Git. | [Packaged provenance](2026-10-28-q2-packaged-provenance.md), [compact sources](2026-10-28-q2-compact-sources.md), [joint/neighbor sources](2026-10-28-q2-joint-neighbor-sources.md), [holdout variants](2026-10-28-q2-holdout-sources.md), [disclosed fixtures](2026-10-28-q2-disclosure-tools.md): retained scripts/policies, exact declared hashes or explicit historic archives, tracked README sources and complete reachable local navigation. Remote dataset identifiers and generated outputs are separately identified inputs/artifacts. |
| Every current experimental bin/gram/ctx has explicit attribution/provenance and scanner accounting. | NOTICE covers all 13 numeric experimental assets. The exact data-policy gate covers 29 entries, and current source preparation/scanner acceptance below passes. |

## Current scanner acceptance

The pre-publication review found that the current disclosure checker failed
after the later case-rejection profile change: the writer hash and snapshot
field inventory were stale, and two documented `PersonalWord` roles were
mistaken for a duplicate row. The current V1/V2 encoder and the guide, privacy
policy and EN/RU consent disclosures were reviewed together. The checker now
binds the current writer, the `caseRejections` list and its 512-entry limit,
requires both guide rows, the privacy-policy statement and both consent
descriptions, and still rejects unreviewed serialization changes. All 14 focused tests pass. This is local
source evidence, not an updated Android consent UI or hosted CI run.

Actual pinned fdroidserver 2.4.5 prepared and scanned committed source
`2c1ff9751e74ef11241e0a6e5e3557ff22353724` in a fresh separate checkout.
All 29 exact data entries, 11 approved prepared-source changes and seven
source/qualification positive/negative probes pass; there are zero fatal scan
findings. Both known historical warnings remain: the calibration gzip and the
upstream Keynote file. Scanner networking was blocked and installed SDK/cache
inputs were reused. Source hashes, actual exit codes and markers are preserved
in the adjacent receipt.

Scanner accounting uses the current typed review policy. Published 0.4.1/0.4.2
recipe pins remain intact. The original suggestion to add every ctx/gram to
scanignore is contradicted by the actual controlled scanner probe: adding the
three inventory-only files gives exactly three fatal unused-path errors;
restoring the exact policy returns zero. Those resources remain explicitly
inventoried without unused suppressions.

This is source/preparation/scanner acceptance, not build_local, a new release
APK, an independent build-server run, source tarball export or final binary scan.
Those distribution requirements remain in Q1. Hosted CI remains in Q7.

## Scope still open in other cards

Q6 still requires canonical-family recovery, missing historic source identities
(including the earlier neighbor corpus generator), complete transitive model/data
lineage and fresh independent qualification. Historical reports and disclosed
corpora do not replace those requirements. Their references and original
claims are now durably retained with explicit historical notices.

Guide/candidate behavior was checked against current source and 160 focused JVM
regressions. Local navigation validates pinned submodule file bytes; it does not
validate remote URLs, anchors, full TalkBack/UI/device matrices or population
accuracy. Those broader review items remain open. The untouched pending named
qualification-case owner patch remains outside this documentation acceptance.
