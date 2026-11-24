# Q7: standalone tests without a pre-existing build directory

After the ignored root `build/` directory was no longer present, direct
execution of `test_holdout_ledger.py` failed: the compact-ledger CLI test tried
to create its temporary directory inside the missing parent. The original run
executed 12 tests with one error. The CI inventory runner normally creates its
output under `build/` before running modules, which concealed this standalone
failure. This is a test setup failure, not a product or ledger failure.

A shared test-only helper now creates the ignored parent if needed and puts
each disposable test directory inside it. Thirteen affected test modules use
it; their own temporary directories are still removed by `TemporaryDirectory`.
The empty parent is intentionally not removed by the helper, so concurrent
users of `build/` are not disrupted. Existing nonempty build data is retained.
No production path, source identity, qualification policy or registry was
changed.

The previously failing module then passed 13 tests, including a regression that
checks parent creation, child removal and preservation of an existing file. In
a staged source archive without `build/`, all 13 affected modules were run
individually, with the empty parent removed between modules: 81 tests passed,
zero failures, errors or skips. This included five scientific modules using an
offline available Python environment. An initial validation launcher failed
with exit 127 because it retained the path of an already-disposed `uv` temporary
environment; no tests ran in that attempt. The corrected launcher invoked
`uv run` for each module and produced the results above. The test-inventory
check passed. The staged source archive and temporary test data were removed.
Hosted CI and the rest of Q7 remain separate outstanding evidence.
