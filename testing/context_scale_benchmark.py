from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cli.context_compression import _decode_restore_blob

DEFAULT_JSON = REPO_ROOT / "testing" / "results" / "context_scale_benchmark.json"
DEFAULT_MD = REPO_ROOT / "testing" / "results" / "context_scale_benchmark.md"
DEFAULT_TEXT_TARGETS = [20_000, 100_000, 400_000]
QUICK_TEXT_TARGETS = [12_000, 40_000]
DEFAULT_TOKENIZER_MODEL = "cl100k_base"
DEFAULT_DIRECTORY_FOCUS_MODES = ["full", "tree", "imports", "symbols"]
DEFAULT_TEXT_FOCUS_MODES = ["full", "writing-outline"]
DEFAULT_SKELETON_DENSITIES = ["adaptive", "standard", "compact"]
DEFAULT_SCALE_HEALTH_THRESHOLDS = {
    "monorepo_min_files": 100,
    "monorepo_max_token_ratio": 0.75,
    "realistic_directory_max_token_ratio": 0.25,
}
DEFAULT_REAL_TEXT_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTEXT_COMPRESSION_PRINCIPLES_20260507.md",
    REPO_ROOT / "CONTEXT_COMPRESSION_SPEC_20260428.md",
    REPO_ROOT / "CHANGELOG.md",
]


@dataclass
class CommandResult:
    payload: dict[str, Any]
    elapsed_ms: float
    stdout: str
    stderr: str
    command: list[str]


def _run_cli_json(args: list[str], *, cwd: Path) -> CommandResult:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "cli", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command did not emit valid JSON: {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        ) from exc
    return CommandResult(payload=payload, elapsed_ms=elapsed_ms, stdout=proc.stdout, stderr=proc.stderr, command=args)


