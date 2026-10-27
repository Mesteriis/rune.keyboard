# U3: owned typing without personalization in NPL editors

`IME_FLAG_NO_PERSONALIZED_LEARNING` without a password now selects `INCOGNITO`.
Password remains `SENSITIVE`, including password+NPL. The append-only policy enum
separates owned composition, editor reads and personalization. Incognito permits
owned composition, qualified suggestions/corrections, mechanics and exact Undo.
`NO_SUGGESTIONS` still suppresses candidate/model work and correction, including
when combined with NPL. Sensitive/raw/non-text restrictions remain in force.

The IME gates package observation, word protection, typing tools, ranking from
personal history, touch learning/remapping, learning collection and quality
recording on explicit personalization eligibility. Incognito uses global typing
settings without reading/applying/registering an app profile. Instrumentation
found and fixed a real intermediate failure: using a null personal snapshot with
app profiles enabled triggered the resolver's loading fallback and disabled
incognito correction. Profile bypass now avoids that fallback.

Both deletion paths force code-point deletion outside the owned span, without
editor text reads. Caps lookup is forbidden; capitalization can follow an owned
sentence boundary only. Preview retains its existing NORMAL-only restriction.
Controller diagnostic admission is explicit, not a side effect of disabling
composition: incognito cannot reopen a diagnostic segment, record text/metadata,
or admit editor outcomes. Previously admitted NORMAL operations retain their
original, content-free terminal outcome across a privacy transition.

Validation:

- Two new old-code policy/capitalization regressions fail. All final 1,186 JVM
  tests pass with zero failures, errors or skips, including eager diagnostic
  observer, reopening, normal re-entry, composing batch and deletion checks.
- Five instrumented scenarios pass together on one disposable Android 36 arm64
  emulator: real fake-Binder correction+Undo in NPL; actual owned composition;
  NPL+NO_SUGGESTIONS with original SEARCH and mechanics; separate diagnostic
  streams frozen across password/NPL; password no-composition/no-read control.
  Normal-field positive controls prove the observers can see composing, caps,
  requests and actual Binder scoring. No downloaded model quality is claimed.
- Six personal-store roots are compared using SHA-256 for every file, including
  sidecars and explicit absence/creation/deletion state. Real stores seed valid
  learning and touch files; normal positive controls populate profile, controls
  and quality stores. The diagnostic scenario starts both real streams and
  compares all six existing roots before/after private input. File bytes and
  both stream snapshots remain unchanged. All seven observed read counters,
  including caps, remain zero in incognito. No owner phone data is used.
- The frozen 12,000-row current-product replay is byte-identical before/after
  after excluding host timings, with identical source/candidate/admission,
  boundary and Undo projections. Baseline observations were reused only after
  verifying every bound source hash against the current pre-change worktree.
  Metrics and product gates are identical; existing EN quality limitations and
  one ES holdout false change remain outside this card.
- Final IME boundary, release privacy and debug lint pass. The test harness was
  repaired for the new fixture allowlist and current schema-8 exact numeric
  metadata vocabulary. After two UI click failures before a dialog, the test
  invokes the enabled real row's click listener; both actual consent dialogs
  and stream behavior remain asserted. No consent requirement was bypassed.

This implements the owner-requested U3 revision to the old password/NPL criterion.
Architecture, current acceptance and the guide describe the revised contract;
the historical acceptance receipt keeps its old result with a supersession note.
Exact outcomes, source/asset/APK identities and replay hashes are adjacent.
The emulator was stopped and deleted. Fold installation and physical acceptance
remain pending through the unavailable paired-phone channel; this card claims
local/emulator acceptance only. Full review completion is not established.
