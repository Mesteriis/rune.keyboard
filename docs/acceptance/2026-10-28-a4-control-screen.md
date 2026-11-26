# A4: authored control screen finds a case change

The 140-row public, authored discovery set was committed at `6b2d381` before
this screen, with contexts and surfaces added to the control ledger. Five
review examples had already been exposed by the earlier discovery run. The set
has 54 abbreviation candidates, 43 synthetic domain-label inputs and 43 list
headings; its [limitations](../../tools/typing_experiments/a4_controls/README.md)
apply. Each input used an empty prefix and was replayed twice per boundary.
The two non-timing projections matched in all three runs; all commands exited 0.

| Category | Rows | Changed before each of space, period and colon |
| --- | ---: | ---: |
| Abbreviation candidates | 54 | 1 |
| Synthetic domain labels | 43 | 0 |
| List headings | 43 | 0 |

The failure is `инн` → `Инн` on all three boundaries; Backspace restored the
original in each host replay. The observation identifies `CANONICAL_CASE`, with
the candidate marked unambiguous and eligible despite the intended abbreviation
reading. A name reading is also possible; these empty-prefix probes do not prove
that a blanket case veto is safe in every context. The zero-change A4 gate is
**not met**. A correction needs contrasting contexts, regression protection and
renewed replay/device evidence.

The first stress reports counted the case change but omitted it from the list of
case-only examples because the control's intended text was compared case-folded.
The report now lists case-only departures even when their folded spelling matches;
a regression test covers that inconsistency. The corrected reports retain input
and observation hashes. The stress unit suite passes 18 tests.

The input SHA-256 is `e1553ebd2dc54dd2358c41b39d9ebd5833dba06165ff79c7c8aea4a93370597a`.
The raw receipts under `build/review-a4-controls-{space,period,colon}-20261028/receipt.json`
have SHA-256 respectively `8a05bd70fb578b5b6b2a52301024a6aabea620ff48de052d1584cce6b1b0d8d7`,
`0b94f40aca5f61e7b2f4bed60e22d4a60d0908f32165e891b68d445710cc8ef4`, and
`1c1604fcf6a43d3ae7f235a105f0634668e061b3547d6a65135b39cc831d8197`.
Corrected case-report hashes in the same order are
`57963e9d463bea7488c5baad18786c9357edb4cb10c643c253f148d74ebe9767`,
`a9bd99a7acd4337b126de500cefbf8f2b2599b3cbac7ff38d58147827377f352`, and
`e592010869349cd743fa608a31ef66918cba3406286e71e25a92c22151dc3a1e`.
This is host replay, not real Fold or independent natural qualification.
