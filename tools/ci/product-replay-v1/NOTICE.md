# Product replay v1 — data attribution and scope

The three verbatim word-frequency files in `sources/` are from **Hermit Dave’s
FrequencyWords**, commit `525f9b560de45753a5ea01069454e72e9aa541c6`, 2018
EN/RU/ES lists. Upstream identifies its content license as **CC BY-SA 4.0** and
its underlying corpus as **OpenSubtitles2018**, accessed through OPUS.

- [Pinned upstream attribution and license declaration](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/README.md)
- [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/)
- [Upstream corpus reference](http://opus.nlpl.eu/OpenSubtitles2018.php)
- Exact source URLs, commit, SHA-256 and byte lengths: `source-lock.json`.

The derived `inputs.jsonl` and `origins.jsonl` are adaptations of that content
under CC BY-SA 4.0. Changes: NFC normalization and case folding, letter/length
filtering, deterministic hash selection of 60 words per length bucket and
language, synthetic contexts made from the preceding three eligible list
entries, deterministic deletion/transposition attempts, and uppercase initials.
Original frequency counts and line numbers are preserved in `origins.jsonl`.
No source sentence or grammatical validity is inferred from list adjacency.
These files contain no private messages and no intended-answer labels.

The v1 generator chooses 540 source groups and emits 2,160 regression rows, 720
per language, before any replay. Frequency lists include errors and names: no
row is asserted correct, incorrect or safe to replace. This is a disclosed
regression corpus, not independent natural qualification or a precision metric.
The `calibration` field is the observer’s historical partition namespace; no
threshold fitting is performed. Context and surface exclusions are registered
in both existing Q6 registries. Surface keys preserve language, ignore case and
do not claim a canonical lemma. Q6’s incomplete family/source coverage remains
incomplete and still prevents claiming a fresh holdout.

Reproduce or verify all derived bytes without `build/` or network:

```sh
python3 tools/ci/generate_product_replay_v1.py --check
python3 tools/ci/register_product_replay_v1.py --check
```

Regeneration writes a fresh output directory and never overwrites these files.
Any data change requires a versioned corpus, new disclosure bindings and a
separate reviewed baseline update. These data licenses do not assign a new
license to the project’s program code or unrelated assets.
