# U11: disclosed EWT annotated-edit experiment

A reproducible offline prototype trains a smoothed single-character edit
channel on UD English EWT `CorrectForm` annotations and ranks candidate words
from the pinned public frequency vocabulary. The source lock and all three EWT
partitions are verified. Original documents do not cross partitions. Exact
corrected target words occurring in training are removed from development; test
also excludes words present in either training or development. This is exact
word separation, not morphological-family independence. The corpus was already
disclosed, its correction labels were not independently adjudicated, and its
web text does not represent all keyboard input.

The train partition contains 1,051 annotated corrections, of which 482 pass the
strict ASCII single-edit filter, covering 353 distinct targets. Dev has 88 and
test 74 filtered rows before word-overlap removal; 22 dev and 29 test rows are
removed for overlap. The remaining dev has 66 rows: 18 have a vocabulary-valid
original and are protected, one target is unavailable, and 47 are scored.
Frequency alone ranks the annotated target first in 42/47; the edit-channel
weight selected on dev ranks it first in 45/47. The remaining test has 45 rows:
14 protected originals, two unavailable targets and 29 scored rows. Both
frequency and the selected edit channel rank the target first in 29/29 scored
rows. A supplemental pool-count probe found only one vocabulary candidate in
23 of these rows and multiple candidates in six. These selected subsets do not
measure overall recall or false changes;
there are no independently labelled correct-word or name controls. This result
does not support replacing the existing model or admission policy.

All 425 distinct corrected target forms that are present in the pinned public
vocabulary are added to the permanent lexical exclusion registry, including
109 keys absent from the prior family exclusions. They use an exact
English-string hash namespace as a conservative overlap signal, not a claim
that inflectional families have been resolved. Other shapes and targets outside
that vocabulary remain uncovered; existing source document and sentence
exclusions remain in force, and global coverage remains incomplete. Hashes of
public vocabulary are reversible by dictionary attack, not anonymization. The
stored receipt contains aggregate counts and target hashes; it contains no
sentence, document ID, typo pair or learned event table.

The [experiment](../../tools/typing_experiments/english_ewt_error_model.py)
was run twice on the pinned source with byte-identical aggregate receipts; the
[registration check](../../tools/typing_experiments/register_ewt_error_targets.py)
works without the source corpus or `build/`. Tests cover edit types, protected
originals, train/dev/test target overlap, document overlap, missing scored
partitions and receipt/parent mutation. No product model, threshold, APK, or
device state was changed. Q6 and U11 remain open for complete exclusion and
independent natural-data qualification.

Validation: the full standard-library inventory passed 843 tests across 173
modules with zero skips; one source-drift unit test was strengthened during the
run and passed separately afterwards. Both historical text-boundary suites,
named regressions and the 279,056-key neighbor check passed. The registration
and its three tests passed from a staged-source archive without `build/`.
The previous EWT lemma registration and all 25 preparation tests passed. Hosted
CI was not run.
