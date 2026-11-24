# Q6 historical neighbor corpus comparison guard

The retained neighbor corpus receipt has SHA-256
`2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e`.
The existing ignored historical `build/neighbor-recovery-20260926/corpus`
manifest matches that receipt byte for byte and its three JSONL files match
the receipt's hashes. This only confirms the preserved local historical files.

`tools/ci/compare_neighbor_reproduction.py` compares a separately generated
local corpus to the pinned receipt. It checks the three exact file names and
bytes against the generated manifest, verifies the retained generator's current
hash, compares historical hashes and all other manifest metadata, and checks
input drift. At comparison time it also checks all seven source shards and the
three referenced assets against the historical hashes; the two helper-source
hashes are recorded as a snapshot, not asserted to be the original versions. A differing generator hash is reported explicitly: matching output
cannot recover or authenticate the earlier generator. The report never marks a
corpus as independently qualified. Four unit tests cover matching data,
changed files/metadata and wrong generator or file sets; the tests are wired in
CI. This comparison is prepared for the ongoing local regeneration. No outcome
of that regeneration is asserted here.

A read-only scan of all local Git blobs at most 5,000,000 bytes (7,223 blobs,
including unreachable objects) did not find the receipt's original generator
SHA-256. Only that size-bounded local Git inventory was searched; this does not
prove the source is unavailable elsewhere or recover its bytes. Q6 remains open.

A later bounded working-tree search examined 37,825 `.py`, `.txt`, `.bak` and
`.orig` files under the local ignored `build/` tree, each at most 5 MB, while
excluding `.git`, `node_modules`, `site-packages` and `__pycache__`. None had
the original generator SHA-256. This broadens the local search beyond the Git
blob inventory, but does not search other extensions or locations and does not
prove that the source cannot be recovered elsewhere.

A further local search checked 2,610 non-symlink Claude file-history snapshots
of at most 5 MB against the historical generator SHA-256; none matched and no
read errors were reported. Separately, 32 Rune project Claude session files
mentioning the generator path contained 77 candidate strings but no exact
hash match. A targeted search of the current Codex session found 856 candidate
strings or embedded code blocks mentioning the generator or its seed; none
matched the historical hash. These are bounded searches of local snapshots and
session text, not a proof that the original source is unavailable elsewhere.
No session content was copied into the repository. Caprock session search was
unavailable because its local service was not running. The generator identity
and independent qualification remain open.

Both current Rune working trees were also scanned by file hash outside `.git`,
`build`, caches and dependency directories: 9,290 non-symlink files at most
5 MB were read without errors and none matched. The remote advertised two
branch tips, both already present in the local object store. The blob scan was
performed earlier and is not a fresh scan of all objects added since. This
does not search deleted remote refs, other machines,
or source embedded in a larger file.
