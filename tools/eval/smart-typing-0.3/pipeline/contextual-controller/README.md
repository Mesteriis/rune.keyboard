# Contextual controller attribution

This isolated host tool attributes all unchanged v5 source-boundary examples through current packaged candidate generation, current controller ownership and eligibility, production model coordinator admission, and the production candidate tap gateway. It has no inference command and establishes no semantic correctness or unseen-data quality gate. Full numeric replay requires separate review authorization.

`prepare` admits the strict existing v5 protocol/export/frozen config and complete calibration/holdout cache chain, binds current source, all twelve packaged assets and the pinned compiler/runtime, compiles the actual sources, types every exact input through an independent editor executor, and exports actual contextual requests. No numeric response is delivered in prepare. Previously excluded examples and every no-query or harness failure remain in the 1,200-row denominator. Exact prefix, ordered IDs and continuation strings are required for cache reuse. New or changed payloads are exported to `unscored-requests.jsonl` with a frozen receipt; they remain unresolved, never measured abstentions.

`replay --prepared DIR --output NEW_BUILD_DIR` validates that freeze again and delivers only exactly matching cached numeric responses to the actual current model coordinator. Native errors and unrepresentable IPC replies remain explicit. One explicit tap is attempted for each actual punctuation offer using its opaque ID, followed by a duplicate-tap refusal check. Reply acceptance alone may not edit the editor. Only the current owned boundary plus selected continuation may change. Source agreement compares an observed source boundary to the actual offered or delivered boundary; it is not semantic correctness. All rows, including engine exclusions, spelling/canonical precedence, errors and unresolved requests, remain reported. Zero denominators use the existing Wilson/rate convention. Unknown results suppress complete agreement claims.

`verify --prepared DIR --replay DIR` reconstructs the full input/export/cache/source closure and commands, checks row metrics, and freshly compiles the current bound source closure and re-executes both prepare and numeric replay against that compilation to compare every observation. It performs no inference. Successful temporary compiler/observation artifacts are removed; a failure preserves them in a fresh build directory ending in `-failed`. It never rewrites prepared or replay artifacts. `test-host` runs public synthetic executor, admission, precedence, threshold, stale-owner, refusal and tap cases. Python guard tests run with `python3 -m unittest discover -s tools/eval/smart-typing-0.3/pipeline/contextual-controller -p 'test_*.py'`.

Host commands require `--java` (pinned JDK 17), `--gradle-cache` (existing cache only), `--android-jar` and `--output` (fresh directory under repository build). The compiler is pinned by the existing contextual toolchain manifest. Compilation and execution use two processors and a 768 MiB heap. Prepare additionally requires `--corpus`, `--export`, `--calibration`, `--holdout`, `--config` and `--protocol`. The strict corpus loader requires its recorded Python/pyarrow runtime; the tool does not install dependencies or access the network. Existing output directories are refused, including partial failures. Keep a failed directory and choose a fresh sibling on retry.

The final-target-ready protocol uses current `KeyboardSettings.DEFAULT`, current qualification, a NORMAL editor, one active language and per-code-point commands with acknowledged composing selections. No prior-word candidate callback is delivered, and no double-space gesture is asserted. The target word receives actual packaged generation. Actual spelling requests and canonical suggestions retain precedence and receive no contextual scores. The model transport is a captured-request host seam; readiness is explicitly ready, pause scheduling is deterministic, and no actual model service or Android `InputConnection` is claimed. Grapheme behavior uses JDK 17 `BreakIterator`. This measures conditional content outcomes for a ready final target, not asynchronous device availability, wall-clock latency, IME rendering, frame timing, or physical key delivery. No source labels enter the JVM. There is no corpus editing, threshold fitting, new qualification, or model call in this tool.

The output includes old engine decisions beside current routing/action results, exact changed-row IDs, all seven decision counts, original unused response/error identities, input-edit ledgers and exact rate denominators. Unrepresentable replies also prevent a complete result. A refused or unattempted offered tap cannot produce a clean functional completion. Native duration is preserved unchanged in response evidence; the host callback field alone truncates toward zero to a `Long`, without waiting. The result does not reinterpret a manual punctuation tap as an automatic edit or automatic Undo.

Final synchronous candidate admission explicitly mirrors the live owner guards in `LocalCandidateCoordinator`: current `canRequestCandidateWork`, current candidate ownership, actual `LanguageRouter` request, all routed languages ready from validated trie/length/rank/case assets, and a second check of session, revision, request ID, language, original token, composing span and invalidation epoch before accepting the reply. The local selection gateway uses the same route request/readiness functions. The host has no loader worker; readiness is a synchronous check over already validated readers. A missing primary or fallback reader is never promoted to ready. Synthetic tests can deny or invalidate these seams, but corpus inputs cannot.

Each row records a terminal route plus `secondaryReasons` in a fixed declared order, independently of corpus labels and engine-export joins. `gateFacts.candidateAdmission` retains requested/live routes, current owner admission, route proof/languages, request/reply identities and each reply guard. `contextualVariantCount` is derived directly from the actual current owned context and production engine. Thus `ENGINE_EXCLUDED` and `NO_OWNED_SPACE` are observed on the host, including when a different terminal reason takes precedence. Action-contract version 2 requires this guard path; prior preparations remain immutable historical artifacts.

## Frozen supplemental responses

Supplement admission has no inference command. It admits only the unmatched contextual payloads regenerated from a fresh preparation. Existing exact-cache and no-contextual-request rows cannot receive a supplement. All seven ordered candidate IDs, original prefix bytes, continuations, opaque row ID, language and split are frozen with the prepared completion, unchanged policy/config, exact backend identity and physical model/runner hashes. This source change requires a new `prepare`; old preparations are preserved and cannot be adopted under changed sources.

