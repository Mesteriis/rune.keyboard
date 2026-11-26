# A4: preliminary abbreviation replay with space

At source `0100dad32173cb08345dda8d497e00c9dea976e9`, the current-product host
replay was run twice on the five examples named by the review: `спб`, `мск`,
`адм`, `пгт`, `экон`, each at an empty prefix and followed by a space. All five
were retained exactly and Backspace returned the text to its pre-boundary state.
Both projected runs agreed; the driver completed with exit 0. These inputs are
review examples and are not an independent qualification set.

The current replay unconditionally calls `type(" ")` and its validation and
observation fields assume that same space. It therefore cannot establish the
behavior of `.` or `:`. The Q6 punctuation component registry records historical
exposure; it does not itself supply the A4 category-level protected-token replay.
The required 100–200 controls, category results, boundary parameterization,
full source/asset/corpus binding, and physical-device correction and Undo tests
remain open. The five unchanged examples must not be read as a category pass.

Raw local artifacts: input `build/review-a4-discovery-input-20261028.jsonl`
(SHA-256 `94ef1b52651356255573d8eceb3a1d7b65a2f693ab64cb41f71911156cdfc259`)
and receipt `build/review-a4-discovery-space-20261028/receipt.json` (SHA-256
`38b24d5fc3b9360fdfd755d4d5149d9ccb15f63eb2632e6a9b5d757d8a0c4b7a`). The
receipt binds the exact compiled sources, packaged assets and toolchain. This is
a host controller observation, not a physical editor or Fold test.
