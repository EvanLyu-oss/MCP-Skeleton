from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "testing" / "results"
DOGFOOD_ROOT = RESULTS_DIR / "dogfood-self-check"
BUNDLE_DIR = DOGFOOD_ROOT / "context-bundle"
RESTORE_PARENT = DOGFOOD_ROOT / "restore"
RESTORED_ROOT = RESTORE_PARENT / ROOT.name
SUMMARY_JSON = DOGFOOD_ROOT / "dogfood_self_check.json"
CONFIG_FILE = DOGFOOD_ROOT / ".mcp-skeleton.json"
ONBOARDING_REPORT = DOGFOOD_ROOT / "mcp-skeleton-onboarding.md"

SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache"}
EXCLUDED_PREFIXES = {"testing/results"}


def _run_cli_json(args: list[str], *, output_file: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", "cli", *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )
    output_file.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {proc.returncode}: {' '.join(args)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not emit JSON: {' '.join(args)}") from exc


def _expected_files(source_root: Path) -> list[str]:
    paths: list[str] = []
    for current_root, dirnames, filenames in os.walk(source_root):
        current_path = Path(current_root)
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for filename in sorted(filenames):
            source_path = current_path / filename
            rel_path = source_path.relative_to(source_root).as_posix()
            if any(rel_path == prefix or rel_path.startswith(f"{prefix}/") for prefix in EXCLUDED_PREFIXES):
                continue
            if source_path.is_symlink():
                continue
            paths.append(rel_path)
    return paths


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_dogfood_self_check() -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if DOGFOOD_ROOT.exists():
        shutil.rmtree(DOGFOOD_ROOT)
    DOGFOOD_ROOT.mkdir(parents=True)

    recommend = _run_cli_json(
        [
            "context",
            "config",
            "--recommend",
            "--input-dir",
            str(ROOT),
            "--preset",
            "codebase",
            "--exclude",
            "testing/results/",
            "--output-file",
            str(CONFIG_FILE),
            "--output-report-file",
            str(ONBOARDING_REPORT),
            "--json",
        ],
        output_file=DOGFOOD_ROOT / "config_recommend.json",
    )
    validate = _run_cli_json(
        ["context", "config", "--validate", "--config", str(CONFIG_FILE), "--json"],
        output_file=DOGFOOD_ROOT / "config_validate.json",
    )
    recommended_args = [str(item) for item in (recommend.get("recommended_command_args") or [])]
    recommended_trial = _run_cli_json(
        recommended_args,
        output_file=DOGFOOD_ROOT / "recommended_trial_compress.json",
    ) if recommended_args else {"status": "skipped"}
    bundle = _run_cli_json(
        [
            "context",
            "bundle",
            "--config",
            str(CONFIG_FILE),
            "--input-dir",
            str(ROOT),
            "--output-dir",
            str(BUNDLE_DIR),
            "--json",
        ],
        output_file=DOGFOOD_ROOT / "bundle.json",
    )
    inspect = _run_cli_json(
        ["context", "inspect", "--package-file", str(BUNDLE_DIR / "context_manifest.json"), "--json"],
        output_file=DOGFOOD_ROOT / "inspect.json",
    )
    restore = _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(BUNDLE_DIR / "context_manifest.json"),
            "--output-dir",
            str(RESTORE_PARENT),
            "--json",
        ],
        output_file=DOGFOOD_ROOT / "restore.json",
    )

    expected_files = _expected_files(ROOT)
    missing: list[str] = []
    mismatched: list[str] = []
    for rel_path in expected_files:
        source_path = ROOT / rel_path
        restored_path = RESTORED_ROOT / rel_path
        if not restored_path.exists():
            missing.append(rel_path)
            continue
        if _sha256(source_path) != _sha256(restored_path):
            mismatched.append(rel_path)

    compression = bundle.get("compression") or {}
    source_summary = compression.get("source_summary") or {}
    dogfood_ok = not missing and not mismatched and recommended_trial.get("status") in {"ok", "skipped"}
    payload = {
        "status": "ok" if dogfood_ok else "error",
        "entrypoint": "dogfood-self-check",
        "runner": "python",
        "source_root": str(ROOT),
        "restored_root": str(RESTORED_ROOT),
        "config_recommend_status": recommend.get("status"),
        "config_validate_status": validate.get("status"),
        "recommended_trial_status": recommended_trial.get("status"),
        "bundle_status": bundle.get("status"),
        "inspect_status": inspect.get("status"),
        "restore_status": restore.get("status"),
        "included_file_count": int(source_summary.get("total_files", 0) or 0),
        "expected_file_count": len(expected_files),
        "skeleton_char_count": int(compression.get("skeleton_char_count", 0) or 0),
        "compression_ratio": compression.get("compression_ratio", 0),
        "recommended_focus_mode": (recommend.get("config") or {}).get("focus_mode", ""),
        "recommended_skeleton_density": (recommend.get("config") or {}).get("skeleton_density", ""),
        "recommended_command_arg_count": len(recommended_args),
        "recommended_trial_skeleton_char_count": int(recommended_trial.get("skeleton_char_count", 0) or 0),
        "report_written": bool(recommend.get("report_written")),
        "missing_count": len(missing),
        "mismatched_count": len(mismatched),
        "missing_paths": missing[:40],
        "mismatched_paths": mismatched[:40],
        "artifacts": {
            "config_file": str(CONFIG_FILE),
            "onboarding_report": str(ONBOARDING_REPORT),
            "config_recommend_json": str(DOGFOOD_ROOT / "config_recommend.json"),
            "config_validate_json": str(DOGFOOD_ROOT / "config_validate.json"),
            "recommended_trial_compress_json": str(DOGFOOD_ROOT / "recommended_trial_compress.json"),
            "bundle_json": str(DOGFOOD_ROOT / "bundle.json"),
            "inspect_json": str(DOGFOOD_ROOT / "inspect.json"),
            "restore_json": str(DOGFOOD_ROOT / "restore.json"),
            "summary_json": str(SUMMARY_JSON),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = run_dogfood_self_check()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
