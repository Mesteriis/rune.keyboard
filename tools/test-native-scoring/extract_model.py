#!/usr/bin/env python3
"""Extract only the exact reviewed GGUF from the fixed Actions artifact ZIP."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

MODEL_NAME = "rune-text-v1-0.1.0-q4_k_m.gguf"
MODEL_SIZE = 396704416
MODEL_SHA256 = "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"
MAX_ARCHIVE_SIZE = 512 * 1024 * 1024


def extract_model(archive: Path, destination: Path) -> None:
    if archive.stat().st_size > MAX_ARCHIVE_SIZE:
        raise ValueError("Artifact archive exceeds the allowed size")
    with zipfile.ZipFile(archive) as package:
        matches = [entry for entry in package.infolist()
                   if PurePosixPath(entry.filename).name == MODEL_NAME and not entry.is_dir()]
        if len(matches) != 1:
            raise ValueError("Artifact must contain exactly one named GGUF")
        entry = matches[0]
        name = PurePosixPath(entry.filename)
        if name.is_absolute() or ".." in name.parts or entry.file_size != MODEL_SIZE:
            raise ValueError("Unexpected model entry path or size")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with package.open(entry) as source, tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".verified-model-", delete=False,
            ) as output:
                temporary = Path(output.name)
                digest = hashlib.sha256()
                size = 0
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > MODEL_SIZE:
                        raise ValueError("Model exceeds the allowed size")
                    digest.update(chunk)
                    output.write(chunk)
            if size != MODEL_SIZE or digest.hexdigest() != MODEL_SHA256:
                raise ValueError("Model size or SHA-256 does not match the reviewed artifact")
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    options = parser.parse_args()
    extract_model(options.archive, options.destination)
    print("Exact inner GGUF size and SHA-256 verified")
