"""Verify the calibration TSV's reconstructed source-context index offline."""

import base64
import bz2
import hashlib
import json

import check_available_v6_rivals as rivals
import check_available_v6_targets as previous
import recover_available_v6_targets as recovery

DIRECTORY = previous.DIRECTORY.parent / "calibration-recovery"
INDEX = DIRECTORY / "source-index.jsonl"
INDEX_SHA256 = "feed2e451dbe91d7afb5eac8fc946b92b2dbda2b414e7cb3f91469df559c44d8"
TSV_SHA256 = "b19e91877a9dc4ec200a4982b191d7c9348efdf8196ddb84047521a4c04b3abb"
TSV_BYTES = 3_266_373


def check(path=INDEX):
    index = path.read_bytes()
    if hashlib.sha256(index).hexdigest() != INDEX_SHA256:
        raise ValueError("V6_CALIBRATION_INDEX_DIGEST")
    with bz2.open(DIRECTORY / "calibration.tsv.bz2", "rb") as stream:
        tsv = stream.read(TSV_BYTES + 1)
    if len(tsv) != TSV_BYTES or hashlib.sha256(tsv).hexdigest() != TSV_SHA256:
        raise ValueError("V6_CALIBRATION_TSV_DIGEST")
    tsv_rows = [
        tuple(base64.b64decode(field, validate=True).decode() for field in line.split(b"\t")[4:])
        for line in tsv.splitlines()
    ]
    rivals.check()
    sources = {
        (row["article"], row["sentenceKey"], row["targetKey"], row["variant"])
        for raw in (
            (previous.DIRECTORY / "matches.jsonl").read_bytes(),
            bz2.decompress(rivals.ARCHIVE.read_bytes()),
        )
        for row in map(json.loads, raw.splitlines())
        if row["sourcePartition"] == row["targetPartition"] == "calibration"
    }
    ledger = recovery.holdout_ledger.load_ledger(recovery.LEDGER)
    registered = next(
        entry["keys"] for entry in ledger["entries"]
        if entry["id"] == recovery.articles.ENTRY + "calibration"
    )

    offset = 0
    sentences, articles, families = set(), set(), set()
    for record in map(json.loads, index.splitlines()):
        count = record["rows"]
        if record["firstRow"] != offset or count not in (4, 5):
            raise ValueError("V6_CALIBRATION_INDEX_ORDER")
        rows = tsv_rows[offset:offset + count]
        prefix, typed = rows[0]
        word = rows[2][1]
        if len(rows) != count or rows[:4] != [
            (prefix, typed), (prefix, typed), (prefix, word), (prefix, "@" + word),
        ]:
            raise ValueError("V6_CALIBRATION_TSV_VARIANTS")

        variants = [(word, "source-word"), ("@" + word, "protected-source-word")]
        if count == 5:
            if rows[4][0] != prefix:
                raise ValueError("V6_CALIBRATION_TSV_VARIANTS")
            variants.append((rows[4][1], "dictionary-rival"))

        article, sentence = record["article"], record["sentenceKey"]
        if sentence in sentences:
            raise ValueError("V6_CALIBRATION_INDEX_DUPLICATE")
        for target, variant in variants:
            key, = recovery.holdout_ledger.keys_for([
                dict(prefix=prefix, typed=target, expectedSpelling=target),
            ], "context")
            if (article, sentence, key, variant) not in sources:
                raise ValueError("V6_CALIBRATION_INDEX_ASSOCIATION")
        offset += count
        sentences.add(sentence)
        articles.update(recovery.holdout_ledger.keys_for([dict(article=article)], "article"))
        families.update(record["familyKeys"])

    if offset != len(tsv_rows) or any(
        values != set(registered[kind]) for kind, values in
        (("sentence", sentences), ("article", articles), ("family", families))
    ):
        raise ValueError("V6_CALIBRATION_INDEX_COVERAGE")
    return dict(rows=offset, contexts=len(sentences), articles=len(articles), families=len(families))


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
