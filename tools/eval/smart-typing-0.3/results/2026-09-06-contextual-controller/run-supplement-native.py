import hashlib, json, pathlib, subprocess, sys
run = pathlib.Path(sys.argv[1]).resolve(strict=True)
hash_file = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
command = json.loads((run / "command.json").read_text())
receipt = json.loads((run / "run-input.json").read_text())
identity = json.loads((run / "identity.json").read_text())
assert not (run / "execution.json").exists()
assert not (run / "complete.json").exists()
assert hash_file(command["argv"][0]) == identity["backendIdentity"]["runnerSha256"]
assert hash_file(command["argv"][1]) == identity["backendIdentity"]["modelSha256"]
assert all(hash_file(run / name) == value for name, value in receipt["files"].items())
exit_code = -1
with open(command["stdin"], "rb") as source, open(command["stdout"], "xb") as output, open(command["stderr"], "xb") as errors:
    try:
        exit_code = subprocess.run(command["argv"], cwd=command["cwd"], stdin=source,
                                   stdout=output, stderr=errors, timeout=900, check=False).returncode
    finally:
        output.flush(); errors.flush()
        evidence = {"schemaVersion": 1, "attempts": 1, "exitCode": exit_code,
                    "commandSha256": hash_file(run / "command.json"),
                    "runInputSha256": hash_file(run / "run-input.json"),
                    "requestsSha256": hash_file(run / "requests.jsonl"),
                    "responsesSha256": hash_file(run / "responses.jsonl"),
                    "stderrSha256": hash_file(run / "stderr.log")}
        with (run / "execution.json").open("x") as stream:
            json.dump(evidence, stream, sort_keys=True, indent=2); stream.write("\n")
if exit_code != 0:
    raise SystemExit("Native attempt failed; preserve this run without retrying")