def _sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_directory(root: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*")):
        rel = item.relative_to(root).as_posix()
        if item.is_dir():
            digest.update(f"dir:{rel}\n".encode("utf-8"))
            continue
        digest.update(f"file:{rel}\n".encode("utf-8"))
        digest.update(item.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _directory_snapshot_from_fs(root: Path) -> dict[str, Any]:
    return _directory_snapshot_from_fs_ignoring(root, ignored_rel_paths=set())


def _directory_snapshot_from_fs_ignoring(root: Path, *, ignored_rel_paths: set[str]) -> dict[str, Any]:
    files: dict[str, str] = {}
    symlinks: dict[str, str] = {}
    empty_dirs: set[str] = set()
    root = root.resolve()
    for current_root, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames.sort()
        filenames.sort()
        current_path = Path(current_root)
        rel_dir = "." if current_path == root else current_path.relative_to(root).as_posix()
        if not dirnames and not filenames and rel_dir != ".":
            empty_dirs.add(rel_dir)
        for filename in filenames:
            item_path = current_path / filename
            rel_path = item_path.relative_to(root).as_posix()
            if rel_path in ignored_rel_paths:
                continue
            if item_path.is_symlink():
                symlinks[rel_path] = os.readlink(item_path)
            else:
                files[rel_path] = hashlib.sha256(item_path.read_bytes()).hexdigest()
    return {
        "files": files,
        "symlinks": symlinks,
        "empty_dirs": sorted(empty_dirs),
    }


def _directory_snapshot_from_restore_package(restore_package: dict[str, Any]) -> dict[str, Any]:
    decoded = _decode_restore_blob(restore_package or {})
    if str(decoded.get("mode") or "") not in {"directory", "directory_incremental"}:
        raise ValueError("restore package is not a directory bundle")
    files: dict[str, str] = {}
    for item in decoded.get("files") or []:
        rel_path = str(item.get("relative_path") or "")
        files[rel_path] = str(item.get("sha256") or hashlib.sha256(base64.b64decode(str(item.get("content_b64") or "").encode("ascii"))).hexdigest())
    symlinks = {
        str(item.get("relative_path") or ""): str(item.get("link_target") or "")
        for item in decoded.get("symlinks") or []
    }
    empty_dirs = sorted(str(item) for item in (decoded.get("empty_dirs") or []))
    return {
        "files": files,
        "symlinks": symlinks,
        "empty_dirs": empty_dirs,
        "removed_paths": sorted(str(item) for item in (decoded.get("removed_paths") or [])),
    }


def _compare_directory_snapshots(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected_files = expected["files"]
    actual_files = actual["files"]
    expected_symlinks = expected["symlinks"]
    actual_symlinks = actual["symlinks"]
    expected_empty_dirs = set(expected["empty_dirs"])
    actual_empty_dirs = set(actual["empty_dirs"])

    missing_files = sorted(path for path in expected_files if path not in actual_files)
    extra_files = sorted(path for path in actual_files if path not in expected_files)
    content_mismatches = sorted(
        path for path in expected_files if path in actual_files and expected_files[path] != actual_files[path]
    )
    missing_symlinks = sorted(path for path in expected_symlinks if path not in actual_symlinks)
    extra_symlinks = sorted(path for path in actual_symlinks if path not in expected_symlinks)
    symlink_target_mismatches = sorted(
        path for path in expected_symlinks if path in actual_symlinks and expected_symlinks[path] != actual_symlinks[path]
    )
    missing_empty_dirs = sorted(path for path in expected_empty_dirs if path not in actual_empty_dirs)
    extra_empty_dirs = sorted(path for path in actual_empty_dirs if path not in expected_empty_dirs)

    ok = not any(
        [
            missing_files,
            extra_files,
            content_mismatches,
            missing_symlinks,
            extra_symlinks,
            symlink_target_mismatches,
            missing_empty_dirs,
            extra_empty_dirs,
        ]
    )
    return {
        "ok": ok,
        "expected_file_count": len(expected_files),
        "actual_file_count": len(actual_files),
        "expected_symlink_count": len(expected_symlinks),
        "actual_symlink_count": len(actual_symlinks),
        "expected_empty_dir_count": len(expected_empty_dirs),
        "actual_empty_dir_count": len(actual_empty_dirs),
        "missing_files": missing_files,
        "extra_files": extra_files,
        "content_mismatches": content_mismatches,
        "missing_symlinks": missing_symlinks,
        "extra_symlinks": extra_symlinks,
        "symlink_target_mismatches": symlink_target_mismatches,
        "missing_empty_dirs": missing_empty_dirs,
        "extra_empty_dirs": extra_empty_dirs,
        "mismatch_preview": (
            missing_files
            or extra_files
            or content_mismatches
            or missing_symlinks
            or extra_symlinks
            or symlink_target_mismatches
            or missing_empty_dirs
            or extra_empty_dirs
        )[:10],
    }


def _build_long_text(target_chars: int) -> str:
    chapter = textwrap.dedent(
        """
        # Chapter {idx}: Compression Continuity

        This chapter explains how structured context compression preserves business logic, route continuity,
        editorial intent, component relationships, and exact restore guarantees while reducing raw prompt weight.

        ## Core Questions

        - Which structural markers should remain visible to downstream AI tools?
        - How should token pressure be reduced without pretending the source no longer exists?
        - Where should review operators inspect drift, patch surfaces, and replay risk before committing edits?

        ## Notes

        Teams working with longer books, larger repositories, and broader delivery systems need both an AI-facing
        skeleton and an exact machine-facing restore package. This section repeats the same deep-context requirement
        with slight variations so the benchmark can measure how skeleton overhead changes as the source grows.

        """
    ).strip()
    parts: list[str] = []
    idx = 1
    while len("\n\n".join(parts)) < target_chars:
        parts.append(chapter.format(idx=idx))
        idx += 1
    return "\n\n".join(parts)


def _build_realistic_text_fixture(
    output_path: Path,
    *,
    source_files: list[Path],
) -> dict[str, Any]:
    sections: list[str] = [
        "# MCP-Skeleton Realistic Corpus",
        "",
        "This corpus is assembled from repository documents so the benchmark can measure behavior on a more realistic long-form handoff surface.",
        "",
    ]
    included_sources: list[str] = []
    for source in source_files:
        source = source.expanduser().resolve()
        if not source.exists():
            continue
        included_sources.append(str(source))
        sections.extend(
            [
                f"## Source: {source.name}",
                "",
                source.read_text(encoding="utf-8"),
                "",
            ]
        )
    output_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")
    return {
        "path": str(output_path),
        "source_files": included_sources,
        "source_file_count": len(included_sources),
        "char_count": output_path.stat().st_size,
    }


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _maybe_import_tiktoken() -> bool:
    try:
        __import__("tiktoken")
    except Exception:
        return False
    return True


def _build_backends(explicit_backends: list[str] | None, *, include_tiktoken: bool) -> list[str]:
    if explicit_backends:
        return explicit_backends
    backends = ["heuristic", "auto"]
    if include_tiktoken and _maybe_import_tiktoken():
        backends.append("tiktoken")
    return backends


def _summarize_case(case: dict[str, Any]) -> dict[str, Any]:
    metrics = case["compress"]["metrics"]
    restore_details = case.get("restore_details") or {}
    return {
        "label": case["label"],
        "backend": case["backend"],
        "kind": case.get("kind", ""),
        "sample_type": case.get("sample_type", "synthetic"),
        "source_path": case.get("source_path", ""),
        "focus_mode": case.get("compress", {}).get("focus_mode", "full"),
        "skeleton_density": case.get("compress", {}).get("skeleton_density", "adaptive"),
        "source_chars": metrics["source_char_count"],
        "skeleton_chars": metrics["skeleton_char_count"],
        "estimated_source_tokens": metrics["estimated_token_count_source"],
        "estimated_skeleton_tokens": metrics["estimated_token_count_skeleton"],
        "estimated_tokens_saved": metrics["estimated_tokens_saved"],
        "token_ratio": metrics["estimated_token_reduction_ratio"],
        "token_backend": metrics["token_estimate_backend"],
        "compress_ms_avg": round(statistics.mean(case["timings_ms"]["compress"]), 2),
        "inspect_ms_avg": round(statistics.mean(case["timings_ms"]["inspect"]), 2),
        "restore_ms_avg": round(statistics.mean(case["timings_ms"]["restore"]), 2),
        "restore_verified": case["restore_verified"],
        "restore_mismatch_preview": restore_details.get("mismatch_preview") or [],
        "change_surface_count": case.get("compress", {}).get("incremental_path_count", 0),
    }


def _build_focus_comparison(
    cases: list[dict[str, Any]],
    *,
    expected_kind: str,
) -> list[dict[str, Any]]:
    summaries = [_summarize_case(case) for case in cases if case.get("kind") == expected_kind]
    baseline_by_backend = {
        (item["backend"], item.get("source_path", ""), item.get("sample_type", "")): item
        for item in summaries
        if item.get("focus_mode") == "full"
    }
    comparisons: list[dict[str, Any]] = []
    for item in summaries:
        focus_mode = item.get("focus_mode", "full")
        if focus_mode == "full":
            continue
        baseline = baseline_by_backend.get((item["backend"], item.get("source_path", ""), item.get("sample_type", "")))
        if baseline is None:
            continue
        full_skeleton_tokens = int(baseline["estimated_skeleton_tokens"])
        focused_skeleton_tokens = int(item["estimated_skeleton_tokens"])
        full_skeleton_chars = int(baseline["skeleton_chars"])
        focused_skeleton_chars = int(item["skeleton_chars"])
        comparisons.append(
            {
                "label": item["label"],
                "backend": item["backend"],
                "kind": expected_kind,
                "sample_type": item.get("sample_type", ""),
                "focus_mode": focus_mode,
                "full_skeleton_chars": full_skeleton_chars,
                "focused_skeleton_chars": focused_skeleton_chars,
                "skeleton_char_size_ratio": round(
                    focused_skeleton_chars / full_skeleton_chars, 4
                ) if full_skeleton_chars else 0.0,
                "full_skeleton_tokens": full_skeleton_tokens,
                "focused_skeleton_tokens": focused_skeleton_tokens,
                "skeleton_token_size_ratio": round(
                    focused_skeleton_tokens / full_skeleton_tokens, 4
                ) if full_skeleton_tokens else 0.0,
                "full_compress_ms_avg": baseline["compress_ms_avg"],
                "focused_compress_ms_avg": item["compress_ms_avg"],
                "compress_time_ratio": round(
                    item["compress_ms_avg"] / baseline["compress_ms_avg"], 4
                ) if baseline["compress_ms_avg"] else 0.0,
            }
        )
    return comparisons


def _build_density_comparison(
    cases: list[dict[str, Any]],
    *,
    expected_kind: str,
) -> list[dict[str, Any]]:
    summaries = [_summarize_case(case) for case in cases if case.get("kind") == expected_kind]
    baseline_by_backend = {
        (item["backend"], item.get("source_path", ""), item.get("sample_type", "")): item
        for item in summaries
        if item.get("skeleton_density") == "standard"
    }
    comparisons: list[dict[str, Any]] = []
    for item in summaries:
        density = item.get("skeleton_density", "adaptive")
        if density == "standard":
            continue
        baseline = baseline_by_backend.get((item["backend"], item.get("source_path", ""), item.get("sample_type", "")))
        if baseline is None:
            continue
        baseline_skeleton_tokens = int(baseline["estimated_skeleton_tokens"])
        density_skeleton_tokens = int(item["estimated_skeleton_tokens"])
        baseline_skeleton_chars = int(baseline["skeleton_chars"])
        density_skeleton_chars = int(item["skeleton_chars"])
        comparisons.append(
            {
                "label": item["label"],
                "backend": item["backend"],
                "kind": expected_kind,
                "sample_type": item.get("sample_type", ""),
                "skeleton_density": density,
                "baseline_skeleton_chars": baseline_skeleton_chars,
                "density_skeleton_chars": density_skeleton_chars,
                "skeleton_char_size_ratio": round(
                    density_skeleton_chars / baseline_skeleton_chars, 4
                ) if baseline_skeleton_chars else 0.0,
                "baseline_skeleton_tokens": baseline_skeleton_tokens,
                "density_skeleton_tokens": density_skeleton_tokens,
                "skeleton_token_size_ratio": round(
                    density_skeleton_tokens / baseline_skeleton_tokens, 4
                ) if baseline_skeleton_tokens else 0.0,
                "baseline_compress_ms_avg": baseline["compress_ms_avg"],
                "density_compress_ms_avg": item["compress_ms_avg"],
                "compress_time_ratio": round(
                    item["compress_ms_avg"] / baseline["compress_ms_avg"], 4
                ) if baseline["compress_ms_avg"] else 0.0,
            }
        )
    return comparisons


def _build_incremental_comparison(
    full_cases: list[dict[str, Any]],
    incremental_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    full_by_backend = {case["backend"]: _summarize_case(case) for case in full_cases}
    incremental_by_backend = {case["backend"]: _summarize_case(case) for case in incremental_cases}
    comparisons: list[dict[str, Any]] = []
    for backend in sorted(set(full_by_backend) & set(incremental_by_backend)):
        full_summary = full_by_backend[backend]
        incremental_summary = incremental_by_backend[backend]
        full_source_tokens = int(full_summary["estimated_source_tokens"])
        incremental_source_tokens = int(incremental_summary["estimated_source_tokens"])
        full_skeleton_tokens = int(full_summary["estimated_skeleton_tokens"])
        incremental_skeleton_tokens = int(incremental_summary["estimated_skeleton_tokens"])
        comparisons.append(
            {
                "backend": backend,
                "token_backend": incremental_summary["token_backend"],
                "change_surface_count": incremental_summary["change_surface_count"],
                "full_source_tokens": full_source_tokens,
                "incremental_source_tokens": incremental_source_tokens,
                "source_token_size_ratio": round(
                    incremental_source_tokens / full_source_tokens, 4
                ) if full_source_tokens else 0.0,
                "full_skeleton_tokens": full_skeleton_tokens,
                "incremental_skeleton_tokens": incremental_skeleton_tokens,
                "skeleton_token_size_ratio": round(
                    incremental_skeleton_tokens / full_skeleton_tokens, 4
                ) if full_skeleton_tokens else 0.0,
                "full_compress_ms_avg": full_summary["compress_ms_avg"],
                "incremental_compress_ms_avg": incremental_summary["compress_ms_avg"],
                "compress_time_ratio": round(
                    incremental_summary["compress_ms_avg"] / full_summary["compress_ms_avg"], 4
                ) if full_summary["compress_ms_avg"] else 0.0,
                "full_restore_ms_avg": full_summary["restore_ms_avg"],
                "incremental_restore_ms_avg": incremental_summary["restore_ms_avg"],
                "restore_time_ratio": round(
                    incremental_summary["restore_ms_avg"] / full_summary["restore_ms_avg"], 4
                ) if full_summary["restore_ms_avg"] else 0.0,
            }
        )
    return comparisons


def _max_token_ratio(summaries: list[dict[str, Any]]) -> float:
    ratios = [float(item["token_ratio"]) for item in summaries if item.get("token_ratio") is not None]
    if not ratios:
        return 0.0
    return round(max(ratios), 4)


def _build_scale_health(
    *,
    monorepo_cases: list[dict[str, Any]],
    realistic_directory_cases: list[dict[str, Any]],
    monorepo_fixture: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    monorepo_summaries = [_summarize_case(case) for case in monorepo_cases]
    realistic_summaries = [_summarize_case(case) for case in realistic_directory_cases]
    monorepo_max_ratio = _max_token_ratio(monorepo_summaries)
    realistic_max_ratio = _max_token_ratio(realistic_summaries)
    expected_min_files = int(monorepo_fixture.get("expected_min_files") or 0)
    checks = [
        {
            "name": "monorepo_restore_verified",
            "severity": "fail",
            "passed": bool(monorepo_summaries) and all(item["restore_verified"] for item in monorepo_summaries),
            "observed": sum(1 for item in monorepo_summaries if item["restore_verified"]),
            "expected": len(monorepo_summaries),
        },
        {
            "name": "monorepo_file_floor",
            "severity": "warn",
            "passed": expected_min_files >= thresholds["monorepo_min_files"],
            "observed": expected_min_files,
            "expected": f">= {thresholds['monorepo_min_files']}",
        },
        {
            "name": "monorepo_token_ratio",
            "severity": "warn",
            "passed": bool(monorepo_summaries) and monorepo_max_ratio <= thresholds["monorepo_max_token_ratio"],
            "observed": monorepo_max_ratio,
            "expected": f"<= {thresholds['monorepo_max_token_ratio']}",
        },
        {
            "name": "realistic_directory_restore_verified",
            "severity": "fail",
            "passed": bool(realistic_summaries) and all(item["restore_verified"] for item in realistic_summaries),
            "observed": sum(1 for item in realistic_summaries if item["restore_verified"]),
            "expected": len(realistic_summaries),
        },
        {
            "name": "realistic_directory_token_ratio",
            "severity": "warn",
            "passed": bool(realistic_summaries) and realistic_max_ratio <= thresholds["realistic_directory_max_token_ratio"],
            "observed": realistic_max_ratio,
            "expected": f"<= {thresholds['realistic_directory_max_token_ratio']}",
        },
    ]
    failed_checks = [item for item in checks if item["severity"] == "fail" and not item["passed"]]
    warned_checks = [item for item in checks if item["severity"] == "warn" and not item["passed"]]
    if failed_checks:
        status = "fail"
    elif warned_checks:
        status = "warn"
    else:
        status = "ok"
    return {
        "status": status,
        "thresholds": thresholds,
        "checks": checks,
    }


def _build_best_verified_recommendations(
    cases: list[dict[str, Any]],
    *,
    expected_kind: str,
) -> list[dict[str, Any]]:
    summaries = [
        _summarize_case(case)
        for case in cases
        if case.get("kind") == expected_kind
    ]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in summaries:
        key = (item["backend"], item.get("sample_type", "synthetic"), item.get("source_path", ""))
        grouped.setdefault(key, []).append(item)

    recommendations: list[dict[str, Any]] = []
    for (backend, sample_type, source_path), items in sorted(grouped.items()):
        verified_items = [item for item in items if item["restore_verified"]]
        if not verified_items:
            continue
        baseline = next(
            (
                item
                for item in verified_items
                if item.get("focus_mode") == "full" and item.get("skeleton_density") == "standard"
            ),
            None,
        ) or next(
            (
                item
                for item in verified_items
                if item.get("focus_mode") == "full" and item.get("skeleton_density") == "adaptive"
            ),
            None,
        )
        best = min(
            verified_items,
            key=lambda item: (
                float(item["token_ratio"]),
                int(item["estimated_skeleton_tokens"]),
                str(item.get("focus_mode", "")),
            ),
        )
        worst_verified = max(
            verified_items,
            key=lambda item: (
                float(item["token_ratio"]),
                int(item["estimated_skeleton_tokens"]),
            ),
        )
        baseline_item = baseline or best
        baseline_tokens = int(baseline_item["estimated_skeleton_tokens"])
        best_tokens = int(best["estimated_skeleton_tokens"])
        baseline_compress_ms = float(baseline_item.get("compress_ms_avg") or 0.0)
        best_compress_ms = float(best.get("compress_ms_avg") or 0.0)
        skeleton_token_size_ratio_vs_baseline = round(best_tokens / baseline_tokens, 4) if baseline_tokens else 0.0
        recommendations.append(
            {
                "backend": backend,
                "kind": expected_kind,
                "sample_type": sample_type,
                "source_path": source_path,
                "candidate_count": len(items),
                "verified_candidate_count": len(verified_items),
                "recommended_focus_mode": best.get("focus_mode", "full"),
                "recommended_skeleton_density": best.get("skeleton_density", "adaptive"),
                "recommended_token_ratio": best["token_ratio"],
                "recommended_skeleton_tokens": best_tokens,
                "recommended_compress_ms_avg": round(best_compress_ms, 2),
                "baseline_focus_mode": baseline_item.get("focus_mode", "full"),
                "baseline_skeleton_density": baseline_item.get("skeleton_density", "adaptive"),
                "baseline_skeleton_tokens": baseline_tokens,
                "baseline_token_ratio": baseline_item["token_ratio"],
                "baseline_compress_ms_avg": round(baseline_compress_ms, 2),
                "skeleton_token_savings_vs_baseline": max(0, baseline_tokens - best_tokens),
                "skeleton_token_savings_percent_vs_baseline": round(
                    max(0.0, 1.0 - skeleton_token_size_ratio_vs_baseline) * 100,
                    2,
                ),
                "skeleton_token_size_ratio_vs_baseline": skeleton_token_size_ratio_vs_baseline,
                "compress_time_ratio_vs_baseline": round(best_compress_ms / baseline_compress_ms, 4)
                if baseline_compress_ms else 0.0,
                "worst_verified_token_ratio": worst_verified["token_ratio"],
                "token_ratio_span_verified": round(
                    float(worst_verified["token_ratio"]) - float(best["token_ratio"]),
                    4,
                ),
                "source_chars": best["source_chars"],
                "restore_verified": best["restore_verified"],
            }
        )
    return recommendations


def _build_release_readiness(
    *,
    scale_health: dict[str, Any],
    large_directory_recommendations: list[dict[str, Any]],
    long_text_recommendations: list[dict[str, Any]],
    all_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    case_summaries = [_summarize_case(case) for case in all_cases]
    restore_failed_cases = [
        item["label"]
        for item in case_summaries
        if not item["restore_verified"]
    ]
    scale_checks = scale_health.get("checks") or []
    failed_scale_checks = [
        item["name"]
        for item in scale_checks
        if item.get("severity") == "fail" and not item.get("passed")
    ]
    warned_scale_checks = [
        item["name"]
        for item in scale_checks
        if item.get("severity") == "warn" and not item.get("passed")
    ]
    readiness_checks = [
        {
            "name": "all_restore_verified",
            "severity": "block",
            "passed": not restore_failed_cases,
            "observed": len(restore_failed_cases),
            "expected": 0,
        },
        {
            "name": "scale_health_has_no_failures",
            "severity": "block",
            "passed": not failed_scale_checks,
            "observed": len(failed_scale_checks),
            "expected": 0,
        },
        {
            "name": "large_directory_recommendations_available",
            "severity": "block",
            "passed": bool(large_directory_recommendations),
            "observed": len(large_directory_recommendations),
            "expected": ">= 1",
        },
        {
            "name": "long_text_recommendations_available",
            "severity": "block",
            "passed": bool(long_text_recommendations),
            "observed": len(long_text_recommendations),
            "expected": ">= 1",
        },
        {
            "name": "scale_health_has_no_warnings",
            "severity": "watch",
            "passed": not warned_scale_checks,
            "observed": len(warned_scale_checks),
            "expected": 0,
        },
    ]
    blocked = [item for item in readiness_checks if item["severity"] == "block" and not item["passed"]]
    watching = [item for item in readiness_checks if item["severity"] == "watch" and not item["passed"]]
    if blocked:
        status = "blocked"
        next_action = "fix blocking restore or benchmark coverage failures before treating this run as release-ready"
    elif watching:
        status = "watch"
        next_action = "review scale-health warnings and decide whether to tune thresholds or improve compression efficiency"
    else:
        status = "ready"
        next_action = "use this run as a candidate baseline for broader cross-platform validation"
    return {
        "status": status,
        "next_action": next_action,
        "checks": readiness_checks,
        "restore_failed_cases": restore_failed_cases[:20],
        "failed_scale_checks": failed_scale_checks,
        "warned_scale_checks": warned_scale_checks,
        "case_count": len(case_summaries),
        "restore_verified_count": sum(1 for item in case_summaries if item["restore_verified"]),
    }


def _case_trend_key(item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("kind") or ""),
            str(item.get("sample_type") or ""),
            str(item.get("backend") or ""),
            str(item.get("label") or ""),
            str(item.get("focus_mode") or ""),
            str(item.get("skeleton_density") or ""),
        ]
    )


def _collect_report_case_summaries(report: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = report.get("summaries") or {}
    collected: list[dict[str, Any]] = []
    for key in [
        "directory_cases",
        "realistic_directory_cases",
        "monorepo_directory_cases",
        "directory_incremental_cases",
        "text_cases",
        "realistic_text_cases",
    ]:
        for item in summaries.get(key) or []:
            if isinstance(item, dict):
                collected.append(item)
    return collected


def _load_baseline_report(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"baseline benchmark JSON not found: {resolved}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def _build_regression_trends(
    *,
    current_cases: list[dict[str, Any]],
    baseline_report: dict[str, Any] | None,
) -> dict[str, Any]:
    if baseline_report is None:
        return {
            "status": "no-baseline",
            "baseline_generated_at": "",
            "matched_case_count": 0,
            "current_case_count": len(current_cases),
            "restore_regressions": [],
            "token_ratio_regressions": [],
            "compress_time_regressions": [],
            "improvements": [],
        }
    current_summaries = [_summarize_case(case) for case in current_cases]
    baseline_by_key = {
        _case_trend_key(item): item
        for item in _collect_report_case_summaries(baseline_report)
    }
    restore_regressions: list[dict[str, Any]] = []
    token_ratio_regressions: list[dict[str, Any]] = []
    compress_time_regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    matched_count = 0
    for current in current_summaries:
        baseline = baseline_by_key.get(_case_trend_key(current))
        if baseline is None:
            continue
        matched_count += 1
        if baseline.get("restore_verified") is True and current.get("restore_verified") is not True:
            restore_regressions.append(
                {
                    "label": current["label"],
                    "backend": current["backend"],
                    "sample_type": current.get("sample_type", ""),
                    "previous": True,
                    "current": current.get("restore_verified"),
                }
            )
        baseline_ratio = float(baseline.get("token_ratio") or 0.0)
        current_ratio = float(current.get("token_ratio") or 0.0)
        ratio_delta = round(current_ratio - baseline_ratio, 4)
        if baseline_ratio and ratio_delta > 0.05:
            token_ratio_regressions.append(
                {
                    "label": current["label"],
                    "backend": current["backend"],
                    "sample_type": current.get("sample_type", ""),
                    "baseline_token_ratio": baseline_ratio,
                    "current_token_ratio": current_ratio,
                    "delta": ratio_delta,
                }
            )
        elif baseline_ratio and ratio_delta < -0.05:
            improvements.append(
                {
                    "label": current["label"],
                    "backend": current["backend"],
                    "sample_type": current.get("sample_type", ""),
                    "metric": "token_ratio",
                    "baseline": baseline_ratio,
                    "current": current_ratio,
                    "delta": ratio_delta,
                }
            )
        baseline_ms = float(baseline.get("compress_ms_avg") or 0.0)
        current_ms = float(current.get("compress_ms_avg") or 0.0)
        if baseline_ms and current_ms / baseline_ms > 1.5:
            compress_time_regressions.append(
                {
                    "label": current["label"],
                    "backend": current["backend"],
                    "sample_type": current.get("sample_type", ""),
                    "baseline_compress_ms_avg": round(baseline_ms, 2),
                    "current_compress_ms_avg": round(current_ms, 2),
                    "ratio": round(current_ms / baseline_ms, 4),
                }
            )
    if restore_regressions:
        status = "regressed"
    elif token_ratio_regressions or compress_time_regressions:
        status = "watch"
    elif improvements:
        status = "improved"
    else:
        status = "stable"
    return {
        "status": status,
        "baseline_generated_at": baseline_report.get("generated_at", ""),
        "matched_case_count": matched_count,
        "current_case_count": len(current_summaries),
        "restore_regressions": restore_regressions[:20],
        "token_ratio_regressions": token_ratio_regressions[:20],
        "compress_time_regressions": compress_time_regressions[:20],
        "improvements": improvements[:20],
    }


def _recommendation_preview(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for item in items[:6]:
        preview.append(
            {
                "backend": item.get("backend", ""),
                "sample_type": item.get("sample_type", ""),
                "source_path": item.get("source_path", ""),
                "focus_mode": item.get("recommended_focus_mode", ""),
                "skeleton_density": item.get("recommended_skeleton_density", ""),
                "token_ratio": item.get("recommended_token_ratio", 0),
                "size_ratio_vs_baseline": item.get("skeleton_token_size_ratio_vs_baseline", 0),
                "savings_percent_vs_baseline": item.get("skeleton_token_savings_percent_vs_baseline", 0),
                "candidate_count": item.get("candidate_count", 0),
                "verified_candidate_count": item.get("verified_candidate_count", 0),
            }
        )
    return preview


def _build_executive_summary(
    *,
    release_readiness: dict[str, Any],
    scale_health: dict[str, Any],
    regression_trends: dict[str, Any],
    large_directory_recommendations: list[dict[str, Any]],
    long_text_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    trend_status = str(regression_trends.get("status") or "unknown")
    readiness_status = str(release_readiness.get("status") or "unknown")
    scale_status = str(scale_health.get("status") or "unknown")
    restore_verified_count = int(release_readiness.get("restore_verified_count") or 0)
    case_count = int(release_readiness.get("case_count") or 0)
    regression_counts = {
        "restore": len(regression_trends.get("restore_regressions") or []),
        "token_ratio": len(regression_trends.get("token_ratio_regressions") or []),
        "compress_time": len(regression_trends.get("compress_time_regressions") or []),
        "improvements": len(regression_trends.get("improvements") or []),
    }
    if readiness_status == "blocked" or trend_status == "regressed":
        overall = "blocked"
    elif readiness_status == "watch" or scale_status == "warn" or trend_status == "watch":
        overall = "watch"
    else:
        overall = "ready"
    return {
        "overall_status": overall,
        "release_readiness": readiness_status,
        "scale_health": scale_status,
        "regression_trends": trend_status,
        "restore_verified": f"{restore_verified_count}/{case_count}",
        "regression_counts": regression_counts,
        "large_directory_recommendations": _recommendation_preview(large_directory_recommendations),
        "long_text_recommendations": _recommendation_preview(long_text_recommendations),
        "next_action": release_readiness.get("next_action", ""),
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Context Scale Benchmark",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- repo_root: `{report['repo_root']}`",
        f"- python: `{report['python']}`",
        f"- platform: `{report['platform']}`",
        f"- synthetic_directory: `{report.get('benchmark_inputs', {}).get('synthetic_directory', '')}`",
        f"- realistic_directory: `{report.get('benchmark_inputs', {}).get('realistic_directory', '')}`",
        f"- monorepo_directory: `{report.get('benchmark_inputs', {}).get('monorepo_directory', '')}`",
        "",
        "## Executive Summary",
        "",
        f"- overall_status: `{report.get('executive_summary', {}).get('overall_status', 'unknown')}`",
        f"- restore_verified: `{report.get('executive_summary', {}).get('restore_verified', '0/0')}`",
        f"- regression_trends: `{report.get('executive_summary', {}).get('regression_trends', 'unknown')}`",
        f"- next_action: {report.get('executive_summary', {}).get('next_action', '')}",
        "",
    ]
    executive = report.get("executive_summary") or {}
    for title, key in [
        ("Large directory recommendation preview", "large_directory_recommendations"),
        ("Long text recommendation preview", "long_text_recommendations"),
    ]:
        items = executive.get(key) or []
        if items:
            lines.extend([f"{title}:", ""])
            lines.extend(
                [
                    f"- `{item.get('sample_type', '')}`/{item.get('backend', '')}: `{item.get('focus_mode', '')}` + `{item.get('skeleton_density', '')}` ratio `{item.get('token_ratio', 0)}`, saves `{item.get('savings_percent_vs_baseline', 0)}%` vs baseline"
                    for item in items[:4]
                ]
            )
            lines.append("")
    lines.extend([
        "## Release Readiness",
        "",
        f"- status: `{report.get('release_readiness', {}).get('status', 'unknown')}`",
        f"- restore_verified: `{report.get('release_readiness', {}).get('restore_verified_count', 0)}/{report.get('release_readiness', {}).get('case_count', 0)}`",
        f"- next_action: {report.get('release_readiness', {}).get('next_action', '')}",
        "",
    ])
    readiness = report.get("release_readiness") or {}
    readiness_rows = [
        [
            item["name"],
            item["severity"],
            item["passed"],
            item["observed"],
            item["expected"],
        ]
        for item in readiness.get("checks", [])
    ]
    lines.append(
        _markdown_table(
            ["Check", "Severity", "Passed", "Observed", "Expected"],
            readiness_rows,
        )
    )
    if readiness.get("restore_failed_cases"):
        lines.extend(["", "Restore failures:", ""])
        lines.extend([f"- `{item}`" for item in readiness.get("restore_failed_cases", [])])
    if readiness.get("warned_scale_checks"):
        lines.extend(["", "Watch items:", ""])
        lines.extend([f"- `{item}`" for item in readiness.get("warned_scale_checks", [])])
    lines.extend([
        "",
        "## Regression Trends",
        "",
        f"- status: `{report.get('regression_trends', {}).get('status', 'unknown')}`",
        f"- baseline_generated_at: `{report.get('regression_trends', {}).get('baseline_generated_at', '')}`",
        f"- matched_cases: `{report.get('regression_trends', {}).get('matched_case_count', 0)}/{report.get('regression_trends', {}).get('current_case_count', 0)}`",
        "",
    ])
    trend = report.get("regression_trends") or {}
    trend_rows = [
        ["restore_regressions", len(trend.get("restore_regressions") or [])],
        ["token_ratio_regressions", len(trend.get("token_ratio_regressions") or [])],
        ["compress_time_regressions", len(trend.get("compress_time_regressions") or [])],
        ["improvements", len(trend.get("improvements") or [])],
    ]
    lines.append(_markdown_table(["Trend", "Count"], trend_rows))
    for title, key in [
        ("Restore Regressions", "restore_regressions"),
        ("Token Ratio Regressions", "token_ratio_regressions"),
        ("Compress Time Regressions", "compress_time_regressions"),
        ("Improvements", "improvements"),
    ]:
        items = trend.get(key) or []
        if items:
            lines.extend(["", f"### {title}", ""])
            lines.extend([f"- `{item.get('label', '')}` ({item.get('backend', '')}, {item.get('sample_type', '')})" for item in items[:10]])
    lines.extend([
        "",
        "## Scale Health",
        "",
        f"- status: `{report.get('scale_health', {}).get('status', 'unknown')}`",
        "",
    ])
    scale_health = report.get("scale_health") or {}
    scale_rows = [
        [
            item["name"],
            item["severity"],
            item["passed"],
            item["observed"],
            item["expected"],
        ]
        for item in scale_health.get("checks", [])
    ]
    lines.append(
        _markdown_table(
            ["Check", "Severity", "Passed", "Observed", "Expected"],
            scale_rows,
        )
    )
    if report["summaries"].get("large_directory_recommendations"):
        lines.extend(["", "## Large Directory Recommendations", ""])
        recommendation_rows = [
            [
                item["backend"],
                item["sample_type"],
                item["source_path"],
                item["recommended_focus_mode"],
                item["recommended_skeleton_density"],
                item["recommended_token_ratio"],
                item["recommended_skeleton_tokens"],
                item["baseline_skeleton_tokens"],
                item["skeleton_token_savings_vs_baseline"],
                item["skeleton_token_savings_percent_vs_baseline"],
                item["skeleton_token_size_ratio_vs_baseline"],
                item["recommended_compress_ms_avg"],
                item["baseline_compress_ms_avg"],
                item["compress_time_ratio_vs_baseline"],
                item["verified_candidate_count"],
                item["candidate_count"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["large_directory_recommendations"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Backend",
                    "Sample type",
                    "Source",
                    "Recommended focus",
                    "Recommended density",
                    "Token ratio",
                    "Recommended tokens",
                    "Baseline tokens",
                    "Tokens saved vs baseline",
                    "Savings % vs baseline",
                    "Size ratio vs baseline",
                    "Recommended ms",
                    "Baseline ms",
                    "Time ratio vs baseline",
                    "Verified candidates",
                    "Candidates",
                    "Restore ok",
                ],
                recommendation_rows,
            )
        )
    if report["summaries"].get("long_text_recommendations"):
        lines.extend(["", "## Long Text Recommendations", ""])
        long_text_recommendation_rows = [
            [
                item["backend"],
                item["sample_type"],
                item["source_path"],
                item["recommended_focus_mode"],
                item["recommended_skeleton_density"],
                item["recommended_token_ratio"],
                item["recommended_skeleton_tokens"],
                item["baseline_skeleton_tokens"],
                item["skeleton_token_savings_vs_baseline"],
                item["skeleton_token_savings_percent_vs_baseline"],
                item["skeleton_token_size_ratio_vs_baseline"],
                item["recommended_compress_ms_avg"],
                item["baseline_compress_ms_avg"],
                item["compress_time_ratio_vs_baseline"],
                item["verified_candidate_count"],
                item["candidate_count"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["long_text_recommendations"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Backend",
                    "Sample type",
                    "Source",
                    "Recommended focus",
                    "Recommended density",
                    "Token ratio",
                    "Recommended tokens",
                    "Baseline tokens",
                    "Tokens saved vs baseline",
                    "Savings % vs baseline",
                    "Size ratio vs baseline",
                    "Recommended ms",
                    "Baseline ms",
                    "Time ratio vs baseline",
                    "Verified candidates",
                    "Candidates",
                    "Restore ok",
                ],
                long_text_recommendation_rows,
            )
        )
    lines.extend([
        "",
        "## Directory Cases",
        "",
    ])
    directory_rows = [
        [
            item["label"],
            item["backend"],
            item["kind"],
            item["source_chars"],
            item["skeleton_chars"],
            item["estimated_source_tokens"],
            item["estimated_skeleton_tokens"],
            item["estimated_tokens_saved"],
            item["token_ratio"],
            item["compress_ms_avg"],
            item["inspect_ms_avg"],
            item["restore_ms_avg"],
            item["restore_verified"],
        ]
        for item in report["summaries"]["directory_full_cases"]
    ]
    lines.append(
        _markdown_table(
            [
                "Case",
                "Backend",
                "Kind",
                "Source chars",
                "Skeleton chars",
                "Source tokens",
                "Skeleton tokens",
                "Tokens saved",
                "Token ratio",
                "Compress ms",
                "Inspect ms",
                "Restore ms",
                "Restore ok",
            ],
            directory_rows,
        )
    )
    if report["summaries"].get("realistic_directory_full_cases"):
        lines.extend(["", "## Realistic Directory Cases", ""])
        realistic_directory_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["source_chars"],
                item["skeleton_chars"],
                item["estimated_source_tokens"],
                item["estimated_skeleton_tokens"],
                item["estimated_tokens_saved"],
                item["token_ratio"],
                item["compress_ms_avg"],
                item["inspect_ms_avg"],
                item["restore_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["realistic_directory_full_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Source chars",
                    "Skeleton chars",
                    "Source tokens",
                    "Skeleton tokens",
                    "Tokens saved",
                    "Token ratio",
                    "Compress ms",
                    "Inspect ms",
                    "Restore ms",
                    "Restore ok",
                ],
                realistic_directory_rows,
            )
        )
    if report["summaries"].get("monorepo_directory_cases"):
        lines.extend(["", "## Monorepo Directory Cases", ""])
        monorepo_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["source_chars"],
                item["skeleton_chars"],
                item["estimated_source_tokens"],
                item["estimated_skeleton_tokens"],
                item["estimated_tokens_saved"],
                item["token_ratio"],
                item["compress_ms_avg"],
                item["inspect_ms_avg"],
                item["restore_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["monorepo_directory_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Source chars",
                    "Skeleton chars",
                    "Source tokens",
                    "Skeleton tokens",
                    "Tokens saved",
                    "Token ratio",
                    "Compress ms",
                    "Inspect ms",
                    "Restore ms",
                    "Restore ok",
                ],
                monorepo_rows,
            )
        )
    if report["summaries"].get("directory_incremental_cases"):
        lines.extend(["", "## Incremental Directory Cases", ""])
        incremental_rows = [
            [
                item["label"],
                item["backend"],
                item["kind"],
                item["change_surface_count"],
                item["source_chars"],
                item["skeleton_chars"],
                item["estimated_source_tokens"],
                item["estimated_skeleton_tokens"],
                item["estimated_tokens_saved"],
                item["token_ratio"],
                item["compress_ms_avg"],
                item["inspect_ms_avg"],
                item["restore_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["directory_incremental_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Kind",
                    "Change surface",
                    "Source chars",
                    "Skeleton chars",
                    "Source tokens",
                    "Skeleton tokens",
                    "Tokens saved",
                    "Token ratio",
                    "Compress ms",
                    "Inspect ms",
                    "Restore ms",
                    "Restore ok",
                ],
                incremental_rows,
            )
        )
    if report["summaries"].get("incremental_comparison"):
        lines.extend(["", "## Incremental Comparison", ""])
        comparison_rows = [
            [
                item["backend"],
                item["change_surface_count"],
                item["full_source_tokens"],
                item["incremental_source_tokens"],
                item["source_token_size_ratio"],
                item["full_skeleton_tokens"],
                item["incremental_skeleton_tokens"],
                item["skeleton_token_size_ratio"],
                item["full_compress_ms_avg"],
                item["incremental_compress_ms_avg"],
                item["compress_time_ratio"],
            ]
            for item in report["summaries"]["incremental_comparison"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Backend",
                    "Change surface",
                    "Full source tokens",
                    "Incremental source tokens",
                    "Source token ratio",
                    "Full skeleton tokens",
                    "Incremental skeleton tokens",
                    "Skeleton token ratio",
                    "Full compress ms",
                    "Incremental compress ms",
                    "Compress ratio",
                ],
                comparison_rows,
            )
        )
    if report["summaries"].get("directory_focus_cases"):
        lines.extend(["", "## Directory Focus Cases", ""])
        focus_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["focus_mode"],
                item["skeleton_density"],
                item["skeleton_chars"],
                item["estimated_skeleton_tokens"],
                item["compress_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["directory_focus_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                "Case",
                "Backend",
                "Sample type",
                "Focus mode",
                "Skeleton density",
                "Skeleton chars",
                "Skeleton tokens",
                "Compress ms",
                "Restore ok",
            ],
                focus_rows,
            )
        )
    if report["summaries"].get("directory_focus_comparison"):
        lines.extend(["", "## Directory Focus Comparison", ""])
        directory_focus_comparison_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["focus_mode"],
                item["full_skeleton_chars"],
                item["focused_skeleton_chars"],
                item["skeleton_char_size_ratio"],
                item["full_skeleton_tokens"],
                item["focused_skeleton_tokens"],
                item["skeleton_token_size_ratio"],
                item["full_compress_ms_avg"],
                item["focused_compress_ms_avg"],
                item["compress_time_ratio"],
            ]
            for item in report["summaries"]["directory_focus_comparison"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Focus mode",
                    "Full skeleton chars",
                    "Focused skeleton chars",
                    "Skeleton char ratio",
                    "Full skeleton tokens",
                    "Focused skeleton tokens",
                    "Skeleton token ratio",
                    "Full compress ms",
                    "Focused compress ms",
                    "Compress ratio",
                ],
                directory_focus_comparison_rows,
            )
        )
    if report["summaries"].get("directory_density_comparison"):
        lines.extend(["", "## Directory Density Comparison", ""])
        directory_density_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["skeleton_density"],
                item["baseline_skeleton_chars"],
                item["density_skeleton_chars"],
                item["skeleton_char_size_ratio"],
                item["baseline_skeleton_tokens"],
                item["density_skeleton_tokens"],
                item["skeleton_token_size_ratio"],
                item["baseline_compress_ms_avg"],
                item["density_compress_ms_avg"],
                item["compress_time_ratio"],
            ]
            for item in report["summaries"]["directory_density_comparison"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Skeleton density",
                    "Standard skeleton chars",
                    "Density skeleton chars",
                    "Skeleton char ratio",
                    "Standard skeleton tokens",
                    "Density skeleton tokens",
                    "Skeleton token ratio",
                    "Standard compress ms",
                    "Density compress ms",
                    "Compress ratio",
                ],
                directory_density_rows,
            )
        )
    lines.extend(["", "## Long Text Cases", ""])
    text_rows = [
        [
            item["label"],
            item["backend"],
            item["kind"],
            item["source_chars"],
            item["skeleton_chars"],
            item["estimated_source_tokens"],
            item["estimated_skeleton_tokens"],
            item["estimated_tokens_saved"],
            item["token_ratio"],
            item["compress_ms_avg"],
            item["inspect_ms_avg"],
            item["restore_ms_avg"],
            item["restore_verified"],
        ]
        for item in report["summaries"]["text_full_cases"]
    ]
    lines.append(
        _markdown_table(
            [
                "Case",
                "Backend",
                "Kind",
                "Source chars",
                "Skeleton chars",
                "Source tokens",
                "Skeleton tokens",
                "Tokens saved",
                "Token ratio",
                "Compress ms",
                "Inspect ms",
                "Restore ms",
                "Restore ok",
            ],
            text_rows,
        )
    )
    if report["summaries"].get("realistic_text_full_cases"):
        lines.extend(["", "## Realistic Text Cases", ""])
        realistic_text_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["source_chars"],
                item["skeleton_chars"],
                item["estimated_source_tokens"],
                item["estimated_skeleton_tokens"],
                item["estimated_tokens_saved"],
                item["token_ratio"],
                item["compress_ms_avg"],
                item["inspect_ms_avg"],
                item["restore_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["realistic_text_full_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Source chars",
                    "Skeleton chars",
                    "Source tokens",
                    "Skeleton tokens",
                    "Tokens saved",
                    "Token ratio",
                    "Compress ms",
                    "Inspect ms",
                    "Restore ms",
                    "Restore ok",
                ],
                realistic_text_rows,
            )
        )
    if report["summaries"].get("text_focus_cases"):
        lines.extend(["", "## Text Focus Cases", ""])
        text_focus_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["focus_mode"],
                item["skeleton_density"],
                item["skeleton_chars"],
                item["estimated_skeleton_tokens"],
                item["compress_ms_avg"],
                item["restore_verified"],
            ]
            for item in report["summaries"]["text_focus_cases"]
        ]
        lines.append(
            _markdown_table(
                [
                "Case",
                "Backend",
                "Sample type",
                "Focus mode",
                "Skeleton density",
                "Skeleton chars",
                "Skeleton tokens",
                "Compress ms",
                "Restore ok",
            ],
                text_focus_rows,
            )
        )
    if report["summaries"].get("text_focus_comparison"):
        lines.extend(["", "## Text Focus Comparison", ""])
        text_focus_comparison_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["focus_mode"],
                item["full_skeleton_chars"],
                item["focused_skeleton_chars"],
                item["skeleton_char_size_ratio"],
                item["full_skeleton_tokens"],
                item["focused_skeleton_tokens"],
                item["skeleton_token_size_ratio"],
                item["full_compress_ms_avg"],
                item["focused_compress_ms_avg"],
                item["compress_time_ratio"],
            ]
            for item in report["summaries"]["text_focus_comparison"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Focus mode",
                    "Full skeleton chars",
                    "Focused skeleton chars",
                    "Skeleton char ratio",
                    "Full skeleton tokens",
                    "Focused skeleton tokens",
                    "Skeleton token ratio",
                    "Full compress ms",
                    "Focused compress ms",
                    "Compress ratio",
                ],
                text_focus_comparison_rows,
            )
        )
    if report["summaries"].get("text_density_comparison"):
        lines.extend(["", "## Text Density Comparison", ""])
        text_density_rows = [
            [
                item["label"],
                item["backend"],
                item["sample_type"],
                item["skeleton_density"],
                item["baseline_skeleton_chars"],
                item["density_skeleton_chars"],
                item["skeleton_char_size_ratio"],
                item["baseline_skeleton_tokens"],
                item["density_skeleton_tokens"],
                item["skeleton_token_size_ratio"],
                item["baseline_compress_ms_avg"],
                item["density_compress_ms_avg"],
                item["compress_time_ratio"],
            ]
            for item in report["summaries"]["text_density_comparison"]
        ]
        lines.append(
            _markdown_table(
                [
                    "Case",
                    "Backend",
                    "Sample type",
                    "Skeleton density",
                    "Standard skeleton chars",
                    "Density skeleton chars",
                    "Skeleton char ratio",
                    "Standard skeleton tokens",
                    "Density skeleton tokens",
                    "Skeleton token ratio",
                    "Standard compress ms",
                    "Density compress ms",
                    "Compress ratio",
                ],
                text_density_rows,
            )
        )
    lines.extend(["", "## Notes", ""])
    lines.append(
        "- `token_ratio` is the skeleton token footprint divided by the source token footprint; smaller is better."
    )
    lines.append(
        "- `source_token_size_ratio` and `skeleton_token_size_ratio` in the incremental comparison show how much smaller the incremental surface is versus the full directory benchmark."
    )
    lines.append(
        "- `heuristic` uses `chars/4`, while `auto` and `tiktoken` prefer tokenizer-backed counts when available."
    )
    lines.append(
        "- This benchmark is designed to show how context compression behaves as directory and long-text surfaces grow, not to claim billing-grade token accounting."
    )
    return "\n".join(lines) + "\n"


