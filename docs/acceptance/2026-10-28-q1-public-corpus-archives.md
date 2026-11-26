# Q1/Q2: public corpus archive inventory

The retained English and Russian Tatoeba CC0 archives were outside the prior
F-Droid data-policy discovery roots. The policy now discovers `.bz2` public
sources, requires each exact path and its exact provenance lock, verifies the
lock's compressed SHA-256 and CC0 declaration, and inventories both archives
without suppressing or deleting them. An unknown public archive, wrong source
lock, changed bytes, changed provenance or attempted scanner suppression is
rejected. This does not approve the data as independent qualification.

At clean source `891e0054dfb5f8f4861c98538798ed97444c2b23`, the real
fdroidserver 2.4.5 `prepare_source` and `scanner.scan_source` ran on a fresh
disposable checkout with network blocked during scanning. The inventory had
31 entries, scanner fatal count was zero, the prepared-source checkpoint had
11 approved changes, and all seven positive and negative probes passed. The
scanner retained its two previous warnings about the calibration gzip and the
upstream llama.cpp Keynote file. This is not a full F-Droid build, a build-server
run or binary distribution acceptance. The local machine receipt is
`build/review-q1-public-archives-20261028/result.json`, SHA-256
`95d02c85b24cc0a7092f9204d11403ff520dcc93f16bfbcea7e6e5ba47187e39`.
The F-Droid policy suite passed 27 tests and typing asset notice suite nine.
