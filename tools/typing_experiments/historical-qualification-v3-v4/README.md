# Disclosed historical qualification corpora v3 and v4

These compressed archives retain the original manifest and seven corpus files
for each version. The bytes were recovered from the Rune Git history at the
commits recorded in `catalog.json`, then checked against each original
manifest. Archive members are stored in deterministic sorted order with fixed
metadata. The archives are approximately 2.4 MB combined; they are durable
test evidence, not temporary build output.

The original manifests identify the Wikimedia Wikipedia 2023-11-01 dataset,
revision `a634f78b1c435397c07001e175fa74cc4ad5e775`, and list CC-BY-SA-3.0
and GFDL-1.3. The archives contain generated excerpts and synthetic or protected
examples; the original files do not provide a complete per-row author or article
attribution. The earlier source-recovery work retained article/window exclusions
for Russian spelling rows, but this does not by itself establish complete
attribution or redistribution rights for every archived row. Review those rights
before publication; do not claim the archives are fully license-cleared.

Both datasets were historically exposed. They must not be treated as fresh
independent holdouts, used to fit a model or justify changed thresholds. Their
restoration does not establish historical score parity or restore available-v6.
No personal messages are declared in the original manifests; that declaration
is not an independent privacy audit of every text row.

Run `python3 tools/typing_experiments/check_historical_qualification_archives.py`
from the repository root to verify archive and original manifest identities and
all member bytes. The checker reads members in memory and does not extract them.

If a source checkout omits the compressed archives, run the fixture
reconstruction command after installing the pinned PyArrow dependency:

```sh
python3 tools/typing_experiments/replay_historical_qualification.py
```

The checked-in replay index contains the original manifests and SHA-256
fingerprints of 22,800 selected spelling and punctuation observations.
The command retrieves the pinned Wikipedia shards one at a time, finds the
expected observations using the article maps, and runs the frozen emitters.
The authored protected rows are generated separately. Both restored TAR/BZip2
files must match the catalog hashes before installation. A verified archive
already present can be reused. For offline execution, `--inputs` accepts a
directory containing the six already downloaded Parquet files. The hosted
stdlib and unit-test jobs run this step before their fixture-dependent checks.

To restore verified members for a local historical investigation, first ensure
`build/` exists, then run:

```sh
python3 tools/typing_experiments/check_historical_qualification_archives.py \
  --restore-output build/historical-qualification-v3-v4
```

The destination must be a fresh directory under `build/` with an existing parent;
existing destinations and destination symlinks are refused. The command validates
both archives in memory before creating the destination, writes only their fixed
member names, and removes its newly created destination on a write failure.
The result is disclosed historical data and must be removed when the investigation
is finished. Restoring it does not turn it into fresh evaluation data.