def _build_directory_fixture(root: Path) -> Path:
    sample_root = root / "sample_project"
    (sample_root / "src").mkdir(parents=True, exist_ok=True)
    (sample_root / "docs").mkdir(parents=True, exist_ok=True)
    (sample_root / "src" / "app.py").write_text(
        "from cart import sync_checkout\n\n\ndef route():\n    sync_checkout()\n    return 'route continuity'\n",
        encoding="utf-8",
    )
    (sample_root / "docs" / "notes.md").write_text(
        "# Notes\n\n- preserve business logic\n- preserve restore exactness\n",
        encoding="utf-8",
    )
    return sample_root


def _build_monorepo_fixture(
    root: Path,
    *,
    package_count: int,
    files_per_package: int,
) -> tuple[Path, dict[str, Any]]:
    monorepo_root = root / "sample_monorepo"
    package_roots: list[str] = []
    language_counts: dict[str, int] = {"python": 0, "typescript": 0, "markdown": 0, "config": 0}
    for package_idx in range(1, package_count + 1):
        package_root = monorepo_root / "packages" / f"service_{package_idx:02d}"
        package_roots.append(package_root.relative_to(monorepo_root).as_posix())
        (package_root / "src").mkdir(parents=True, exist_ok=True)
        (package_root / "tests").mkdir(parents=True, exist_ok=True)
        (package_root / "docs").mkdir(parents=True, exist_ok=True)
        (package_root / "config").mkdir(parents=True, exist_ok=True)
        for file_idx in range(1, files_per_package + 1):
            lane = file_idx % 4
            if lane == 0:
                target = package_root / "src" / f"handler_{file_idx:03d}.py"
                target.write_text(
                    "from pathlib import Path\n\n"
                    f"def handle_service_{package_idx}_{file_idx}(payload: dict) -> str:\n"
                    "    normalized = {key: str(value).strip() for key, value in payload.items()}\n"
                    "    audit_path = Path('audit') / 'events.log'\n"
                    "    event_parts = []\n"
                    "    for key in sorted(normalized):\n"
                    "        event_parts.append(f'{key}={normalized[key]}')\n"
                    "    event_parts.append(str(audit_path))\n"
                    f"    event_parts.append('service-{package_idx}-handler-{file_idx}')\n"
                    "    return '|'.join(event_parts)\n",
                    encoding="utf-8",
                )
                language_counts["python"] += 1
            elif lane == 1:
                target = package_root / "src" / f"component_{file_idx:03d}.ts"
                target.write_text(
                    "import { createHash } from 'crypto'\n\n"
                    "type ComponentEvent = { id: string; payload: Record<string, string> }\n\n"
                    f"export function component{package_idx}_{file_idx}(value: string): string {{\n"
                    "  const event: ComponentEvent = { id: value, payload: { source: 'monorepo-benchmark' } }\n"
                    "  const digest = createHash('sha256').update(event.id).digest('hex')\n"
                    "  return `${event.payload.source}:${digest}`\n"
                    "}\n",
                    encoding="utf-8",
                )
                language_counts["typescript"] += 1
            elif lane == 2:
                target = package_root / "docs" / f"chapter_{file_idx:03d}.md"
                target.write_text(
                    f"# Service {package_idx} Chapter {file_idx}\n\n"
                    "This document preserves operator context, architecture notes, and handoff continuity.\n\n"
                    "## Interfaces\n\n"
                    "The service exposes request handlers, configuration surfaces, and review notes that should remain visible in compressed skeletons.\n\n"
                    "## Operations\n\n"
                    "Operators use this package-level context to understand rollout sequencing, ownership boundaries, and incident response expectations.\n",
                    encoding="utf-8",
                )
                language_counts["markdown"] += 1
            else:
                target = package_root / "config" / f"settings_{file_idx:03d}.yaml"
                target.write_text(
                    f"service: service_{package_idx:02d}\n"
                    f"setting: value_{file_idx:03d}\n"
                    "enabled: true\n"
                    "owners:\n"
                    "  - platform\n"
                    "  - context-compression\n"
                    "limits:\n"
                    "  max_batch_size: 128\n"
                    "  retry_budget: 3\n",
                    encoding="utf-8",
                )
                language_counts["config"] += 1
        (package_root / "README.md").write_text(
            f"# Service {package_idx:02d}\n\n"
            "Package-level README for monorepo grouping and overview benchmark coverage.\n",
            encoding="utf-8",
        )
        language_counts["markdown"] += 1

    (monorepo_root / ".mcp-skeletonignore").write_text(
        "node_modules/\n"
        "dist/\n"
        "*.map\n",
        encoding="utf-8",
    )
    return monorepo_root, {
        "package_count": package_count,
        "files_per_package": files_per_package,
        "package_roots": package_roots,
        "language_counts": language_counts,
        "expected_min_files": package_count * files_per_package,
    }


