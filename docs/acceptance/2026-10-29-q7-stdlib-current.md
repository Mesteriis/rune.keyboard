# Q7 current standard-library inventory

The versioned standard-library profile ran at source `d402b7f0`: all 163
assigned modules completed with zero failures or errors. Their unittest
summaries contain 802 tests and zero skips. The runner receipt SHA-256 is
`7f71a50e374ace4de3c0ca280512cf13072997565e39e543405ab09268fbb6fe`
(`build/q7-stdlib-current-20261029/receipt.json`).

This covers the committed inventory, including the retrieval Unicode boundary
audit. The separate `tools/ci` comparator tests were checked separately, not
through this profile. This local run does not prove hosted CI, the scientific
profile, or the ongoing Gradle/Android suite. Q7 remains open.
