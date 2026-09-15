# Local morphology and personal writing style

This host-only experiment compares current Rune local spelling proposals with a
morphological ranker and a morphological ranker plus short-context frequencies.
It also imports authorized personal Telegram exports into a local writing-style
model. No Android source, installed keyboard, neural weight or existing release
qualification is changed.

## Components

- `ProductionCandidates.kt` calls the actual production `CandidateGenerator`,
  packed lexicons, `LocalCorrectionPolicy` and common-confusion policy. It uses
  `CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES` (currently three). Expected
  spellings, prefix text and cohort labels never reach this generator.
- `ranker.py` reads all dictionary analyses through the pinned OpenCorpora-derived
  compact word graph. Each analysis links a surface form to a lemma and grammar
  features. Unknown-word guesses are excluded. Case/number agreement, possible
  preposition cases and a few grammatical constructions provide soft evidence.
- `telegram_style.py` imports only the explicitly identified author's text in
  personal chats. It counts within-sentence unigrams, bigrams and trigrams and
  exposes a bounded contextual bonus. The serialized model is data, not code.
- `evaluate.py` freezes source/asset/input identities, executes the production
  observer and compares proposals without passing expected labels to ranking.
- `personal_holdout.py` prepares controlled spelling corruptions from separate
  validation chats, so natural typing mistakes are not presented as gold labels.

The new ranker requires complete distance-one local evidence, keeps original as
an option and preserves existing protected/valid-word restrictions. It uses
frozen morphology weight 16, style weight 8, original penalty 64 and minimum
margin 24. With no context evidence it falls back to the current local proposal;
after an evaluated insufficient-margin decision it keeps original. This is an
experiment, not a claim that these coefficients are optimal or release-qualified.

The production generator often has no complete local-search certificate for
words under five characters. This experiment abstains on that path. More lexical
coverage, full short-word retrieval and changing valid-word spellings are separate
changes. Mechanical punctuation and canonical capitalization are outside this
proposal comparison. Editor ownership, Undo and Android scheduling remain in the
existing controller; this host ranker does not exercise those paths.

## Setup

Use an installed Python **3.11** interpreter and JDK17. The exporter also needs the
same `ANDROID_HOME`/`ANDROID_SDK_ROOT` and pinned Kotlin compiler cache used by the
existing production replay toolchain. No dictionary is added to normal Gradle
builds. From the repository/worktree root:

```sh
python3.11 -m venv build/morphology-venv
build/morphology-venv/bin/python -m pip install --require-hashes -r tools/morphology/requirements.lock
PYTHONDONTWRITEBYTECODE=1 build/morphology-venv/bin/python -m unittest discover -s tools/morphology -p 'test_*.py'
```

`requirements.lock` pins pure-Python wheels by SHA-256: pymorphy3 2.0.6,
pymorphy3-dicts-ru 2.4.417150.4580142 and dawg2-python 0.9.0. The dictionary reports
OpenCorpora source version 0.92/revision 417150. Experiment receipts additionally
hash installed package files. Python3.12+ requires a different dependency closure
and is not the locked environment here.

