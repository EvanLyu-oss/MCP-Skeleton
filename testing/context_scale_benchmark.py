from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
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


def _run_cli(args: list[str], *, cwd: Path) -> tuple[int, float, str, str]:
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
    return proc.returncode, elapsed_ms, proc.stdout, proc.stderr


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
    if str(decoded.get("mode") or "") != "directory":
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
        "",
        "## Directory Cases",
        "",
    ]
    directory_rows = [
        [
            item["label"],
            item["backend"],
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
        for item in report["summaries"]["directory_cases"]
    ]
    lines.append(
        _markdown_table(
            [
                "Case",
                "Backend",
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
    lines.extend(["", "## Long Text Cases", ""])
    text_rows = [
        [
            item["label"],
            item["backend"],
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
        for item in report["summaries"]["text_cases"]
    ]
    lines.append(
        _markdown_table(
            [
                "Case",
                "Backend",
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
    lines.extend(["", "## Notes", ""])
    lines.append(
        "- `token_ratio` is the skeleton token footprint divided by the source token footprint; smaller is better."
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


def _benchmark_directory_case(
    *,
    label: str,
    source_dir: Path,
    backend: str,
    tokenizer_model: str,
    iterations: int,
    workspace: Path,
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
                "--input-dir",
                str(source_dir),
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


def _benchmark_text_case(
    *,
    label: str,
    text_path: Path,
    backend: str,
    tokenizer_model: str,
    iterations: int,
    workspace: Path,
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
        rc, elapsed_ms, stdout, stderr = _run_cli(
            [
                "context",
                "restore",
                "--package-file",
                str(manifest_path),
                "--emit-text",
            ],
            cwd=REPO_ROOT,
        )
        if rc != 0:
            raise RuntimeError(
                f"command failed ({rc}): context restore --package-file {manifest_path} --emit-text\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
        restored_text.write_text(stdout, encoding="utf-8")
        restore_times.append(elapsed_ms)
    assert compress_payload is not None and inspect_payload is not None
    restored_text = workspace / f"{label}_{backend}_restore_{iterations - 1}.md"
    return {
        "label": label,
        "backend": backend,
        "kind": "text",
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
    parser.add_argument("--iterations", type=int, default=2, help="Iterations per case/backend.")
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL, help="Tokenizer model/encoding to request.")
    parser.add_argument("--backends", nargs="*", help="Explicit tokenizer backends to benchmark.")
    parser.add_argument("--text-target-chars", nargs="*", type=int, default=DEFAULT_TEXT_TARGETS, help="Synthetic long-text sizes.")
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

    with tempfile.TemporaryDirectory(prefix="context_scale_benchmark.") as tmp:
        workspace = Path(tmp)
        directory_path = Path(args.directory).expanduser().resolve()
        text_targets = list(args.text_target_chars)
        iterations = max(1, args.iterations)
        if args.quick:
            directory_path = _build_directory_fixture(workspace)
            text_targets = QUICK_TEXT_TARGETS
            iterations = 1

        backends = _build_backends(args.backends, include_tiktoken=True)
        text_cases: list[dict[str, Any]] = []
        for target_chars in text_targets:
            text_path = workspace / f"synthetic_book_{target_chars}.md"
            text_path.write_text(_build_long_text(target_chars), encoding="utf-8")
            for backend in backends:
                text_cases.append(
                    _benchmark_text_case(
                        label=f"book_{target_chars}",
                        text_path=text_path,
                        backend=backend,
                        tokenizer_model=args.tokenizer_model,
                        iterations=iterations,
                        workspace=workspace,
                    )
                )

        directory_cases = [
            _benchmark_directory_case(
                label=directory_path.name,
                source_dir=directory_path,
                backend=backend,
                tokenizer_model=args.tokenizer_model,
                iterations=iterations,
                workspace=workspace,
            )
            for backend in backends
        ]

        report = {
            "status": "ok",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repo_root": str(REPO_ROOT),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "tokenizer_model": args.tokenizer_model,
            "backends": backends,
            "iterations": iterations,
            "directory_cases": directory_cases,
            "text_cases": text_cases,
            "summaries": {
                "directory_cases": [_summarize_case(case) for case in directory_cases],
                "text_cases": [_summarize_case(case) for case in text_cases],
            },
        }
        output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_md.write_text(_render_markdown(report), encoding="utf-8")
        print(json.dumps({"status": "ok", "output_json": str(output_json), "output_md": str(output_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
