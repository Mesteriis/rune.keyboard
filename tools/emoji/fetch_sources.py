#!/usr/bin/env python3
"""Restore the exact pinned source archive; existing archives are verified without network I/O."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.parse
import urllib.request

from generate_catalog import ARCHIVE, MANIFEST, CatalogError, atomic_write, load_manifest, load_sources, make_archive, require, sha


def fetch_to(output: Path, manifest_path: Path = MANIFEST) -> None:
    manifest = load_manifest(manifest_path)
    if output.exists():
        load_sources(manifest, output)
        return

    def download(item):
        name, expected = item
        request = urllib.request.Request(expected["url"], headers={"User-Agent": "Rune Keyboard emoji source restore"})
        with urllib.request.urlopen(request, timeout=30) as response:
            final = urllib.parse.urlparse(response.geturl())
            require(final.scheme == "https" and final.hostname in {"www.unicode.org", "unicode.org", "raw.githubusercontent.com"}, "SOURCE_REDIRECT")
            raw = response.read(expected["bytes"] + 1)
        require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"], "FETCH_MEMBER_IDENTITY")
        return name, raw

    with ThreadPoolExecutor(max_workers=3) as pool:
        members = dict(pool.map(download, manifest["members"].items()))
    archive = make_archive(members)
    require(len(archive) == manifest["archive"]["bytes"] and sha(archive) == manifest["archive"]["sha256"], "FETCH_ARCHIVE_IDENTITY")
    atomic_write(output, archive)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ARCHIVE)
    parser.add_argument("--source-manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    try:
        fetch_to(args.output, args.source_manifest)
        print("Pinned emoji source archive verified")
    except (CatalogError, OSError) as error:
        parser.exit(1, "Emoji source restore failed: " + (str(error) if isinstance(error, CatalogError) else type(error).__name__) + "\n")


if __name__ == "__main__":
    main()
