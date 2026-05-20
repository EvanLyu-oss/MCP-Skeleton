from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "testing" / "results"
DEFAULT_RESULTS_JSON = RESULTS_DIR / "cli_smoke_python_results.json"


class SmokeFailure(AssertionError):
    pass


def _run(args: list[str], *, cwd: Path = ROOT, expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.returncode != expect:
        raise SmokeFailure(
            f"command failed: {' '.join(args)}\n"
            f"expected exit {expect}, got {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def _run_cli_json(args: list[str], *, cwd: Path = ROOT, expect: int = 0) -> dict[str, Any]:
    proc = _run([sys.executable, "-m", "cli", *args], cwd=cwd, expect=expect)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"command did not emit JSON: {' '.join(args)}\nSTDOUT:\n{proc.stdout}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(args: list[str], *, cwd: Path) -> None:
    _run(["git", *args], cwd=cwd)


def _check_py_compile(workspace: Path) -> None:
    del workspace
    _run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(ROOT / "cli" / "ail_cli.py"),
            str(ROOT / "cli" / "context_compression.py"),
            str(ROOT / "testing" / "context_scale_benchmark.py"),
        ]
    )


def _check_preset_json(workspace: Path) -> None:
    del workspace
    payload = _run_cli_json(["context", "preset", "--json"])
    assert payload["status"] == "ok"
    assert payload["selected_preset"]["preset_id"] == "generic"
    assert payload["preset_count"] >= 5


def _check_text_restore(workspace: Path) -> None:
    text_file = workspace / "long_text.md"
    text_file.write_text(
        "# MCP Skeleton\n\n"
        "This is a cross-platform smoke paragraph about exact restore and context compression.\n",
        encoding="utf-8",
    )
    bundle_dir = workspace / "text_bundle"
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(text_file),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["compression_mode"] == "text"

    restore_file = workspace / "restored_text.md"
    restore = _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-file",
            str(restore_file),
            "--json",
        ]
    )
    assert restore["status"] == "ok"
    assert _sha256(text_file) == _sha256(restore_file)


def _check_text_writing_outline(workspace: Path) -> None:
    text_file = workspace / "outline_text.md"
    text_file.write_text(
        "# MCP Skeleton\n\n"
        "This paragraph keeps restore fidelity while exposing chapter and section outlines.\n\n"
        "## Notes\n\n"
        "The writing-outline view should show enough structure for long-form review.\n",
        encoding="utf-8",
    )
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(text_file),
            "--focus-mode",
            "writing-outline",
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["focus_mode"] == "writing-outline"
    assert "FOCUS_MODE: writing-outline" in payload["skeleton_text"]
    assert "CHAPTER_FOLDS:" in payload["skeleton_text"]
    assert "HEADINGS:" in payload["skeleton_text"]
    assert "SECTIONS:" in payload["skeleton_text"]


def _check_text_density(workspace: Path) -> None:
    text_file = workspace / "large_text.md"
    parts = []
    for idx in range(1, 181):
        parts.append(
            f"# Chapter {idx}\n\n"
            "This chapter keeps repeating context compression continuity, exact restore, "
            f"patch replay, and benchmark harness language {idx}.\n\n"
            "## Notes\n\n"
            "The structure should stay visible while compact skeletons get more selective.\n"
        )
    text_file.write_text("\n".join(parts), encoding="utf-8")
    standard = _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(text_file),
            "--skeleton-density",
            "standard",
            "--json",
        ]
    )
    compact = _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(text_file),
            "--skeleton-density",
            "compact",
            "--json",
        ]
    )
    assert standard["status"] == "ok"
    assert compact["status"] == "ok"
    assert standard["skeleton_density"] == "standard"
    assert compact["skeleton_density"] == "compact"
    assert "SKELETON_DENSITY: standard" in standard["skeleton_text"]
    assert "SKELETON_DENSITY: compact" in compact["skeleton_text"]
    assert compact["source_summary"]["chapter_group_count"] >= 6
    assert "CHAPTER_FOLDS:" in compact["skeleton_text"]
    assert compact["skeleton_char_count"] < standard["skeleton_char_count"]
    assert "... (+" in compact["skeleton_text"]


def _check_non_utf8_text_restore(workspace: Path) -> None:
    source = workspace / "gbk_notes.md"
    source.write_bytes("# 标题\n\n这是 GBK 编码文本，用于测试无损恢复。\n".encode("gb18030"))
    bundle_dir = workspace / "gbk_bundle"
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(source),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["source_summary"]["source_encoding"] in {"gb2312", "gb18030"}
    restored = workspace / "gbk_restored.md"
    _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-file",
            str(restored),
            "--json",
        ]
    )
    assert _sha256(source) == _sha256(restored)


