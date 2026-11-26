# Q5: isolated packed colloquial-word candidate

The post-hoc seven-word candidate is now reproducibly packed with the existing
rare-word packer. The builder reconstructs keys and rank order from the committed
`ru.rare` and verifies that repacking produces the exact original bytes. Counts
in this reconstructed input are explicit zero placeholders: the asset does not
contain the original occurrence statistics. The source is public and the eight
reviewed source articles are already excluded from future qualification. Two
candidate builds were byte-identical. The 288,246 original keys retain their
ranks; seven reviewed forms are appended. The product asset itself is unchanged.

A host probe using the real `PackedRareWordLexicon` checked every original key
and rank plus all seven additions; corrupted bytes were refused. It also tested
the actual new SHA against six existing fingerprints: compact public, joint
short, joint long, joint rescue, word-context and recovery. Each accepted the
old fingerprint and refused the changed rare-word fingerprint. Five existing
qualification test classes passed seven JVM tests.

A separate observer run used the actual candidate bytes, updated only the
resource identity constants in an isolated source copy, and left all
qualification gates unchanged. All copied assets and source bindings were
verified before and after. On 4,720 disclosed, unlabeled Russian parity inputs,
2,382 rows differed in at least one non-timing observer field and 658 had a
different boundary result. The original observer changed 1,534 boundaries and
the candidate observer changed 892: 650 previous changes stopped and eight new
changes appeared. These are **behavior differences, not labeled gains or losses**.
All eight post-hoc reviewed controls were preserved. No APK was built or
installed and no qualification certificate was changed.

The original in-memory overlay did not change fingerprint checks and therefore
was not representative of this packaged candidate. This candidate must not be
promoted merely on the overlay results. It requires complete independent data,
requalification of affected sources, broad regression and device acceptance.
Thirty-six targeted Python tests passed. [Candidate receipt](2026-10-28-q5-chat-packed-candidate-receipt.json),
[impact](2026-10-28-q5-chat-packed-impact.json),
[non-timing comparison](2026-10-28-q5-chat-packed-comparison.json), and
[hash-bound evidence](2026-10-28-q5-chat-packed-evidence.json).
