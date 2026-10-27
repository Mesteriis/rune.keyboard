#!/usr/bin/env python3
"""Verify the actual APK native payload against the pinned runtime strip outputs."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

ABIS = ("arm64-v8a", "x86_64")
LIBRARIES = ("libc++_shared.so", "librune_llama.so")
MAX_LIBRARY_BYTES = 128 * 1024 * 1024


class NativePayloadError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise NativePayloadError(code)


def verify_sections(output: str) -> None:
    names = set(re.findall(r"^\s*\[\s*\d+\]\s+(\S+)", output, re.MULTILINE))
    require({".text", ".rodata", ".dynsym"} <= names, "NATIVE_REQUIRED_SECTIONS")
    require(not any(name.startswith((".debug_", ".zdebug_")) or name in
                    {".symtab", ".gnu_debugdata", ".gnu_debuglink"} for name in names),
            "NATIVE_DEBUG_SECTIONS")


def verify_paths(payload: bytes) -> None:
    # Report a fixed code, never a captured machine-local path or string payload.
    require(re.search(rb"/(?:Users|home)/", payload) is None, "NATIVE_LOCAL_SOURCE_PATH")


def verify(apk: Path, stripped: Path, readelf: Path, *, require_no_local_paths: bool = False) -> list[dict]:
    expected = {f"lib/{abi}/{name}" for abi in ABIS for name in LIBRARIES}
    report = []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="rune-native-") as directory:
        infos = [item for item in archive.infolist() if item.filename.startswith("lib/")]
        require(len(infos) == len(expected) and {item.filename for item in infos} == expected,
                "NATIVE_APK_MEMBER_SET")
        for item in sorted(infos, key=lambda value: value.filename):
            require(not item.is_dir() and not item.flag_bits & 1 and
                    0 < item.file_size <= MAX_LIBRARY_BYTES, "NATIVE_APK_MEMBER_SIZE_OR_FORMAT")
            _, abi, name = item.filename.split("/")
            path = Path(directory) / abi / name
            path.parent.mkdir(exist_ok=True)
            payload = archive.read(item)
            path.write_bytes(payload)
            result = subprocess.run([str(readelf), "--section-headers", "--wide", str(path)],
                                    capture_output=True, text=True, check=True)
            verify_sections(result.stdout)
            if require_no_local_paths:
                verify_paths(payload)
            references = [p for p in stripped.rglob(name) if p.parent.name == abi and p.is_file()]
            require(len(references) == 1, "NATIVE_STRIPPED_REFERENCE_SET")
            # Exact bytes imply .text/.rodata, dynamic exports and DT_NEEDED parity too.
            require(payload == references[0].read_bytes(), "NATIVE_STRIPPED_PAYLOAD_MISMATCH")
            report.append(dict(entry=item.filename, bytes=len(payload),
                               sha256=hashlib.sha256(payload).hexdigest()))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--stripped", type=Path, required=True)
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--require-no-local-paths", action="store_true",
                        help="Also refuse /Users/ or /home/ strings retained in runtime data")
    args = parser.parse_args()
    try:
        for item in verify(args.apk, args.stripped, args.readelf, require_no_local_paths=args.require_no_local_paths):
            print(f"Packaged native verified: {item['entry']} {item['bytes']} bytes {item['sha256']}")
    except (NativePayloadError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, "Packaged native gate failed: " +
                    (str(error) if isinstance(error, NativePayloadError) else type(error).__name__) + "\n")


if __name__ == "__main__":
    main()