def _check_directory_restore(workspace: Path) -> None:
    project = workspace / "project"
    (project / "src").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "empty" / "leaf").mkdir(parents=True)
    (project / "src" / "app.py").write_text("def run() -> str:\n    return 'alpha'\n", encoding="utf-8")
    (project / "docs" / "notes.md").write_text("# Notes\n\nDirectory restore smoke.\n", encoding="utf-8")
    (project / "assets.bin").write_bytes(bytes(range(32)))

    bundle_dir = workspace / "dir_bundle"
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["compression_mode"] == "directory"
    assert payload["source_summary"]["total_files"] == 3

    restore_root = workspace / "dir_restore"
    restore = _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(restore_root),
            "--json",
        ]
    )
    assert restore["status"] == "ok"
    restored_project = restore_root / "project"
    for rel in ["src/app.py", "docs/notes.md", "assets.bin"]:
        assert _sha256(project / rel) == _sha256(restored_project / rel)
    assert (restored_project / "empty" / "leaf").is_dir()


def _build_simple_project(workspace: Path, *, name: str = "simple_project", with_git: bool = False) -> Path:
    project = workspace / name
    (project / "src").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "src" / "app.py").write_text(
        "from pathlib import Path\n\n"
        "def run() -> str:\n"
        "    return 'alpha'\n",
        encoding="utf-8",
    )
    (project / "src" / "utils.py").write_text("def helper() -> int:\n    return 3\n", encoding="utf-8")
    (project / "docs" / "notes.md").write_text("Initial note.\n", encoding="utf-8")
    if with_git:
        _git(["init", "-q"], cwd=project)
        _git(["config", "user.email", "smoke@example.com"], cwd=project)
        _git(["config", "user.name", "Python Smoke"], cwd=project)
        _git(["add", "."], cwd=project)
        _git(["commit", "-q", "-m", "initial"], cwd=project)
    return project


def _check_bundle_outputs(workspace: Path) -> None:
    project = _build_simple_project(workspace, name="bundle_project", with_git=True)
    (project / "src" / "app.py").write_text(
        "from pathlib import Path\n\n"
        "def run() -> str:\n"
        "    return 'beta'\n",
        encoding="utf-8",
    )
    (project / "src" / "new.py").write_text("def created() -> str:\n    return 'new'\n", encoding="utf-8")
    (project / "docs" / "notes.md").unlink()

    bundle_dir = workspace / "context_bundle"
    bundle = _run_cli_json(
        ["context", "bundle", "--input-dir", str(project), "--output-dir", str(bundle_dir), "--json"]
    )
    assert bundle["status"] == "ok"
    assert bundle["entrypoint"] == "context-bundle"
    assert bundle["file_count"] >= 7
    assert (bundle_dir / "context_manifest.json").exists()
    assert (bundle_dir / "context_skeleton.mcp").exists()

    incremental_dir = workspace / "context_bundle_incremental"
    incremental = _run_cli_json(
        [
            "context",
            "bundle",
            "--input-dir",
            str(project),
            "--incremental",
            "--output-dir",
            str(incremental_dir),
            "--json",
        ]
    )
    assert incremental["status"] == "ok"
    assert incremental["incremental_mode"] is True
    assert incremental["incremental_changed_paths"] == ["src/app.py"]
    assert incremental["incremental_added_paths"] == ["src/new.py"]
    assert incremental["incremental_removed_paths"] == ["docs/notes.md"]


def _check_clean_incremental_diagnostics(workspace: Path) -> None:
    project = _build_simple_project(workspace, name="clean_incremental_project", with_git=True)
    payload = _run_cli_json(["context", "compress", "--input-dir", str(project), "--incremental", "--json"])
    assert payload["status"] == "ok"
    assert payload["incremental_mode"] is True
    assert payload["incremental_path_count"] == 0
    assert payload["incremental_changed_paths"] == []
    assert payload["incremental_added_paths"] == []
    assert payload["incremental_removed_paths"] == []
    assert payload["incremental_diagnostics"]["no_changes_detected"] is True
    assert payload["incremental_diagnostics"]["notes"]
    assert "No git changes were detected" in payload["incremental_diagnostics"]["notes"][0]


