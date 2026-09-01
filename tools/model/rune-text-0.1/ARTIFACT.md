# Rune Text 0.1 candidate evidence

The two clean Linux jobs and the byte-for-byte comparison completed successfully in
[GitHub Actions run 33508047561](https://github.com/Mesteriis/rune.keyboard/actions/runs/33508047561).
An independent download of the compared candidate produced:

- asset: `rune-text-v1-0.1.0-q4_k_m.gguf`
- size: `396704416` bytes
- SHA-256: `7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`
- GGUF version: `3`
- architecture: `qwen3`
- file type: `15` (`Q4_K_M`)
- tensor count: `310`
- metadata entries: `28`

This is reproducible-build evidence, not release qualification. The immutable GitHub Release must
not be created until this exact digest passes the physical Fold load/generation/lifecycle/thermal
matrix in `docs/ACCEPTANCE.md`.
