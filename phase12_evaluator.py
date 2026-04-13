#!/usr/bin/env python3
"""Evaluate this repository against Phase 1 and Phase 2 requirements.

Usage:
  python phase12_evaluator.py
  python phase12_evaluator.py --skip-docker
"""

from __future__ import annotations

import argparse
import importlib
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml


ROOT = Path(__file__).resolve().parent
INFERENCE = ROOT / "inference.py"
OPENENV_YAML = ROOT / "openenv.yaml"
DOCKERFILE = ROOT / "Dockerfile"

START_RE = re.compile(r"^\[START\] task=\S+ env=\S+ model=\S+$")
STEP_RE = re.compile(
    r"^\[STEP\] step=\d+ action=\S+ reward=-?\d+\.\d{2} done=(true|false) error=(null|.*)$"
)
END_RE = re.compile(
    r"^\[END\] success=(true|false) steps=\d+ score=-?\d+\.\d{2} rewards=(-?\d+\.\d{2})(,-?\d+\.\d{2})*$"
)


@dataclass
class CheckResult:
    ok: bool
    details: str = ""
    fix: str = ""


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _http_call(method: str, url: str, payload: str | None = None) -> tuple[int, str]:
    data = payload.encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=12) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def check_openenv_reset_post() -> CheckResult:
    server = subprocess.Popen(
        [sys.executable, "-m", "src.app"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base = "http://127.0.0.1:7860"
        for _ in range(12):
            code, _ = _http_call("GET", f"{base}/health")
            if code == 200:
                break
            time.sleep(1)

        code, body = _http_call("POST", f"{base}/reset", '{"task_id":"easy-memory-leak"}')
        if code == 200:
            return CheckResult(True)
        return CheckResult(False, f"POST /reset returned {code}: {body[:200]}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:
            server.kill()


def check_openenv_validate() -> CheckResult:
    proc = _run([sys.executable, "-m", "openenv.cli", "validate"], timeout=180)
    if proc.returncode == 0:
        return CheckResult(True)
    return CheckResult(False, (proc.stderr or proc.stdout).strip()[:400])


def check_docker_build() -> CheckResult:
    proc = _run(["docker", "build", "-t", "cloudscalerenv-phase12-eval", "."], timeout=600)
    if proc.returncode == 0:
        return CheckResult(True)
    return CheckResult(False, (proc.stderr or proc.stdout).strip()[-600:])


def check_inference_execution() -> tuple[CheckResult, list[str]]:
    env = os.environ.copy()
    env.setdefault("HF_TOKEN", "dummy-token")
    env.setdefault("API_BASE_URL", "http://127.0.0.1:1/v1")
    env.setdefault("MODEL_NAME", "test-model")
    env.setdefault("TASK_NAME", "easy-memory-leak")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(
        [sys.executable, "inference.py"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if len(lines) >= 2:
        return CheckResult(True), lines
    return CheckResult(False, "inference.py produced insufficient stdout lines"), lines


def check_output_parsing(lines: list[str]) -> CheckResult:
    if not lines:
        return CheckResult(False, "No output lines found")
    if not START_RE.match(lines[0]):
        return CheckResult(False, f"Invalid START line: {lines[0]}")
    if not END_RE.match(lines[-1]):
        return CheckResult(False, f"Invalid END line: {lines[-1]}")
    for line in lines[1:-1]:
        if not STEP_RE.match(line):
            return CheckResult(False, f"Invalid STEP line: {line}")
    return CheckResult(True)


def _grader_ok(value: Any) -> bool:
    if isinstance(value, (float, int)):
        return 0.0 <= float(value) <= 1.0
    if isinstance(value, dict) and "reward" in value:
        try:
            reward = float(value["reward"])
        except Exception:
            return False
        return 0.0 <= reward <= 1.0
    return False


def check_task_validation() -> CheckResult:
    if not OPENENV_YAML.exists():
        return CheckResult(False, "openenv.yaml not found")

    try:
        manifest = yaml.safe_load(OPENENV_YAML.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult(False, f"openenv.yaml parse error: {exc}")

    tasks = manifest.get("tasks", []) if isinstance(manifest, dict) else []
    valid = 0
    failures: list[str] = []

    for task in tasks:
        task_id = task.get("id") or task.get("task_id") or "unknown"
        ep = task.get("grader") or task.get("grader_entrypoint") or task.get("grader_fn")
        if not ep or ":" not in ep:
            failures.append(f"{task_id}: missing grader entrypoint")
            continue
        mod_name, fn_name = ep.split(":", 1)
        try:
            mod = importlib.import_module(mod_name)
            grader = getattr(mod, fn_name)
            value = grader(None)
            if _grader_ok(value):
                valid += 1
            else:
                failures.append(f"{task_id}: grader return out of range or invalid ({value})")
        except Exception as exc:
            failures.append(f"{task_id}: grader import/call failed ({exc})")

    if valid >= 3:
        return CheckResult(True)
    msg = "Not enough tasks with graders"
    if failures:
        msg += " | " + "; ".join(failures[:3])
    return CheckResult(False, msg, "Add or fix grader entrypoints so at least 3 tasks are callable and return 0.0-1.0 scores.")


def check_llm_criteria() -> CheckResult:
    if not INFERENCE.exists():
        return CheckResult(False, "inference.py missing")
    text = INFERENCE.read_text(encoding="utf-8")

    issues: list[str] = []
    if "from openai import OpenAI" not in text:
        issues.append("missing OpenAI client import")
    if not re.search(r'API_BASE_URL\s*=\s*os\.getenv\(\s*"API_BASE_URL"\s*,', text):
        issues.append("API_BASE_URL default missing")
    if not re.search(r'MODEL_NAME\s*=\s*os\.getenv\(\s*"MODEL_NAME"\s*,', text):
        issues.append("MODEL_NAME default missing")
    if 'HF_TOKEN = os.getenv("HF_TOKEN")' not in text:
        issues.append("HF_TOKEN read missing")

    if issues:
        return CheckResult(False, "; ".join(issues))
    return CheckResult(True)


def _print_check(name: str, result: CheckResult) -> None:
    prefix = "✓" if result.ok else "✗"
    print(f"{prefix}\n{name}")
    if not result.ok and result.details:
        print("Error details")
        print(result.details)
        print("Why it failed")
        print(f"{name} check did not satisfy the required criteria.")
        if result.fix:
            print("How to fix")
            print(f"1.\n{result.fix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1/2 evaluator for this repository")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker build check")
    args = parser.parse_args()

    print("phase 1 requirements")
    p1_reset = check_openenv_reset_post()
    p1_dockerfile = CheckResult(DOCKERFILE.exists(), "Dockerfile at repo root not found")
    p1_inference = CheckResult(INFERENCE.exists(), "inference.py at repo root not found")
    p1_validate = check_openenv_validate()

    _print_check("OpenEnv Reset (POST OK)", p1_reset)
    _print_check("Dockerfile at repo root", p1_dockerfile)
    _print_check("inference.py at repo root", p1_inference)
    _print_check("openenv validate", p1_validate)

    print("phase 2 requirements")
    p2_docker = CheckResult(True)
    if not args.skip_docker:
        p2_docker = check_docker_build()
    p2_infer_exec, infer_lines = check_inference_execution()
    p2_output = check_output_parsing(infer_lines)
    p2_tasks = check_task_validation()
    p2_llm = check_llm_criteria()

    _print_check("Docker Build Creation", p2_docker)
    _print_check("inference.py Execution", p2_infer_exec)
    _print_check("Output Parsing", p2_output)
    _print_check("Task Validation", p2_tasks)
    _print_check("LLM Criteria Check", p2_llm)

    all_results = [
        p1_reset,
        p1_dockerfile,
        p1_inference,
        p1_validate,
        p2_docker,
        p2_infer_exec,
        p2_output,
        p2_tasks,
        p2_llm,
    ]

    ok = all(r.ok for r in all_results)
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
