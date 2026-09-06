from pathlib import Path
import json, sys
repo = Path.cwd().resolve()
sys.path.insert(0, str(repo / "tools/eval/smart-typing-0.3/pipeline"))
import contextual_quality as cq
base = repo / "build/smart-typing-0.3/contextual-v5-20260906"
rows = cq.load_export(base / "production-export")
binding = cq.records_binding(rows)
output = base / "row-decisions.jsonl"
assert not output.exists()
result = []
for split in ("calibration", "holdout"):
    selected = [row for row in rows if row["split"] == split]
    complete, scores = cq.load_scores(base / split, cq.requests(rows, split), binding)
    for row, decision in zip(selected, cq.decisions(selected, scores)):
        score = scores.get(row["id"])
        result.append({"id": row["id"], "language": row["language"], "split": split,
            "observedBoundary": row["observedBoundary"], "decisionId": decision,
            "decisionBoundary": cq.BOUNDARIES[decision], "suggestion": decision != 0,
            "sourceAgreement": cq.BOUNDARIES[decision] == row["observedBoundary"],
            "productionExcluded": not row["variants"],
            "runtimeError": score.get("error") if isinstance(score, dict) else None,
            "missingResponse": bool(row["variants"]) and score is None,
            "scoreRowDigest": cq.evaluator().digest(score) if score is not None else None})
output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result))
print(json.dumps({"rows": len(result), "sha256": cq.shared.sha(output),
    "holdoutSuggestedDisagreements": sum(row["split"] == "holdout" and row["suggestion"] and not row["sourceAgreement"] for row in result)}))