def _build_incremental_repo_fixture(source_dir: Path, workspace: Path) -> tuple[Path, dict[str, Any]]:
    repo_root = workspace / f"{source_dir.name}_incremental_repo"
    shutil.copytree(source_dir, repo_root)
    subprocess.run(["git", "init", "-q"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.com"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "config", "user.name", "Context Benchmark"], cwd=str(repo_root), check=True)
    subprocess.run(["git", "add", "."], cwd=str(repo_root), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=str(repo_root), check=True)

    candidates = sorted(
        path for path in repo_root.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    )
    if not candidates:
        raise RuntimeError(f"incremental benchmark fixture could not find files under {source_dir}")

    changed_rel = candidates[0].relative_to(repo_root).as_posix()
    changed_path = candidates[0]
    changed_bytes = changed_path.read_bytes()
    if changed_bytes:
        changed_path.write_bytes(changed_bytes + b"\n# incremental benchmark change\n")
    else:
        changed_path.write_text("# incremental benchmark change\n", encoding="utf-8")

    removed_rel = None
    if len(candidates) > 1:
        removed_rel = candidates[1].relative_to(repo_root).as_posix()
        candidates[1].unlink()

    added_rel = "benchmark_added.py"
    added_path = repo_root / added_rel
    added_path.write_text(
        "def incremental_helper():\n    return 'added by context scale benchmark'\n",
        encoding="utf-8",
    )

    expected_files = {
        changed_rel: hashlib.sha256(changed_path.read_bytes()).hexdigest(),
        added_rel: hashlib.sha256(added_path.read_bytes()).hexdigest(),
    }
    metadata = {
        "changed_paths": [changed_rel],
        "added_paths": [added_rel],
        "removed_paths": [removed_rel] if removed_rel else [],
        "expected_files": expected_files,
    }
    return repo_root, metadata


def _benchmark_directory_case(
    *,
    label: str,
    source_dir: Path,
    backend: str,
    tokenizer_model: str,
    iterations: int,
    workspace: Path,
    focus_mode: str = "full",
    skeleton_density: str = "adaptive",
) -> dict[str, Any]:
    compress_times: list[float] = []
    inspect_times: list[float] = []
    restore_times: list[float] = []
    compress_payload: dict[str, Any] | None = None
    inspect_payload: dict[str, Any] | None = None
    for idx in range(iterations):
        out_dir = workspace / f"{label}_{backend}_bundle_{idx}"
        compress_result = _run_cli_json(
            [
                "context",
                "compress",
                "--preset",
                "codebase",
                "--focus-mode",
                focus_mode,
                "--skeleton-density",
                skeleton_density,
                "--input-dir",
                str(source_dir),
                "--exclude",
                "testing/results/",
                "--output-dir",
                str(out_dir),
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        compress_payload = compress_result.payload
        compress_times.append(compress_result.elapsed_ms)
        manifest_path = out_dir / "context_manifest.json"
        inspect_result = _run_cli_json(
            [
                "context",
                "inspect",
                "--package-file",
                str(manifest_path),
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        inspect_payload = inspect_result.payload
        inspect_times.append(inspect_result.elapsed_ms)
        restore_root = workspace / f"{label}_{backend}_restore_{idx}"
        restore_result = _run_cli_json(
            [
                "context",
                "restore",
                "--package-file",
                str(manifest_path),
                "--output-dir",
                str(restore_root),
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        restore_times.append(restore_result.elapsed_ms)
    assert compress_payload is not None and inspect_payload is not None
    restored_root = workspace / f"{label}_{backend}_restore_{iterations - 1}" / source_dir.name
    restore_details = _compare_directory_snapshots(
        _directory_snapshot_from_restore_package(compress_payload.get("restore_package") or {}),
        _directory_snapshot_from_fs(restored_root),
    )
    return {
        "label": label,
        "backend": backend,
        "kind": "directory",
        "sample_type": "synthetic",
        "source_path": str(source_dir.resolve()),
        "compress": compress_payload,
        "inspect": inspect_payload,
        "timings_ms": {
            "compress": compress_times,
            "inspect": inspect_times,
            "restore": restore_times,
        },
        "restore_verified": restore_details["ok"],
        "restore_details": restore_details,
    }


def _benchmark_incremental_directory_case(
    *,
    label: str,
    repo_dir: Path,
    backend: str,
    tokenizer_model: str,
    iterations: int,
    workspace: Path,
    fixture_metadata: dict[str, Any],
) -> dict[str, Any]:
    compress_times: list[float] = []
    inspect_times: list[float] = []
    restore_times: list[float] = []
    compress_payload: dict[str, Any] | None = None
    inspect_payload: dict[str, Any] | None = None
    for idx in range(iterations):
        out_dir = workspace / f"{label}_{backend}_incremental_bundle_{idx}"
        compress_result = _run_cli_json(
            [
                "context",
                "compress",
                "--input-dir",
                str(repo_dir),
                "--incremental",
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--output-dir",
                str(out_dir),
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        compress_payload = compress_result.payload
        compress_times.append(compress_result.elapsed_ms)
        manifest_path = out_dir / "context_manifest.json"
        inspect_result = _run_cli_json(
            [
                "context",
                "inspect",
                "--package-file",
                str(manifest_path),
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        inspect_payload = inspect_result.payload
        inspect_times.append(inspect_result.elapsed_ms)
        restore_root = workspace / f"{label}_{backend}_incremental_restore_{idx}"
        restore_result = _run_cli_json(
            [
                "context",
                "restore",
                "--package-file",
                str(manifest_path),
                "--output-dir",
                str(restore_root),
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        restore_times.append(restore_result.elapsed_ms)
    assert compress_payload is not None and inspect_payload is not None
    restored_root = workspace / f"{label}_{backend}_incremental_restore_{iterations - 1}" / repo_dir.name
    restore_details = _compare_directory_snapshots(
        _directory_snapshot_from_restore_package(compress_payload.get("restore_package") or {}),
        _directory_snapshot_from_fs_ignoring(
            restored_root,
            ignored_rel_paths={".ail_incremental_manifest.json"},
        ),
    )
    manifest_path = restored_root / ".ail_incremental_manifest.json"
    incremental_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest_removed_paths = list(incremental_manifest.get("removed_paths") or [])
    manifest_ok = manifest_removed_paths == list(fixture_metadata.get("removed_paths") or [])
    return {
        "label": label,
        "backend": backend,
        "kind": "directory_incremental",
        "sample_type": "synthetic",
        "source_path": str(repo_dir.resolve()),
        "compress": compress_payload,
        "inspect": inspect_payload,
        "timings_ms": {
            "compress": compress_times,
            "inspect": inspect_times,
            "restore": restore_times,
        },
        "restore_verified": bool(restore_details["ok"] and manifest_ok),
        "restore_details": {
            **restore_details,
            "incremental_manifest_present": manifest_path.exists(),
            "incremental_manifest_removed_paths": manifest_removed_paths,
            "expected_removed_paths": list(fixture_metadata.get("removed_paths") or []),
            "incremental_manifest_ok": manifest_ok,
        },
        "fixture_metadata": fixture_metadata,
    }


def _benchmark_text_case(
    *,
    label: str,
    text_path: Path,
    backend: str,
    tokenizer_model: str,
    iterations: int,
    workspace: Path,
    focus_mode: str = "full",
    skeleton_density: str = "adaptive",
) -> dict[str, Any]:
    compress_times: list[float] = []
    inspect_times: list[float] = []
    restore_times: list[float] = []
    compress_payload: dict[str, Any] | None = None
    inspect_payload: dict[str, Any] | None = None
    for idx in range(iterations):
        out_dir = workspace / f"{label}_{backend}_bundle_{idx}"
        compress_result = _run_cli_json(
            [
                "context",
                "compress",
                "--preset",
                "writing",
                "--focus-mode",
                focus_mode,
                "--skeleton-density",
                skeleton_density,
                "--text-file",
                str(text_path),
                "--output-dir",
                str(out_dir),
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        compress_payload = compress_result.payload
        compress_times.append(compress_result.elapsed_ms)
        manifest_path = out_dir / "context_manifest.json"
        inspect_result = _run_cli_json(
            [
                "context",
                "inspect",
                "--package-file",
                str(manifest_path),
                "--tokenizer-backend",
                backend,
                "--tokenizer-model",
                tokenizer_model,
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        inspect_payload = inspect_result.payload
        inspect_times.append(inspect_result.elapsed_ms)
        restored_text = workspace / f"{label}_{backend}_restore_{idx}.md"
        restore_result = _run_cli_json(
            [
                "context",
                "restore",
                "--package-file",
                str(manifest_path),
                "--output-file",
                str(restored_text),
                "--json",
            ],
            cwd=REPO_ROOT,
        )
        restore_times.append(restore_result.elapsed_ms)
    assert compress_payload is not None and inspect_payload is not None
    restored_text = workspace / f"{label}_{backend}_restore_{iterations - 1}.md"
    return {
        "label": label,
        "backend": backend,
        "kind": "text",
        "sample_type": "synthetic",
        "source_path": str(text_path.resolve()),
        "compress": compress_payload,
        "inspect": inspect_payload,
        "timings_ms": {
            "compress": compress_times,
            "inspect": inspect_times,
            "restore": restore_times,
        },
        "restore_verified": _sha256_text(text_path) == _sha256_text(restored_text),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo-scale and long-text context compression benchmarks.")
    parser.add_argument("--directory", default=str(REPO_ROOT / "cli"), help="Directory input to benchmark.")
    parser.add_argument("--real-directory", default=str(REPO_ROOT), help="Real repository directory input to benchmark alongside the synthetic directory case.")
    parser.add_argument("--iterations", type=int, default=2, help="Iterations per case/backend.")
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL, help="Tokenizer model/encoding to request.")
    parser.add_argument("--backends", nargs="*", help="Explicit tokenizer backends to benchmark.")
    parser.add_argument("--directory-focus-modes", nargs="*", default=DEFAULT_DIRECTORY_FOCUS_MODES, help="Focus modes to benchmark for directory cases.")
    parser.add_argument("--text-focus-modes", nargs="*", default=DEFAULT_TEXT_FOCUS_MODES, help="Focus modes to benchmark for text cases.")
    parser.add_argument("--skeleton-densities", nargs="*", default=DEFAULT_SKELETON_DENSITIES, help="Skeleton density modes to benchmark for full skeleton cases.")
    parser.add_argument("--text-target-chars", nargs="*", type=int, default=DEFAULT_TEXT_TARGETS, help="Synthetic long-text sizes.")
    parser.add_argument("--real-text-files", nargs="*", default=[str(path) for path in DEFAULT_REAL_TEXT_FILES], help="Repository documents to concatenate into one realistic long-text corpus.")
    parser.add_argument("--monorepo-packages", type=int, default=6, help="Package roots to generate for the synthetic monorepo benchmark.")
    parser.add_argument("--monorepo-files-per-package", type=int, default=80, help="Files to generate per synthetic monorepo package.")
    parser.add_argument("--scale-health-monorepo-min-files", type=int, default=DEFAULT_SCALE_HEALTH_THRESHOLDS["monorepo_min_files"], help="Warning threshold for the generated monorepo fixture file floor.")
    parser.add_argument("--scale-health-monorepo-max-token-ratio", type=float, default=DEFAULT_SCALE_HEALTH_THRESHOLDS["monorepo_max_token_ratio"], help="Warning threshold for the largest monorepo skeleton/source token ratio.")
    parser.add_argument("--scale-health-realistic-directory-max-token-ratio", type=float, default=DEFAULT_SCALE_HEALTH_THRESHOLDS["realistic_directory_max_token_ratio"], help="Warning threshold for the largest realistic-directory skeleton/source token ratio.")
    parser.add_argument("--baseline-json", help="Optional previous benchmark JSON report used to compute non-blocking regression trends.")
    parser.add_argument("--output-json", default=str(DEFAULT_JSON), help="Where to write the benchmark JSON report.")
    parser.add_argument("--output-md", default=str(DEFAULT_MD), help="Where to write the Markdown benchmark report.")
    parser.add_argument("--quick", action="store_true", help="Run a smaller benchmark suitable for smoke coverage.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_json = Path(args.output_json).expanduser()
    output_md = Path(args.output_md).expanduser()
    _ensure_parent(output_json)
    _ensure_parent(output_md)
    baseline_report = _load_baseline_report(Path(args.baseline_json) if args.baseline_json else None)

    with tempfile.TemporaryDirectory(prefix="context_scale_benchmark.") as tmp:
        workspace = Path(tmp)
        directory_path = Path(args.directory).expanduser().resolve()
        real_directory_path = Path(args.real_directory).expanduser().resolve()
        text_targets = list(args.text_target_chars)
        iterations = max(1, args.iterations)
        if args.quick:
            directory_path = _build_directory_fixture(workspace)
            text_targets = QUICK_TEXT_TARGETS
            iterations = 1

        backends = _build_backends(args.backends, include_tiktoken=True)
        monorepo_packages = 3 if args.quick else max(1, args.monorepo_packages)
        monorepo_files_per_package = 60 if args.quick else max(1, args.monorepo_files_per_package)
        monorepo_path, monorepo_fixture = _build_monorepo_fixture(
            workspace,
            package_count=monorepo_packages,
            files_per_package=monorepo_files_per_package,
        )
        directory_focus_modes = list(dict.fromkeys(args.directory_focus_modes or DEFAULT_DIRECTORY_FOCUS_MODES))
        text_focus_modes = list(dict.fromkeys(args.text_focus_modes or DEFAULT_TEXT_FOCUS_MODES))
        skeleton_densities = list(dict.fromkeys(args.skeleton_densities or DEFAULT_SKELETON_DENSITIES))
        scale_health_thresholds = {
            "monorepo_min_files": max(1, args.scale_health_monorepo_min_files),
            "monorepo_max_token_ratio": max(0.0, args.scale_health_monorepo_max_token_ratio),
            "realistic_directory_max_token_ratio": max(0.0, args.scale_health_realistic_directory_max_token_ratio),
        }
        incremental_repo_dir, incremental_fixture_metadata = _build_incremental_repo_fixture(directory_path, workspace)
        realistic_text_path = workspace / "realistic_repo_corpus.md"
        realistic_text_fixture = _build_realistic_text_fixture(
            realistic_text_path,
            source_files=[Path(item).expanduser() for item in (args.real_text_files or [])],
        )
        text_cases: list[dict[str, Any]] = []
        for target_chars in text_targets:
            text_path = workspace / f"synthetic_book_{target_chars}.md"
            text_path.write_text(_build_long_text(target_chars), encoding="utf-8")
            for backend in backends:
                for focus_mode in text_focus_modes:
                    densities = skeleton_densities if focus_mode == "full" else ["adaptive"]
                    for skeleton_density in densities:
                        text_cases.append(
                            _benchmark_text_case(
                                label=f"book_{target_chars}_{focus_mode}_{skeleton_density}",
                                text_path=text_path,
                                backend=backend,
                                tokenizer_model=args.tokenizer_model,
                                iterations=iterations,
                                workspace=workspace,
                                focus_mode=focus_mode,
                                skeleton_density=skeleton_density,
                            )
                        )
        realistic_text_cases: list[dict[str, Any]] = []
        for backend in backends:
            for focus_mode in text_focus_modes:
                densities = skeleton_densities if focus_mode == "full" else ["adaptive"]
                for skeleton_density in densities:
                    case = _benchmark_text_case(
                        label=f"realistic_repo_docs_{focus_mode}_{skeleton_density}",
                        text_path=realistic_text_path,
                        backend=backend,
                        tokenizer_model=args.tokenizer_model,
                        iterations=iterations,
                        workspace=workspace,
                        focus_mode=focus_mode,
                        skeleton_density=skeleton_density,
                    )
                    case["sample_type"] = "realistic"
                    case["fixture_metadata"] = realistic_text_fixture
                    realistic_text_cases.append(case)

        directory_cases = [
            _benchmark_directory_case(
                label=f"{directory_path.name}_{focus_mode}_{skeleton_density}",
                source_dir=directory_path,
                backend=backend,
                tokenizer_model=args.tokenizer_model,
                iterations=iterations,
                workspace=workspace,
                focus_mode=focus_mode,
                skeleton_density=skeleton_density,
            )
            for backend in backends
            for focus_mode in directory_focus_modes
            for skeleton_density in (skeleton_densities if focus_mode == "full" else ["adaptive"])
        ]
        realistic_directory_cases = []
        for backend in backends:
            for focus_mode in directory_focus_modes:
                for skeleton_density in (skeleton_densities if focus_mode == "full" else ["adaptive"]):
                    case = _benchmark_directory_case(
                        label=f"{real_directory_path.name}_realistic_{focus_mode}_{skeleton_density}",
                        source_dir=real_directory_path,
                        backend=backend,
                        tokenizer_model=args.tokenizer_model,
                        iterations=iterations,
                        workspace=workspace,
                        focus_mode=focus_mode,
                        skeleton_density=skeleton_density,
                    )
                    case["sample_type"] = "realistic"
                    realistic_directory_cases.append(case)
        monorepo_directory_cases = []
        for backend in backends:
            for focus_mode in directory_focus_modes:
                for skeleton_density in (skeleton_densities if focus_mode == "full" else ["adaptive"]):
                    case = _benchmark_directory_case(
                        label=f"{monorepo_path.name}_monorepo_{focus_mode}_{skeleton_density}",
                        source_dir=monorepo_path,
                        backend=backend,
                        tokenizer_model=args.tokenizer_model,
                        iterations=iterations,
                        workspace=workspace,
                        focus_mode=focus_mode,
                        skeleton_density=skeleton_density,
                    )
                    case["sample_type"] = "monorepo"
                    case["fixture_metadata"] = monorepo_fixture
                    monorepo_directory_cases.append(case)
        directory_incremental_cases = [
            _benchmark_incremental_directory_case(
                label=f"{directory_path.name}_incremental",
                repo_dir=incremental_repo_dir,
                backend=backend,
                tokenizer_model=args.tokenizer_model,
                iterations=iterations,
                workspace=workspace,
                fixture_metadata=incremental_fixture_metadata,
            )
            for backend in backends
        ]
        full_density_directory_cases = [
            case
            for case in (directory_cases + realistic_directory_cases + monorepo_directory_cases)
            if case.get("compress", {}).get("focus_mode") == "full"
        ]
        full_density_text_cases = [
            case for case in (text_cases + realistic_text_cases) if case.get("compress", {}).get("focus_mode") == "full"
        ]
        full_directory_cases = [
            case
            for case in full_density_directory_cases
            if case.get("compress", {}).get("skeleton_density") == "adaptive" and case.get("sample_type") == "synthetic"
        ]
        full_text_cases = [
            case
            for case in full_density_text_cases
            if case.get("compress", {}).get("skeleton_density") == "adaptive" and case.get("sample_type") == "synthetic"
        ]
        realistic_full_directory_cases = [
            case
            for case in full_density_directory_cases
            if case.get("compress", {}).get("skeleton_density") == "adaptive" and case.get("sample_type") == "realistic"
        ]
        realistic_full_text_cases = [
            case
            for case in full_density_text_cases
            if case.get("compress", {}).get("skeleton_density") == "adaptive" and case.get("sample_type") == "realistic"
        ]
        incremental_comparison = _build_incremental_comparison(full_directory_cases, directory_incremental_cases)
        directory_focus_comparison = _build_focus_comparison(directory_cases + realistic_directory_cases + monorepo_directory_cases, expected_kind="directory")
        text_focus_comparison = _build_focus_comparison(text_cases + realistic_text_cases, expected_kind="text")
        directory_density_comparison = _build_density_comparison(full_density_directory_cases, expected_kind="directory")
        text_density_comparison = _build_density_comparison(full_density_text_cases, expected_kind="text")
        large_directory_recommendations = _build_best_verified_recommendations(
            directory_cases + realistic_directory_cases + monorepo_directory_cases,
            expected_kind="directory",
        )
        long_text_recommendations = _build_best_verified_recommendations(
            text_cases + realistic_text_cases,
            expected_kind="text",
        )
        scale_health = _build_scale_health(
            monorepo_cases=monorepo_directory_cases,
            realistic_directory_cases=realistic_directory_cases,
            monorepo_fixture=monorepo_fixture,
            thresholds=scale_health_thresholds,
        )
        release_readiness = _build_release_readiness(
            scale_health=scale_health,
            large_directory_recommendations=large_directory_recommendations,
            long_text_recommendations=long_text_recommendations,
            all_cases=(
                directory_cases
                + realistic_directory_cases
                + monorepo_directory_cases
                + directory_incremental_cases
                + text_cases
                + realistic_text_cases
            ),
        )
        all_benchmark_cases = (
            directory_cases
            + realistic_directory_cases
            + monorepo_directory_cases
            + directory_incremental_cases
            + text_cases
            + realistic_text_cases
        )
        regression_trends = _build_regression_trends(
            current_cases=all_benchmark_cases,
            baseline_report=baseline_report,
        )
        executive_summary = _build_executive_summary(
            release_readiness=release_readiness,
            scale_health=scale_health,
            regression_trends=regression_trends,
            large_directory_recommendations=large_directory_recommendations,
            long_text_recommendations=long_text_recommendations,
        )

        report = {
            "status": "ok",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repo_root": str(REPO_ROOT),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "tokenizer_model": args.tokenizer_model,
            "backends": backends,
            "iterations": iterations,
            "benchmark_inputs": {
                "synthetic_directory": str(directory_path),
                "realistic_directory": str(real_directory_path),
                "monorepo_directory": str(monorepo_path),
                "monorepo_fixture": monorepo_fixture,
                "realistic_text_fixture": realistic_text_fixture,
                "baseline_json": str(Path(args.baseline_json).expanduser().resolve()) if args.baseline_json else "",
            },
            "scale_health": scale_health,
            "release_readiness": release_readiness,
            "regression_trends": regression_trends,
            "executive_summary": executive_summary,
            "directory_cases": directory_cases,
            "realistic_directory_cases": realistic_directory_cases,
            "monorepo_directory_cases": monorepo_directory_cases,
            "directory_incremental_cases": directory_incremental_cases,
            "text_cases": text_cases,
            "realistic_text_cases": realistic_text_cases,
            "summaries": {
                "directory_cases": [_summarize_case(case) for case in directory_cases],
                "directory_full_cases": [_summarize_case(case) for case in full_directory_cases],
                "realistic_directory_cases": [_summarize_case(case) for case in realistic_directory_cases],
                "realistic_directory_full_cases": [_summarize_case(case) for case in realistic_full_directory_cases],
                "monorepo_directory_cases": [_summarize_case(case) for case in monorepo_directory_cases],
                "directory_incremental_cases": [_summarize_case(case) for case in directory_incremental_cases],
                "incremental_comparison": incremental_comparison,
                "text_cases": [_summarize_case(case) for case in text_cases],
                "text_full_cases": [_summarize_case(case) for case in full_text_cases],
                "realistic_text_cases": [_summarize_case(case) for case in realistic_text_cases],
                "realistic_text_full_cases": [_summarize_case(case) for case in realistic_full_text_cases],
                "directory_focus_cases": [_summarize_case(case) for case in (directory_cases + realistic_directory_cases + monorepo_directory_cases)],
                "directory_focus_comparison": directory_focus_comparison,
                "directory_density_comparison": directory_density_comparison,
                "large_directory_recommendations": large_directory_recommendations,
                "text_focus_cases": [_summarize_case(case) for case in (text_cases + realistic_text_cases)],
                "text_focus_comparison": text_focus_comparison,
                "text_density_comparison": text_density_comparison,
                "long_text_recommendations": long_text_recommendations,
            },
        }
        output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_md.write_text(_render_markdown(report), encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "ok",
                    "output_json": str(output_json),
                    "output_md": str(output_md),
                    "executive_summary": executive_summary,
                    "release_readiness": {
                        "status": release_readiness["status"],
                        "restore_verified": f"{release_readiness['restore_verified_count']}/{release_readiness['case_count']}",
                        "next_action": release_readiness["next_action"],
                    },
                    "regression_trends": {
                        "status": regression_trends["status"],
                        "matched_case_count": regression_trends["matched_case_count"],
                        "current_case_count": regression_trends["current_case_count"],
                        "restore_regression_count": len(regression_trends["restore_regressions"]),
                        "token_ratio_regression_count": len(regression_trends["token_ratio_regressions"]),
                        "compress_time_regression_count": len(regression_trends["compress_time_regressions"]),
                        "improvement_count": len(regression_trends["improvements"]),
                    },
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
