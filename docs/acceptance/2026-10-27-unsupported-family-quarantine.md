# Q6: classify and quarantine unsupported lexical targets

Audited every remaining unsupported target in the registered historical spelling,
ranker and joint lexical inputs, plus the three early RU components. All original
row-file hashes/counts are checked. There are 1,402 unsupported row targets in
11 parent entries, representing 1,357 distinct NFC/casefolded RU word surfaces.
Every one invokes predictive analysis units in the pinned default analyzer.

Dictionary-only analyses remain the only canonical-family authority. The default
analyzer is used diagnostically to record method classes (known/unknown prefix,
suffix or unknown-word handling), not its guessed normal forms. A contradictory
all-dictionary result aborts for investigation. Predicted lemmas and probabilities
are never stored as family evidence or imported into training/exclusion families.

Each affected parent gains unsupportedSurfaceKeys. All its prior keys, bindings,
missing axes and global incomplete coverage remain unchanged. These exact-form
keys provide direct target reuse protection across source contexts, preserving
e/yo distinctions while normalizing NFC and case. They do not establish an
inflectional family or cover every other form of a name. The 1,402 canonical
family questions are explicitly unsupported, not silently marked recovered.

Protected mentions are checked against their original group/cohort/noAuto and
@word construction before being excluded from lexical analysis. Private/user
corpora are not imported. The receipt stores public row IDs, method names and
surface hashes, without source phrases, plaintext targets or guessed lemmas.
Hashes themselves are not claimed to anonymize private data.

New versioned preparation now checks both typed and expected unsupported
surfaces. A proposal using `ДАРСИ`/`дарси` cannot evade the exclusion by claiming
an unseen canonical family. This protection is independent of known context,
article, family and control matches; it changes no runtime correction policy.

All 129 tests pass in a source-only directory without build data, models, PyArrow
or morphology packages. Eight new tests cover diagnostic-only predictions,
protected construction, contradictory dictionary evidence, explicit no-analysis,
NFC/case/e-yo scope, malformed hashes, registry persistence and shared/CLI target
blocking. Current registries still forbid final corpus publication. CI includes
the tests; no remote CI run is claimed. Extraction uses the pinned dictionary.

Q6 remains open for complete derived-history inventory, unproven canonical
families/inflections and remaining historical source/runtime provenance. These
facts cannot be closed by substituting a predictor's plausible lemma. No model
fit, APK build or Fold action is performed.
