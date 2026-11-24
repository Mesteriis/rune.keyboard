# Q6 historical refinement text source-token boundaries

The retained 1,069 historical refinement text records contain 10,745 distinct
Russian surfaces unresolved by the pinned dictionary-only analysis. Reading
the exact pinned Wikipedia shard against those records found complete
occurrences for 10,738; seven distinct surfaces occurred only at truncated
ends. Ten distinct surfaces were seen truncated, including some that also had
complete occurrences. No canonical family is inferred for an unknown word.

For 3,297 source-attributed occurrences the complete source token is larger
than the cleaned Cyrillic fragment. They comprise 1,370 full hyphenated or
mixed-script forms in 704 articles: 79 forms were already control exclusions
and 1,291 are new. The new control entry excludes all 1,370 forms, 704 article
identities and 2,617 input keys; the lexical entry excludes 2,606 distinct
source-context keys. The original 51 control and 200 lexical entries and
incomplete-coverage declarations are preserved. These disclosures are not a
fresh independent corpus or model qualification; unknown canonical families
and full historical provenance remain open.

The source audit binds the pinned public shard, archive, dictionary, the ledger
before registration and helper bytes. Two runs were byte-identical. The retained
contexts SHA-256 is
`642292acfc9147a3c4592940df7e0461d0ed3b63bb101397df751b646e95efbb`;
the receipt SHA-256 is
`0d6fa8499ff20789511a797519ad89bc0557f03acf8c4bfda4611b0fd0fe8fb7`.
Reproducing the original new-versus-existing counts requires the exact prior
control ledger. Two registration outputs also matched byte for byte. The
registration retains the two archived guard versions and checks their hashes;
it verifies archive/fixture bindings and each row's article, source ordinal
and token relationship. It does not infer source-token offsets from the
retained cleaned fragment alone. No application, model or APK was changed.

Final validation: 818 standard-library tests across 168 modules passed with no
failures, errors or skips; receipt SHA-256
`5431eec131cad44358822a3419f424d935da6762554d4d19ab31129905dc97c7`.
Four focused registration tests passed, including fixture, source-token and
archived-guard mutation refusals and both real registry overlap gates. A staged
source archive without `build/` passed registration. The existing isolated
historical text and named-regression checks passed with the expanded registries.
An initial `--check` before copying the newly generated ledger entries failed
with `REF_SOURCE_DRIFT` as expected for absent entries; the subsequent check
passed. Hosted CI and the scientific profile were not rerun for this data slice.
