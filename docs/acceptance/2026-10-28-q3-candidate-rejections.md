# Q3 — rejected candidate response diagnostics (partial)

The primary response still consumes its matching request and emits its existing
response event before rechecking ownership. A rejected response now adds its
exact metadata-only reason: `STALE`, `INVALID` or `LIMIT`. Cancellation already
has its own response event and is not duplicated. Existing stale-request and
stale-revision distinctions remain. No numeric reason code or schema changes.

Selection construction now explains its existing null returns: overlarge joint,
local or compact pools and out-of-range local search counters report `LIMIT`;
inconsistent completion/validity, absent originals, protected or duplicate
candidate text, invalid canonical identity and an out-of-pool joint winner report
`INVALID`. Display-only supplemental validation retains `recordDecision=false`,
so its rejected pool does not mislabel the accepted primary response. The analyzer
includes these candidate rejection reasons without inventing editor outcomes or
reclassifying unrelated ranking `INVALID` events.

Validation:

- All 1,291 JVM tests pass with zero failures/errors/skips; debug lint, 30 analyzer
  tests and the scoring boundary gate pass. After the deliberate old-code probe,
  Gradle restored the same candidate compilation/test results from its cache;
  the preceding full candidate run actually executed these tests successfully.
- Nineteen invalid/over-limit response snapshots retain the original refusal,
  consume the request, preserve the composing state and candidates, and perform
  no editor writes. Their final diagnostic has the exact reason and originating
  request/session/revision with no text callback. Both inclusive search-limit
  endpoints remain accepted without changing the editor.
- Separate cases cover one cancellation event, an out-of-pool joint winner,
  suppressed display-only rejection metadata, and reentrant input from the first
  response diagnostic. The latter still invalidates the old response before any
  publication. Checks stay after that initial callback, as before.
- With only the controller replaced by parent `05fdae9`, three new tests fail on
  the old missing explanations (`NONE` instead of `INVALID`/`STALE`). The exact
  candidate source was restored and checked by hash before final validation.
- One preliminary test fixture switched personalization after registering its
  request and therefore cancelled its own request. The setup order was corrected;
  that failed log is retained separately from the intentional old-code probe.

The adjacent evidence binds sources, logs and the red probe. Full source-bound
12,012/1,676/1,600 replay will run at Q3 integration; earlier receipts do not bind
this edited controller. Mechanical refusal diagnostics, editor metadata/schema 9
and actual boundary-journal stress accounting remain open. No device install or
full Q3 completion is claimed here.
