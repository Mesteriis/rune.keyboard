from pathlib import Path
import datetime, hashlib, json, subprocess, sys
repo = Path.cwd().resolve()
sys.path.insert(0, str(repo / "tools/eval/smart-typing-0.3/pipeline"))
import contextual_quality as cq
sh = cq.shared.sha
ev = cq.evaluator()
base = repo / "build/smart-typing-0.3/contextual-v5-20260906"
output = base / "protocol-freeze"
assert not output.exists()
assert not list(base.rglob("scores.jsonl")), "Real v5 scores must not precede protocol freeze"
corpus = base / "run-c"
runner = repo / "build/smart-typing-0.3/native-current-20260906/rune-score"
model = repo / "build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf"
assert sh(runner) == "bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553"
assert sh(model) == ev.MODEL_SHA256 and model.stat().st_size == ev.MODEL_SIZE
assert sh(corpus / "manifest.json") == "dbce48cfc68d36a52a1f7c60d96d612dc568012d409dd1015e5685c386461660"
verification = base / "adapter-policy-parity-downgrade-fix"
cq.load_verification(verification)
identity = {"protocol": ev.PROTOCOL, "runnerSha256": sh(runner), "modelSha256": sh(model)}
backend = {"schemaVersion": 1, "scope": "contextual-v5-backend-only", "modelIdentity": identity,
    "modelBytes": model.stat().st_size, "runner": str(runner.relative_to(repo)),
    "model": str(model.relative_to(repo)), "thresholdsIncluded": False,
    "upstreamLlamaSha": "36b10154383b60eb15baac2c7a40d2a5f784faa7",
    "qualification": {"nativeMathCases": 1, "scalarOracleMaxSumDelta": 0,
        "historicalSpellingResponseCompatibility": 2940, "compatibilityIsNewQualityQualification": False},
    "evidence": {str(p.relative_to(repo)): sh(p) for p in
        (repo / "tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-current-native-compatibility").iterdir() if p.is_file()}}
backend["configSha256"] = ev.digest(backend)
output.mkdir()
cq.shared.write_json(output / "backend-config.json", backend)
freeze = {"schemaVersion": 1, "scope": "pre-score-contextual-v5-protocol-freeze",
    "createdAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "baselineHead": "b5400cbadadd29e8ee915a0fb33fb11ec5bebc79",
    "corpusDirectory": str(corpus.relative_to(repo)),
    "corpusFiles": {p.name: sh(p) for p in sorted(corpus.iterdir()) if p.is_file()},
    **cq.v5_binding(), **cq.policy_binding(),
    "sources": {str(p.relative_to(repo)): sh(p) for p in (cq.ENGINE, cq.POLICY, cq.HARNESS, cq.PROBE,
        Path(cq.__file__), cq.HERE / "export_calibration.py", cq.HERE / "score_product_holdout.py",
        cq.HERE.parent / "evaluate.py")},
    "backendConfigSha256": sh(output / "backend-config.json"),
    "backendIdentity": identity,
    "policyVerificationSha256": sh(verification / "verification.json"),
    "freezeScriptSha256": sh(Path(__file__)),
    "modelScoringPerformedBeforeFreeze": False,
    "counts": {"languages": ["en", "ru", "es"], "calibrationPerLanguage": 200,
        "holdoutPerLanguage": 200, "observedBoundaryQuotaPerSplitLanguage": 50},
    "protocol": {"order": ["exact-Kotlin-export", "all-calibration-scores", "config-freeze", "all-holdout-scores", "report"],
        "thresholdSearch": False, "changeThresholdsAfterHoldout": False,
        "excludeRowsAfterScoring": False, "automaticPunctuationApplication": False,
        "errorPolicy": "retain every eligible request error and every excluded corpus row; no retry to select successful results",
        "metrics": ["observed-source-boundary-agreement", "suggestion-coverage", "abstention", "insertion-at-source-spaces", "production-exclusions", "runtime-errors", "missing-responses", "candidate-decision-counts"],
        "grouping": "each language and each observed boundary", "intervals": "Wilson 95 percent row-descriptive",
        "semanticCorrectnessEvaluated": False, "qualityGateEstablished": False,
        "limitations": ["source punctuation is not a unique semantic label", "balanced quotas are not chat prevalence",
            "no question, exclamation or semicolon source strata", "unknown base-model pretraining overlap",
            "related articles may share information", "does not qualify spelling"]}}
freeze["freezeSha256"] = ev.digest(freeze)
cq.shared.write_json(output / "protocol.json", freeze)
print(json.dumps({"protocolSha256": sh(output / "protocol.json"), "backendConfigSha256": sh(output / "backend-config.json"), "corpusManifestSha256": sh(corpus / "manifest.json")}))
