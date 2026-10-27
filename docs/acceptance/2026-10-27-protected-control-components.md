# Q6: preserve exact authored protected-control components

Appended all 5,400 protected rows from qualification-v2 and compact-v3/v4:
600 per language/component, RU/EN/ES. The archived generators reproduce every
original row exactly, including category, typed token, prefix, candidates,
expected candidate, split, noAuto and orthographic policies. The component
file/manifest hashes and generator/lock identities are checked before import.

The three versions repeat a matrix of 1,800 unique protected identities. Counts
retain each corpus exposure while keys deduplicate repeated identities. Language
and control-kind namespaces prevent accidental cross-task/language merging.
Exact typed-token case, command syntax, identifiers, whitespace and e/yo
contrasts are preserved; NFC equivalence alone is normalized. No token is
converted into a Pymorph family or a personal dictionary entry.

All nine punctuation entries and their bindings are unchanged. The lexical
registry and its article-overlap report are also unchanged. Repeated component
imports now fail before touching original files; the new guard and malformed
row handling have regression coverage. No source corpus or archived generator
was rewritten. Historical control source hashes remain preserved by Git.

All 86 tests pass in an isolated directory without original build data, models,
PyArrow or morphology packages. New snapshot checks verify all protected counts,
a persisted RU control rejection and the entire protected matrix key set
regenerated from committed archived sources. Existing tests preserve case/NFC/
label-independent identity contracts and now explicitly check e/yo distinction.
CI includes these tests; no remote CI run is claimed.

Both registries still report incomplete overall freshness. New versioned
preparation integration and source-article/window recovery for punctuation remain
open. The accompanying receipt binds inputs, registry and successful checks.
No runtime, model, threshold, APK or Fold change is claimed.
