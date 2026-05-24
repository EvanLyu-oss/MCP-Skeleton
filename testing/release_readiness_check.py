from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "testing" / "results"
DEFAULT_RESULTS_JSON = RESULTS_DIR / "release_readiness_check.json"


def _run(args: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["MCP_SKELETON_IGNORE_CWD_CONFIG"] = "1"
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    return {
        "args": args,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "passed": proc.returncode == 0,
    }


def _json_from_stdout(result: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError:
        return {}


def _compact_result(result: dict[str, Any], *, include_stdout_json: bool = True) -> dict[str, Any]:
    compact = {
        "args": result["args"],
        "returncode": result["returncode"],
        "passed": result["passed"],
    }
    if include_stdout_json:
        parsed = _json_from_stdout(result)
        if parsed:
            compact["stdout_json"] = parsed
    if result.get("stderr"):
        compact["stderr_tail"] = str(result["stderr"])[-1200:]
    return compact


def _count_summary(stdout_json: dict[str, Any]) -> str:
    passed = stdout_json.get("passed")
    total = stdout_json.get("check_count") or stdout_json.get("total")
    if isinstance(passed, int) and isinstance(total, int):
        return f"{passed}/{total}"
    return "unknown"


def build_executive_summary(checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    passed_count = sum(1 for item in checks.values() if item.get("passed"))
    failed_count = sum(1 for item in checks.values() if not item.get("passed"))
    python_smoke = checks.get("python_smoke", {}).get("stdout_json") or {}
    quickstart = checks.get("quickstart_check", {}).get("stdout_json") or {}
    dogfood = checks.get("dogfood_self_check", {}).get("stdout_json") or {}
    doctor = checks.get("context_doctor", {}).get("stdout_json") or {}
    benchmark = checks.get("quick_benchmark", {}).get("stdout_json") or {}
    benchmark_summary = benchmark.get("executive_summary") or {}
    expected_files = dogfood.get("expected_file_count")
    included_files = dogfood.get("included_file_count")
    dogfood_files = (
        f"{included_files}/{expected_files}"
        if isinstance(included_files, int) and isinstance(expected_files, int)
        else "unknown"
    )
    restore_check = doctor.get("restore_check") or {}
    status = "ok" if failed_count == 0 else "error"
    blocking = [name for name, item in checks.items() if not item.get("passed")]
    benchmark_status = str(benchmark_summary.get("overall_status") or "unknown")
    scale_health = str(benchmark_summary.get("scale_health") or "unknown")
    if blocking:
        next_action = f"fix failing checks: {', '.join(blocking)}"
    elif benchmark_status in {"watch", "blocked"} or scale_health in {"warn", "fail"}:
        next_action = str(benchmark_summary.get("next_action") or "review benchmark watch items")
    else:
        next_action = "ready for release"
    return {
        "status": status,
        "passed": passed_count,
        "failed": failed_count,
        "python_smoke": _count_summary(python_smoke),
        "quickstart": _count_summary(quickstart),
        "dogfood_restore_status": dogfood.get("restore_status", "unknown"),
        "dogfood_files": dogfood_files,
        "dogfood_missing_count": dogfood.get("missing_count", "unknown"),
        "dogfood_mismatched_count": dogfood.get("mismatched_count", "unknown"),
        "doctor_readiness": doctor.get("readiness_status", "unknown"),
        "doctor_restore_status": restore_check.get("status", "unknown"),
        "benchmark_overall_status": benchmark_summary.get("overall_status", "unknown"),
        "benchmark_release_readiness": benchmark_summary.get("release_readiness", "unknown"),
        "benchmark_scale_health": benchmark_summary.get("scale_health", "unknown"),
        "benchmark_restore_verified": benchmark_summary.get("restore_verified", "unknown"),
        "best_large_directory_savings_percent": benchmark_summary.get("best_large_directory_savings_percent", "unknown"),
        "best_long_text_savings_percent": benchmark_summary.get("best_long_text_savings_percent", "unknown"),
        "blocking_checks": blocking,
        "next_action": next_action,
    }


def build_release_readiness_payload() -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    py_compile = _run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(ROOT / "cli" / "ail_cli.py"),
            str(ROOT / "cli" / "context_compression.py"),
            str(ROOT / "testing" / "context_scale_benchmark.py"),
            str(ROOT / "testing" / "run_cli_checks.py"),
            str(ROOT / "testing" / "quickstart_check.py"),
            str(ROOT / "testing" / "dogfood_self_check.py"),
            str(ROOT / "testing" / "release_readiness_check.py"),
        ]
    )
    python_smoke = _run([sys.executable, str(ROOT / "testing" / "run_cli_checks.py")])
    quickstart = _run([sys.executable, str(ROOT / "testing" / "quickstart_check.py")])
    dogfood = _run([sys.executable, str(ROOT / "testing" / "dogfood_self_check.py")])
    doctor = _run(
        [
            sys.executable,
            "-m",
            "cli",
            "context",
            "doctor",
            "--input-dir",
            str(ROOT),
            "--preset",
            "codebase",
            "--exclude",
            "testing/results/",
            "--exclude",
            ".mcp-skeleton.json",
            "--exclude",
            ".mcp-skeleton.yaml",
            "--exclude",
            ".mcp-skeleton.yml",
            "--exclude",
            "mcp-skeleton-onboarding.md",
            "--exclude",
            ".workspace_ail/",
            "--json",
        ]
    )
    benchmark_json = RESULTS_DIR / "release_quick_benchmark.json"
    benchmark_md = RESULTS_DIR / "release_quick_benchmark.md"
    baseline_json = RESULTS_DIR / "release_quick_baseline.json"
    quick_benchmark = _run(
        [
            sys.executable,
            str(ROOT / "testing" / "context_scale_benchmark.py"),
            "--scale-profile",
            "quick",
            "--output-json",
            str(benchmark_json),
            "--output-md",
            str(benchmark_md),
            "--save-baseline-json",
            str(baseline_json),
        ]
    )
    bash_available = shutil.which("bash") is not None
    bash_smoke = _run(["bash", str(ROOT / "testing" / "run_cli_checks.sh")]) if bash_available else {
        "args": ["bash", str(ROOT / "testing" / "run_cli_checks.sh")],
        "returncode": 0,
        "stdout": json.dumps({"status": "skipped", "reason": "bash not available"}),
        "stderr": "",
        "passed": True,
    }

    checks = {
        "py_compile": _compact_result(py_compile, include_stdout_json=False),
        "python_smoke": _compact_result(python_smoke),
        "quickstart_check": _compact_result(quickstart),
        "dogfood_self_check": _compact_result(dogfood),
        "context_doctor": _compact_result(doctor),
        "quick_benchmark": _compact_result(quick_benchmark),
        "bash_smoke": _compact_result(bash_smoke),
    }
    passed = all(item["passed"] for item in checks.values())
    executive_summary = build_executive_summary(checks)
    payload = {
        "status": "ok" if passed else "error",
        "entrypoint": "release-readiness-check",
        "runner": "python",
        "platform": sys.platform,
        "check_count": len(checks),
        "passed": sum(1 for item in checks.values() if item["passed"]),
        "failed": sum(1 for item in checks.values() if not item["passed"]),
        "executive_summary": executive_summary,
        "checks": checks,
        "artifacts": {
            "results_json": str(DEFAULT_RESULTS_JSON),
            "benchmark_json": str(benchmark_json),
            "benchmark_md": str(benchmark_md),
            "baseline_json": str(baseline_json),
        },
    }
    DEFAULT_RESULTS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = build_release_readiness_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
