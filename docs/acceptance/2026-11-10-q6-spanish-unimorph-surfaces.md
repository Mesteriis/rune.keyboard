# Q6: Spanish UniMorph control-surface exclusions

[UniMorph Spanish](https://github.com/unimorph/spa/tree/b9655efb0e5ce0f99809badaa7f4e93017ab8430)
identifies English Wiktionary as its source and declares CC BY-SA 3.0. Two
downloads of the pinned `spa` file were byte-identical: 50,335,761 bytes,
SHA-256 `7a165d4b44eb078d23964f3eee3813f5140c5df0ffab0143c806c562e67f8771`
and Git blob `715b9b2e8120a824ef5653a9d7fbf872fc02924d`. Both captures
independently reproduced the same projection; the downloads were not retained.

The 1,196,245 source rows were compared against the existing exact surfaces
from the original Spanish spelling regression, product replay and named
confusion regression. Every supported one-word form of each matched headword
was retained, including ambiguous headwords. The fixture contains 983 source
titles, 46,911 distinct headword/form pairs and 46,294 exact form keys. Its
SHA-256 is `a62e9ace940ec9beddc5c1b033c08e15064e2ce1ddf811bbab22d9b18e0c2df2`.
The [notice](../../tools/typing_experiments/spanish-unimorph-control-surfaces-v1.NOTICE.md)
describes attribution and share-alike terms. These exact-form exclusions do
not establish intended senses, complete Spanish families or independent data.

Of those forms, 45,289 keys were absent from the prior control surface entries.
They are added as a new regression exclusion; all 66 previous entries and
coverage metadata remain unchanged. Other exclusion axes may also reject a
proposal, so this is not a count of previously admissible words. The source-bound
importer checks the fixture and parent identities; `--capture <spa> --check`
can reproduce the projection from the pinned source. The focused tests check
ambiguous alternatives, source and fixture drift, and actual preflight refusal
in both collection profiles. The source does not establish complete coverage;
fresh independent qualification remains blocked pending the remaining Q6 work.

The three importer tests, six control-ledger tests, 29 preparation tests and
three English importer tests passed. The original and product replay checks,
isolated historical text-boundary and suspended-retrieval checks, and test
inventory validation passed. The importer and its tests also passed from a
staged source archive without `build/`; that temporary archive was removed.
Hosted CI and a full test inventory were not run in this step.
