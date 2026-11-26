# Q5: Russian GEC source screen

The [Russian Grammar Error-Correction Dataset](https://github.com/dreuxx/Russian-Grammar-Error-Correction-Dataset/tree/335f543f7bff7860a8ac35303b3b708a5dfe44e9)
declares CC BY 4.0 and describes its sentences as synthetic and
semi-crowdsourced, with human-corrected target text. Its card does not establish
that the material represents ordinary chat or that each correction is suitable
as an unchanged control. Rights in constituent sources and overlap with Rune
data remain unverified.

The pinned CSV was downloaded twice and checked against Git blob
`c56c52a6195201f17c4c81fc6647970aa1ee9bfd`, 13,157,130 bytes, and SHA-256
`7db5fac98a2fb7d732a7b4f1596934e167ac63c9b5b3b01fc94ae8f9c743b3e7`. The
file has the four declared columns and 24,998 data rows, versus 25,362 pairs
stated on the card. There are 24,643 distinct exact input/target pairs and
17,569 distinct exact corrected strings. These are mechanical counts, not an
independent check of the claimed human corrections.

No corrected string passed the strict 2–6 whitespace-separated Cyrillic-word
filter with punctuation retained. A separate relaxed screen removes only
trailing `.`, `!`, `?` and `…`, then requires 2–6 Cyrillic-only words. It
finds 138 occurrences, 94 distinct lowercased corrected strings and 134
distinct original/corrected pairs. The original and corrected texts never
matched after this same trailing-punctuation and lowercase normalization in
that subset. The two screens have different filters and are not independent
reproductions of the same count.

No corpus text, row fingerprints or temporary download was retained, and no
keyboard or model was run. This screen does not provide the 3,840 controls,
prove correctness, clear Q6 or establish a false-change baseline.
