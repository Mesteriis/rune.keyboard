# Frozen device TSV protocol, version 1

ASCII record names, tab-separated fields, LF terminators. Query strings are only
in the public frozen input fixtures; outputs contain predeclared IDs, language,
format, enum labels, hashes, counters and timing/memory values. No timestamps,
host paths, serials, PIDs, model/editor/user content. Negative optional metrics use
-1 for unavailable; wall times/counters are nonnegative. The historical full
allocation column is parsed as an integer but entirely unsupported on Android.
Every record is required; extra/missing/duplicate rows and failed processes reject
the run. `records.py` is the strict gate for newly pulled transcripts.

## Full and cold

Preflight: `DEX <sha256>` followed by `VERIFY PASS <frozen-file-count>`.

- `META api language format profile mode 3 1 timeout_seconds`. Language en/es/ru;
  format front/trie/delete; profile development/smoke; mode full/cold. API -1 is
  host and cannot satisfy an API26 gate. The two constants are measured repetitions
  and full-profile warmup count.
- `FIXTURE <sha256>` binds the selected query TSV; the DEX's Frozen map binds all
  assets, separate frequency, notices and all six query TSVs during preflight.
- `LOAD frequency|index elapsed_ns` has exactly one record for each stage.
- `MEM_HEADER stage heap_used heap_committed native_allocated pss private_dirty rss peak_rss`.
- `MEM` has that stage and seven byte-valued observations. Cold stages: boot,
  fixtures_loaded, frequency_loaded, index_opened, first_query. Full additionally
  has warmup_complete, measure_complete, post_gc_requested. A requested GC is not
  proof that all garbage was reclaimed.
- `ROW_HEADER language format profile phase id repeat search_ns topn_ns cpu_ns allocated_bytes gc_count states verified rows reason expected returned top7_equal prohibits_autoreplace`.
- `ROW` uses that header. `topn_ns` includes search and ranking; `search_ns` ends
  before ranking. `rows` counts evaluated DP rows, separate from inspected search
  `states`. `verified` counts candidates sent to distance verification. `reason`
  is NONE/STATES/VERIFIED. Complete rows require oracle neighbor count and top-7
  equality; capped rows always stay within 8192/64 and an exhausted result vetoes
  automatic replacement. Expected counts are pinned per query ID in the manifest.
- `DONE PASS query_count measured_reference_count completed_bounded_runs`.
- `FAIL stage id exception_class` or `TIMEOUT stage id` fails the process/run;
  no exception message or query text is emitted.

Cold has one `cold_first` row (repeat 0) for the first fixed query, per process.
Full adds every query as `warmup` (repeat 0), and every query as both `reference`
and `bounded` for repeat 0,1,2. There are exactly nine full processes, or 27 cold
processes (three per language/format). No row is silently omitted from validation.
The retained legacy full reducer is behind the stricter portable record gate.

## Standalone exact

Preflight: `DEX <sha256>`, `MANIFEST <exact-manifest-sha256>`,
`VERIFY PASS <base-frozen-file-count> 3`. The base hashes are the full comparison's
unchanged assets/frequency/notices/query fixture records.

- `META api language format 277 1 5 timeout_seconds`.
- `MANIFEST <exact-manifest-sha256>`.
- `OPEN elapsed_ns` includes opening the same format files/sidecars as full.
- `MEM stage heap_used heap_committed native_allocated pss private_dirty rss peak_rss`.
  Numeric stages 0 boot, 1 fixtures loaded, 2 index opened, 3 first query,
  4 warmup complete, 5 measured passes complete.
- `ROW phase numeric_id repeat cohort label wall_ns cpu_ns allocated_bytes gc_count passed`.
  Phases 3 first-query, 4 warmup, 5 measured. `passed` must be 1. Labels 0 absent,
  1 present, 2 empty; cohorts 0 original development, 1 present controls,
  2 structural absent controls, 3 empty control.
- `DONE PASS 277 1385 found_total`. `found_total` includes first, warmup and
  measured true results, ensuring lookup values are consumed.
- `FAIL stage numeric_id` or `TIMEOUT stage numeric_id` fails the process/run.

IDs are EN 0..276, ES 1000..1276 and RU 2000..2276. Each language's original 240
query IDs map explicitly through `original_id` in the manifest. There is one
first-query row, all 277 warmup rows, and 277×5 measured rows in each of nine
processes. Measured query offsets rotate by `37 * repeat`. Records retain all
unavailable values. CPU/allocation/GC p95 is null if any contributing repetition
is unavailable before median reduction. Current Android allocation is always -1.

## Files and history

`manifests/full.json` and `manifests/exact.json` are unchanged frozen input schemas.
Each asset record has relative `path`, SHA-256 and byte count. Each query group
has language/profile/count, frozen query SHA, and IDs/category/stratum plus exact
labels or full neighbor counts. `package-manifest.json` pins repository proposal
files; `source-origins.json` records unchanged historical source identities.
`toolchain.json` pins the promotion-time cached jars and documents build versions and processor/heap
limits, with no local dependency paths.

The historical record archive is a UTF-8 JSON map from safe relative record names
to the exact original UTF-8 transcript, compressed with deterministic gzip and transported as 120-column base64 in
`evidence/records.json.gz.b64` so the repository proposal stays text-only. Its
manifest carries the compressed hash, bounded decoded byte count and individual
transcript SHA/size. Readers check every entry. There is no executable artifact
inside that archive. Preserved JSON summaries are descriptive original evidence;
`decision.json` explicitly identifies authoritative and diagnostic cohorts and
excludes unsupported metric claims. Fresh summaries are always tied to the new
build's actual DEX, not rewritten to resemble the historical preflight.
