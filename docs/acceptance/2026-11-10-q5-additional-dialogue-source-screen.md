# Q5: additional dialogue source screen

## SAGE social-media partitions

The publisher describes manual spelling correction and validation across
its RUSpellRU and MultidomainGold datasets. The released row schemas
provide the source and correction, plus the domain for MultidomainGold.
The publisher declares MIT for the benchmark. Rights and clustering of
the underlying posts require separate evidence.
[Publisher dataset card at the checked revision](https://huggingface.co/datasets/ai-forever/spellcheck_benchmark/blob/3395aa540689e4393c3e18d063e73a5b99d7f047/README.md)
[RUSpellRU source documentation](https://sage-documentation-main.readthedocs.io/en/latest/rst/datasets/RUSpellRU.html)

Both copies of each JSON Lines split matched byte for byte. The size
and Git blob ID also matched the pinned tree `3395aa540689e4393c3e18d063e73a5b99d7f047`.
The short filter used NFC, case folding, whitespace normalization,
optional terminal punctuation removal and 2–6 Cyrillic-only words.

| Publisher partition | Pairs | Exact unchanged | Distinct short corrected texts | Distinct short unchanged after normalization | Lowercase short exact unchanged |
| --- | ---: | ---: | ---: | ---: | ---: |
| RUSpellRU train | 2,000 | 12 | 379 | 65 | 0 |
| RUSpellRU test | 2,008 | 802 | 150 | 40 | 40 |
| MultidomainGold social train | 430 | 90 | 8 | 4 | 0 |
| MultidomainGold social test | 200 | 28 | 2 | 1 | 1 |

There are 110 distinct short unchanged strings across all four splits,
before clustering or overlap checks against Rune's training data. The
train and test corrected texts share 12 normalized strings for
RUSpellRU and one for MultidomainGold social. This leaves the source
below Q5's 3,840-control target. For A2, the separate screen required
paired whitespace-delimited token sequences with one changed Cyrillic
token and a byte-identical preceding context. Zero such pairs had a
prefix of 300, 600 or 1,000 characters.

| Pinned split | Bytes | SHA-256 |
| --- | ---: | --- |
| RUSpellRU train | 1,692,992 | `fb0eee97d0a4c6fe5d807ffe3888554bc6e88396b2acec3272b11884dd57e90b` |
| RUSpellRU test | 1,946,556 | `e6435c9b0d0b78efea114856f9ba3ea7f89e3733d293e247edbb407b5f64d9c9` |
| MultidomainGold social train | 723,356 | `7b2245e3d01fb1c6ee4d8e8793d2f73a9176538bbf49bfdfca8b8decdae26215` |
| MultidomainGold social test | 309,857 | `4561ada01e1c11cfd7c26f1b8743d5cff7c226ab621730323da17c1d932d2f22` |

In-memory screening retained aggregate counts and file identities.
No per-row text or fingerprints were written and no model was run.

## RuSpellGold and other dialogue sources

The [RuSpellGold dataset card](https://huggingface.co/datasets/RussianNLP/RuSpellGold)
describes two-stage human annotation of 1,711 sentence pairs from five domains,
including 200 social-media sentences, and declares Apache 2.0 while reserving
underlying authors' or publishers' rights where applicable. The card does not
establish author clustering, chat-register representativeness, or clearance of
all underlying source rights. The dataset loader requires arbitrary code; it was
not executed.

The social-media JSON Lines file was downloaded twice at Hugging Face revision
`8b6694e45ac9222bc705ee4af9d6367ac083ff5c`. The second download matched the
first at 309,856 bytes and SHA-256
`a560cc55b3168d6ac93a07467278780cccc423279afb97c89ae1f49c8ea3014b`.
It has 200 rows, all labelled social media, and 200 unique exact source/target
pairs; 28 source and correction strings match exactly. After lowercasing,
trimming whitespace and terminal `. ! ? …`, and requiring 2–6
space-separated Cyrillic-only words, two corrected rows pass (two distinct
strings); one of these also has an unchanged normalized source. This mechanical
screen does not validate the annotations, prove original text rights, or
establish held-out independence. The first attempt interpreted JSON Lines as
one JSON document and failed; the subsequent two reads used the actual format.
No message text or fingerprints were retained, and no model was evaluated.

The [Russian IT Community Corpus dataset card](https://huggingface.co/datasets/wwewtech/russian-it-community-corpus)
labels the dataset MIT, but its repository's separate
[dataset terms](https://github.com/wwewtech/russian-it-community-corpus/blob/main/DATASET_TERMS.md)
limit the curated data to academic research, education and linguistic study,
while reserving MIT for code. Its README describes heuristic de-identification;
that is not independent proof of consent or absence of personal data. No data
was downloaded or imported. This source is not a cleared distributable baseline.

The [Russian thread-reconstruction dataset](https://data.mendeley.com/datasets/7rms5vdhf8/1)
claims CC BY 4.0 and identifies Telegram chats as its source. Its stated labels
concern reply relationships, not spelling correctness; the linked paper could
not be retrieved in this check. Consent, underlying rights, privacy, author
clustering and overlap with existing Rune data remain unverified. No data was
downloaded or imported. These screens do not supply the required independent
natural-chat controls or close Q5/Q6.

## Toloka Persona Chat Rus

The [Toloka team's original announcement](https://habr.com/ru/companies/yandex/articles/458326/)
describes approximately 10,000 typed conversations collected with iPavlov by
asking participants to act out assigned profiles. The announcement describes
the release as noncommercial and academic. The current
[Toloka dataset catalog](https://toloka.ai/datasets/) did not establish broader
distribution terms for this corpus. Its stated collection design supports a
role-play dialogue analysis. It does not supply independently verified spelling
labels or demonstrate that author identities suitable for clustering are
available. No dialogues were downloaded or used. The source does not
currently provide the publishable Q5 baseline.

## 2026-11-24 source eligibility follow-up

- FutureBeeAI describes more than 15,000 everyday Russian text conversations
  from 200 contributors. Its off-the-shelf offering uses a commercial license
  and specifies annotation by request. The public description does not
  establish redistributable spelling controls or a stable author identifier
  suitable for clustering. [Publisher dataset and licensing terms](https://www.futurebeeai.com/dataset/text-dataset/russian-general-domain-conversation-text-dataset)
- The Russian colloquial SFT dataset pairs Gemini rewrites of phrases drawn
  from Telegram and related text. Its upstream Telegram card declares
  CC BY-NC-SA 4.0. The cards supply neither independent proofreading for an
  unchanged-control set nor project-specific rights for the underlying text.
  [SFT dataset card](https://huggingface.co/datasets/pavelfedortsov/russian-colloquial-sft-50k)
  [Upstream corpus card](https://huggingface.co/datasets/kurumikz/telegram-corpus-russian-kazakh)
- Magic Data's 3,842 daily-use utterances are scripted monologues from ten
  speakers under CC BY-NC-ND 4.0. The headline count includes all utterances
  before the word-count, proofreading, or independence checks.
  [Publisher dataset and license](https://magichub.com/datasets/russian-scripted-speech-corpus-command-and-query/)
- Amazon's MASSIVE includes a professionally localized Russian split under
  CC BY 4.0. The source task is single-turn spoken-assistant interaction.
  Its labels describe intents and slots, and its language register is outside
  the ordinary written dialogue baseline.
  [Amazon source description](https://www.amazon.science/code-and-datasets/massive)
  [Dataset notice](https://github.com/alexa/massive/blob/main/NOTICE.md)

This was a review of public documentation. It retained zero new controls.
