# Original public joint/neighbor source receipts

These five JSON files retain their exact historical bytes from the origins
listed in the Q2 joint/neighbor acceptance evidence. They contain public corpus,
model, calibration and source hashes. They are read as metadata, not executed.

The original joint policy's trainerSha256 and follow-up v2 calibratorSha256
match the retained current source bytes. Three preparation-source identities
also match copies already indexed in frozen_sources/manifest.json.

The neighbor corpus generator (`bf2118a0b7d54f10a56d59c73ae77900fbd957c997f8307452b33549769b0323`)
differs from the retained current neighbor_recovery.py and remains unrecovered.
The frozen policy tool (`8d42d7e854ea205e797f9d0d2e41dc1f260a050613c708eb933ef3aebfa856bd`)
was reconstructed by reversing four replay-mode changes; its entire file SHA-256
exactly matches the original receipt. The exact bytes are retained in the parent
directory. The receipt preserves the remaining corpus-generator gap; current
tests do not establish historical corpus generation parity.
Fresh independent qualification and model reproduction remain separate work.