def _check_apply_check_drift(workspace: Path) -> None:
    source_text = workspace / "apply_source.md"
    source_text.write_text(
        "# MCP Skeleton\n\n"
        "This is one long test paragraph about preserving restore fidelity while shrinking the AI-facing context surface.\n",
        encoding="utf-8",
    )
    text_bundle = workspace / "apply_text_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(source_text),
            "--output-dir",
            str(text_bundle),
            "--json",
        ]
    )
    drift_text = workspace / "drift_text.md"
    drift_text.write_text("Tiny unrelated note.\n", encoding="utf-8")
    text_drift = _run_cli_json(
        [
            "context",
            "apply-check",
            "--package-file",
            str(text_bundle / "context_manifest.json"),
            "--text-file",
            str(drift_text),
            "--json",
        ],
        expect=3,
    )
    assert text_drift["status"] == "warning"
    assert text_drift["apply_check_passed"] is False
    assert text_drift["alignment_band"] == "drifting"
    assert text_drift["drift_findings"]
    assert text_drift["revision_targets"]

    project = _build_simple_project(workspace, name="apply_dir_source")
    dir_bundle = workspace / "apply_dir_bundle"
    _run_cli_json(
        ["context", "compress", "--input-dir", str(project), "--output-dir", str(dir_bundle), "--json"]
    )
    drift_dir = workspace / "apply_dir_drift"
    (drift_dir / "src").mkdir(parents=True)
    (drift_dir / "docs").mkdir()
    (drift_dir / "extras").mkdir()
    (drift_dir / "src" / "app.py").write_text(
        "from pathlib import Path\n\n"
        "def run() -> str:\n"
        "    return 'drifted'\n",
        encoding="utf-8",
    )
    (drift_dir / "docs" / "notes.md").write_text("Symlink fallback content on platforms without symlink support.\n", encoding="utf-8")
    for idx in range(1, 6):
        (drift_dir / "extras" / f"extra_{idx}.txt").write_text(f"extra {idx}\n", encoding="utf-8")
    dir_drift = _run_cli_json(
        [
            "context",
            "apply-check",
            "--package-file",
            str(dir_bundle / "context_manifest.json"),
            "--input-dir",
            str(drift_dir),
            "--json",
        ],
        expect=3,
    )
    assert dir_drift["status"] == "warning"
    assert dir_drift["apply_check_passed"] is False
    assert dir_drift["alignment_band"] == "drifting"
    assert any("file tree dropped" in finding.lower() for finding in dir_drift["drift_findings"])
    assert any("large number of files" in finding.lower() for finding in dir_drift["drift_findings"])
    assert dir_drift["revision_targets"]


def _check_directory_filtering(workspace: Path) -> None:
    project = workspace / "filter_project"
    (project / "src").mkdir(parents=True)
    (project / "logs").mkdir()
    (project / "node_modules" / "pkg").mkdir(parents=True)
    (project / "dist").mkdir()
    (project / ".mcp-skeletonignore").write_text("logs/\nnode_modules/\n*.tmp\n", encoding="utf-8")
    (project / "README.md").write_text("# Filter Project\n", encoding="utf-8")
    (project / "src" / "app.py").write_text("def keep() -> str:\n    return 'included'\n", encoding="utf-8")
    (project / "logs" / "debug.log").write_text("ignored log\n", encoding="utf-8")
    (project / "node_modules" / "pkg" / "index.js").write_text("ignored dependency\n", encoding="utf-8")
    (project / "dist" / "app.js").write_text("ignored build\n", encoding="utf-8")
    (project / "src" / "app.py.map").write_text("ignored map\n", encoding="utf-8")
    (project / "tmp.tmp").write_text("ignored tmp\n", encoding="utf-8")

    bundle_dir = workspace / "filter_bundle"
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--exclude",
            "dist/",
            "--exclude",
            "*.map",
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    summary = payload["source_summary"]
    assert summary["filtered_path_count"] >= 5
    paths = {item["relative_path"] for item in summary["entries"]}
    assert "README.md" in paths
    assert "src/app.py" in paths
    assert "logs/debug.log" not in paths
    assert "node_modules/pkg/index.js" not in paths
    assert "dist/app.js" not in paths
    assert "src/app.py.map" not in paths
    assert "tmp.tmp" not in paths

    restore_root = workspace / "filter_restore"
    _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(restore_root),
            "--json",
        ]
    )
    restored = restore_root / "filter_project"
    assert (restored / "README.md").exists()
    assert (restored / "src" / "app.py").exists()
    assert not (restored / "logs" / "debug.log").exists()
    assert not (restored / "dist" / "app.js").exists()


def _check_directory_focus_density(workspace: Path) -> None:
    project = workspace / "focus_project"
    (project / "src").mkdir(parents=True)
    (project / "docs").mkdir()
    for idx in range(1, 45):
        (project / "src" / f"module_{idx:02d}.py").write_text(
            "import json\n\n"
            f"def function_{idx}(value: str) -> str:\n"
            "    return json.dumps({'value': value})\n",
            encoding="utf-8",
        )
        (project / "docs" / f"chapter_{idx:02d}.md").write_text(
            f"# Chapter {idx}\n\nThis chapter preserves writing context for focus testing.\n",
            encoding="utf-8",
        )

    codebase = _run_cli_json(
        ["context", "compress", "--preset", "codebase", "--input-dir", str(project), "--json"]
    )
    writing = _run_cli_json(
        ["context", "compress", "--preset", "writing", "--input-dir", str(project), "--json"]
    )
    symbols = _run_cli_json(
        [
            "context",
            "compress",
            "--preset",
            "codebase",
            "--focus-mode",
            "symbols",
            "--input-dir",
            str(project),
            "--json",
        ]
    )
    standard = _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--skeleton-density",
            "standard",
            "--json",
        ]
    )
    compact = _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--skeleton-density",
            "compact",
            "--json",
        ]
    )

    assert codebase["status"] == "ok"
    assert writing["status"] == "ok"
    assert symbols["status"] == "ok"
    assert symbols["focus_mode"] == "symbols"
    assert "FOCUS_MODE: symbols" in symbols["skeleton_text"]
    assert "SYMBOLS:" in symbols["skeleton_text"]
    assert codebase["skeleton_text"] != writing["skeleton_text"]
    assert compact["skeleton_char_count"] < standard["skeleton_char_count"]


