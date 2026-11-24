# Q5 public author-written dialogue source

Ekaterina Myskina's [Russian Everyday Dialogues](https://huggingface.co/datasets/kukunechka/russian-everyday-dialogues)
is an attributed CC BY 4.0 source of 20 dialogues written by a native speaker.
The source and original card are retained at the pinned revision in
`tools/typing_experiments/authored-dialogue-v1/`. These are authored examples,
not recordings of spontaneous messages; the small set is not representative of
natural chat and its spelling and intended corrections are not independently
labelled.

The 40 distinct utterances contain 262 Cyrillic token occurrences and 248
unique lexical prefix/target identities. Before any replay, their exact contexts
were added to both public exclusion registries. Two distinct lexical context
keys already appeared in earlier entries; none matched earlier regression
control keys. Prefixes are taken from the original utterance with punctuation
and case, limited to the preceding 128 characters. Generic word surfaces are
not globally excluded by this addition; its scope is the exact contexts.

The registry checker verifies pinned source bytes, derived contexts and exact
entries, and runs in CI. Tests cover mutation refusal, overlap refusal in both
registries, and a checkout without `build/`. No product scoring or quality
qualification was performed. The data is disclosed regression material; the
3,840 labelled-control baseline, natural-message coverage and fresh Q6 holdout
remain outstanding.
