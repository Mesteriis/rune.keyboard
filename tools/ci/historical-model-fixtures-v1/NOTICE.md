# Original historical model test fixtures

Host-only public regression data and original full reference models, not new
training or qualification. Model CBMs, decoded weights, rows and observations
are preserved byte for byte. Original SHA-256 identities are recorded per file.
The CBMs retain public upstream CatBoost build metadata; original project/user
paths are not included. No model weights are reserialized or replaced.

Receipts, source-freeze maps and logs replace original project/external paths
with $ROOT/$EXTERNAL tokens. Receipt hashes are updated for the transformed
metadata. At runtime, isolated temporary workspaces rebase these tokens and
rehash metadata edges. Original candidate/source/data/model byte identities are
retained; external runtimes and candidate reproduction are not established.

Public Wikipedia snapshot 20231101, wikimedia/wikipedia parquet conversion
revision a634f78b1c435397c07001e175fa74cc4ad5e775:
https://huggingface.co/datasets/wikimedia/wikipedia
The original word-ranking manifests and all advertised payloads are preserved.
The text was normalized, truncated and combined with synthetic spelling errors
by its hash-bound original preparation script. Each of the 4,920 consumed
articles is credited by title and contributor-history link in articles.jsonl.
Core refinement/additional-epoch attribution remains in historical-data-v1.
Use the text collection under CC-BY-SA-3.0, not the repository code license:
https://creativecommons.org/licenses/by-sa/3.0/
https://creativecommons.org/licenses/by-sa/3.0/legalcode
The original source notice also records GFDL-1.3; see
 tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md and source-lock.json.

The baseline export's 4,000 rows match already-versioned public qualification-v2
spelling/protected-token rows; their original attribution/licensing is retained.
Project-authored fixtures and model assets retain their existing project terms.
All these data remain permanently excluded from fresh qualification. Original
assertions execute in isolated source snapshots; no archived script is executed.