def _check_directory_symbols(workspace: Path) -> None:
    project = workspace / "symbols_project"
    (project / "src").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "src" / "app.py").write_text(
        "import json\n\n"
        "class AppRunner:\n"
        "    def run(self, value: str) -> str:\n"
        "        return json.dumps({'value': value})\n",
        encoding="utf-8",
    )
    (project / "src" / "helpers.py").write_text(
        "from pathlib import Path\n\n"
        "def helper(path: Path) -> str:\n"
        "    return path.name\n",
        encoding="utf-8",
    )
    (project / "docs" / "notes.md").write_text("# Notes\n\nSymbol focus should prefer code shape.\n", encoding="utf-8")
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--preset",
            "codebase",
            "--focus-mode",
            "symbols",
            "--input-dir",
            str(project),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["focus_mode"] == "symbols"
    assert "FOCUS_MODE: symbols" in payload["skeleton_text"]
    assert "SYMBOLS:" in payload["skeleton_text"]
    assert "IMPORTS:" not in payload["skeleton_text"]
    assert "TREE:" not in payload["skeleton_text"]


def _check_directory_aggregation(workspace: Path) -> None:
    project = workspace / "large_project"
    for rel in ["src/api", "src/core", "docs", "tests", "scripts", "examples"]:
        (project / rel).mkdir(parents=True)
    for idx in range(1, 51):
        (project / "src" / "api" / f"handler_{idx}.py").write_text(
            "from pathlib import Path\n\n"
            f"def handler_{idx}() -> str:\n"
            f"    return 'api-{idx}'\n",
            encoding="utf-8",
        )
        (project / "src" / "core" / f"service_{idx}.py").write_text(
            "import json\n\n"
            f"def service_{idx}() -> str:\n"
            f"    return 'core-{idx}'\n",
            encoding="utf-8",
        )
    for idx in range(1, 21):
        (project / "docs" / f"chapter_{idx}.md").write_text(
            f"# Chapter {idx}\n\nThis chapter describes context compression structure {idx}.\n",
            encoding="utf-8",
        )
        (project / "tests" / f"test_case_{idx}.py").write_text(
            f"def test_case_{idx}() -> None:\n    assert True\n",
            encoding="utf-8",
        )
    for idx in range(1, 11):
        (project / "scripts" / f"task_{idx}.sh").write_text(
            "#!/bin/sh\n"
            f"echo task-{idx}\n",
            encoding="utf-8",
        )
        (project / "examples" / f"snippet_{idx}.md").write_text(
            f"# Example {idx}\n\nThis example mirrors compression usage {idx}.\n",
            encoding="utf-8",
        )

    standard = _run_cli_json(
        [
            "context",
            "compress",
            "--preset",
            "codebase",
            "--input-dir",
            str(project),
            "--skeleton-density",
            "standard",
            "--json",
        ]
    )
    adaptive = _run_cli_json(
        [
            "context",
            "compress",
            "--preset",
            "codebase",
            "--input-dir",
            str(project),
            "--skeleton-density",
            "adaptive",
            "--json",
        ]
    )
    assert standard["status"] == "ok"
    assert adaptive["status"] == "ok"
    assert adaptive["source_summary"]["directory_groups"]
    assert adaptive["source_summary"]["extension_mix"]
    assert "DIRECTORY_GROUPS:" in adaptive["skeleton_text"]
    assert "HOT_SUBTREES:" in adaptive["skeleton_text"]
    assert "COLLAPSED_SUBTREES:" in adaptive["skeleton_text"]
    assert "EXTENSION_MIX:" in adaptive["skeleton_text"]
    assert "sample_paths=" in adaptive["skeleton_text"]
    assert "roots=" in adaptive["skeleton_text"]
    assert adaptive["skeleton_char_count"] < standard["skeleton_char_count"]
    assert "... (+" in adaptive["skeleton_text"]


def _build_incremental_repo(workspace: Path, *, name: str = "incremental_project") -> Path:
    project = workspace / name
    (project / "src").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "src" / "app.py").write_text("def run() -> str:\n    return 'base'\n", encoding="utf-8")
    (project / "docs" / "notes.md").write_text("Initial notes.\n", encoding="utf-8")
    _git(["init", "-q"], cwd=project)
    _git(["config", "user.email", "smoke@example.com"], cwd=project)
    _git(["config", "user.name", "Python Smoke"], cwd=project)
    _git(["add", "."], cwd=project)
    _git(["commit", "-q", "-m", "base"], cwd=project)
    (project / "src" / "app.py").write_text("def run() -> str:\n    return 'changed'\n", encoding="utf-8")
    (project / "src" / "new.py").write_text("def added() -> str:\n    return 'new'\n", encoding="utf-8")
    (project / "docs" / "notes.md").unlink()
    return project


