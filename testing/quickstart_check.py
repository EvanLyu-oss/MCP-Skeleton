from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "testing" / "results"
DEFAULT_RESULTS_JSON = RESULTS_DIR / "quickstart_check.json"


def _python310_plus() -> str:
    candidates = [sys.executable, "python3.12", "python3.11", "python3.10", "python3"]
    for candidate in candidates:
        try:
            proc = subprocess.run(
                [
                    candidate,
                    "-c",
                    "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)",
                ],
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            continue
        if proc.returncode == 0:
            return candidate
    raise RuntimeError("Python 3.10+ is required for quickstart checks")


def _run(args: list[str], *, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=str(cwd), env=env, text=True, capture_output=True)
    return {
        "args": args,
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout": proc.stdout,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def _json_from_command(args: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = _run(args, cwd=cwd, env=env)
    try:
        parsed = json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError:
        parsed = {}
    result.pop("stdout", None)
    return result, parsed


def build_quickstart_check_payload() -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mcp_skeleton_quickstart.") as tmp:
        workspace = Path(tmp)
        home = workspace / "home"
        project = workspace / "project"
        home.mkdir()
        (project / "src").mkdir(parents=True)
        (project / "src" / "app.py").write_text(
            "def run() -> str:\n"
            "    return 'quickstart-ready'\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["MCP_SKELETON_HOME"] = str(home / ".mcp-skeleton")
        env["PYTHON"] = _python310_plus()
        env["PYTHONPATH"] = str(ROOT)
        env["MCP_SKELETON_IGNORE_CWD_CONFIG"] = "1"
        env["PATH"] = f"{home / '.local' / 'bin'}{os.pathsep}{env.get('PATH', '')}"

        command_path = home / ".local" / "bin" / "mcp-skeleton"
        install = _run(["sh", str(ROOT / "install.sh")], cwd=ROOT, env=env)
        install.pop("stdout", None)
        demo, demo_json = _json_from_command(
            [str(command_path), "demo", "--output-dir", str(workspace / "demo"), "--json"],
            cwd=project,
            env=env,
        )
        quick, quick_json = _json_from_command(
            [str(command_path), "quick", "--input-dir", str(project), "--output-dir", str(workspace / "bundle"), "--json"],
            cwd=project,
            env=env,
        )
        reuse, reuse_json = _json_from_command(
            [
                str(command_path),
                "quick",
                "--reuse-if-fresh",
                "--input-dir",
                str(project),
                "--output-dir",
                str(workspace / "bundle"),
                "--json",
            ],
            cwd=project,
            env=env,
        )

        install_passed = bool(install["passed"] and command_path.exists() and "MCP-Skeleton Install Ready" in install["stdout_tail"])
        demo_passed = bool(demo["passed"] and demo_json.get("demo_status") == "ready" and (demo_json.get("quick") or {}).get("restore_safe"))
        quick_passed = bool(
            quick["passed"]
            and quick_json.get("quick_status") == "ready"
            and quick_json.get("restore_safe")
            and Path(str(quick_json.get("manifest_file") or "")).exists()
        )
        reuse_passed = bool(
            reuse["passed"]
            and reuse_json.get("reuse_status") == "reused"
            and reuse_json.get("freshness_status") == "fresh"
        )
        checks = {
            "install_sh": {
                **install,
                "passed": install_passed,
                "command_exists": command_path.exists(),
                "has_ready_panel": "MCP-Skeleton Install Ready" in install["stdout_tail"],
            },
            "mcp_skeleton_demo": {
                **demo,
                "passed": demo_passed,
                "demo_status": demo_json.get("demo_status", ""),
                "restore_safe": bool((demo_json.get("quick") or {}).get("restore_safe")),
            },
            "mcp_skeleton_quick": {
                **quick,
                "passed": quick_passed,
                "quick_status": quick_json.get("quick_status", ""),
                "restore_safe": bool(quick_json.get("restore_safe")),
                "manifest_exists": Path(str(quick_json.get("manifest_file") or "")).exists(),
            },
            "mcp_skeleton_quick_reuse_if_fresh": {
                **reuse,
                "passed": reuse_passed,
                "quick_status": reuse_json.get("quick_status", ""),
                "reuse_status": reuse_json.get("reuse_status", ""),
                "freshness_status": reuse_json.get("freshness_status", ""),
            },
        }

    passed = all(bool(item.get("passed")) for item in checks.values())
    payload = {
        "status": "ok" if passed else "error",
        "entrypoint": "quickstart-check",
        "runner": "python",
        "platform": sys.platform,
        "check_count": len(checks),
        "passed": sum(1 for item in checks.values() if item.get("passed")),
        "failed": sum(1 for item in checks.values() if not item.get("passed")),
        "checks": checks,
        "artifacts": {"results_json": str(DEFAULT_RESULTS_JSON)},
    }
    DEFAULT_RESULTS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = build_quickstart_check_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
