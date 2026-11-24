# Q6 historical neighbor prefix exclusions

The 15,000 retained source-attributed neighbor rows contain 2,500 distinct
prefixes and 12,856 distinct Cyrillic token surfaces under the importer’s
projection. The pinned Pymorphy dictionary recognizes 11,693 surfaces and
leaves 1,163 unresolved. All dictionary analyses yield 7,903 family keys,
including 878 absent from the preceding ledger; unresolved surfaces yield 1,163
exact keys, including 979 previously absent. Prefix boundaries, mixed scripts
and hyphens can produce fragments; these are dictionary projections, not a
claim of complete linguistic analysis. Unknown forms are protected only by
exact surface, without inventing family identities.

Two independent imports produced identical ledger bytes (SHA-256
`ad11f81bf3d5a4c5fba6dbeed5f24c950f8857bf4ef1e3ab8ecb0f096b7596b7`)
and numeric receipts (SHA-256
`57a319469b7bf31d81542552882857065438dbb8bc9f177016ea434e190329ca`).
A dictionary family and a previously unknown exact surface that passed the
preceding incomplete registry were rejected by the updated preparation gates.
Focused tests cover multiple dictionary analyses and unresolved forms. The
static check verifies source and entry bindings without a build directory or
scientific dependencies; it does not redo morphology analysis.

The preceding source-segment checkpoint passed 807 stdlib tests across 165
modules without failures or skips (receipt SHA-256
`5327b553b00fe187ef66852b510d60ef071ec28b46678fd94707c0e80c31db52`).
The original historical generator remains unrecovered; global provenance and
independent qualification remain incomplete. No model was trained or scored.

The first full stdlib run after this entry failed one of 166 modules: the
public-ledger snapshot test still assumed the previous number of entries with
unsupported surfaces. The assertion was updated to check this new entry
explicitly while retaining the original checks for unresolved family axes. All
24 tests in that module passed on rerun. The first full run remains failed; a
new complete run is needed for the corrected checkpoint.

The subsequent full stdlib run completed successfully: 809 tests across 166
modules, zero failures, errors or skips (receipt SHA-256
`d7e90d61cf4180d01e72cb5f69d11684bed525acbc5a6cfd1f0ba1df69b33fe3`).
The separate Android boundary-runner test file changed during this run and is
not part of this inventory; its 12 tests were run independently.
