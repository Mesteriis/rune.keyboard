# Q6: disclosed v2–v4 qualification inputs in the control registry

The retained qualification-v2, v3 and v4 corpora contain 39,600 historical
inputs: 30,600 spelling, 3,600 punctuation and 5,400 protected-token rows across
English, Spanish and Russian. They were already disclosed and are not fresh
holdouts. Before this registration, their punctuation/protected context keys
were present in the control registry, while all 30,600 spelling input-context
keys and many exact input surfaces were absent.

The source-bound registrar validates all original manifests and member hashes,
checks the 18 existing punctuation/protected entries against their real rows,
and adds 12 entries: nine exact spelling-context groups and three per-language
surface groups anchored to existing regression entries. This preserves the
existing punctuation article-coverage calculation and prior entries. It adds
30,600 distinct regression context keys and 30,997 previously absent exact
surface keys: 10,614 English, 10,130 Spanish and 10,253 Russian. Some ordinary
words and synthetic typo forms are consequently excluded from future controls;
this is conservative disclosure handling, not an accuracy or freshness claim.
No canonical family, intent or label is inferred.

An isolated dry run and the actual atomic registration produced byte-identical
control registries. The dry run verified every prior entry and top-level field
was unchanged and punctuation article coverage remained true. The registrar
verifies the v2 original manifest and rows and both retained v3/v4 archives;
it records source/code bindings and refuses changed input, missing prior
components, duplicates or a concurrent registry change. The new `--check` is
wired into CI and the stdlib inventory.

The final local suite passed 102 tests across historical registration, early
unknown surfaces, control and RU importers, archive integrity, both registries,
public corpus preparation and v6 target checks. Tests demonstrate actual
surface-overlap refusal for spelling, punctuation and protected-token samples,
and reject a changed historical punctuation component. The independent replay
disclosure checks and the existing early-unknown and v6 target checks also
passed. The first 27-entry design caused two failures and one error in the
existing punctuation/protected snapshot tests and would have made article
coverage appear incomplete; it was discarded before the final 12-entry design.
An earlier new test also used an invalid empty protected prefix and was corrected.
These failed runs are not passes. The temporary checkout was removed.

The registries remain explicitly incomplete; this change does not restore
available-v6, prove complete source attribution or family coverage, create a
fresh evaluation set, run a model, qualify a policy, test Fold, or run hosted
CI. Original evaluation corpora and product code were not modified.

## Full stdlib integration after historical surface registration

A clean clone of commit `1da2387e` ran the complete stdlib inventory with
Python 3.12.14. The initial run completed all 210 modules and 1,025 tests,
but failed two modules, with two failures and no skips. Both failures were
older test expectations overtaken by the newly registered surface exclusions:
Taiga's surface guard now precedes its incomplete-coverage guard, and the
public-control fixture used a newly protected surface.

The Taiga test now separately verifies that its regression context is absent
when its entry is removed, while expecting the independent surface guard to
refuse the input. The public-control test uses a synthetic unregistered
surface so it still exercises incomplete coverage. With only these two test
files changed in the clone, the full stdlib runner exited 0: 210 modules,
1,025 tests, zero failures, errors, skips, timeouts or missing receipts. The
product code and exclusion rules were not changed to obtain this result.
This local result is not a hosted CI run or evidence of model qualification.