def _check_incremental_compress_restore(workspace: Path) -> None:
    project = _build_incremental_repo(workspace)
    bundle_dir = workspace / "incremental_bundle"
    payload = _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--incremental",
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["incremental_mode"] is True
    assert payload["incremental_changed_paths"] == ["src/app.py"]
    assert payload["incremental_added_paths"] == ["src/new.py"]
    assert payload["incremental_removed_paths"] == ["docs/notes.md"]
    assert payload["incremental_path_count"] == 3

    inspect = _run_cli_json(
        ["context", "inspect", "--package-file", str(bundle_dir / "context_manifest.json"), "--json"]
    )
    assert inspect["status"] == "ok"
    assert inspect["incremental_mode"] is True
    assert inspect["incremental_path_count"] == 3

    restore_root = workspace / "incremental_restore"
    restore = _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(restore_root),
            "--json",
        ]
    )
    assert restore["status"] == "ok"
    restored = restore_root / project.name
    assert _sha256(project / "src" / "app.py") == _sha256(restored / "src" / "app.py")
    assert _sha256(project / "src" / "new.py") == _sha256(restored / "src" / "new.py")
    manifest = json.loads((restored / ".ail_incremental_manifest.json").read_text(encoding="utf-8"))
    assert manifest["removed_paths"] == ["docs/notes.md"]


def _check_apply_patch_roundtrip(workspace: Path) -> None:
    source = workspace / "source.md"
    candidate = workspace / "candidate.md"
    source.write_text("# Plan\n\nOriginal context.\n", encoding="utf-8")
    candidate.write_text("# Plan\n\nOriginal context with a safe update.\n", encoding="utf-8")
    bundle_dir = workspace / "patch_source_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(source),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    apply_check = _run_cli_json(
        [
            "context",
            "apply-check",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--text-file",
            str(candidate),
            "--json",
        ]
    )
    assert apply_check["status"] == "ok"
    assert apply_check["apply_check_passed"] is True

    patch_dir = workspace / "patch_bundle"
    patch = _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--text-file",
            str(candidate),
            "--output-dir",
            str(patch_dir),
            "--json",
        ]
    )
    assert patch["status"] == "ok"

    output_file = workspace / "patched.md"
    replay = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--output-file",
            str(output_file),
            "--json",
        ]
    )
    assert replay["status"] == "ok"
    assert _sha256(candidate) == _sha256(output_file)


def _check_patch_text_manifest(workspace: Path) -> None:
    source = workspace / "text_patch_source.md"
    candidate = workspace / "text_patch_candidate.md"
    source.write_text("# Plan\n\nOriginal context.\n", encoding="utf-8")
    candidate.write_text("# Plan\n\nOriginal context with a targeted update.\n", encoding="utf-8")
    bundle_dir = workspace / "text_patch_source_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(source),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    patch_dir = workspace / "text_patch_bundle"
    payload = _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--text-file",
            str(candidate),
            "--output-dir",
            str(patch_dir),
            "--json",
        ]
    )
    manifest = json.loads((patch_dir / "patch_manifest.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["patch_mode"] == "text_unified_diff"
    assert payload["changed_paths"] == [candidate.name]
    assert manifest["patch_mode"] == "text_unified_diff"
    assert manifest["change_counts"]["changed_paths"] == 1
    assert manifest["files"]["candidate_snapshot_file"].endswith("candidate_snapshot.txt")
    assert (patch_dir / "candidate_snapshot.txt").exists()
    assert _sha256(candidate) == _sha256(patch_dir / "candidate_snapshot.txt")


def _check_patch_incremental_manifest(workspace: Path) -> None:
    project = _build_incremental_repo(workspace, name="incremental_patch_manifest_project")
    bundle_dir = workspace / "incremental_patch_manifest_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--incremental",
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    restore_root = workspace / "incremental_patch_manifest_restore"
    _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(restore_root),
            "--json",
        ]
    )
    candidate = workspace / "incremental_patch_manifest_candidate"
    shutil.copytree(restore_root / project.name, candidate)
    (candidate / "src" / "app.py").write_text("def run() -> str:\n    return 'candidate'\n", encoding="utf-8")
    (candidate / "docs").mkdir(exist_ok=True)
    (candidate / "docs" / "notes.md").write_text("Recovered note.\n", encoding="utf-8")

    patch_dir = workspace / "incremental_patch_manifest_patch"
    payload = _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--input-dir",
            str(candidate),
            "--output-dir",
            str(patch_dir),
            "--json",
        ]
    )
    manifest = json.loads((patch_dir / "patch_manifest.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["incremental_mode"] is True
    assert payload["incremental_changed_paths"] == ["src/app.py"]
    assert payload["incremental_added_paths"] == ["src/new.py"]
    assert payload["incremental_removed_paths"] == []
    assert payload["changed_paths"] == ["src/app.py"]
    assert payload["added_paths"] == ["docs/notes.md"]
    assert manifest["incremental_mode"] is True
    assert manifest["incremental_changed_paths"] == ["src/app.py"]
    assert manifest["incremental_added_paths"] == ["src/new.py"]
    assert manifest["incremental_removed_paths"] == []
    assert manifest["change_counts"]["added_paths"] == 1
    assert manifest["change_counts"]["changed_paths"] == 1


def _check_patch_apply_merge_conflict(workspace: Path) -> None:
    source = workspace / "merge_source.md"
    candidate = workspace / "merge_candidate.md"
    target = workspace / "merge_target.md"
    source.write_text("# Merge\n\nOriginal content.\n", encoding="utf-8")
    candidate.write_text("# Merge\n\nUpdated candidate content.\n", encoding="utf-8")
    target.write_text("Conflicting local edit before replay.\n", encoding="utf-8")

    bundle_dir = workspace / "merge_source_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--text-file",
            str(source),
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    patch_dir = workspace / "merge_patch_bundle"
    _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--text-file",
            str(candidate),
            "--output-dir",
            str(patch_dir),
            "--json",
        ]
    )
    payload = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--merge-mode",
            "reject-conflicts",
            "--output-file",
            str(target),
            "--json",
        ],
        expect=3,
    )
    assert payload["status"] == "warning"
    assert payload["apply_mode"] == "merge_conflict_blocked"
    assert payload["merge_check_passed"] is False
    assert payload["merge_conflict_count"] >= 1
    assert target.read_text(encoding="utf-8") == "Conflicting local edit before replay.\n"


