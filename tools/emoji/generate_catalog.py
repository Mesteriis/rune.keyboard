#!/usr/bin/env python3
"""Build the offline emoji palette from pinned Unicode/CLDR bytes; never accesses the network."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = HERE / "source-manifest.json"
ARCHIVE = HERE / "sources/unicode-15.1-cldr-44.1.zip"
CATEGORIES = HERE / "categories.json"
OUTPUT = REPO / "app/src/main/assets/emoji"
LANGUAGES = ("en", "ru", "es")
MAX_ARCHIVE_BYTES = 5_000_000
MAX_MEMBER_BYTES = 2_000_000
MAX_CATALOG_BYTES = 320_000
ROW = re.compile(r"([0-9A-F ]+)\s*;\s*(fully-qualified|minimally-qualified|unqualified|component)\s*# (\S+) E([0-9.]+) (.+)")


class CatalogError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CatalogError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def parse_json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CatalogError("INVALID_JSON") from error
    require(isinstance(value, dict), "JSON_OBJECT_REQUIRED")
    return value


def source_urls(commit: str) -> dict[str, str]:
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "CLDR_COMMIT")
    base = "https://raw.githubusercontent.com/unicode-org/cldr-json/" + commit + "/"
    urls = {"emoji-test.txt": "https://www.unicode.org/Public/emoji/15.1/emoji-test.txt", "LICENSE.txt": base + "LICENSE"}
    for language in LANGUAGES:
        urls["annotations-" + language + ".json"] = base + "cldr-json/cldr-annotations-full/annotations/" + language + "/annotations.json"
        urls["derived-" + language + ".json"] = base + "cldr-json/cldr-annotations-derived-full/annotationsDerived/" + language + "/annotations.json"
    return urls


def load_manifest(path: Path = MANIFEST) -> dict:
    manifest = parse_json(path.read_bytes())
    require(manifest.get("schema") == 1 and manifest.get("emojiVersion") == "15.1" and manifest.get("cldrVersion") == "44.1", "SOURCE_VERSIONS")
    expected = source_urls(manifest.get("cldrCommit", ""))
    members = manifest.get("members", {})
    require(set(members) == set(expected), "SOURCE_MEMBER_SET")
    for name, url in expected.items():
        item = members[name]
        require(item.get("url") == url, "SOURCE_URL")
        require(isinstance(item.get("bytes"), int) and 0 < item["bytes"] <= MAX_MEMBER_BYTES, "SOURCE_MEMBER_SIZE")
        require(re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) is not None, "SOURCE_MEMBER_SHA")
    metadata = manifest.get("archive", {})
    require(metadata.get("file") == "sources/unicode-15.1-cldr-44.1.zip" and metadata.get("method") == "ZIP_STORED", "SOURCE_ARCHIVE_FORMAT")
    require(isinstance(metadata.get("bytes"), int) and 0 < metadata["bytes"] <= MAX_ARCHIVE_BYTES, "SOURCE_ARCHIVE_SIZE")
    require(re.fullmatch(r"[0-9a-f]{64}", metadata.get("sha256", "")) is not None, "SOURCE_ARCHIVE_SHA")
    return manifest


def make_archive(members: dict[str, bytes]) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return target.getvalue()


def load_sources(manifest: dict, path: Path = ARCHIVE) -> dict[str, bytes]:
    require(path.stat().st_size <= MAX_ARCHIVE_BYTES, "SOURCE_ARCHIVE_SIZE")
    data = path.read_bytes()
    require(len(data) == manifest["archive"]["bytes"] and sha(data) == manifest["archive"]["sha256"], "SOURCE_ARCHIVE_IDENTITY")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            require(len(infos) == len(manifest["members"]) and {item.filename for item in infos} == set(manifest["members"]), "ARCHIVE_MEMBER_SET")
            require(sum(item.file_size for item in infos) <= MAX_ARCHIVE_BYTES, "ARCHIVE_EXPANDED_SIZE")
            result = {}
            for item in infos:
                require(not item.is_dir() and not item.flag_bits & 1 and item.compress_type == zipfile.ZIP_STORED, "ARCHIVE_MEMBER_FORMAT")
                expected = manifest["members"][item.filename]
                require(item.file_size == expected["bytes"] and item.file_size <= MAX_MEMBER_BYTES, "ARCHIVE_MEMBER_SIZE")
                raw = archive.read(item)
                require(sha(raw) == expected["sha256"], "ARCHIVE_MEMBER_IDENTITY")
                result[item.filename] = raw
            return result
    except zipfile.BadZipFile as error:
        raise CatalogError("INVALID_SOURCE_ARCHIVE") from error


def field(value: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(), "INVALID_NAME")
    require(not any(ord(char) < 32 or 0x7F <= ord(char) <= 0x9F or char in "\u2028\u2029" for char in value), "NAME_CONTROL")
    try:
        require(len(value.encode("utf-8")) <= 512, "NAME_SIZE")
    except UnicodeError as error:
        raise CatalogError("NAME_ENCODING") from error
    return value


def parse_emojis(data: bytes) -> tuple[list[dict], dict]:
    text = data.decode("utf-8")
    require("# Version: 15.1" in text.splitlines(), "EMOJI_VERSION")
    group = None
    entries = []
    seen = set()
    counts = Counter()
    omitted = 0
    for line in text.splitlines():
        if line.startswith("# group: "):
            group = line.removeprefix("# group: ")
        elif line.strip() and not line.startswith("#"):
            match = ROW.fullmatch(line)
            require(match is not None and group is not None, "EMOJI_ROW")
            points = [int(item, 16) for item in match[1].split()]
            require(all(0 <= point <= 0x10FFFF and not 0xD800 <= point <= 0xDFFF for point in points), "EMOJI_SCALAR")
            glyph = "".join(chr(point) for point in points)
            require(glyph == match[3], "EMOJI_GLYPH")
            counts[match[2]] += 1
            if match[2] != "fully-qualified":
                continue
            require(glyph not in seen, "DUPLICATE_EMOJI")
            seen.add(glyph)
            if any(0x1F3FB <= point <= 0x1F3FF for point in points):
                omitted += 1
                continue
            entries.append({"group": group, "glyph": glyph})
    require(bool(entries), "EMPTY_CATALOG")
    return entries, {"statusCounts": dict(counts), "omittedSkinToneEntries": omitted}


def load_names(sources: dict[str, bytes], language: str) -> dict[str, str]:
    result = {}
    for filename, root in (("annotations-", "annotations"), ("derived-", "annotationsDerived")):
        document = parse_json(sources[filename + language + ".json"])[root]
        require(document["identity"]["version"]["_cldrVersion"] == "44.1" and document["identity"]["language"] == language, "CLDR_IDENTITY")
        for glyph, annotation in document["annotations"].items():
            names = annotation.get("tts")
            if not names:
                continue
            require(isinstance(names, list) and len(names) == 1, "CLDR_TTS")
            name = field(names[0])
            require(glyph not in result or result[glyph] == name, "CONFLICTING_CLDR_TTS")
            result[glyph] = name
    return result


def build(source_archive: Path = ARCHIVE, source_manifest: Path = MANIFEST, categories: Path = CATEGORIES) -> dict[str, bytes]:
    manifest = load_manifest(source_manifest)
    sources = load_sources(manifest, source_archive)
    entries, source_counts = parse_emojis(sources["emoji-test.txt"])
    groups = parse_json(categories.read_bytes())
    require(groups.get("schema") == 1 and isinstance(groups.get("groups"), list), "CATEGORY_SCHEMA")
    groups = groups["groups"]
    require(len(groups) == 9 and len({group["id"] for group in groups}) == 9, "CATEGORY_SET")
    source_order = list(dict.fromkeys(entry["group"] for entry in entries))
    require([group["sourceGroup"] for group in groups] == source_order, "CATEGORY_ORDER")
    by_source = {group["sourceGroup"]: group for group in groups}
    names = {language: load_names(sources, language) for language in LANGUAGES}
    rows = ["# rune-emoji-catalog-v1"]
    for group in groups:
        require(re.fullmatch(r"[a-z][a-z-]{0,31}", group["id"]) is not None, "CATEGORY_ID")
        require(any(entry["glyph"] == group["icon"] and entry["group"] == group["sourceGroup"] for entry in entries), "CATEGORY_ICON")
        rows.append("\t".join(["G", group["id"], group["icon"], *[field(group["names"][language]) for language in LANGUAGES]]))
    lookup = {language: Counter() for language in LANGUAGES}
    counts = Counter()
    for entry in entries:
        glyph = entry["glyph"]
        labels = []
        for language in LANGUAGES:
            key = glyph if glyph in names[language] else glyph.replace("\ufe0f", "")
            require(key in names[language], "MISSING_NAME_" + language.upper())
            lookup[language]["exact" if key == glyph else "withoutVariationSelector"] += 1
            labels.append(names[language][key])
        group = by_source[entry["group"]]["id"]
        counts[group] += 1
        rows.append("\t".join(["E", group, glyph, *labels]))
    catalog = ("\n".join(rows) + "\n").encode("utf-8")
    require(len(catalog) <= MAX_CATALOG_BYTES, "CATALOG_SIZE_BUDGET")
    license_data = ("Unicode Emoji 15.1 data: Copyright © 2023 Unicode, Inc.\nCLDR 44.1 and Unicode data license:\n\n".encode("utf-8") + sources["LICENSE.txt"])
    output = {"catalog-v1.tsv": catalog, "LICENSE.txt": license_data}
    record = {"schema": 1, "emojiVersion": "15.1", "cldrVersion": "44.1", "entries": len(entries),
              "groups": [{"id": group["id"], "entries": counts[group["id"]]} for group in groups],
              "itemNames": "CLDR tts; exact key or removal of U+FE0F only; no language fallback",
              "categoryNames": "Rune-authored UI captions; source group ordering is Unicode",
              "lookupCounts": {language: dict(value) for language, value in lookup.items()}, **source_counts,
              "generatorSha256": sha(Path(__file__).read_bytes()), "sourceManifestSha256": sha(source_manifest.read_bytes()),
              "sourceArchiveSha256": manifest["archive"]["sha256"], "categoriesSha256": sha(categories.read_bytes()),
              "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in output.items()}}
    output["catalog-manifest.json"] = json_bytes(record)
    return output


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".emoji-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, default=ARCHIVE)
    parser.add_argument("--source-manifest", type=Path, default=MANIFEST)
    parser.add_argument("--categories", type=Path, default=CATEGORIES)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        output = build(args.source_archive, args.source_manifest, args.categories)
        for name, data in output.items():
            path = args.output_dir / name
            if args.check:
                require(path.is_file() and path.read_bytes() == data, "GENERATED_FILE_MISMATCH:" + name)
            else:
                atomic_write(path, data)
        print("Emoji catalog", "verified" if args.check else "generated", "—", json.loads(output["catalog-manifest.json"])["entries"], "entries")
    except (CatalogError, KeyError, TypeError, UnicodeError, OSError) as error:
        parser.exit(1, "Emoji catalog failed: " + (str(error) if isinstance(error, CatalogError) else type(error).__name__) + "\n")


if __name__ == "__main__":
    main()
