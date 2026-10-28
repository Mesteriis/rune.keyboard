# Local quality counters: storage contract

`QualityRecorder.recordAutomatic` accepts a fixed `AutomaticQualitySource` and
`AutomaticQualityOutcome`; `modelResponseMillis` accepts one integer duration.
These methods do not accept words, package names, arbitrary labels or timestamps.
They share the existing quality-metrics and eligible-editor gates. Shadow
comparison remains independently controlled, and its existing ephemeral text
comparison is excluded from the persisted snapshot.

The source/outcome table is separate from the existing eight `QualityEvent`
counters. Its fixed source order is common confusion, general local, compact
public, neighbor recovery, joint short, joint long, joint rescue, word context,
contextual ranker, infinitive revision, noun-case revision, model, contextual and
canonical case. The four outcomes are applied, explicit Undo, explicitly kept
original and expired application window. Model refinement is excluded because
that automatic source is disabled. Canonical case is counted separately from
word substitutions. Call sites must identify the source of an actual action or
expired application opportunity; the counter itself never supplies admission.

The table contains 56 integer counters. Model response time has five separate
buckets: below 50, 50–<100, 100–<250, 250–<500 and at least 500 milliseconds.
The existing six candidate-request latency buckets retain their identities and
values. All counters saturate at 1,000,000,000,000.

`QualityCodec` writes `RUNE_QUALITY_3`, followed by one unsigned decimal integer
per line in this order: eight legacy actions, six candidate-response buckets,
six shadow results, 56 source/outcome counters in source-major order, and five
model-response buckets. A final newline is required. The complete payload is
bounded to 2,048 bytes. Enum order and dimensions are part of this version's
persisted schema; changes require an explicit codec migration.

The reader retains versions 1 and 2. Old action/candidate/shadow values are
preserved, the version-1 manual-retype action is padded with zero, and all new
source/model counters start at zero. Old aggregate applications cannot be
attributed to a source, and old >=100 ms observations cannot be split into new
model buckets. Migration does not invent that history. The existing atomic
`no_backup/typing-quality-v1.txt` filename is retained; its header identifies the
payload version. No typed text or pending shadow comparison enters this file.

Counts cover the period since the last reset. An explicit Undo fraction is
available only after at least 100 source applications, with a valid numerator
not exceeding applications. A zero observed Undo fraction is not a correctness
estimate. This observational value does not enable/disable a source or alter
ranking, admission or editor operations. Hooks, dashboard reporting, debug-only
export and the review's real two-week owner-use acceptance must each retain
separate integration evidence.

Acknowledged automatic application and exact Undo hooks are now connected to
all existing automatic commit paths. A single-use in-memory application ticket
binds an actually incremented APPLIED count to its recorder and collection period;
reset/restore and metrics/eligibility transitions revoke it. The ticket contains
no text, does not retain the recorder/editor and is excluded from persistence.
Editor behavior never depends on whether a ticket was issued. Model refinement
remains excluded; CONTEXTUAL is manual-only and supplies no automatic count.
Explicit Original now records a current source proposal once; it does not imply
that the proposal passed automatic admission. Late local windows record only a
known preferred source; model windows record an owned pending spelling
opportunity. Existing 250 ms boundaries are unchanged and covered at 249/250/251.
Model response time is admitted at actual submission and consumed once for a
normal or late/discarded reply, with at most eight outstanding numeric identities.
Only the empty collection-period permission is retained; no input/prefix or word
fingerprint enters this history. Reset/privacy/recorder changes and shutdown
revoke it. This bounded sample includes reported refusals, including UNAVAILABLE
for CPU limits or engine failures; zero refusal duration is not inference time.
It is not a complete latency distribution. Debug-only export and final owner
integration still remain. Dashboard instrumentation also retains its synthetic
fixtures and actual reset checks.
Upgrade compatibility covers v1/v2 reads by this version; older binaries are not
claimed to read a v3 file.
