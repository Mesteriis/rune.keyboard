#!/usr/bin/env python3
"""Measure one release APK against reviewed byte budgets, without extracting files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import os
import zipfile

HERE = Path(__file__).resolve().parent
BUDGETS = HERE / "apk-footprint-budgets.json"
GROUPS = ("lib", "lexicon", "experiments", "res", "dex", "other")
ABIS = ("arm64-v8a", "x86_64")


class FootprintError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FootprintError(code)


def parse_json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=unique)
    require(isinstance(value, dict), "JSON_OBJECT_REQUIRED")
    return value


def read_json(path: Path) -> dict:
    return parse_json(path.read_bytes())


def load_budgets(path: Path) -> dict:
    return validate_budgets(read_json(path))


def validate_budgets(value: dict) -> dict:
    require(set(value) == {"schema", "baseline", "maxApkBytes", "maxUncompressedBytes",
                           "maxContainerBytes", "categories", "nativeByAbi"} and
            type(value["schema"]) is int and value["schema"] == 1, "BUDGET_SCHEMA")
    baseline = value["baseline"]
    require(isinstance(baseline, dict) and set(baseline) == {"commit", "apkSha256", "apkBytes"} and
            isinstance(baseline.get("commit"), str) and
            re.fullmatch(r"[0-9a-f]{40}", baseline["commit"]) is not None and
            isinstance(baseline.get("apkSha256"), str) and
            re.fullmatch(r"[0-9a-f]{64}", baseline["apkSha256"]) is not None,
            "BUDGET_BASELINE")
    require(isinstance(value["categories"], dict) and set(value["categories"]) == set(GROUPS) and
            isinstance(value["nativeByAbi"], dict) and set(value["nativeByAbi"]) == set(ABIS),
            "BUDGET_COMPONENT_SET")
    limits = [baseline["apkBytes"], value["maxApkBytes"], value["maxUncompressedBytes"],
              value["maxContainerBytes"], *value["categories"].values(), *value["nativeByAbi"].values()]
    require(all(type(limit) is int and limit > 0 for limit in limits), "BUDGET_POSITIVE_INTEGER")
    require(baseline["apkBytes"] <= value["maxApkBytes"], "BUDGET_BELOW_BASELINE")
    return value


def release_apk(directory: Path) -> Path:
    metadata = read_json(directory / "output-metadata.json")
    elements = metadata.get("elements")
    require(metadata.get("variantName") == "release" and isinstance(elements, list) and
            len(elements) == 1, "RELEASE_SINGLE_APK_REQUIRED")
    item = elements[0]
    require(isinstance(item, dict) and item.get("type") == "SINGLE" and item.get("filters") == [],
            "RELEASE_SINGLE_APK_REQUIRED")
    name = item.get("outputFile")
    require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+\.apk", name) is not None,
            "RELEASE_APK_NAME")
    path = directory / name
    require(path.is_file() and path.resolve().parent == directory.resolve(), "RELEASE_APK_LOCATION")
    return path


def category(name: str) -> str:
    if name.startswith("lib/"):
        return "lib"
    if name.startswith("assets/smarttyping/lexicon/"):
        return "lexicon"
    if name.startswith("assets/smarttyping/experiments/"):
        return "experiments"
    if name.startswith("res/"):
        return "res"
    if re.fullmatch(r"classes[0-9]*\.dex", name):
        return "dex"
    return "other"


def measure(apk: Path, budgets: dict) -> dict:
    initial = apk.stat()
    groups = {key: dict(uncompressedBytes=0, compressedBytes=0, entries=0) for key in GROUPS}
    native = dict.fromkeys(ABIS, 0)
    seen = set()
    with zipfile.ZipFile(apk) as archive:
        for item in archive.infolist():
            name = item.filename
            require(name not in seen, "DUPLICATE_APK_MEMBER")
            seen.add(name)
            require(not name.startswith("/") and "\\" not in name and
                    ".." not in PurePosixPath(name).parts, "UNSAFE_APK_MEMBER")
            require(not item.flag_bits & 1, "ENCRYPTED_APK_MEMBER")
            if item.is_dir():
                require(item.file_size == 0, "NONEMPTY_APK_DIRECTORY")
                continue
            group = groups[category(name)]
            group["entries"] += 1
            group["uncompressedBytes"] += item.file_size
            group["compressedBytes"] += item.compress_size
            if name.startswith("lib/"):
                parts = name.split("/")
                require(len(parts) == 3 and parts[1] in native and parts[2].endswith(".so"),
                        "NATIVE_ABI_OR_MEMBER")
                native[parts[1]] += item.file_size
    require(all(native.values()), "NATIVE_ABI_SET")
    apk_bytes = initial.st_size
    uncompressed = sum(item["uncompressedBytes"] for item in groups.values())
    compressed = sum(item["compressedBytes"] for item in groups.values())
    container = apk_bytes - compressed
    require(container >= 0, "INVALID_APK_CONTAINER_SIZE")
    digest = hashlib.sha256()
    with apk.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    final = apk.stat()
    require((initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns, initial.st_ctime_ns) ==
            (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns, final.st_ctime_ns),
            "APK_CHANGED_DURING_MEASUREMENT")
    failures = []
    for actual, maximum, code in [(apk_bytes, budgets["maxApkBytes"], "APK_TOTAL"),
                                   (uncompressed, budgets["maxUncompressedBytes"], "UNCOMPRESSED_TOTAL"),
                                   (container, budgets["maxContainerBytes"], "ZIP_CONTAINER")]:
        if actual > maximum:
            failures.append(code)
    failures += ["CATEGORY_" + key.upper() for key in GROUPS
                 if groups[key]["uncompressedBytes"] > budgets["categories"][key]]
    failures += ["NATIVE_" + key for key in ABIS if native[key] > budgets["nativeByAbi"][key]]
    return dict(schema=1, apkSha256=digest.hexdigest(), apkBytes=apk_bytes,
                uncompressedBytes=uncompressed, compressedBytes=compressed, containerBytes=container,
                categories=groups, nativeByAbi=native, passed=not failures, violations=failures)


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".footprint-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--apk", type=Path)
    source.add_argument("--apk-dir", type=Path)
    parser.add_argument("--budgets", type=Path, default=BUDGETS)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.report:
            output = args.report.resolve()
            require(output != args.budgets.resolve() and
                    (args.apk is None or output != args.apk.resolve()) and
                    (args.apk_dir is None or not output.is_relative_to(args.apk_dir.resolve())),
                    "REPORT_OVERLAPS_INPUT")
            args.report.unlink(missing_ok=True)
        budget_bytes = args.budgets.read_bytes()
        budgets = validate_budgets(parse_json(budget_bytes))
        report = measure(args.apk or release_apk(args.apk_dir), budgets)
        report["budgetSha256"] = hashlib.sha256(budget_bytes).hexdigest()
        if args.report:
            write_report(args.report, report)
        print(f"APK footprint: {report['apkBytes']} bytes; unpacked {report['uncompressedBytes']} bytes")
        for key, value in report["categories"].items():
            print(f"  {key}: {value['uncompressedBytes']} bytes (ZIP payload {value['compressedBytes']})")
        for abi, size in report["nativeByAbi"].items():
            print(f"  native {abi}: {size} bytes")
        require(report["passed"], "FOOTPRINT_BUDGET:" + ",".join(report["violations"]))
    except (FootprintError, OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeError) as error:
        parser.exit(1, "APK footprint failed: " +
                    (str(error) if isinstance(error, FootprintError) else type(error).__name__) + "\n")


if __name__ == "__main__":
    main()