Code and linguistic data have separate provenance. pymorphy3 and dawg2-python
identify their code as MIT. OpenCorpora describes its data under CC BY-SA3.0;
the dictionary wrapper's MIT metadata does not relicense the linguistic data.
The Android integration includes a derived OpenCorpora dictionary index under CC BY-SA3.0;
see [dictionary asset provenance and rebuild instructions](DICTIONARY_ASSET.md).
Personal profiles and raw conversations are never bundled with the APK.
Sources: [pymorphy3](https://pypi.org/project/pymorphy3/2.0.6/),
[OpenCorpora](https://opencorpora.org/?page=faq),
[dictionary representation](https://pymorphy2.readthedocs.io/en/stable/internals/dict.html).

## Public three-way comparison

Output directories must be fresh, beneath this checkout's ignored `build/`.
The corpus is the existing source-hashed RU qualification-v2 set: 2,000 calibration
and 2,000 holdout rows. Public style training uses calibration references only.
The fixed-policy reproduction uses already revealed data and does not establish
unseen generalization.

```sh
build/morphology-venv/bin/python tools/morphology/evaluate.py export --output build/morphology-export
build/morphology-venv/bin/python tools/morphology/evaluate.py compare --export build/morphology-export --output build/morphology-comparison --train-public-style
```

Exports retain raw compiler/generator logs and receipts. A failed child process
cannot produce a successful receipt. Altered, moved, copied or incomplete inputs
must not validate against the original export's hashes. Source changes require
regenerating the export. Use a new output name on each run.

## Personal Telegram data

Use Telegram Desktop JSON exports of the authorized personal chats, with media
excluded. Keep original JSONs under an ignored `build/private/` directory. Extract
only known JSON entries from an archive, without trusting archive paths. A ZIP is
not accepted directly by the importer.

The sender ID must be established explicitly. Supply its numeric part or
`user`-prefixed value; never guess it from message volume. Replace the quoted
example below with the confirmed account ID:

```sh
build/morphology-venv/bin/python tools/morphology/telegram_style.py --input build/private/telegram/chat-01.json --input build/private/telegram/chat-02.json --self-id 'YOUR_NUMERIC_USER_ID' --output build/private/style
build/morphology-venv/bin/python tools/morphology/evaluate.py compare --export build/morphology-export --output build/private/style-public-comparison --style-model build/private/style/model.json
```

The importer handles single-chat and full-export envelopes, skips other chat
types, incoming/forwarded/service/bot-authored material and conservatively removes
whole messages containing contact/link/code entities or obvious contact/code
patterns. This is **not comprehensive anonymization**. Retained prose, vocabulary,
learned model and receipts remain private local artifacts. Nothing is uploaded.

Deduplication precedes a deterministic split of entire chats. The default aims
for 20% of chats in validation while keeping at least half of the retained messages
for training. Actual counts are reported; a single-chat import cannot establish
held-out evaluation. Duplicates never bridge training and validation. Global text
deduplication also reduces the apparent frequency of identical repeated replies;
counts represent retained unique messages, not raw chat frequency.

Outputs are `train.jsonl` and `validation.jsonl` (`{"text": "..."}`), `model.json`,
`report.json` and `receipt.json`. Directories are 0700 and files 0600. Input bytes,
training messages, chat groups and produced artifacts are hash-bound. Do not
commit these files, copy them into APK assets or send them to a training service.

These authored-text datasets can support later neural style adaptation, but they
contain natural spelling mistakes. They are not corrected-text pairs or clean
spelling supervision. The model produced here is a local n-gram profile; **no
neural fine-tuning is performed**. Style support is bounded and can only influence
already generated dictionary candidates.

## Personal held-out diagnostic

```sh
build/morphology-venv/bin/python tools/morphology/personal_holdout.py --dataset-dir build/private/style --output build/private/recovery --limit 400
build/morphology-venv/bin/python tools/morphology/evaluate.py export --rows build/private/recovery/rows.jsonl --output build/private/recovery-candidates
build/morphology-venv/bin/python tools/morphology/evaluate.py compare --export build/private/recovery-candidates --output build/private/recovery-comparison --style-model build/private/style/model.json
```

This selects up to 400 distinct lowercase dictionary words of length 5–12 from
validation messages, excludes proper-name analyses, and creates one unknown
single-deletion/transposition corruption per target. Every target also gets an
unchanged negative control. Context stays within a sentence. No expected word
is inserted into the production candidate list. A missing target remains missing.
The result measures **synthetic recovery**, not accuracy on observed user typos or
all negative chat inputs. Public and personal reports must remain separate.

## Interpreting results

`precision` is correct changes / all changes; `typoRecall` is correct changes /
labeled typo rows; `negativeFalseChangeRate` includes both correct and protected
negative controls. Empty/unlabeled cohorts have null rates. Source corpus mixes
are not chat prevalence estimates. Baseline is production general-local plus
common-confusion proposals, not full Android behavior or all keyboard features.

Timing is single-process Mac/JVM/Python timing. Dictionary loading is measured by
forcing a public-word lookup before ranking. Each variant has a separate bounded
cache; per-row distributions include eligibility shortcuts. Generator time is
reported separately. These are not Android keystroke latency, energy or neural
inference comparisons.

## Android personal phrase profile

`export_android_profile.py` converts an explicitly selected local `telegram_style.py`
`model.json` into a portable phrase-only profile. It never reads a corpus by itself
or contacts a network service. The current command supports Russian, using the
public `ru.morph` dictionary generated by `export_dictionary.py`:

```sh
python3 tools/morphology/export_android_profile.py \
  --model /path/to/private/model.json \
  --dictionary app/src/main/assets/smarttyping/lexicon/ru.morph \
  --language ru --min-support 3 \
  --output /path/to/private/android.runephrases
```

The output is **private typing data**. Keep it out of git, APK assets, backups,
shared folders, and public reports. The exporter creates a new mode-0600 file and
refuses to overwrite existing paths. Its terminal receipt contains counts only.
The script's tests use synthetic messages and dictionary fixtures.

Portable UTF-8 format (no BOM, LF lines): first line `RUNE_PERSONAL_PHRASES_V1`,
then at most 1,024 tab-separated records:
`LANGUAGE<TAB>prefix<TAB>continuation<TAB>support`. Language uses the Android enum
name (`RUSSIAN`, `ENGLISH`, or `SPANISH`); the current dictionary exporter supplies
Russian only. Prefix and continuation each contain one or two lowercase NFC words,
letters only, separated by one ASCII space. Each word is at most 48 characters.
Support is 3–255; the file is at most 1 MiB. Duplicate keys, malformed UTF-8,
unknown languages, extra fields, noncanonical words, and unsupported counts are
rejected. Import replaces existing support with the larger count, so importing
the same profile twice does not manufacture additional observations.

Both export and Android import require dictionary membership for every word;
raw chat frequency never certifies spelling. Android still validates dictionary
membership or an explicit on-device spelling confirmation when displaying a
saved phrase. Imported files cannot carry correction pairs, spelling confirmations,
message hashes, full messages, or automatic-correction permissions. Existing
local rejection feedback survives imports.

On-device feedback and phrase counts live in an atomic private snapshot under
`Context.noBackupFilesDir/personal-typing/`. The process-wide `PersonalTypingStore`
is shared by settings and the service. It loads and writes on one storage thread;
`isReady` gates queries and `update` refuses learning before readiness. Updates
coalesce to a bounded snapshot write; no editor text is queued while loading.
`lastWriteSucceeded` reports the last completed write, and reset/import completion
callbacks run on the storage thread. Settings must dispatch those callbacks to
the UI thread. A corrupt snapshot leaves readiness `FAILED` until explicit reset.

`recordAccepted` and `recordManualRetype` are for acknowledged explicit user
choices; `recordRejected` records an undo veto without certifying the original.
`recordConfirmedWord` protects explicitly retained spellings. Positive pair counts
order manual suggestions only. The model stores at most 512 feedback pairs,
512 confirmed spellings, and 1,024 phrase pairs, with counts capped at 255. New
rejections replace positive-only entries first. If the entire feedback table
contains rejections, unknown correction pairs are also vetoed until reset.
Phrase training requires three observations and accepts only validated words;
callers must pass context from the current message and honor sensitive-field,
learning-disable, acknowledgement, lifecycle, and editor-ownership gates.
