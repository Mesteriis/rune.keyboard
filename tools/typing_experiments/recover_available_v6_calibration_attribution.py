"""Recover public page titles and URLs for the verified v6 calibration TSV."""

import argparse
from collections import defaultdict
import importlib.metadata
import json
from pathlib import Path
import tempfile

import check_available_v6_articles as mapping
import check_available_v6_calibration_index as calibration
import recover_available_v6_articles as sources
from recover_historical_spelling_attribution import scan_article_metadata


def expected_articles():
    rows = [
        json.loads(line) for line in calibration.INDEX.read_bytes().splitlines()
    ]
    wanted = {row["article"] for row in rows}
    result = {
        row["article"]: row["shard"]
        for row in map(json.loads, (mapping.DIRECTORY / "articles.jsonl").read_bytes().splitlines())
        if row["partition"] == "calibration"
    }
    if set(result) != wanted:
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_ARTICLES")
    return result


def scan_shard(path, shard, wanted):
    import pyarrow.parquet as parquet

    if path.stat().st_size != shard["bytes"] or sources.sha_file(path) != shard["sha256"]:
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_SHARD")
    parquet_file = parquet.ParquetFile(path)
    records = scan_article_metadata(
        parquet_file.iter_batches(columns=["id", "title", "url"]), wanted, "ru",
    )
    if path.stat().st_size != shard["bytes"] or sources.sha_file(path) != shard["sha256"]:
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_SHARD_DRIFT")
    return [dict(row, shard=shard["name"]) for row in records], parquet_file.metadata.num_rows


def recover(source_dir):
    calibration.check()
    expected = expected_articles()
    lock, _ = sources.read_lock()
    input_paths = (
        sources.LOCK, calibration.INDEX, mapping.DIRECTORY / "articles.jsonl",
        calibration.DIRECTORY / "calibration.tsv.bz2", Path(__file__),
        Path(__file__).with_name("recover_historical_spelling_attribution.py"),
    )
    bindings = {str(path.relative_to(sources.ROOT)): sources.sha_file(path) for path in input_paths}
    wanted_by_shard = defaultdict(set)
    for article, shard in expected.items():
        wanted_by_shard[shard].add(article)
    if set(wanted_by_shard) != {shard["name"] for shard in lock["shards"]}:
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_SHARDS")

    result = []
    scanned = {}
    with tempfile.TemporaryDirectory(prefix="rune-v6-attribution-shards-") as directory:
        for shard in lock["shards"]:
            name = shard["name"]
            path = (Path(directory) if source_dir is None else source_dir) / name
            try:
                if source_dir is None:
                    sources.download(shard, path)
                records, source_rows = scan_shard(path, shard, wanted_by_shard[name])
                result.extend(records)
                scanned[name] = dict(sourceRows=source_rows, articles=len(records))
            finally:
                if source_dir is None:
                    path.unlink(missing_ok=True)
            print(name, scanned[name], flush=True)
    if any(sources.sha_file(path) != bindings[str(path.relative_to(sources.ROOT))] for path in input_paths):
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_INPUT_DRIFT")
    result.sort(key=lambda row: int(row["article"]))
    if len(result) != len(expected):
        raise ValueError("V6_CALIBRATION_ATTRIBUTION_COVERAGE")
    return result, dict(
        schema=1, scope="historical-calibration-article-metadata",
        articleCount=len(result), sourceRevision=lock["revision"],
        pyarrowVersion=importlib.metadata.version("pyarrow"),
        scannedShards=scanned, bindings=bindings,
        revisionIdsVerified=False, publicationRightsReviewed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-dir", type=Path)
    source.add_argument("--download-temporary", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a fresh directory")
    records, receipt = recover(args.source_dir)
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "articles.jsonl"
    with path.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    receipt["articlesSha256"] = sources.sha_file(path)
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
