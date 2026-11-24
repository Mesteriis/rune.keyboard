"""Check the retained dictionary-rival associations against the v6 registry."""

import bz2
from collections import Counter
import hashlib
import json

import check_available_v6_targets as previous
import recover_available_v6_targets as recovery

ARCHIVE = previous.DIRECTORY.parent / "rival-recovery/matches.jsonl.bz2"
MATCHES_SIZE = 1_063_621
MATCHES_SHA256 = "44af5d541f2c302a0afc9acfe67352551c4444f0f7de49aef891f58912e04b2f"


def check(archive=ARCHIVE):
    with bz2.open(archive, "rb") as stream:
        raw = stream.read(MATCHES_SIZE + 1)
    if len(raw) != MATCHES_SIZE or hashlib.sha256(raw).hexdigest() != MATCHES_SHA256:
        raise ValueError("V6_RIVAL_ARTIFACT")

    previous.check()
    prior = {
        json.loads(line)["targetKey"]
        for line in (previous.DIRECTORY / "matches.jsonl").read_bytes().splitlines()
    }
    targets = recovery.target_index(recovery.holdout_ledger.load_ledger(recovery.LEDGER))
    eligible = {
        (anchor["source"], anchor["article"], anchor["wordStart"], anchor["wordEnd"],
         anchor["contextHash"], anchor["sentenceKey"], anchor["sentencePartition"])
        for anchor in map(json.loads, recovery.ANCHORS.read_bytes().splitlines())
        if anchor["articlePartition"] == anchor["sentencePartition"]
    }
    seen = set()
    counts = Counter()
    for row in map(json.loads, raw.splitlines()):
        anchor = (
            row["source"], row["article"], row["wordStart"], row["wordEnd"],
            row["contextHash"], row["sentenceKey"], row["sourcePartition"],
        )
        key = row["targetKey"]
        if (
            anchor not in eligible or anchor in seen or key in prior
            or row["variant"] != "dictionary-rival"
            or targets.get(key) != row["targetPartition"]
            or row["targetPartition"] != row["sourcePartition"]
        ):
            raise ValueError("V6_RIVAL_ASSOCIATION")
        seen.add(anchor)
        counts[key] += 1
    if set(counts) != set(targets) - prior:
        raise ValueError("V6_RIVAL_COVERAGE")
    return {
        "newTargetKeys": len(counts),
        "matches": sum(counts.values()),
        "ambiguousTargetKeys": sum(count > 1 for count in counts.values()),
        "unmappedTargetKeys": 0,
    }


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