Run the following with the recorded Python 3.11/pyarrow environment. `TOOL`, `PREPARED`, and `SUPPLEMENT` below are task-specific shell variables pointing to this Python file, the fresh completed preparation, and a fresh build directory. The freeze reserves exactly `SUPPLEMENT/calibration` and `SUPPLEMENT/holdout`; alternate run directories and existing/orphan slots are refused. Commands only stage or validate files; an authorized operator performs native scoring separately.

```sh
python3 "$TOOL" supplement-freeze --prepared "$PREPARED" --output "$SUPPLEMENT"
python3 "$TOOL" supplement-stage --freeze "$SUPPLEMENT" --split calibration --output "$SUPPLEMENT/calibration"
```

The staged `requests.jsonl` is plain native protocol input, one `{id,prefix,candidates}` object per line, in frozen order. Candidate IDs remain bound in `freeze.json`; their positions are 0 through 6. `identity.json`, `command.json`, and `run-input.json` are created before any native invocation. The command contains the absolute two-element runner/model argv, cwd and three stream paths. No shell command interpolation is needed. The runner and model paths come from the already admitted backend config. The score output must be plain response JSONL, with no cache-identity header. Each response is either `{id,error}` or `{id,durationMillis,scores:[{id,sumLogProbability,scoredTokenCount},...]}` under the existing strict response validator. A valid response with an IPC-unrepresentable token count/duration remains explicitly unresolved. Native errors are retained as unavailable; neither case is retried or dropped.

For the authorized operator, this standalone invocation records one attempt and creates every output exclusively. It does not contain a retry loop. Save its exact source in the run's parent evidence directory if an independently archived command script is desired. Invoke with the staged run directory as the sole argument; use it only after review authorization.

```python
import hashlib, json, pathlib, subprocess, sys
run = pathlib.Path(sys.argv[1]).resolve(strict=True)
hash_file = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
command = json.loads((run / "command.json").read_text())
receipt = json.loads((run / "run-input.json").read_text())
identity = json.loads((run / "identity.json").read_text())
assert not (run / "execution.json").exists()
assert not (run / "complete.json").exists()
assert hash_file(command["argv"][0]) == identity["backendIdentity"]["runnerSha256"]
assert hash_file(command["argv"][1]) == identity["backendIdentity"]["modelSha256"]
assert all(hash_file(run / name) == value for name, value in receipt["files"].items())
exit_code = -1
with open(command["stdin"], "rb") as source, open(command["stdout"], "xb") as output, open(command["stderr"], "xb") as errors:
    try:
        exit_code = subprocess.run(command["argv"], cwd=command["cwd"], stdin=source,
                                   stdout=output, stderr=errors, timeout=900, check=False).returncode
    finally:
        output.flush(); errors.flush()
        evidence = {"schemaVersion": 1, "attempts": 1, "exitCode": exit_code,
                    "commandSha256": hash_file(run / "command.json"),
                    "runInputSha256": hash_file(run / "run-input.json"),
                    "requestsSha256": hash_file(run / "requests.jsonl"),
                    "responsesSha256": hash_file(run / "responses.jsonl"),
                    "stderrSha256": hash_file(run / "stderr.log")}
        with (run / "execution.json").open("x") as stream:
            json.dump(evidence, stream, sort_keys=True, indent=2); stream.write("\n")
if exit_code != 0:
    raise SystemExit("Native attempt failed; preserve this run without retrying")
```

Admission requires a successful process completion plus exactly one response for every staged request, in order. Missing/duplicate/unexpected/reordered IDs, malformed numbers, candidate reordering, partial JSONL, output/hash/identity drift and nonzero process exits fail without writing a completion marker. A zero-exit run containing native error responses can complete and retains every error ID. Partial evidence never becomes complete. The execution receipt attests the external command and hashes; it is not a trusted execution or timing proof beyond the operator's preserved artifacts.

```sh
python3 "$TOOL" supplement-complete --freeze "$SUPPLEMENT" --run "$SUPPLEMENT/calibration"
python3 "$TOOL" supplement-stage --freeze "$SUPPLEMENT" --split holdout --output "$SUPPLEMENT/holdout" --calibration "$SUPPLEMENT/calibration"
# Only now invoke the staged holdout command once using the same operator procedure.
python3 "$TOOL" supplement-complete --freeze "$SUPPLEMENT" --run "$SUPPLEMENT/holdout"
python3 "$TOOL" replay --prepared "$PREPARED" --supplement-freeze "$SUPPLEMENT" --supplement-calibration "$SUPPLEMENT/calibration" --supplement-holdout "$SUPPLEMENT/holdout" --output "$REPLAY"
python3 "$TOOL" verify --prepared "$PREPARED" --replay "$REPLAY"
```

Holdout's staged receipt binds the full immutable calibration completion before scoring; completion and later replay revalidate that chain. There is no calibration fitting step. Replay requires all three supplement locations together, validates both complete splits and refuses unconsumed supplemental IDs. `SUPPLEMENT_OK` and `SUPPLEMENT_ERROR` remain distinct from `EXACT_CACHE_OK`/`EXACT_CACHE_ERROR` through the actual host transport and row ledger. Every delivered supplemental response binds its own directory, response-file hash, completion hash and freeze identity. Original-cache rows retain their original file hash. Verify reopens all exact supplement files, reconstructs their admissions and all row metrics, and recompiles the bound current host to replay both preparation and delivered outcomes. All 1,200 rows and the existing error, exclusion, tap and source-agreement semantics remain unchanged.
