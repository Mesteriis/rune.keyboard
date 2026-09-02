"""Compile an isolated radix selector and run only the frozen public calibration spelling rows."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PIPELINE = ROOT / "tools/eval/smart-typing-0.3/pipeline"
SELECTOR_SHA = "083b337c8931e24b12fb6862978cec0d2f2ea2544b461b8e7e072d1668048275"
HARNESS_SHA = "9231f661ed0a57a609de5351fa30c31c079a22b5e6735369cf3f9d5e4b62f486"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


export = module("calibration_export", PIPELINE / "export_calibration.py")


def once(text, old, new):
    export.require(text.count(old) == 1, "SELECTOR_TRANSFORM_DRIFT")
    return text.replace(old, new)


def selector_source(text):
    text = once(text, "internal class PackedTopSeven", "internal class ProbeRadixTopSeven")
    text = text.replace("PackedLexiconData", "ProbeRadixData")
    text = once(text, "    private val path = IntArray(32)",
                "    private val paths = IntArray(CAPACITY * 32)\n    private val path = IntArray(32)")
    text = once(text, "                var ancestor = region\n"
        "                while (depth[ancestor] > 0) { path[depth[ancestor] - 1] = codepoint[ancestor]; ancestor = parent[ancestor] }",
        "                paths.copyInto(path, 0, region * 32, region * 32 + parentDepth)")
    text = once(text, "                        val cp = index.label(node)\n"
        "                        path[parentDepth] = cp\n"
        "                        prefix.restoreParent(parentDepth, restore)\n"
        "                        if (!prefix.append(cp, lang, control)) return stopped()\n"
        "                        val u = maxOf(unitLower[region], gap, prefix.unitMinimum)\n"
        "                        val w = maxOf(weightedLower[region], prefix.weightedMinimum, 3 * u, 4 * gap)",
        "                        val endDepth = parentDepth + index.copyLabel(node, path, parentDepth)\n"
        "                        prefix.restoreParent(parentDepth, restore)\n"
        "                        var u = maxOf(unitLower[region], gap)\n"
        "                        var w = maxOf(weightedLower[region], 3 * u, 4 * gap)\n"
        "                        for (i in parentDepth until endDepth) {\n"
        "                            if (!prefix.append(path[i], lang, control)) return stopped()\n"
        "                            u = maxOf(u, prefix.unitMinimum)\n"
        "                            w = maxOf(w, prefix.weightedMinimum, 3 * u)\n"
        "                            if (u > radius) break\n"
        "                        }\n"
        "                        val cp = path[endDepth - 1]")
    text = text.replace("parentDepth + 1", "endDepth")
    text = once(text, "kotlin.math.abs(size - parentDepth - 1)", "kotlin.math.abs(size - endDepth)")
    text = once(text, "        val id = used++", "        val id = used++\n        path.copyInto(paths, id * 32, 0, d)")
    text = once(text, "    private fun clear() {", "    private fun clear() {\n        paths.fill(0)")
    text = once(text, "listOf(parent, codepoint, depth, language", "listOf(paths, parent, codepoint, depth, language")
    return "// Generated host-only experiment from the pinned production selector.\n" + text


def run(args):
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(ROOT / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    index = Path(args.index_dir).resolve(strict=True)
    ranks = Path(args.rank_dir).resolve(strict=True)
    radix = Path(args.radix_dir).resolve(strict=True)
    selector = ROOT / (export.PRODUCTION + "smarttyping/lexicon/PackedTopSeven.kt")
    harness = PIPELINE / "CandidateExport.kt"
    export.require(export.sha(selector) == SELECTOR_SHA and export.sha(harness) == HARNESS_SHA, "PINNED_BASE_SOURCE")
    manifest = json.loads((PIPELINE.parent / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        export.require(export.sha(PIPELINE.parent / name) == digest, "CORPUS_DIGEST")
    evaluator = module("prepared_evaluator", PIPELINE.parent / "evaluate.py")
    rows = evaluator.load_corpus()
    evaluator.validate(rows)
    rows = [r for r in rows if r["split"] == "calibration" and r["task"] == "spelling"]
    export.require(len(rows) == 6000, "CALIBRATION_COUNT")
    derived = json.loads((HERE / "results/2026-09-03/derivation.json").read_text())
    for language, record in derived["languages"].items():
        export.require(export.sha(radix / (language + ".radix")) == record["sha256"], "RADIX_HASH")
    toolchain = HERE.parent / "weighted-qualification/manifests/reproduction-toolchain.json"
    jars = []
    for record in json.loads(toolchain.read_text())["jars"]:
        found = list((Path(args.gradle_cache) / record["group"] / record["artifact"] / record["version"]).glob("*/*.jar"))
        export.require(len(found) == 1 and export.sha(found[0]) == record["sha256"], "PINNED_TOOLCHAIN")
        jars.append(found[0])
    version = subprocess.run([args.java, "-version"], capture_output=True, timeout=15, check=True)
    export.require(b'version "17.' in version.stderr, "JAVA_17")
    output.mkdir(parents=True)
    data = output / "assets"
    data.mkdir()
    for language in ("en", "ru", "es"):
        shutil.copyfile(ranks / (language + ".ranks"), data / (language + ".ranks"))
        shutil.copyfile(radix / (language + ".radix"), data / (language + ".radix"))
    (output / "ProbeRadixTopSeven.kt").write_text(selector_source(selector.read_text()))
    (output / "CandidateExport.kt").write_text(once(harness.read_text(),
        "CandidateGenerator(PackedCandidateLexicon(handles))", "CandidateGenerator(ProbeRadixLexicon(handles, File(args[2])))"))
    identities = ["package io.github.mesteriis.rune.keyboard.smarttyping.lexicon",
        "import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage", "internal object ProbeRadixIdentities {",
        "    val assets = mapOf("]
    for code, record in derived["languages"].items():
        language = {"en": "ENGLISH", "ru": "RUSSIAN", "es": "SPANISH"}[code]
        identities.append(f'        KeyboardLanguage.{language} to PackedAsset("{code}.radix", {record["bytes"]}L, "{record["sha256"]}"),')
    (output / "ProbeRadixIdentities.kt").write_text("\n".join(identities + ["    )", "}", ""]))
    sources = [ROOT / (export.PRODUCTION + p) for p in export.SOURCES]
    sources += [HERE / "ProbeRadixLexicon.kt", *sorted(output.glob("*.kt"))]
    assets = [index / (code + suffix) for code in ("en", "ru", "es") for suffix in (".trie", ".trie.lengths")]
    assets += [data / (code + ".ranks") for code in ("en", "ru", "es")]
    extra_assets = [data / (code + ".radix") for code in ("en", "ru", "es")]
    source_hashes = {str(p.relative_to(ROOT)): export.sha(p) for p in sources}
    asset_hashes = {p.name: export.sha(p) for p in assets}
    radix_hashes = {p.name: export.sha(p) for p in extra_assets}
    with (output / "inputs.tsv").open("x") as stream:
        for i, row in enumerate(rows):
            stream.write(f'{i}\t{row["language"]}\t{base64.b64encode(row["typed"].encode()).decode()}\n')
    binary = output / "generator.jar"
    java = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp"]
    with (output / "compile.log").open("xb") as log:
        subprocess.run(java + [os.pathsep.join(map(str, jars)), "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
            "-no-stdlib", "-no-reflect", "-jvm-target", "17", "-classpath", os.pathsep.join(map(str, jars[1:3])),
            "-d", str(binary), *map(str, sources)], stdout=log, stderr=log, timeout=120, check=True)
    with (output / "actual.tsv").open("xb") as raw, (output / "run.log").open("xb") as log:
        subprocess.run(java + [os.pathsep.join(map(str, [binary, *jars[1:3]])),
            "io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport", str(output / "inputs.tsv"),
            str(index), str(data)], stdout=raw, stderr=log, timeout=600, check=True)
    actual = export.parse_output((output / "actual.tsv").read_text(), rows)
    export.require(source_hashes == {str(p.relative_to(ROOT)): export.sha(p) for p in sources} and
        asset_hashes == {p.name: export.sha(p) for p in assets} and
        radix_hashes == {p.name: export.sha(p) for p in extra_assets}, "EXECUTION_DRIFT")
    with (output / "candidates.jsonl").open("x") as stream:
        for row in actual:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    export.write_json(output / "summary.json", dict(export.summarize(rows, actual), experimentalRadix=True))
    export.write_json(output / "provenance.json", {"sources": source_hashes, "assets": asset_hashes,
        "radixAssets": radix_hashes, "binary": export.sha(binary), "script": export.sha(Path(__file__)),
        "calibrationRows": evaluator.digest(rows), "toolchain": export.sha(toolchain),
        "originalExactLookupRetained": True, "productionIntegrated": False})
    print("Experimental radix calibration complete. No holdout, model or Android qualification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "index-dir", "rank-dir", "radix-dir", "java", "gradle-cache"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())
