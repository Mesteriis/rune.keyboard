# Q3 — bounded mechanical refusal diagnostics (partial)

The controller retains its existing planner result and BYPASS behavior, but now
records selected `Unchanged` reasons as metadata-only `MECHANICAL` events. The
allowlist is `PROTECTED_TOKEN`, `PROTECTED_PUNCTUATION`, `PROTECTED_LINE`,
`AMBIGUOUS_DOT`, `AMBIGUOUS_COLON`, `DOUBLE_SPACE_INELIGIBLE`, `TRUNCATED_CONTEXT`
and `OWNERSHIP_MISMATCH`. Numeric codes 66–73 are appended; earlier identities
and admission VERSION 1 are unchanged. The analyzer recognizes the new refusals
without treating them as editor modifications. Diagnostic schema remains 8.

Only an explicit single ASCII space, one of `,.;:!?`, or the existing double-space
gesture may emit these events. Letters, pasted fragments, newlines, tabs and
non-text commands remain silent. Ordinary no-change, disabled, unsupported,
policy and bounds results are not added to the journal. Existing replacement
and Undo code remains unchanged; new refusals have no diagnostic text callback.

Validation:

- All 1,296 app JVM tests pass without failures/errors/skips; debug lint, 31 analyzer
  tests and the scoring boundary gate pass.
- The boundary/reason contract covers all 18 current planner refusal reasons
  across eight qualifying and thirteen suppressed action fixtures (378 pairs).
  Existing numeric identities are locked by sequence.
- Five real controller/executor scenarios verify protected line/token/punctuation,
  an ineligible double-space gesture and truncated context. The independent editor
  retains exactly the input plus requested punctuation/space, with zero payload
  reads, no automatic Undo, and one metadata-only refusal event.
- Twenty-five ordinary letter inputs within an explicit command line and 450
  ordinary prose inputs produce no mechanical events. Two ambiguous dot/colon
  letter-input scenarios preserve their text and remain silent. The current
  planner's ambiguity reasons arise on letter input, so the boundary restriction
  deliberately takes precedence; the mapper does not invent a different action.
  Ownership may also be refused before a planner result exists; that preflight
  remains silent rather than fabricating a planner reason.
- One preliminary fixture incorrectly assumed a bare command name protects the
  line. Existing rules protect explicit flags/code markers/dot arguments. The
  fixture was corrected to an explicit flag; production planner rules were not
  changed. The failed log is retained.

## Replay compiler compatibility

Both actual Kotlin host compilers pass. The product manifest includes the new
component. The contextual host additionally consumes that same versioned source
manifest alongside its legacy and explicit host inputs, and binds the manifest
in runtime receipts. This repairs an observed stale source closure that omitted
current morphology/experiment/personalization/tool dependencies. Sources must be
versioned, unique and inside the repository; malformed schema, non-string,
absolute, traversal and duplicate paths are covered. All 37 contextual Python
tests pass. Its actual compiled host passes all 22 declared synthetic cases.

The initial contextual attempt refused a duplicate ambient-cache JAR under its
existing strict pin rule. An isolated view containing only SHA-256-verified pinned
JARs was provided; the strict check was preserved. A subsequent compile exposed
the stale source closure; after repairing it, the actual compilation and cases
passed. Both failures remain recorded privately. The final current selector's
source identities and compile/run commands match the compiled artifact, including
its recorded JVM, pinned compiler and Android stub. This is local host compatibility, not
native inference or renewed quality qualification. Old preparations/receipts
remain historical and require a fresh preparation under changed sources.

Full source-bound 12,012/1,676/1,600 product parity, actual boundary-journal stress
accounting, editor class/variation metadata and schema 9 remain for Q3 integration.
No phone update or full Q3 completion is claimed by this receipt.
