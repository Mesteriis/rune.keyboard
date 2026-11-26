# Q5: exact reviewed chat-original protection

Seven exact Russian forms from eight previously disclosed, post-hoc reviewed
Tatoeba controls are now protected against automatic word substitution:
`пейринг`, `токсиков`, `админку`, `забанили`, `бадлон`, `могёт` and `ебобо`.
The list is a small source-level supplement, not an alteration of the frozen
packed rare-word asset or a claim about complete word families. NFC and case
normalization use the existing token normalization. Other suggestions remain
available; the later real-IME follow-up restores the previously lost
contextual proposal as a manual option. The existing canonical-case
and finite-confusion policy boundaries are retained. Missing rare-word
resources still fail closed.

The public-original veto is also checked by the compact automatic-decision
path and its replay adapter. The first isolated candidate changed only the
ordinary public veto and preserved six of the eight reviewed occurrences;
both `бадлон` cases still changed through compact admission. That candidate is
not the final implementation. Its 2,160-row frozen replay matched; the first
12,000-row invocation used a nonexistent input path and failed before replay.
The corrected invocation of that first candidate matched all 12,000 rows.

For the final staged five-file patch (SHA-256
`cb6e6afc7bb84b8a7ee5675037ca8a12a195935a38d0bb6211899d7dd511d0d9`), a clean
temporary checkout generated the identical historical 34,330-row chat input
and separately ran baseline and candidate current-product controller replay.
Eight boundary outputs changed, all eight reviewed controls were preserved,
and unproofread control changes decreased from 41 to 33 of 9,543. Across the
24,787 synthetic typo rows there were zero gained and zero lost exact targets;
every Undo flag matched the actual pre-boundary and post-Backspace text, and
there were zero candidate Undo failures on changed boundaries. This is a
post-hoc regression comparison, not a natural false-change rate or independent
qualification. Exact protection can suppress a desired correction when a user
actually intends a different word.

The final candidate's two-run frozen current-product replay matched the 2,160
and 12,000 row baselines. The targeted `AutoCorrectionAdmissionGuardTest`
passed in a clean temporary checkout. The four personal-admission Android
methods, including a compact-path assertion for `бадлон`, passed with zero
skips on separate isolated ARM64 API 26 and API 37 emulators using real
packaged resources. These are targeted checks, not full Android or physical
Fold acceptance. Temporary checkouts, harnesses, APKs and emulators were
removed. No independent corpus, model qualification or hosted CI is implied.

At committed source `c7281faf`, a clean isolated Git checkout with the pinned
initialized llama.cpp submodule passed offline app JVM tests, lint, unsigned
release assembly, release privacy, IME boundary, forbidden runtime dependency,
native symbol and APK footprint gates. The fresh JVM XML reports contain 1,392
tests with zero failures, errors or skips. The unsigned APK was 180,122,901
bytes, SHA-256 `53d7a29411e94614409ae5e85cde03b2c6f1d2726bec08bef09e3d05a09ace79`.
The checkout, build outputs, temporary Gradle user directory and APK were
removed. Fold was not connected; no installation or physical-device result is
claimed. This does not establish independent source qualification or hosted CI.