def _check_directory_patch_apply_reports(workspace: Path) -> None:
    original = workspace / "mixed_original"
    modified = workspace / "mixed_modified"
    for root in [original, modified]:
        (root / "subdir").mkdir(parents=True)
    (original / "file1.txt").write_text("alpha\n", encoding="utf-8")
    (original / "file2.txt").write_text("remove me\n", encoding="utf-8")
    (original / "subdir" / "file3.txt").write_text("keep me\n", encoding="utf-8")
    (modified / "file1.txt").write_text("alpha updated\n", encoding="utf-8")
    (modified / "file5.txt").write_text("brand new\n", encoding="utf-8")
    (modified / "subdir" / "file3.txt").write_text("keep me edited\n", encoding="utf-8")

    bundle_dir = workspace / "mixed_bundle"
    _run_cli_json(
        ["context", "bundle", "--input-dir", str(original), "--output-dir", str(bundle_dir), "--json"]
    )
    patch_dir = workspace / "mixed_patch"
    patch = _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--input-dir",
            str(modified),
            "--output-dir",
            str(patch_dir),
            "--json",
        ],
        expect=3,
    )
    assert patch["change_counts"]["added_paths"] == 1
    assert patch["change_counts"]["removed_paths"] == 1
    assert patch["change_counts"]["changed_paths"] >= 2

    output_dir = workspace / "mixed_output"
    applied = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--policy-mode",
            "open",
            "--merge-mode",
            "overwrite",
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    assert applied["status"] == "ok"
    replayed = output_dir / "mixed_original"
    for rel in ["file1.txt", "file5.txt", "subdir/file3.txt"]:
        assert _sha256(modified / rel) == _sha256(replayed / rel)
    assert not (replayed / "file2.txt").exists()

    dry_output = workspace / "dry_output"
    dry_report = workspace / "dry_run_report.json"
    dry_run = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--dry-run",
            "--write-dry-run-report",
            str(dry_report),
            "--output-dir",
            str(dry_output),
            "--json",
        ]
    )
    report = json.loads(dry_report.read_text(encoding="utf-8"))
    assert dry_run["dry_run"] is True
    assert report["dry_run"] is True
    assert report["surface_size"] >= 1
    assert report["risk_band"] in {"small", "medium", "large"}
    assert not dry_output.exists()

    blocked = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--policy-mode",
            "strict",
            "--output-dir",
            str(workspace / "policy_blocked_output"),
            "--json",
        ],
        expect=3,
    )
    assert blocked["status"] == "warning"
    assert blocked["apply_mode"] == "policy_blocked"
    assert blocked["policy_passed"] is False


