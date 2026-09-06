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

This is reproducible-build evidence. At the user's direction, the exact artifact was published as
an experimental Hugging Face model on 2026-09-05 at commit
`c057e37928624d3c3c4bd526d3515f7202395920`. Hub file metadata reports the same byte size and
SHA-256. The full physical Fold load/scoring/lifecycle/thermal matrix in `docs/ACCEPTANCE.md`
remains a release gate; the publication is model delivery evidence, not final Rune Keyboard
release qualification.
