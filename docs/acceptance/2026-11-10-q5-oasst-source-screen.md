# Q5: OpenAssistant source screen

The [OASST1 dataset card](https://huggingface.co/datasets/OpenAssistant/oasst1)
labels the human-generated assistant conversation dataset Apache-2.0 and
includes Russian, contributor identifiers, review metadata, and a synthetic
flag. Its 9,089 Russian messages are a count for the card's full described
collection, not a count of short, verified chat controls. Assistant-oriented
prompts and responses are a different register from ordinary personal chat.

A metadata-only aggregate screen queried the Hugging Face dataset API at source
revision `fdf72ae0827c1cda404aff25b6603abec9e3399b`, then read both server
Parquet conversions in memory using PyArrow 25.0.0. The train conversion was
39,516,251 bytes, SHA-256
`bbfadf5ed1278ba2208c837fdcad865adf65f5df55d80abadab2745db13fcb5e`;
the validation conversion was 2,080,179 bytes, SHA-256
`24002597bb13a7edd42d92f773762f25e285f72c31a70449393d0ded1dc7b416`.
The hashes identify the observed converted files; their derivation from the
original revision was not independently reproduced.

The conversions contained 7,611 rows labelled Russian. Of those, 7,308 were
marked non-synthetic, non-deleted and review-approved. Among these, 1,191
contained 2–6 whitespace-separated tokens; those rows had 335 distinct
`user_id` field values and 552 distinct `message_tree_id` field values across
both splits. Only 144 rows passed the further strict Cyrillic-letters-only
filter on every token. These are mechanical counts, not independently verified
authors, correctness labels, distinct controls, consent or user intent. The
filter does not remove punctuation and therefore the strict count omits many
otherwise usable utterances. The counts do not prove a representative chat
baseline or a 3,840-control qualification set.

No messages, contributor identifiers, model observations, or extracted corpus
were retained. Source rows were read during this screen: no subset can be
represented as a fresh independent holdout without a separately designed,
source-bound selection and the required Q6 exclusion and provenance checks.
No Rune model was evaluated. The temporary Python environment was removed.
The first attempt to create a temporary environment via a shell cleanup command
was rejected before execution; a scoped Python temporary directory was used.