def _check_incremental_patch_apply_reports(workspace: Path) -> None:
    project = _build_incremental_repo(workspace, name="incremental_patch_project")
    bundle_dir = workspace / "incremental_patch_bundle"
    _run_cli_json(
        [
            "context",
            "compress",
            "--input-dir",
            str(project),
            "--incremental",
            "--output-dir",
            str(bundle_dir),
            "--json",
        ]
    )
    restore_root = workspace / "incremental_patch_restore"
    _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(restore_root),
            "--json",
        ]
    )
    candidate = workspace / "incremental_candidate"
    restored = restore_root / project.name
    shutil.copytree(restored, candidate)
    (candidate / "docs").mkdir(exist_ok=True)
    (candidate / "src" / "app.py").write_text("def run() -> str:\n    return 'candidate'\n", encoding="utf-8")
    (candidate / "docs" / "notes.md").write_text("Recovered note.\n", encoding="utf-8")

    apply_check = _run_cli_json(
        [
            "context",
            "apply-check",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--input-dir",
            str(candidate),
            "--json",
        ]
    )
    assert apply_check["status"] == "ok"
    assert apply_check["apply_check_passed"] is True
    assert apply_check["incremental_mode"] is True
    assert apply_check["incremental_changed_paths"] == ["src/app.py"]
    assert apply_check["incremental_added_paths"] == ["src/new.py"]
    assert apply_check["incremental_removed_paths"] == []
    assert apply_check["incremental_path_count"] == 2

    patch_dir = workspace / "incremental_patch"
    patch = _run_cli_json(
        [
            "context",
            "patch",
            "--package-file",
            str(bundle_dir / "context_manifest.json"),
            "--input-dir",
            str(candidate),
            "--output-dir",
            str(patch_dir),
            "--json",
        ]
    )
    assert patch["incremental_mode"] is True
    assert patch["incremental_changed_paths"] == ["src/app.py"]
    assert patch["incremental_added_paths"] == ["src/new.py"]
    assert patch["incremental_removed_paths"] == []
    assert patch["added_paths"] == ["docs/notes.md"]

    output_dir = workspace / "incremental_replay"
    replay = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    replayed = output_dir / project.name
    assert replay["status"] == "ok"
    assert replay["incremental_mode"] is True
    assert replay["apply_mode"] == "directory_incremental_restore_plus_overlay"
    assert replay["incremental_changed_paths"] == ["src/app.py"]
    assert replay["incremental_added_paths"] == ["src/new.py"]
    assert replay["incremental_removed_paths"] == []
    for rel in ["src/app.py", "src/new.py", "docs/notes.md"]:
        assert _sha256(candidate / rel) == _sha256(replayed / rel)
    manifest = json.loads((replayed / ".ail_incremental_manifest.json").read_text(encoding="utf-8"))
    assert manifest["removed_paths"] == []

    dry_report = workspace / "incremental_dry_run_report.json"
    dry_output = workspace / "incremental_dry_output"
    dry = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--patch-file",
            str(patch_dir / "patch_manifest.json"),
            "--source-package-file",
            str(bundle_dir / "context_manifest.json"),
            "--dry-run",
            "--write-dry-run-report",
            str(dry_report),
            "--output-dir",
            str(dry_output),
            "--json",
        ]
    )
    report = json.loads(dry_report.read_text(encoding="utf-8"))
    assert dry["dry_run"] is True
    assert dry["incremental_mode"] is True
    assert report["dry_run"] is True
    assert report["incremental_mode"] is True
    assert report["incremental_change_counts"]["changed_paths"] == 1
    assert report["incremental_change_counts"]["added_paths"] == 1
    assert report["incremental_change_counts"]["removed_paths"] == 0
    assert report["first_incremental_changed_path"] == "src/app.py"
    assert report["first_incremental_added_path"] == "src/new.py"
    assert report["first_incremental_removed_path"] == ""
    assert not dry_output.exists()


def _check_policy_template_json(workspace: Path) -> None:
    del workspace
    payload = _run_cli_json(
        [
            "context",
            "patch-apply",
            "--sample-policy",
            "strict",
            "--allow-root",
            "src",
            "--forbid-root",
            "src/generated",
            "--emit-policy-template",
            "--json",
        ]
    )
    assert payload["status"] == "ok"
    assert payload["policy_mode"] == "strict"
    assert "src" in payload["policy_template"]["allow_roots"]
    assert "src/generated" in payload["policy_template"]["forbid_roots"]


def _check_invalid_input_dir(workspace: Path) -> None:
    missing = workspace / "missing"
    payload = _run_cli_json(
        ["context", "compress", "--input-dir", str(missing), "--json"],
        expect=2,
    )
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_usage"


