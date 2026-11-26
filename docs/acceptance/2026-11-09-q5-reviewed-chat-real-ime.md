# Q5: reviewed chat originals through the real IME

Two public Tatoeba-derived controls are now permanent emulator instrumentation
tests. They type `том натянул на себя бадлон` and `выдай мне админку` through
actual Rune keys and the remote composing editor, wait for the previously
observed `баллон` and `спинку` correction suggestions, then press Space and
require the original text. This exercises compact and contextual admission;
waiting for the actual competing suggestions prevents an unready candidate from
making the control vacuously pass.

On an isolated ARM64 API 37 emulator, the same two tests ran first on the
pre-fix source `177674d4` with the test added: both failed, showing the actual
replacements `бадлон → баллон` and `админку → спинку`. After applying the
committed protection change `c7281faf` in that temporary checkout, both passed
with zero skips. The earlier failure is a deliberate negative control, not a
passing result.

A third test confirms that the user can explicitly select `спинку` from the
candidate strip despite protection of `админку`. The final three-test class
passed without failures or skips on separate isolated ARM64 API 26 and API 37
emulators, using committed product source `c3cac0c8` and the new test source.
All three identities are required by the general Android CI report gate; its
14 host tests passed, including missing and skipped required-case probes.
Older general-suite reports predate these test identities and do not satisfy
the strengthened gate.

Five further controls exercise `пейринг`, `токсиков`, `забанили`, `могёт`
and `ебобо`, including the real long-press entry of `ё`. On API 37 the five
tests all failed against pre-fix source `177674d4`, with the corresponding
previous substitutions, then four passed against the protection change. The
fifth initially failed while waiting for the exact `бобо` suggestion: the
candidate was not visible, so that attempt did not establish whether Space
would preserve the original. A controller replay found `бобо` in the compact
pool but not in its displayed candidates. The revised preservation test waits
for any correction suggestion before Space; it does not assert that `бобо` is
visible or selectable. The manual-candidate follow-up below addresses that
specific visibility issue.
The expanded eight-test class passed on isolated ARM64 API 26 and API 37
emulators with zero failures or skips. All eight identities are required by the
general Android CI report gate; its 14 host tests passed.

The contextual policy now retains a proposal refused because the original is
valid as display-only evidence. The controller accepts it only from the
complete current joint search, validates it as a manual suggestion and keeps it
separate from automatic ranking and admission. On isolated ARM64 API 26 and
API 37 emulators, `ты ебобо` remained unchanged after Space, and selecting
`бобо` explicitly followed by Space produced `ты бобо `; both tests passed on
each API without skips. The full local JVM suite passed 1,394 tests with no
failures or skips, and the Android CI report gate host tests passed 14/14. The
ninth real-IME identity is required by that gate. The earlier four-pass,
one-failure run is the negative observation, not a passing result. These
results do not establish natural-chat quality or physical Fold behavior.

The full current-product parity gate ran twice for each fixed corpus in an
isolated checkout: all 2,160 disclosed CI rows and 12,000 historical rows
matched their respective frozen projections, with zero differing rows and zero
tolerated score differences. These synthetic regression inputs do not estimate
natural-chat quality. Temporary source checkouts, replay outputs and emulators
were removed.

A follow-up full-list regression reproduced the display-only proposal being
discarded when all seven baseline positions were occupied. The controller now
keeps baseline indices unchanged and considers one extra priority proposal
before limiting the ranked visible/expanded candidates to seven. The new
controller test failed before that change and passes afterward; it verifies the
seven-candidate limit, the expanded list, explicit selection and the following
Space. The full local JVM suite passed 1,395 tests with no failures or skips;
the final added expanded-list and Space assertions also passed in a targeted
controller-suite rerun. No new physical-device result is implied.
The two-pass frozen replay gate also passed again: 2,160 and 12,000 rows
matched their baseline projections with zero differences. Temporary checkouts
and replay outputs were removed.

These are disclosed controls selected after observing the errors, not an
independent natural-chat qualification or a complete phrase-quality measure.
No physical Fold or hosted CI run was performed. Temporary source checkouts,
APK files, screenshots and emulators were removed.

## Fold inner-screen follow-up — 2026-11-10

The reviewed-controls class now admits a physical Fold only with explicit
`allowPhysicalDevice=true` and `runeFailureArtifacts=false`. It disables the
personal-learning, touch, metrics and app-profile inputs for the synthetic run
and compares personal-store snapshots excluding the rotating diagnostic streams.
The existing driver restores and verifies the complete keyboard preference map.

On the unfolded Fold, all 11 current tests passed: nine disclosed phrase
preservation cases and two explicit manual-candidate selections. The device
reported `OPENED` before and after the class, not continuously. The test APK was
built from the clean `086b4433` source plus the test-only change, using the
pinned Git submodule, and installed as an update to the test package. The app
APK was not installed by this run. The first archive-based build failed the
expected upstream-revision check because it lacked Git metadata; the Git-based
build then passed without disabling that check. Both temporary source trees and
build outputs were removed.

The original keyboard and diagnostic preference maps and four IME settings
matched after the run. The test's non-diagnostic personal-store comparisons
passed. Eight displaced diagnostic files were preserved byte-for-byte in a
private, ignored recovery directory; these owner records must not be deleted as
build artifacts. No screen or hierarchy failure captures were enabled. These
observed controls do not establish independent natural-chat qualification.
