# Q5: same left context with conflicting capitalization

The same two-word sequence `моя клава` can refer to a keyboard or to a person
named Клава. The common-word use appears in the pinned public Tatoeba CC0
article 11113126. A personal-name use appears in a public [artist channel
post](https://t.me/s/klavacoca?before=4843). Only the two shared words are
retained; the latter page is an external reference, not a captured or
license-cleared training source. No private messages were used.

Two constructed rows deliberately provide the identical lowercase prefix and
target to the controller while assigning opposite illustrative desired cases.
The current-product host replay produced `моя Клава` for both; the previously
rejected lowercase-evidence overlay produced `моя клава` for both. Thus each
matched one illustrative sense and missed the other. The runner sends only
opaque IDs, language, split, prefix and typed word to the controller; sense and
expected spelling remain outside it. The test confirms the two actual outputs
are identical within each system. No classifier restricted to this same input
can determine both senses from that input alone. This is a constructed ambiguity
example, not a measured user error rate or an independent holdout.

The [rows and source note](../../tools/typing_experiments/chat_regression/case-context-collision-v1/NOTICE.md)
are retained, and their single normalized context key is now in the permanent
public-data exclusion ledger. The Tatoeba article was already separately
excluded. Family, full sentence and other article coverage are not asserted;
ledger coverage remains incomplete. The previously recorded lowercase screen
was regenerated against the new ledger; its results were identical. The
[receipt](2026-10-28-q5-case-collision.json) binds the fixture, updated screen,
ledger, runner, harness and real observer outputs. Existing evidence with the
prior ledger hash remains historical. Five runner tests and 24 public-ledger
tests pass, including rejection of this context as a fresh holdout.

No product policy or APK changed. Any future rule needs to preserve explicit
user case and consider available additional evidence, including subsequent text
or user selection, without claiming certainty when that evidence is absent.
