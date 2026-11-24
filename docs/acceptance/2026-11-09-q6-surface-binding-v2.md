# Q6: versioned acceptance binding for English surface exclusions

The versioned public-preparation binding now uses
`rune-acceptance-registry-bindings-v2`. It retains the exact lexical and control
ledger bytes and per-entry digests and additionally binds the EWT surface fixture,
its source lock and the code used to compute and check its keys. The normal
preparation verifier and independent corpus guard require the current v2
binding. Training, calibration, evaluation and promotion already compare this
shared registry binding, so a missing, changed or v1 binding is rejected on
those independent paths. This is an identity and exclusion check only: neither
registry is complete, and no corpus, labels, model or policy is qualified.

Historical reproduction continues to generate the original v1 ledger-only
binding. `verify_historical_registry_bindings_v1` can recheck those ledger
identities, but it does not check the EWT surface fixture and must not be used
as current acceptance. The regular verifier rejects a v1-only report.

The resumed validation passed the public preparation, no-build registry,
refinement, word-ranking, extra-epoch, retrieval, joint evaluation, joint
calibration and promotion test modules. A targeted training test also verified
that replacing the v2 binding by a v1-only binding is refused. A staged source
archive without `build/` passed 69 tests across the no-build registry, public
preparation, text preflight and selector modules. The isolated historical
boundary runner passed its original registered checks. The interrupted run at
the preceding pause exited 130 and is not treated as a pass. Temporary test
archives and the task-created empty root `build/` directory were removed.
Hosted CI and physical-device testing were not run.

At source `77bd1814`, a subsequent clean Git checkout with no initial root
`build/` passed the complete standard-library inventory: 181 modules and 896
tests, with no failed modules, timeouts, missing receipts, failures, errors,
expected failures, unexpected successes or skips. The pinned llama.cpp source
was exported from its locally available Git object. The temporary receipt
SHA-256 was `b62a8307f3e9fcf4db78c587c5fff09172627666bd81e1733c5c8e0b8845c22f`;
the checkout and receipt were removed. This does not cover scientific
backends, hosted CI, Android or device qualification.

At source `9cec783a`, a clean shared Git checkout with its initialized pinned
llama.cpp submodule and no initial root `build/` again ran the complete
standard-library inventory. The runner exited zero and reported 182 modules,
900 tests, zero failures, errors, skips, timeouts or missing receipts.
The surrounding temporary-checkout script then exited one: its post-run
summary attempted to read the output directory as a file. This was a wrapper
error after the successful runner, not an additional passing check; no receipt
hash was captured. The temporary checkout and output directory were removed.
The result does not establish registry completeness, fresh qualification,
hosted CI, Android or physical-device acceptance.
