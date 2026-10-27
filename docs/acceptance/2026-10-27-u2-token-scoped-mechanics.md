# U2: token-scoped mechanical punctuation protection

Earlier prose symbols no longer disable every mechanical rule for the remainder
of a line. Spanish `¿Cómo estás ,` can remove the space before the comma;
`кто-то пришёл` can use the existing double-space gesture. The hyphenated,
apostrophe-bearing or quote-prefixed token itself remains protected. Existing
ownership, truncated-token, case/script and composing bounds remain unchanged.

Whole-line protection now covers the existing command-dot rule, explicit code
markers (`=`, either brace, backtick, dollar, backslash, pipe, either angle
bracket, slash or `::`) and CLI flags (start/whitespace followed by one or two
hyphens and a letter). This gives the appended `PROTECTED_LINE` reason; existing
enum ordinals are preserved. Other punctuation/token failures have exact
regression assertions, including expressive punctuation, opening quotes,
brackets, emoji, non-ASCII spaces and tabs. Protection ends at the newline.
No opening-quote acceptance, Cyrillic no-space sentence inference or new
number/abbreviation/newline double-space behavior was added.

Five new old-code regressions fail before the production change. Seven new test
methods in total cover useful behavior, every code marker and flag, existing
protected boundaries, and actual controller/executor composing commands. Both
hyphen-line correction and double-space Undo restore the exact expected raw
text with zero editor reads and one replacement command. All 1,181 app JVM
tests pass with no failures, errors or skips. IME boundary, release privacy and
debug lint pass. The first integration command used nonexistent task names and
failed before execution; corrected repository task names passed.

The frozen original 12,000 spelling rows (EN/RU/ES, calibration and holdout,
including 6,000 correct/protected rows) were replayed through current product
sources in `noun-case-production` mode before and after. Both runs complete
without row errors; all observation projections are byte-identical after
excluding only host timings. This includes input rendering, candidate/source
admission, boundary commands/text and immediate Backspace/Undo. Product metrics
and the actual `product_policy_gates` were computed for both splits and all
languages. New aggregate false changes: **zero**, including each negative
cohort. Existing ES holdout has one aggregate false change per 1,000 negatives;
EN does not pass every quality gate in either run. Those existing limitations
remain open under other review cards; this is not a new quality qualification.
No downloaded-model scoring or phone acceptance is claimed.

Exact commands, outcomes, per-language metrics, source/asset/input identities and
projection hashes are recorded in the adjacent evidence JSON. The replay driver
is a pre-existing modified workspace file, executed at its recorded hash and
not included in this commit. No thresholds, models or frozen assets changed.
