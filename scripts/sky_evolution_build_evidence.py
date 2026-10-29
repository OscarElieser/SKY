"""Generate a truthful, metadata-only CI evidence record for SKY Core.

Never upload raw test logs, environment variables, tokens or user conversations.
A build must be marked failed unless both compilation and unit tests passed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "neural_core/sky_adaptive_policy.py",
    "neural_core/sky_cognition.py",
    "metaverse/sky_cognition_api.py",
    "tests/test_sky_adaptive_policy.py",
)


def build_manifest(compile_exit: int, test_exit: int, test_log: str) -> dict:
    if compile_exit < 0 or test_exit < 0:
        raise ValueError("Invalid status codes")
    # Only parse local CI output. Never embed raw output in public artifacts.
    match = re.search(r"^Ran (\d+) tests? in [\d.]+s$", test_log, re.M)
    count = int(match.group(1)) if match else 0
    passed = compile_exit == 0 and test_exit == 0 and count >= 9 and "\nOK" in test_log
    hashes = {}
    for name in SOURCES:
        path = PROJECT_ROOT / name
        if not path.is_file():
            raise FileNotFoundError(name)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    # Do not construct a link for arbitrary env strings; GitHub workflow injects these.
    url = (f"https://github.com/{repo}/actions/runs/{run_id}"
           if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
           and re.fullmatch(r"\d+", run_id) else None)
    return {
        "schema": "sky-ci-evidence-v1",
        "scope": "SKY native adaptive core: Python compile and nine unit tests",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repository": repo,
        "commit_sha": sha,
        "ref": os.environ.get("GITHUB_REF", ""),
        "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "run_id": run_id,
        "run_url": url,
        "python": platform.python_version(),
        "source_sha256": hashes,
        "compile_exit_code": compile_exit,
        "test_exit_code": test_exit,
        "tests_count": count,
        "result": "passed" if passed else "failed",
        "device_tested": False,
        "external_llm_tested": False,
        "signature": "none_github_actions_run_metadata_only",
        "notice": "Artifact provenance is linked to GitHub Actions. This record does not certify phone execution or other modules.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile-exit", type=int, required=True)
    parser.add_argument("--test-exit", type=int, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Read only generated local test logs, with hard input bound.
    if args.test_log.stat().st_size > 1_000_000:
        raise ValueError("Oversized test log")
    log = args.test_log.read_text(encoding="utf-8", errors="replace")
    evidence = build_manifest(args.compile_exit, args.test_exit, log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": evidence["schema"],
        "result": evidence["result"],
        "tests_count": evidence["tests_count"],
        "run_url": evidence["run_url"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
