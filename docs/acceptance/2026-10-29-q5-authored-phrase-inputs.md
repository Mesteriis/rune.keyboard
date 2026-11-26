# Q5 authored dialogue phrase input disclosure

From the previously retained and attributed source, 20 utterances have two to
six Cyrillic words and no Latin letters or digits. The phrase replay harness
accepts space-separated words, so these inputs retain spelling and case but
remove punctuation. They contain 80 word occurrences. Their derived contexts
are registered in both exclusion ledgers before scoring; the original 262
source contexts remain registered separately.

The derivation is deterministic and bound to the pinned source and the original
source registration. Tests verify input registration and overlap refusal, source
mutation refusal and a checkout without `build/`. The inputs are disclosed
written examples, not natural messages, proofread labels, or independent
qualification. Product output and any additional contexts observed during replay
must be registered separately before using this as a regression set.
