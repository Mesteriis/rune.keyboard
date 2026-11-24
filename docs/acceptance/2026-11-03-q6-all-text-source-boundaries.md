# Q6 source-token boundaries for all historical text partitions

The 430 retained historical word-ranking text fragments contain 2,078 distinct
Russian surfaces unresolved by the pinned dictionary-only analysis. The pinned
Wikipedia source provides complete occurrences for 2,076; two were only found
truncated in the retained fragments. Among the complete matches, 470 source
occurrences have a larger hyphenated or mixed-script token. They represent 258
full token surfaces in 127 source articles. Of those surfaces, 97 were already
excluded by the preceding shared-fragment audit and 161 are additional.
Unknown fragments are not assigned guessed canonical families.

The retained attributed fixture binds each occurrence to its source article,
offsets and unknown-word ordinal, including multiple unknown parts of the same
compound. The control ledger now excludes all 258 exact full surfaces and 384
source contexts; the lexical ledger excludes those 384 contexts. All existing
50 control and 199 lexical entries and their incomplete-coverage declarations
are preserved. These disclosures do not establish full sentence or family
coverage, a fresh independent holdout, or model qualification.

The audit binds the source shard, historical archive, dictionary, helper code
and input ledger. Two source-audit runs and two independently generated ledger
pairs matched byte for byte. The fixture contexts SHA-256 is
`df51e62b0196b2c2ac74f4f5a74d1c6254f3717dd3979701f904d6ed7997ada3`;
the receipt SHA-256 is
`e48941dae2690e3a861334225a148ebfb582f71801654850fa8a54489ae9abee`.
The receipt describes the ledger before this registration; reproducing its
counts requires that exact prior ledger. Registration validates source and
fixture bindings and source-token relationships. Focused tests cover truncated
fragments, multiple unknown parts, modified fixtures and actual overlap gates.
No model or APK is changed by this slice.

The final standard-library profile passed 817 tests across 168 isolated modules
with zero failures, errors or skips; its receipt SHA-256 is
`f3e44f3716aff737ccd0f873cda67431622e90677cf37763d3e27550ff29e6be`.
The focused audit and registration suites passed four and three tests. The
staged-source archive passed registration without `build/`; the test inventory
check passed. The scientific profile and hosted CI were not rerun for this
source-disclosure slice.
