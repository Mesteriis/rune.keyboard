# Q5: RuLexNorm source screen

[RuLexNorm](https://github.com/SmartEngines/RuLexNorm/tree/59a8ebc3d314fafe25f918f50e5048f8ac00bed8)
describes over 6,000 original/normalized pairs from Russian Twitter text and
declares CC BY-SA 2.5. The authors warn that it contains real and potentially
sensitive comments. The declared license and publication alone do not establish
the rights or suitability of redistributing the underlying comments. The
normalization task includes expansions and merges, and the card does not
establish that unchanged tokens were manually proofread.

Two downloads of `data/RuLexNorm.norm` from commit
`59a8ebc3d314fafe25f918f50e5048f8ac00bed8` independently matched the Git
blob `cbe58698805229ed0b7901631fdccc53020094de`, 1,699,640 bytes and SHA-256
`896a0915301cdc0ccd208550f71f8dd4dd4d15f9b4ecb0f2dd55744eba7f6565`.
Both in-memory screens produced identical counts. Entries were split at blank
lines; within each entry every line was required to contain exactly two
tab-separated fields. An eligible control had 2–6 token rows, each original
exactly equal to its normalized form, with every original consisting only of
Cyrillic letters including ё. Uniqueness below uses lowercase;
no punctuation stripping, model scoring or correctness inference was applied.

| Measure | Count |
| --- | ---: |
| Entries | 6,393 |
| Entries outside the simple two-field format | 12 |
| Token rows in accepted-format entries | 71,872 |
| Accepted-format entries with every pair unchanged | 704 |
| Eligible unchanged entries / token rows | 8 / 26 |
| Unique lowercase eligible entries | 8 |

The 12 unparsed entries were excluded, not interpreted as malformed upstream
data. The exact-equality filter is intentionally strict and these counts do
not estimate the number of correct words in longer entries. No raw text,
per-row fingerprints or downloaded files were retained. This screen cannot
provide Q5's 3,840 labelled chat controls, establish labels or independence,
or clear Q6's incomplete registries. The corpus was not used to tune or run
the keyboard; licensing, privacy, annotation quality and source overlap would
need separate review before any further use.

## Token-level follow-up

The pinned source was fetched again and matched the recorded identity. Across
the 704 unchanged groups, 2,429 tokens consist solely of 2–20 lowercase
Cyrillic letters; 511 groups have at least one such token and 340 groups have
two to six tokens. Across all accepted-format groups, 30,381 tokens meet the
same lowercase and exact original/normalized equality filter, including 30,372
with a preceding token. The 12 groups excluded by the earlier screen remain
excluded; their lines have two, three, four or eighteen tab-separated fields.
These counts describe potential review material, not verified correct words:
normalization can preserve slang or errors, and a token is not a whole message.
Author/source independence, rights, privacy, annotation quality and historical
overlap remain unverified. No keyboard or model was run.

`tools/typing_experiments/screen_rulexnorm_source.py` reproduces aggregate
counts after verifying the source SHA-256, Git blob and size. It emits no text,
identifiers or row fingerprints. Two focused tests cover aggregation, excluded
format, source identity and invalid UTF-8. The source was held in memory for
this follow-up and no download or per-row material was retained.

## Published source and rights clarification

The authors' [paper](https://www.researchgate.net/publication/398871190_RuLexNorm_A_Lexical_Normalization_Dataset_for_Russian_Social_Media_Text)
reports that the dataset combines 5,394 authentic tweets from a 2021 public
stream with 1,002 generated tweets, and that model-assisted normalization was
followed by manual correction. Its normalization scope includes slang and
abbreviation expansion: a normalized form is not necessarily what the writer
intended the keyboard to insert. The two-column format described in the
[source repository](https://github.com/SmartEngines/RuLexNorm/tree/59a8ebc3d314fafe25f918f50e5048f8ac00bed8)
does not identify the origin of each entry or its author. Thus the paper's
aggregate origin counts cannot be assigned to the groups screened above or used
to calculate author-clustered false-change rates. The paper reports 6,396
messages and 72,039 words; the 6,393 blank-line groups found in this pinned
file have not been reconciled with that figure.

The repository declares CC BY-SA 2.5, while the paper describes the dataset
as available for research purposes only. Their different statements and the
underlying third-party text rights must be resolved before redistribution or
product use. This clarification does not validate the labels, establish source
independence, or qualify the dataset for Q5. No text was copied into Rune.
