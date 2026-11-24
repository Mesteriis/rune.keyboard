# Q6 complete source tokens behind shared unknown text fragments

The retained historical word-ranking text partitions contain 131 distinct
unresolved Russian surfaces shared across partitions. Re-reading their 430
retained fragments against the exact pinned Wikipedia shard maps every one
back to source text. For 179 occurrences the actual source token is larger
than the extracted Cyrillic fragment; these comprise 97 distinct full
hyphenated or mixed-alphanumeric surfaces in 81 source articles. None of the
97 full surfaces was in the earlier control surface exclusions. Other matching
occurrences are standalone. No canonical family is inferred for an unknown
fragment or compound.

The 179 source-attributed contexts are retained under
`tools/typing_experiments/shared-text-boundary-origin-v1/` with public-source
attribution. The two permanent registries add 97 exact full-surface keys and
174 distinct source-context keys; the control entry also binds all 81 article
identities. Existing 49 control and 198 lexical entries and both incomplete
coverage declarations remain unchanged. This is historical disclosure, not a
fresh independent holdout or model qualification.

The source audit verifies the pinned parquet, preserved archive, dictionary
receipt and input stability; two runs generated identical outputs. The fixture
contexts SHA-256 is
`e3975b29720430dadcbc6f90a0c9d7453a92f7732d8740ed3f4fbc06ea8c158e`;
its receipt is
`3a33f5cb656248546381def8c97720625455ae6c65abb3fd7364fb35f789adaa`.
The registration verifies source/receipt bindings, article membership,
fragment ordinal, token relation and identity; two generated registry pairs
matched byte for byte. Mutation tests reject altered fixture bytes and an
unrelated token even if its fixture hash is recomputed. Actual control and
lexical gates reject a sampled new full surface and source context. A staged-source
archive without `build/` passed the registration check. The initial inventory
ordering and malformed-fixture tests exposed errors that were corrected before
final validation. No model or APK was changed.

The final standard-library inventory passed 813 tests in 167 isolated modules,
with zero failures, errors or skips; its receipt SHA-256 is
`7d00a42c22229f6f8bad15ef1dc8e5e80069a12cf985f4026df8150050f174d3`.
The focused source audit and registry checks each passed three tests. The
scientific profile and hosted CI were not rerun for this data-only slice.
