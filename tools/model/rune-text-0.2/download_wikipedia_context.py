#!/usr/bin/env python3
"""Download and verify the exact bounded Wikipedia parquet inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

from generate_pairwise_data import sha


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def verify(path: Path, expected: dict) -> bool:
    return (path.is_file() and path.stat().st_size == expected["bytes"]
            and sha(path) == expected["sha256"])


def run(args: argparse.Namespace) -> None:
    document = json.loads(Path(args.lock).resolve(strict=True).read_text())
    lock = document.get("wikipediaContext", document)
    output = Path(args.output).resolve()
    if not output.is_relative_to(REPO / "build"):
        raise ValueError("output must be below build")
    output.mkdir(parents=True, exist_ok=True)
    repository = urllib.parse.quote(lock["repository"], safe="/")
    revision = urllib.parse.quote(lock["parquetRevision"], safe="")
    for filename, expected in sorted(lock["files"].items()):
        target = output / filename
        if verify(target, expected):
            print(f"verified {filename}")
            continue
        if target.exists():
            raise ValueError(f"existing Wikipedia input does not match lock: {filename}")
        temporary = output / f".{filename}.partial"
        if temporary.exists():
            temporary.unlink()
        source_path = "/".join(urllib.parse.quote(part, safe="")
                               for part in expected["repositoryPath"].split("/"))
        url = f"https://huggingface.co/datasets/{repository}/resolve/{revision}/{source_path}"
        try:
            with urllib.request.urlopen(url, timeout=60) as source, temporary.open("xb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            if not verify(temporary, expected):
                raise ValueError(f"downloaded Wikipedia input does not match lock: {filename}")
            temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        print(f"downloaded and verified {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=HERE / "source-lock.json")
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
