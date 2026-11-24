# Q5: preliminary synthetic dialogue source screening

[GlayAI/Tiny-Russian-Dialogs](https://huggingface.co/datasets/GlayAI/Tiny-Russian-Dialogs)
identifies itself as a synthetic Russian question/assistant-answer dataset under
CC0-1.0. Its card explicitly says that it does not represent the breadth of real
conversation and describes repeated, templated answers. It is a possible extra
regression source, not evidence of natural chat quality.

The pinned revision `4f85463dc22850a2f6e961c9c21b13510d362d3a` contains
125,000 pairs. Filtering each side to lowercase 2–6 word Cyrillic phrases after
removing final sentence punctuation yields 6,008 question occurrences and 7,871
answer occurrences, with 6,326 unique phrases across both sides. None exactly
matches the 9,543 previously generated Tatoeba controls under the same normalized
phrase comparison. These are descriptive counts, not proof that the data is
independent of training or other holdouts; template and semantic overlap have
not been checked and spelling has not been proofread. The source was not added
to any evaluation, training set, ledger or release.

The adjacent receipt binds the public CSV and card bytes, the earlier control
rows and audit script. Two runs produced identical reports; source and input
hashes are checked before and after reading. The focused tests cover filtering,
deduplication, exact overlap and malformed input. The 23 MB source stays in
ignored local build output; no private conversations were collected. Q5's
verified-control baseline and real multiword revision replay remain open.