def _check_restore_invalid_relpath(workspace: Path) -> None:
    invalid_manifest = workspace / "invalid_manifest.json"
    invalid_manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "compression_mode": "directory",
                "source_kind": "mixed_project",
                "source_label": "bad",
                "restore_package": {
                    "encoding": "zlib+base64+json",
                    "sha256": "",
                    "raw_byte_count": 0,
                    "compressed_byte_count": 0,
                    "payload": "",
                },
            }
        ),
        encoding="utf-8",
    )
    import base64
    import zlib

    decoded = {
        "mode": "directory",
        "source_label": "bad",
        "source_kind": "mixed_project",
        "root_name": "bad",
        "files": [
            {
                "relative_path": "../escape.txt",
                "content_b64": base64.b64encode(b"bad").decode("ascii"),
                "sha256": hashlib.sha256(b"bad").hexdigest(),
            }
        ],
        "symlinks": [],
        "empty_dirs": [],
    }
    raw = json.dumps(decoded, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    manifest = json.loads(invalid_manifest.read_text(encoding="utf-8"))
    manifest["restore_package"] = {
        "encoding": "zlib+base64+json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "raw_byte_count": len(raw),
        "compressed_byte_count": len(compressed),
        "payload": base64.b64encode(compressed).decode("ascii"),
    }
    invalid_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    payload = _run_cli_json(
        [
            "context",
            "restore",
            "--package-file",
            str(invalid_manifest),
            "--output-dir",
            str(workspace / "invalid_restore"),
            "--json",
        ],
        expect=2,
    )
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_usage"


def _check_scale_benchmark_quick(workspace: Path) -> None:
    output_json = workspace / "benchmark.json"
    output_md = workspace / "benchmark.md"
    proc = _run(
        [
            sys.executable,
            str(ROOT / "testing" / "context_scale_benchmark.py"),
            "--quick",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=ROOT,
    )
    stdout_payload = json.loads(proc.stdout)
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert output_md.exists()
    assert stdout_payload["status"] == "ok"
    assert stdout_payload["executive_summary"]["overall_status"] in {"ready", "watch"}
    assert report["status"] == "ok"
    assert report["release_readiness"]["restore_verified_count"] == report["release_readiness"]["case_count"]
    assert report["scale_health"]["status"] in {"ok", "warn"}
    assert report["executive_summary"]["large_directory_recommendations"]
    assert report["executive_summary"]["long_text_recommendations"]
    for key in ["large_directory_recommendations", "long_text_recommendations"]:
        preview = report["executive_summary"][key][0]
        assert "savings_percent_vs_baseline" in preview
        assert preview["candidate_count"] >= preview["verified_candidate_count"] >= 1
        recommendation = report["summaries"][key][0]
        assert "recommended_compress_ms_avg" in recommendation
        assert "baseline_compress_ms_avg" in recommendation
        assert "compress_time_ratio_vs_baseline" in recommendation
        assert "token_ratio_span_verified" in recommendation
    assert max(item["skeleton_token_savings_percent_vs_baseline"] for item in report["summaries"]["large_directory_recommendations"]) >= 30
    assert max(item["skeleton_token_savings_percent_vs_baseline"] for item in report["summaries"]["long_text_recommendations"]) >= 10


CHECKS: list[tuple[str, Callable[[Path], None]]] = [
    ("py_compile_ok", _check_py_compile),
    ("context_preset_json_ok", _check_preset_json),
    ("context_restore_text_json_ok", _check_text_restore),
    ("context_compress_text_writing_outline_json_ok", _check_text_writing_outline),
    ("context_compress_text_density_json_ok", _check_text_density),
    ("context_non_utf8_text_restore_json_ok", _check_non_utf8_text_restore),
    ("context_restore_directory_json_ok", _check_directory_restore),
    ("context_bundle_json_ok", _check_bundle_outputs),
    ("context_compress_incremental_clean_diagnostics_json_ok", _check_clean_incremental_diagnostics),
    ("context_apply_check_drift_json_ok", _check_apply_check_drift),
    ("context_directory_filter_ignore_json_ok", _check_directory_filtering),
    ("context_directory_focus_density_json_ok", _check_directory_focus_density),
    ("context_compress_directory_symbols_json_ok", _check_directory_symbols),
    ("context_compress_directory_aggregation_json_ok", _check_directory_aggregation),
    ("context_compress_incremental_json_ok", _check_incremental_compress_restore),
    ("context_apply_patch_roundtrip_json_ok", _check_apply_patch_roundtrip),
    ("context_patch_text_json_ok", _check_patch_text_manifest),
    ("context_patch_incremental_json_ok", _check_patch_incremental_manifest),
    ("context_patch_apply_merge_conflict_json_ok", _check_patch_apply_merge_conflict),
    ("context_patch_apply_directory_reports_json_ok", _check_directory_patch_apply_reports),
    ("context_patch_apply_incremental_reports_json_ok", _check_incremental_patch_apply_reports),
    ("context_patch_apply_policy_template_json_ok", _check_policy_template_json),
    ("context_invalid_input_dir_json_ok", _check_invalid_input_dir),
    ("context_restore_invalid_relpath_json_ok", _check_restore_invalid_relpath),
    ("context_scale_benchmark_quick_json_ok", _check_scale_benchmark_quick),
]


def run_checks(*, results_json: Path) -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    checks: dict[str, bool] = {}
    failures: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="mcp_skeleton_py_smoke.") as tmp:
        workspace = Path(tmp)
        for name, func in CHECKS:
            try:
                func(workspace)
            except Exception as exc:  # noqa: BLE001 - report all smoke failures as structured JSON
                checks[name] = False
                failures[name] = f"{type(exc).__name__}: {exc}"
            else:
                checks[name] = True
    status = "ok" if all(checks.values()) else "error"
    payload = {
        "status": status,
        "exit_code": 0 if status == "ok" else 1,
        "runner": "python",
        "platform": sys.platform,
        "check_count": len(checks),
        "passed": sum(1 for value in checks.values() if value),
        "failed": sum(1 for value in checks.values() if not value),
        "checks": checks,
        "failures": failures,
    }
    results_json.parent.mkdir(parents=True, exist_ok=True)
    results_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cross-platform MCP-Skeleton CLI smoke checks.")
    parser.add_argument("--results-json", default=str(DEFAULT_RESULTS_JSON), help="Where to write the smoke result JSON.")
    args = parser.parse_args()
    payload = run_checks(results_json=Path(args.results_json).expanduser())
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
