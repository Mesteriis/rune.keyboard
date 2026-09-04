#!/usr/bin/env python3
"""Build bounded exact lowercase-to-canonical-case assets from frozen surface forms."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import unicodedata

MAGIC = b"RNC1"
LANGUAGES = ("en", "es", "ru")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_title_surface(value: str) -> bool:
    return bool(value and value[0].isupper() and value[1:] == value[1:].lower())


def derive(path: Path) -> list[tuple[str, str, bool]]:
    surfaces: dict[str, set[str]] = defaultdict(set)
    titles: dict[str, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="utf-8").splitlines():
        surface = unicodedata.normalize("NFC", line)
        key = unicodedata.normalize("NFC", surface.lower())
        if not key or len(key) > 32 or any(char.isspace() for char in key):
            raise ValueError("invalid frozen surface form")
        surfaces[key].add(surface)
        if is_title_surface(surface):
            titles[key].add(surface)
    result = []
    for key, candidates in titles.items():
        if len(candidates) != 1:
            continue
        canonical = next(iter(candidates))
        result.append((key, canonical, key not in surfaces[key]))
    return sorted(result, key=lambda item: item[0].encode("utf-8"))


def encode(rows: list[tuple[str, str, bool]]) -> bytes:
    records = bytearray()
    offsets = [0]
    for key, canonical, unambiguous in rows:
        key_bytes = key.encode("utf-8")
        canonical_bytes = canonical.encode("utf-8")
        if len(key_bytes) > 255 or len(canonical_bytes) > 255:
            raise ValueError("canonical case record exceeds byte boundary")
        records.extend((1 if unambiguous else 0, len(key_bytes), len(canonical_bytes)))
        records.extend(key_bytes)
        records.extend(canonical_bytes)
        offsets.append(len(records))
    return MAGIC + struct.pack(">I", len(rows)) + struct.pack(f">{len(offsets)}I", *offsets) + records


def build(surface_dir: Path, output_dir: Path, frozen_manifest: Path) -> dict:
    frozen = json.loads(frozen_manifest.read_text(encoding="utf-8"))
    expected = {item["language"]: item["surface_forms"]["sha256"] for item in frozen["languages"]}
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for language in LANGUAGES:
        source = surface_dir / f"{language}.surface-forms.txt"
        if sha256(source) != expected[language]:
            raise ValueError(f"surface-form digest mismatch: {language}")
        rows = derive(source)
        target = output_dir / f"{language}.case"
        target.write_bytes(encode(rows))
        entries.append({
            "language": language,
            "sourceSurfaceSha256": expected[language],
            "records": len(rows),
            "unambiguousRecords": sum(row[2] for row in rows),
            "asset": {"path": f"smarttyping/lexicon/case/{target.name}",
                      "bytes": target.stat().st_size, "sha256": sha256(target)},
        })
    return {"schema": 1, "format": "RNC1", "builderSha256": sha256(Path(__file__)),
            "frozenManifestSha256": sha256(frozen_manifest), "policy":
            "One unique NFC title-case surface per lowercase key; ambiguity flag is false when the lowercase surface also exists.",
            "languages": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.surface_dir, args.output_dir, args.frozen_manifest)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
