# Disclosed Wikipedia source contrasts

These short lowercased prefixes and original-cased tokens are adapted from the
Russian Wikimedia Wikipedia 2023-11-01 snapshot, pinned in
`tools/eval/smart-typing-0.3/qualification-v2/source-lock.json`. The source lock
lists CC-BY-SA-3.0 and GFDL-1.3. Each record retains its numeric Wikipedia
article ID and source character offset. Article contributors and revision
history are available at `https://ru.wikipedia.org/?curid=<article>&action=history`.
The extraction lowercases the prefix and typed token, preserving the original
case as `expectedSpelling`; it is a disclosed regression experiment, not a new
independent corpus or a statement of the original typist's intent.
