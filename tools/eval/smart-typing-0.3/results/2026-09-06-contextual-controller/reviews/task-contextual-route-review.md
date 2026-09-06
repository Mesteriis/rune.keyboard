# Contextual controller production-route rereview

**Scoped verdict: PASS for prior finding 2.** The current implementation and frozen model-free evidence close the production owner, routing/readiness, live reply identity, and controller-side reason-attribution gap. No residual issue was found in this scope. Prior findings 1 and 3 were already closed by `task-contextual-metrics-closure-review.md` and were not reaudited here. Supplemental-cache admission remains the next separate task; this review does not approve scoring the 46 unresolved payloads.

## Production-equivalent admission

The bounded synchronous final-target bridge now preserves the relevant `LocalCandidateCoordinator` request and reply conditions:

- It reads the current owner at request time and requires both `owner.canRequestCandidateWork` and `controller.canRequestCandidates` before generation (`ContextualControllerAttribution.kt:146-156`).
- It calls the actual `LanguageRouter.route` for the current composing token, records the primary/fallback route, and requires route request plus readiness before `beginCandidateRequest` (`:157-170`).
- `PrevalidatedRoutes` derives the complete required language set from the actual route and admits it only when every primary/fallback language is both validated and ready (`:48-65`). The corpus path constructs this set only after all packaged trie, length, rank, and canonical-case readers validate (`:307-322,431`).
- Before `acceptCandidates`, it re-reads the current owner/controller state and route, then requires the exact reply and live session/revision/request identity, unchanged active language, original token, composing ownership, admission epoch, and current route readiness (`:171-201`). Rejection prevents candidate acceptance and the downstream model request.
- The same route request/readiness/invalidation/close functions are installed on the real `LocalCandidateCoordinator`, whose production selection gateway remains the tap path (`:108-110,389-403`). This evidence remains conditional on an already-ready final-target host route and makes no asynchronous worker-timing claim.

These checks match the production conditions at `LocalCandidateCoordinator.kt:195-237` within the approved direct-generation boundary. The bridge adds some stricter observable checks, including the reply stamp and captured composition equality, without relaxing a production guard.

## Label-free routing reasons

The JVM input remains exactly index, opaque ID, language, prefix, and current word (`ContextualControllerAttribution.kt:326-330`). No split, observed-boundary label, expected candidate, or old export classification enters the host decision. Terminal routing and secondary reasons are derived from current owner/controller state, actual generated alternatives, and current `ContextualPunctuationEngine` variants (`:204-245`). Kotlin defines one fixed reason order (`:68-74`), Python independently requires that exact order (`contextual_controller_attribution.py:34,416-429`), and the regression keeps overlapping `NO_OWNED_SPACE`/`ENGINE_EXCLUDED` reasons ordered without labels (`HostTypingEditExecutor.kt:295-304`).

## Regression and frozen evidence

The host regressions cover owner denial, a missing or unvalidated fallback reader, request denial/closure, successful EN-primary/ES-fallback admission, and thirteen reply/live-state invalidations (`HostTypingEditExecutor.kt:223-293`). The frozen receipts report:

- Python: 30 passing tests in `route-review-python-01.log`, file SHA-256 `1ed1572e46eb9ac101dfb9e1f5beeb557f34d5c6c80354d0c7b6937b19f017c4`.
- Host: 22 passing cases in `route-review-host-03/complete.json`, file SHA-256 `4fcbb672cec359aa4cdaa15cd91eeebac5f601e0eb1647363108a7aaa5482e15`.
- Prepare: 1,200 rows, zero harness errors, zero native calls, and no full-corpus numeric results consumed in `route-review-prepare-01/prepare-complete.json`, file SHA-256 `438796e396e3a24b41edc6c0fe4f3425663376b6183cf85b56463bdf7b5caf0e`.
- Routing: 909 contextual requests, 63 spelling requests, 42 canonical precedence, 25 incomplete generation, 1 unknown/no-alternative, 157 engine exclusions, and 3 no-owned-space rows. Payload admission remains 863 exact, 291 no contextual request, and 46 unresolved prefix-only mismatches.
- `route-review-comparison.json`, file SHA-256 `25718ef8af32cc55428567eafbdfe7600d6350b4538aa6fcbd8fda293bf068bd`, records no changed rows for input steps, before-candidate state, full/request generation, candidate acceptance, model requests, request counts, or request payloads relative to immutable `prepare-04`. It also records unchanged payload bindings, no packaged production-asset binding changes, and byte-identical unscored requests.

The unscored request bytes independently compare equal between `route-review-prepare-01` and `prepare-04`, both SHA-256 `a06a8571b61f20c4db56f22261ab8c35086b380dd360e56ddb9aacf3927bc9a6`. Thus the 160 former coarse contextual-ineligible terminals are refined to 157 `ENGINE_EXCLUDED` and 3 `NO_OWNED_SPACE` without changing the contextual request universe or treating any of the 46 unresolved payloads as abstentions.

Reviewed final identities:

| File | SHA-256 |
|---|---|
| `ContextualControllerAttribution.kt` | `7a9a89bab7b28d5a92cceebc86d1acfd5cf747e07ab4f81bdf515103aed012ba` |
| `HostTypingEditExecutor.kt` | `483972c83262de03cf615c40d434b707a2863f99cc61fdb0cf0ed343c3e28b6d` |
| `README.md` | `3dcf525004f7674423c3a9ef77b64b64ef7ff0f761cb9e51212696582299a58f` |
| `contextual_controller_attribution.py` | `be7209be14001dfdf843bb3645a31af9f6eb41a6872b85e7c02c732a69a04753` |
| `test_contextual_controller_attribution.py` | `ca31df0a22a36e3c55b5bfa1d96f34d64e35fa606aac788a3a84aa4052040772` |
| `route-review-prepare-01/protocol.json` | `a6938f4e19ad9781aae2075aed526d9f49cfdf113b5ccca4936d4baea920c3fd` |

This rereview was read-only except for this report. It ran no tests, Gradle, device operation, model call, scoring, numeric delivery, network access, or product/tool source edit.
