# Q6: joint dictionary-family coverage

The previous import reported 5,385 unresolved target rows. All of them were
protected controls: their expected text starts with `@`, so it is not itself a
Russian dictionary word. This audit checks the control construction and uses
the original source word for dictionary lookup. It checks every row in the
three manifest-bound corpora, retains all pinned Pymorph dictionary analyses,
and compares their family keys against the already registered addenda.

For all 44,816 rows, including 5,385 protected controls, there are zero
unresolved words and zero missing or extra family keys in each of the seven
partitions. Original entries and their historical missing-axis declarations
remain unchanged; this follow-up provides separate evidence of this specific
coverage. It does not prove whole-registry completeness, full source sentences,
historical model execution parity or independent qualification.

The [evidence](2026-10-28-q6-joint-family-closure-evidence.json) binds the
ledger, corpora, audit code and pinned dictionary files. Regression tests cover
protected controls, a missing alternative lemma and changed corpus bytes.
