from __future__ import annotations

import base64
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import zlib
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_VERSION = "mcp_context_bundle.v1"
SKELETON_LANGUAGE = "MCP-SKL.v1"
SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".workspace_ail",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".cache",
}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".html", ".json", ".yaml", ".yml", ".toml", ".sh", ".bash", ".zsh", ".rb", ".php",
    ".swift", ".kt", ".sql", ".mdx",
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".scss", ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".sql",
}
TEXT_DECODE_CANDIDATES = (
    "utf-8",
    "utf-8-sig",
    "shift_jis",
    "euc_jp",
    "gb2312",
    "gb18030",
    "big5",
    "euc_kr",
    "cp1252",
    "latin-1",
)
STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "have", "will", "more", "than",
    "what", "when", "where", "which", "their", "them", "they", "about", "would", "could", "should",
    "write", "make", "build", "using", "into", "onto", "while", "include", "包含", "一个", "我们", "你们",
    "以及", "可以", "这个", "那个", "需要", "进行", "通过", "作为", "用于", "项目", "内容",
}
TOKENIZER_BACKENDS = {"auto", "heuristic", "tiktoken"}
CONTEXT_FOCUS_MODES = {"full", "tree", "imports", "symbols", "writing-outline"}
SKELETON_DENSITY_MODES = {"adaptive", "standard", "compact"}
PATCH_APPLY_MERGE_MODES = {"overwrite", "reject-conflicts"}
PATCH_POLICY_MODES: dict[str, dict[str, Any]] = {
    "open": {
        "policy_mode": "open",
        "require_apply_check_passed": False,
        "block_removals": False,
        "block_additions": False,
        "max_changed_paths": None,
        "allow_roots": [],
        "forbid_roots": [],
    },
    "safe": {
        "policy_mode": "safe",
        "require_apply_check_passed": True,
        "block_removals": True,
        "block_additions": False,
        "max_changed_paths": None,
        "allow_roots": [],
        "forbid_roots": [],
    },
    "strict": {
        "policy_mode": "strict",
        "require_apply_check_passed": True,
        "block_removals": True,
        "block_additions": True,
        "max_changed_paths": 12,
        "allow_roots": [],
        "forbid_roots": [],
    },
}
PATCH_POLICY_SAMPLES: dict[str, dict[str, Any]] = {
    "safe": {
        "policy_mode": "safe",
        "require_apply_check_passed": True,
        "block_removals": True,
        "block_additions": False,
        "max_changed_paths": 12,
        "allow_roots": ["src", "docs"],
        "forbid_roots": ["src/generated", "secrets"],
    },
    "strict": {
        "policy_mode": "strict",
        "require_apply_check_passed": True,
        "block_removals": True,
        "block_additions": True,
        "max_changed_paths": 8,
        "allow_roots": ["src", "docs"],
        "forbid_roots": ["src/generated", "secrets"],
    },
}

ALIGNMENT_STRONG_THRESHOLD = 82
ALIGNMENT_WORKABLE_THRESHOLD = 64
CONTEXT_PRESETS: dict[str, dict[str, Any]] = {
    "generic": {
        "preset_id": "generic",
        "label": "Generic Context Skeleton",
        "focus": [
            "preserve the core structure without assuming a domain-specific workflow",
            "keep headings, symbols, routes, and file-tree relationships visible",
            "treat the bundle as a balanced AI-facing compression surface",
        ],
        "best_for": ["mixed notes", "unknown repos", "general AI handoff"],
        "skeleton_strategy": [
            "balanced ordering across code, prose, tree, and relationship signals",
            "moderate budgets for directory entries, headings, symbols, and top terms",
        ],
        "suggested_excludes": ["dist/", "build/", "node_modules/", "__pycache__/", ".workspace_ail/", "*.pyc"],
    },
    "codebase": {
        "preset_id": "codebase",
        "label": "Codebase Relationship Skeleton",
        "focus": [
            "prioritize imports, symbols, file roles, and cross-file structure",
            "keep component, route, and runtime wiring legible for engineering review",
            "optimize the skeleton for code-reading models and IDE copilots",
        ],
        "best_for": ["backend repos", "frontend code trees", "refactor and onboarding handoff"],
        "skeleton_strategy": [
            "spend more skeleton budget on imports, symbols, routes, and code-bearing hot subtrees",
            "prefer code entries over prose entries when large directories must be folded",
        ],
        "suggested_excludes": ["node_modules/", "dist/", "build/", "coverage/", ".next/", ".venv/", "__pycache__/", ".workspace_ail/", "*.pyc", "*.map"],
    },
    "writing": {
        "preset_id": "writing",
        "label": "Long-form Writing Skeleton",
        "focus": [
            "prioritize headings, section flow, paragraph density, and topic vocabulary",
            "keep the narrative or editorial shape visible without forcing full prose into context",
            "optimize for review, expansion, and continuation workflows",
        ],
        "best_for": ["books", "articles", "copy drafts", "story planning"],
        "skeleton_strategy": [
            "spend more skeleton budget on chapter folds, headings, section flow, and vocabulary",
            "prefer prose entries over implementation detail when mixed directories must be folded",
        ],
        "suggested_excludes": ["exports/", "draft-renders/", ".obsidian/workspace*", "*.pdf", "*.epub"],
    },
    "website": {
        "preset_id": "website",
        "label": "Website Architecture Skeleton",
        "focus": [
            "prioritize page structure, routes, sections, component roles, and managed boundaries",
            "keep page-to-section relationships and frontend wiring visible to design or implementation agents",
            "optimize for static-site and customization workflows",
        ],
        "best_for": ["landing pages", "personal sites", "company/product sites"],
        "skeleton_strategy": [
            "spend more skeleton budget on routes, page structure, components, and managed content boundaries",
            "prefer frontend source and content files over generated assets when directories must be folded",
        ],
        "suggested_excludes": ["node_modules/", "dist/", "build/", ".next/", ".workspace_ail/", "public/assets/generated/", "*.map"],
    },
    "ecommerce": {
        "preset_id": "ecommerce",
        "label": "Ecommerce Flow Skeleton",
        "focus": [
            "prioritize storefront pages, browse/search/product/cart/checkout continuity, and account shells",
            "keep transaction-adjacent structure visible without pretending to hold a full commerce backend",
            "optimize for experimental ecommerce scaffolds and operator review",
        ],
        "best_for": ["storefront skeletons", "catalog review", "checkout-flow analysis"],
        "skeleton_strategy": [
            "spend more skeleton budget on catalog, cart, checkout, account, and transaction-adjacent flows",
            "prefer route and state-flow files over generated assets when directories must be folded",
        ],
        "suggested_excludes": ["node_modules/", "dist/", "build/", "coverage/", ".workspace_ail/", "product-images/generated/", "*.map"],
    },
}


def build_context_compress_payload(
    *,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    preset_id: str | None = None,
    output_dir: Path | None = None,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
    incremental: bool = False,
    base_commit: str | None = None,
    focus_mode: str | None = None,
    skeleton_density: str | None = None,
    exclude_patterns: list[str] | None = None,
    config_file: Path | None = None,
    config_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preset = resolve_context_preset(preset_id)
    resolved_focus_mode = _normalize_context_focus_mode(focus_mode)
    resolved_skeleton_density = _normalize_skeleton_density(skeleton_density)
    if incremental:
        if any(item for item in [inline_text.strip() if inline_text else "", text_file, input_file]) or input_dir is None:
            raise ValueError("context compress --incremental currently requires exactly one directory input via --input-dir")
        source = _build_incremental_directory_source(
            input_dir,
            base_commit=base_commit,
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
            exclude_patterns=exclude_patterns,
        )
    else:
        source = _resolve_context_input_source(
            inline_text=inline_text,
            text_file=text_file,
            input_file=input_file,
            input_dir=input_dir,
            command_label="context compress",
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
            exclude_patterns=exclude_patterns,
        )

    skeleton_text = _render_skeleton_text(
        source,
        preset=preset,
        focus_mode=resolved_focus_mode,
        skeleton_density=resolved_skeleton_density,
    )
    restore_blob = _encode_restore_blob(source["restore_blob"])
    metrics = _build_context_metrics(
        source["source_summary"],
        skeleton_text=skeleton_text,
        source_token_text=None if source.get("source_token_hints") else _build_token_source_text_from_source(source),
        source_token_hints=source.get("source_token_hints"),
        tokenizer_backend=tokenizer_backend,
        tokenizer_model=tokenizer_model,
    )
    advice = _build_compression_advice(
        source_summary=source["source_summary"],
        metrics=metrics,
        focus_mode=resolved_focus_mode,
        skeleton_density=resolved_skeleton_density,
        preset_id=preset["preset_id"],
    )
    recommended_command_args = _build_recommended_context_compress_args(
        source=source,
        recommended_config=advice["recommended_config"],
    )
    payload = {
        "status": "ok",
        "entrypoint": "context-compress",
        "manifest_version": MANIFEST_VERSION,
        "bundle_created_at": _utc_now(),
        "skeleton_language": SKELETON_LANGUAGE,
        "preset_id": preset["preset_id"],
        "preset_label": preset["label"],
        "preset_focus": list(preset["focus"]),
        "preset_best_for": list(preset["best_for"]),
        "preset_skeleton_strategy": list(preset.get("skeleton_strategy") or []),
        "preset_suggested_excludes": list(preset.get("suggested_excludes") or []),
        "config_file": str(config_file.resolve()) if config_file is not None else "",
        "config_values": dict(config_values or {}),
        "focus_mode": resolved_focus_mode,
        "skeleton_density": resolved_skeleton_density,
        "compression_mode": source["compression_mode"],
        "source_kind": source["source_kind"],
        "source_label": source["source_label"],
        "source_path": source.get("source_path", ""),
        "source_summary": source["source_summary"],
        "source_token_hints": source.get("source_token_hints") or {},
        "incremental_mode": bool(source.get("incremental_mode")),
        "incremental_scope": source.get("incremental_scope", ""),
        "incremental_base_commit": source.get("incremental_base_commit", ""),
        "incremental_git_root": source.get("incremental_git_root", ""),
        "incremental_changed_paths": list(source.get("incremental_changed_paths") or []),
        "incremental_added_paths": list(source.get("incremental_added_paths") or []),
        "incremental_removed_paths": list(source.get("incremental_removed_paths") or []),
        "incremental_path_count": int(source.get("incremental_path_count", 0) or 0),
        "incremental_diagnostics": source.get("incremental_diagnostics") or {},
        "skeleton_text": skeleton_text,
        "skeleton_char_count": len(skeleton_text),
        "restore_package": restore_blob,
        "compression_ratio": metrics["char_reduction_ratio"],
        "metrics": metrics,
        "compression_warnings": advice["warnings"],
        "compression_recommendations": advice["recommendations"],
        "compression_explanations": advice["explanations"],
        "recommended_config": advice["recommended_config"],
        "recommended_command_args": recommended_command_args,
        "source_scale_profile": advice["source_scale_profile"],
        "next_steps": [
            "feed skeleton_text to the target AI or IDE instead of the original raw context",
            "keep the restore package together with the skeleton so the original source can be reconstructed exactly",
            "run `python3 -m cli context restore --package-file /absolute/path/to/context_manifest.json ...` when you need the original content back",
        ],
    }
    if output_dir is not None:
        package_files = _write_context_package(output_dir, payload)
        payload["output_dir"] = str(output_dir.resolve())
        payload["files"] = {key: str(value) for key, value in package_files.items()}
        payload["next_steps"].insert(0, f"open {package_files['skeleton_file']}")
    payload["summary_text"] = _build_context_compress_summary_text(payload)
    return payload


def restore_context_from_package(
    package_payload: dict[str, Any],
    *,
    output_dir: Path | None = None,
    output_file: Path | None = None,
) -> tuple[dict[str, Any], str | None]:
    restore_package = package_payload.get("restore_package") or {}
    decoded = _decode_restore_blob(restore_package)
    mode = str(decoded.get("mode") or "")
    source_label = str(package_payload.get("source_label") or decoded.get("source_label") or "restored-context")
    restore_summary: dict[str, Any] = {
        "status": "ok",
        "entrypoint": "context-restore",
        "manifest_version": package_payload.get("manifest_version", MANIFEST_VERSION),
        "skeleton_language": package_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "compression_mode": package_payload.get("compression_mode", mode),
        "source_kind": package_payload.get("source_kind", decoded.get("source_kind", "text")),
        "source_label": source_label,
        "restored_at": _utc_now(),
        "restore_mode": mode,
        "restored_paths": [],
        "next_steps": [],
    }

    if mode == "text":
        text = str(decoded.get("text") or "")
        if output_file is not None:
            content_b64 = str(decoded.get("content_b64") or "").strip()
            if content_b64:
                _write_bytes_file(output_file, _decode_restore_content_b64(content_b64))
            else:
                _write_text(output_file, text)
            restore_summary["restored_paths"].append(str(output_file.resolve()))
            restore_summary["next_steps"].append(f"open {output_file.resolve()}")
            return restore_summary, None
        return restore_summary, text

    if mode == "file":
        target_path = _resolve_restore_file_path(
            output_dir=output_dir,
            output_file=output_file,
            suggested_name=str(decoded.get("file_name") or source_label),
        )
        _restore_file_blob(target_path, decoded)
        restore_summary["restored_paths"].append(str(target_path.resolve()))
        restore_summary["next_steps"].append(f"open {target_path.resolve()}")
        return restore_summary, None

    if mode == "directory":
        if output_dir is None:
            raise ValueError("context restore requires --output-dir when restoring a directory package")
        root_name = str(decoded.get("root_name") or source_label or "restored-context")
        restore_root = output_dir.expanduser().resolve() / root_name
        _restore_directory_blob(restore_root, decoded)
        restore_summary["restored_paths"].append(str(restore_root))
        restore_summary["next_steps"].append(f"open {restore_root}")
        return restore_summary, None

    if mode == "directory_incremental":
        if output_dir is None:
            raise ValueError("context restore requires --output-dir when restoring an incremental directory package")
        root_name = str(decoded.get("root_name") or source_label or "restored-context")
        restore_root = output_dir.expanduser().resolve() / root_name
        _restore_directory_blob(restore_root, decoded)
        removed_manifest_path = restore_root / ".ail_incremental_manifest.json"
        _write_incremental_restore_manifest(
            removed_manifest_path,
            incremental_scope=str(decoded.get("incremental_scope") or ""),
            base_commit=str(decoded.get("base_commit") or ""),
            removed_paths=list(decoded.get("removed_paths") or []),
        )
        restore_summary["restored_paths"].append(str(restore_root))
        restore_summary["restored_paths"].append(str(removed_manifest_path))
        restore_summary["next_steps"].append(f"open {restore_root}")
        restore_summary["next_steps"].append(f"open {removed_manifest_path}")
        return restore_summary, None

    raise ValueError(f"Unsupported restore mode: {mode}")


def load_context_package(package_file: Path) -> dict[str, Any]:
    return json.loads(package_file.read_text(encoding="utf-8"))


def build_context_preset_payload(preset_id: str | None = None) -> dict[str, Any]:
    preset = resolve_context_preset(preset_id)
    presets = [CONTEXT_PRESETS[key] for key in sorted(CONTEXT_PRESETS.keys())]
    payload = {
        "status": "ok",
        "entrypoint": "context-preset",
        "default_preset_id": "generic",
        "preset_count": len(presets),
        "available_preset_ids": [item["preset_id"] for item in presets],
        "presets": presets,
        "selected_preset": preset,
        "next_steps": [
            f"use `python3 -m cli context compress --preset {preset['preset_id']} ...` when you want this preset applied during compression",
            "run `context preset --json` when you want the full preset catalog",
        ],
    }
    return payload


def build_context_bundle_payload(
    *,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    preset_id: str | None,
    output_dir: Path | None,
    make_zip: bool,
    candidate_inline_text: str | None,
    candidate_text_file: Path | None,
    candidate_input_file: Path | None,
    candidate_input_dir: Path | None,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
    incremental: bool = False,
    base_commit: str | None = None,
    focus_mode: str | None = None,
    skeleton_density: str | None = None,
    exclude_patterns: list[str] | None = None,
    config_file: Path | None = None,
    config_values: dict[str, Any] | None = None,
    compression_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if compression_payload is None:
        compression_payload = build_context_compress_payload(
            inline_text=inline_text,
            text_file=text_file,
            input_file=input_file,
            input_dir=input_dir,
            preset_id=preset_id,
            output_dir=None,
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
            incremental=incremental,
            base_commit=base_commit,
            focus_mode=focus_mode,
            skeleton_density=skeleton_density,
            exclude_patterns=exclude_patterns,
            config_file=config_file,
            config_values=config_values,
        )
    inspect_payload = inspect_context_package(
        compression_payload,
        tokenizer_backend=tokenizer_backend,
        tokenizer_model=tokenizer_model,
    )

    bundle_root = _resolve_context_bundle_dir(
        source_label=str(compression_payload.get("source_label") or "context"),
        output_dir=output_dir,
    )
    bundle_root.mkdir(parents=True, exist_ok=True)
    package_files = _write_context_package(bundle_root, compression_payload)

    files: dict[str, Path] = {
        **package_files,
        "inspect_json": bundle_root / "inspect.json",
        "inspect_summary_txt": bundle_root / "inspect_summary.txt",
        "bundle_manifest_json": bundle_root / "bundle_manifest.json",
    }
    _write_json(files["inspect_json"], inspect_payload)
    _write_text_file(files["inspect_summary_txt"], str(inspect_payload.get("summary_text", "")))

    apply_check_requested = any(
        item
        for item in [
            candidate_inline_text.strip() if candidate_inline_text else "",
            candidate_text_file,
            candidate_input_file,
            candidate_input_dir,
        ]
    )
    if apply_check_requested and bool(compression_payload.get("incremental_mode")):
        raise ValueError("context bundle does not yet support candidate apply-check inputs together with --incremental")
    apply_check_payload = None
    if apply_check_requested:
        apply_check_payload = build_context_apply_check_payload(
            package_payload=compression_payload,
            inline_text=candidate_inline_text if candidate_inline_text and candidate_inline_text.strip() else None,
            text_file=candidate_text_file,
            input_file=candidate_input_file,
            input_dir=candidate_input_dir,
        )
        files["apply_check_json"] = bundle_root / "apply_check.json"
        files["apply_check_summary_txt"] = bundle_root / "apply_check_summary.txt"
        _write_json(files["apply_check_json"], apply_check_payload)
        _write_text_file(files["apply_check_summary_txt"], str(apply_check_payload.get("summary_text", "")))

    bundle_manifest = {
        "status": "ok" if compression_payload.get("status") == "ok" else compression_payload.get("status", "error"),
        "entrypoint": "context-bundle",
        "manifest_version": "context_bundle.v1",
        "bundle_created_at": _utc_now(),
        "preset_id": compression_payload.get("preset_id", "generic"),
        "preset_label": compression_payload.get("preset_label", CONTEXT_PRESETS["generic"]["label"]),
        "focus_mode": compression_payload.get("focus_mode", "full"),
        "skeleton_density": compression_payload.get("skeleton_density", "adaptive"),
        "skeleton_language": compression_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "compression_mode": compression_payload.get("compression_mode", ""),
        "source_kind": compression_payload.get("source_kind", ""),
        "source_label": compression_payload.get("source_label", ""),
        "incremental_mode": bool(compression_payload.get("incremental_mode")),
        "incremental_scope": compression_payload.get("incremental_scope", ""),
        "incremental_base_commit": compression_payload.get("incremental_base_commit", ""),
        "incremental_changed_paths": list(compression_payload.get("incremental_changed_paths") or []),
        "incremental_added_paths": list(compression_payload.get("incremental_added_paths") or []),
        "incremental_removed_paths": list(compression_payload.get("incremental_removed_paths") or []),
        "incremental_path_count": int(compression_payload.get("incremental_path_count", 0) or 0),
        "incremental_diagnostics": compression_payload.get("incremental_diagnostics") or {},
        "bundle_root": str(bundle_root),
        "zip_enabled": make_zip,
        "apply_check_included": bool(apply_check_payload),
        "files": {label: str(path) for label, path in files.items()},
        "compression": compression_payload,
        "inspect": inspect_payload,
        "apply_check": apply_check_payload,
        "next_steps": [
            f"open {files['skeleton_file']}",
            f"open {files['inspect_summary_txt']}",
            "share the bundle directory or zip with the downstream AI or IDE",
        ],
    }
    if apply_check_payload is not None:
        bundle_manifest["next_steps"].insert(1, f"open {files['apply_check_summary_txt']}")
    if make_zip:
        archive_path = shutil.make_archive(str(bundle_root), "zip", root_dir=bundle_root.parent, base_dir=bundle_root.name)
        bundle_manifest["archive_path"] = str(Path(archive_path).resolve())
        bundle_manifest["next_steps"].insert(0, f"share {bundle_manifest['archive_path']}")
    bundle_manifest["file_count"] = len(files)
    bundle_manifest["summary_text"] = _build_context_bundle_summary_text(bundle_manifest)
    _write_json(files["bundle_manifest_json"], bundle_manifest)
    return bundle_manifest


def build_context_patch_payload(
    *,
    package_payload: dict[str, Any],
    source_package_file: Path | None,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    output_dir: Path | None,
    make_zip: bool,
) -> dict[str, Any]:
    candidate = _resolve_context_candidate_source_for_package(
        package_payload=package_payload,
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
        command_label="context patch",
    )
    original_mode = str(package_payload.get("compression_mode") or "")
    candidate_mode = str(candidate.get("compression_mode") or "")
    if original_mode != candidate_mode:
        raise ValueError(
            f"context patch requires a candidate input that matches the original bundle mode `{original_mode}`; "
            f"received `{candidate_mode}` instead"
        )

    apply_check_payload = build_context_apply_check_payload(
        package_payload=package_payload,
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
    )
    patch_root = _resolve_context_patch_dir(
        source_label=str(package_payload.get("source_label") or "context"),
        output_dir=output_dir,
    )
    patch_root.mkdir(parents=True, exist_ok=True)

    patch_result = _build_context_patch_artifacts(
        package_payload=package_payload,
        candidate=candidate,
        patch_root=patch_root,
    )
    if bool(package_payload.get("incremental_mode")):
        candidate_incremental_removed_paths = candidate.get("incremental_removed_paths")
        if candidate_incremental_removed_paths is None:
            effective_incremental_removed_paths = list(package_payload.get("incremental_removed_paths") or [])
        else:
            effective_incremental_removed_paths = list(candidate_incremental_removed_paths)
        patch_result["incremental_removed_paths"] = effective_incremental_removed_paths
        patch_result["removed_paths"] = sorted(
            set(patch_result.get("removed_paths") or []) | set(effective_incremental_removed_paths)
        )
        counts = dict(patch_result.get("change_counts") or {})
        counts["removed_paths"] = len(patch_result["removed_paths"])
        patch_result["change_counts"] = counts

    files: dict[str, Path] = {
        **patch_result["files"],
        "apply_check_json": patch_root / "apply_check.json",
        "apply_check_summary_txt": patch_root / "apply_check_summary.txt",
        "patch_manifest_json": patch_root / "patch_manifest.json",
        "patch_summary_txt": patch_root / "patch_summary.txt",
        "readme_file": patch_root / "README.txt",
    }
    _write_json(files["apply_check_json"], apply_check_payload)
    _write_text_file(files["apply_check_summary_txt"], str(apply_check_payload.get("summary_text", "")))

    payload = {
        "status": "ok" if bool(apply_check_payload.get("apply_check_passed")) else "warning",
        "entrypoint": "context-patch",
        "manifest_version": "context_patch.v1",
        "bundle_created_at": _utc_now(),
        "preset_id": package_payload.get("preset_id", "generic"),
        "preset_label": package_payload.get("preset_label", CONTEXT_PRESETS["generic"]["label"]),
        "source_package_file": str(source_package_file.resolve()) if source_package_file is not None else "",
        "compression_mode": original_mode,
        "incremental_mode": bool(package_payload.get("incremental_mode")),
        "incremental_scope": package_payload.get("incremental_scope", ""),
        "incremental_base_commit": package_payload.get("incremental_base_commit", ""),
        "incremental_changed_paths": list(package_payload.get("incremental_changed_paths") or []),
        "incremental_added_paths": list(package_payload.get("incremental_added_paths") or []),
        "incremental_removed_paths": list(
            patch_result["incremental_removed_paths"]
            if "incremental_removed_paths" in patch_result
            else list(package_payload.get("incremental_removed_paths") or [])
        ),
        "incremental_path_count": int(
            len(package_payload.get("incremental_changed_paths") or [])
            + len(package_payload.get("incremental_added_paths") or [])
            + len(
                patch_result["incremental_removed_paths"]
                if "incremental_removed_paths" in patch_result
                else list(package_payload.get("incremental_removed_paths") or [])
            )
        ),
        "source_kind": package_payload.get("source_kind", ""),
        "source_label": package_payload.get("source_label", ""),
        "candidate_source_kind": candidate.get("source_kind", ""),
        "candidate_source_label": candidate.get("source_label", ""),
        "patch_mode": patch_result["patch_mode"],
        "patch_root": str(patch_root),
        "zip_enabled": make_zip,
        "apply_check_passed": bool(apply_check_payload.get("apply_check_passed")),
        "change_counts": patch_result["change_counts"],
        "changed_paths": patch_result.get("changed_paths", []),
        "added_paths": patch_result.get("added_paths", []),
        "removed_paths": patch_result.get("removed_paths", []),
        "files": {label: str(path) for label, path in files.items()},
        "apply_check": apply_check_payload,
        "next_steps": [
            f"open {files['patch_summary_txt']}",
            f"open {files['apply_check_summary_txt']}",
            "review the diff artifacts before handing the edited candidate to another AI or IDE",
        ],
    }
    if make_zip:
        archive_path = shutil.make_archive(str(patch_root), "zip", root_dir=patch_root.parent, base_dir=patch_root.name)
        payload["archive_path"] = str(Path(archive_path).resolve())
        payload["next_steps"].insert(0, f"share {payload['archive_path']}")
    payload["file_count"] = len(files)
    payload["summary_text"] = _build_context_patch_summary_text(payload)
    _write_text_file(files["patch_summary_txt"], str(payload.get("summary_text", "")))
    _write_text_file(files["readme_file"], _build_context_patch_readme_text(payload, files))
    payload["file_count"] = len(files)
    _write_json(files["patch_manifest_json"], payload)
    return payload


def apply_context_patch_payload(
    *,
    patch_payload: dict[str, Any],
    source_package_payload: dict[str, Any] | None,
    output_dir: Path | None,
    output_file: Path | None,
    dry_run: bool = False,
    merge_mode: str = "overwrite",
    policy_mode: str | None = None,
    sample_policy: str | None = None,
    policy_file: Path | None = None,
    allow_roots: list[str] | None = None,
    forbid_roots: list[str] | None = None,
    block_removals: bool = False,
    block_additions: bool = False,
    require_apply_check_passed: bool = False,
    max_changed_paths: int | None = None,
) -> dict[str, Any]:
    patch_mode = str(patch_payload.get("patch_mode") or "")
    files = patch_payload.get("files") or {}
    source_label = str(patch_payload.get("source_label") or "context")
    status = "ok"
    incremental_mode = bool(patch_payload.get("incremental_mode"))
    merge_mode = str(merge_mode or "overwrite").strip().lower() or "overwrite"
    if merge_mode not in PATCH_APPLY_MERGE_MODES:
        supported = ", ".join(sorted(PATCH_APPLY_MERGE_MODES))
        raise ValueError(f"Unsupported context patch-apply merge mode `{merge_mode}`. Supported modes: {supported}")
    policy = _resolve_patch_apply_policy(
        policy_mode=policy_mode,
        sample_policy=sample_policy,
        policy_file=policy_file,
        allow_roots=allow_roots,
        forbid_roots=forbid_roots,
        block_removals=block_removals,
        block_additions=block_additions,
        require_apply_check_passed=require_apply_check_passed,
        max_changed_paths=max_changed_paths,
    )
    policy_review = _evaluate_patch_apply_policy(patch_payload=patch_payload, policy=policy)
    if not policy_review["passed"]:
        payload = {
            "status": "warning",
            "entrypoint": "context-patch-apply",
            "apply_mode": "policy_blocked",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "dry_run": dry_run,
            "applied_paths": [],
            "removed_paths_applied": [],
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": False,
            "policy_findings": policy_review["findings"],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [
                "inspect the policy findings before replaying this patch",
                "relax the patch-apply policy or narrow the candidate patch surface",
                "re-run context patch if you need a patch bundle with a smaller or safer change set",
            ],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    merge_review = _evaluate_patch_apply_merge(
        patch_payload=patch_payload,
        source_package_payload=source_package_payload,
        patch_mode=patch_mode,
        source_label=source_label,
        output_dir=output_dir,
        output_file=output_file,
        merge_mode=merge_mode,
    )
    if not merge_review["passed"]:
        payload = {
            "status": "warning",
            "entrypoint": "context-patch-apply",
            "apply_mode": "merge_conflict_blocked",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "dry_run": dry_run,
            "applied_paths": [],
            "removed_paths_applied": [],
            "merge_mode": merge_mode,
            "merge_check_passed": False,
            "merge_conflicts": merge_review["conflicts"],
            "merge_conflict_records": merge_review.get("conflict_records", []),
            "merge_conflict_count": len(merge_review["conflicts"]),
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [
                "inspect the merge conflicts before replaying this patch",
                "re-run patch-apply with --merge-mode overwrite if you intentionally want to replace the current target",
                "or replay into a fresh output path to avoid overwriting another edited target",
            ],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    if patch_mode == "text_unified_diff":
        snapshot_path = Path(str(files.get("candidate_snapshot_file") or "")).expanduser()
        if not snapshot_path.exists():
            raise ValueError("context patch-apply could not find candidate_snapshot_file in the patch bundle")
        if output_file is not None:
            target_path = _resolve_output_target_file(output_file)
        elif output_dir is not None:
            target_path = output_dir.expanduser().resolve() / source_label
        else:
            raise ValueError("context patch-apply requires --output-file or --output-dir")
        if not dry_run:
            _write_bytes_file(target_path, snapshot_path.read_bytes())
        preview_manifest = _build_context_patch_apply_preview_manifest(
            patch_payload=patch_payload,
            patch_mode=patch_mode,
            applied_root_or_file=target_path,
            directory_root=None,
        )
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": "text_snapshot_replay_preview" if dry_run else "text_snapshot_replay",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "dry_run": dry_run,
            "applied_paths": [str(target_path.resolve())],
            "removed_paths_applied": [],
            "preview_manifest": preview_manifest,
            "merge_mode": merge_mode,
            "merge_check_passed": True,
            "merge_conflicts": [],
            "merge_conflict_records": [],
            "merge_conflict_count": 0,
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [
                f"re-run context patch-apply without --dry-run to write {target_path.resolve()}"
                if dry_run
                else f"open {target_path.resolve()}"
            ],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    if patch_mode in {"file_unified_diff", "file_binary_replace"}:
        snapshot_path = Path(str(files.get("candidate_snapshot_file") or "")).expanduser()
        if not snapshot_path.exists():
            raise ValueError("context patch-apply could not find candidate_snapshot_file in the patch bundle")
        if output_file is not None:
            target_path = _resolve_output_target_file(output_file)
        elif output_dir is not None:
            target_path = output_dir.expanduser().resolve() / snapshot_path.name
        else:
            raise ValueError("context patch-apply requires --output-file or --output-dir")
        if not dry_run:
            _write_bytes_file(target_path, snapshot_path.read_bytes())
        preview_manifest = _build_context_patch_apply_preview_manifest(
            patch_payload=patch_payload,
            patch_mode=patch_mode,
            applied_root_or_file=target_path,
            directory_root=None,
        )
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": "file_snapshot_replay_preview" if dry_run else "file_snapshot_replay",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "dry_run": dry_run,
            "applied_paths": [str(target_path.resolve())],
            "removed_paths_applied": [],
            "preview_manifest": preview_manifest,
            "merge_mode": merge_mode,
            "merge_check_passed": True,
            "merge_conflicts": [],
            "merge_conflict_records": [],
            "merge_conflict_count": 0,
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [
                f"re-run context patch-apply without --dry-run to write {target_path.resolve()}"
                if dry_run
                else f"open {target_path.resolve()}"
            ],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    if patch_mode == "directory_structural_patch":
        if output_dir is None:
            raise ValueError("context patch-apply requires --output-dir when replaying a directory patch")
        if source_package_payload is None:
            raise ValueError("context patch-apply requires --source-package-file for directory patch replay")
        if dry_run:
            restore_package = source_package_payload.get("restore_package") or {}
            decoded = _decode_restore_blob(restore_package)
            root_name = str(decoded.get("root_name") or source_package_payload.get("source_label") or source_label or "restored-context")
            applied_root = output_dir.expanduser().resolve() / root_name
        else:
            _restore_summary, _ = restore_context_from_package(source_package_payload, output_dir=output_dir)
            applied_root = Path(str((_restore_summary.get("restored_paths") or [""])[0])).expanduser().resolve()
        snapshot_root = Path(str(files.get("candidate_snapshot_root") or "")).expanduser()
        if not dry_run and snapshot_root.exists():
            for item in sorted(snapshot_root.rglob("*")):
                if item.is_dir():
                    continue
                rel_path = item.relative_to(snapshot_root)
                _write_bytes_file(
                    _safe_context_target_path(applied_root, rel_path.as_posix(), field_name="candidate_snapshot_file"),
                    item.read_bytes(),
                )
        removed_paths = [str(item) for item in (patch_payload.get("removed_paths") or []) if str(item).strip()]
        removed_applied: list[str] = []
        for rel_path in removed_paths:
            target = _safe_context_target_path(applied_root, rel_path, field_name="removed_paths")
            if dry_run:
                removed_applied.append(str(target))
                continue
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                removed_applied.append(str(target))
        incremental_manifest_path = applied_root / ".ail_incremental_manifest.json"
        effective_incremental_removed_paths = [
            _normalize_context_relpath(str(item or ""), field_name="incremental_removed_paths")
            for item in (patch_payload.get("incremental_removed_paths") or [])
            if str(item or "").strip()
        ]
        if incremental_mode and not dry_run:
            _write_incremental_restore_manifest(
                incremental_manifest_path,
                incremental_scope=str(
                    patch_payload.get("incremental_scope")
                    or source_package_payload.get("incremental_scope")
                    or ""
                ),
                base_commit=str(
                    patch_payload.get("incremental_base_commit")
                    or source_package_payload.get("incremental_base_commit")
                    or ""
                ),
                removed_paths=effective_incremental_removed_paths,
            )
        preview_manifest = _build_context_patch_apply_preview_manifest(
            patch_payload=patch_payload,
            patch_mode=patch_mode,
            applied_root_or_file=applied_root,
            directory_root=applied_root,
        )
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": (
                "directory_incremental_restore_plus_overlay_preview"
                if dry_run and incremental_mode
                else "directory_incremental_restore_plus_overlay"
                if incremental_mode
                else "directory_restore_plus_overlay_preview"
                if dry_run
                else "directory_restore_plus_overlay"
            ),
            "patch_mode": patch_mode,
            "source_label": source_label,
            "dry_run": dry_run,
            "applied_paths": [str(applied_root)] + (
                [str(incremental_manifest_path.resolve())] if incremental_mode and not dry_run else []
            ),
            "removed_paths_applied": removed_applied,
            "preview_manifest": preview_manifest,
            "incremental_mode": incremental_mode,
            "incremental_scope": str(patch_payload.get("incremental_scope") or ""),
            "incremental_base_commit": str(patch_payload.get("incremental_base_commit") or ""),
            "incremental_changed_paths": list(patch_payload.get("incremental_changed_paths") or []),
            "incremental_added_paths": list(patch_payload.get("incremental_added_paths") or []),
            "incremental_removed_paths": effective_incremental_removed_paths,
            "incremental_path_count": int(
                len(patch_payload.get("incremental_changed_paths") or [])
                + len(patch_payload.get("incremental_added_paths") or [])
                + len(effective_incremental_removed_paths)
            ),
            "merge_mode": merge_mode,
            "merge_check_passed": True,
            "merge_conflicts": [],
            "merge_conflict_records": [],
            "merge_conflict_count": 0,
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [
                f"re-run context patch-apply without --dry-run to materialize {applied_root}"
                if dry_run
                else f"open {applied_root}"
            ],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    raise ValueError(f"Unsupported context patch apply mode: {patch_mode}")


def build_context_apply_check_payload(
    *,
    package_payload: dict[str, Any],
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
) -> dict[str, Any]:
    candidate = _resolve_context_candidate_source_for_package(
        package_payload=package_payload,
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
        command_label="context apply-check",
    )
    original_mode = str(package_payload.get("compression_mode") or "")
    original_kind = str(package_payload.get("source_kind") or "")
    original_summary = package_payload.get("source_summary") or {}
    candidate_mode = str(candidate.get("compression_mode") or "")
    candidate_summary = candidate.get("source_summary") or {}
    incremental_mode = bool(package_payload.get("incremental_mode"))
    effective_incremental_removed_paths = (
        list(candidate.get("incremental_removed_paths") or [])
        if incremental_mode and candidate.get("incremental_removed_paths") is not None
        else list(package_payload.get("incremental_removed_paths") or [])
    )
    incremental_details = {
        "incremental_mode": incremental_mode,
        "incremental_scope": package_payload.get("incremental_scope", ""),
        "incremental_base_commit": package_payload.get("incremental_base_commit", ""),
        "incremental_changed_paths": list(package_payload.get("incremental_changed_paths") or []),
        "incremental_added_paths": list(package_payload.get("incremental_added_paths") or []),
        "incremental_removed_paths": effective_incremental_removed_paths,
        "incremental_path_count": int(
            len(package_payload.get("incremental_changed_paths") or [])
            + len(package_payload.get("incremental_added_paths") or [])
            + len(effective_incremental_removed_paths)
        ),
    }

    if original_mode != candidate_mode:
        payload = {
            "status": "warning",
            "entrypoint": "context-apply-check",
            "apply_check_mode": "skeleton_continuity_gate",
            "apply_check_passed": False,
            "source_kind": original_kind,
            "source_label": package_payload.get("source_label", ""),
            "candidate_source_kind": candidate.get("source_kind", ""),
            "candidate_source_label": candidate.get("source_label", ""),
            "alignment_score": 0,
            "alignment_band": "drifting",
            "strengths": [],
            "drift_findings": [
                f"Candidate input mode `{candidate_mode}` does not match the bundle mode `{original_mode}`."
            ],
            "revision_targets": [
                "Re-run apply-check with a candidate input that matches the original bundle mode."
            ],
            "source_summary": original_summary,
            "candidate_summary": candidate_summary,
            "next_steps": [
                "use a text candidate for a text bundle, a file candidate for a file bundle, or a directory candidate for a directory bundle",
                "re-run context inspect if you need a quick reminder of the original bundle shape",
            ],
        }
        payload.update(incremental_details)
        payload["summary_text"] = _build_context_apply_check_summary_text(payload)
        return payload

    if original_mode == "text":
        review = _build_text_apply_check(original_summary, candidate_summary)
    elif original_mode == "file":
        review = _build_file_apply_check(original_summary, candidate_summary)
    elif original_mode in {"directory", "directory_incremental"}:
        review = _build_directory_apply_check(original_summary, candidate_summary)
    else:
        raise ValueError(f"Unsupported context apply-check mode: {original_mode}")

    alignment_score = int(review["score"])
    alignment_band = _alignment_band(alignment_score)
    apply_check_passed = bool(alignment_band in {"workable", "strong"} and not review["drift_findings"])
    payload = {
        "status": "ok" if apply_check_passed else "warning",
        "entrypoint": "context-apply-check",
        "apply_check_mode": "skeleton_continuity_gate",
        "apply_check_passed": apply_check_passed,
        "preset_id": package_payload.get("preset_id", "generic"),
        "preset_label": package_payload.get("preset_label", CONTEXT_PRESETS["generic"]["label"]),
        "source_kind": original_kind,
        "source_label": package_payload.get("source_label", ""),
        "candidate_source_kind": candidate.get("source_kind", ""),
        "candidate_source_label": candidate.get("source_label", ""),
        "alignment_score": alignment_score,
        "alignment_band": alignment_band,
        "strengths": review["strengths"],
        "drift_findings": review["drift_findings"],
        "revision_targets": review["revision_targets"],
        "source_summary": original_summary,
        "candidate_summary": candidate_summary,
        "next_steps": (
            [
                "candidate still looks structurally aligned to the original bundle",
                "run context restore if you need to compare against the exact original content",
            ]
            if apply_check_passed
            else [
                "inspect the drift findings and restore the original bundle if you need a precise baseline",
                "repair one structural gap at a time before re-running context apply-check",
            ]
        ),
    }
    payload.update(incremental_details)
    payload["summary_text"] = _build_context_apply_check_summary_text(payload)
    return payload


def inspect_context_package(
    package_payload: dict[str, Any],
    *,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
) -> dict[str, Any]:
    restore_package = package_payload.get("restore_package") or {}
    decoded = _decode_restore_blob(restore_package)
    restore_mode = str(decoded.get("mode") or "")
    source_summary = package_payload.get("source_summary") or {}
    tree_preview = list((source_summary.get("tree") or [])[:12])
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    stored_metrics = package_payload.get("metrics") or {}
    use_stored_metrics = bool(stored_metrics) and requested_backend == "auto" and not (tokenizer_model or "").strip()
    metrics = (
        dict(stored_metrics)
        if use_stored_metrics
        else _build_context_metrics(
            source_summary,
            skeleton_text=str(package_payload.get("skeleton_text") or ""),
            source_token_text=(
                None
                if _can_reuse_source_token_hints(
                    package_payload.get("source_token_hints") or {},
                    tokenizer_backend=tokenizer_backend,
                    tokenizer_model=tokenizer_model,
                )
                else _build_token_source_text_from_restore_blob(decoded)
            ),
            source_token_hints=package_payload.get("source_token_hints") or {},
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
        )
    )
    inspect_payload = {
        "status": "ok",
        "entrypoint": "context-inspect",
        "manifest_version": package_payload.get("manifest_version", MANIFEST_VERSION),
        "bundle_created_at": package_payload.get("bundle_created_at", ""),
        "skeleton_language": package_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "preset_id": package_payload.get("preset_id", "generic"),
        "preset_label": package_payload.get("preset_label", CONTEXT_PRESETS["generic"]["label"]),
        "preset_focus": list(package_payload.get("preset_focus") or CONTEXT_PRESETS["generic"]["focus"]),
        "focus_mode": package_payload.get("focus_mode", "full"),
        "skeleton_density": package_payload.get("skeleton_density", "adaptive"),
        "compression_mode": package_payload.get("compression_mode", restore_mode),
        "source_kind": package_payload.get("source_kind", decoded.get("source_kind", "")),
        "source_label": package_payload.get("source_label", decoded.get("source_label", "")),
        "source_path": package_payload.get("source_path", ""),
        "incremental_mode": bool(package_payload.get("incremental_mode")),
        "incremental_scope": package_payload.get("incremental_scope", ""),
        "incremental_base_commit": package_payload.get("incremental_base_commit", ""),
        "incremental_git_root": package_payload.get("incremental_git_root", ""),
        "incremental_changed_paths": list(package_payload.get("incremental_changed_paths") or []),
        "incremental_added_paths": list(package_payload.get("incremental_added_paths") or []),
        "incremental_removed_paths": list(package_payload.get("incremental_removed_paths") or []),
        "incremental_path_count": int(package_payload.get("incremental_path_count", 0) or 0),
        "incremental_diagnostics": package_payload.get("incremental_diagnostics") or {},
        "restore_mode": restore_mode,
        "skeleton_char_count": int(package_payload.get("skeleton_char_count", 0) or 0),
        "restore_encoding": restore_package.get("encoding", ""),
        "restore_raw_byte_count": int(restore_package.get("raw_byte_count", 0) or 0),
        "restore_compressed_byte_count": int(restore_package.get("compressed_byte_count", 0) or 0),
        "compression_ratio": package_payload.get("compression_ratio", 0),
        "metrics": metrics,
        "source_summary": source_summary,
        "tree_preview": tree_preview,
        "has_restore_package": bool(restore_package),
        "next_steps": [
            "use context_skeleton.mcp or skeleton_text as the AI-facing context surface",
            "keep the manifest and restore blob together if you need exact reconstruction later",
            "run context restore when you want the original text, file, or directory tree back",
        ],
    }
    inspect_payload["summary_text"] = _build_context_inspect_summary_text(inspect_payload)
    return inspect_payload


def _build_inline_text_source(text: str) -> dict[str, Any]:
    normalized = text.rstrip("\n")
    summary = _text_summary(normalized, label="inline-text")
    return {
        "compression_mode": "text",
        "source_kind": summary["source_kind"],
        "source_label": "inline-text",
        "source_summary": summary,
        "restore_blob": {
            "mode": "text",
            "source_label": "inline-text",
            "source_kind": summary["source_kind"],
            "text": normalized,
        },
    }


def _build_text_file_source(path: Path) -> dict[str, Any]:
    path = _resolve_existing_context_file(path, field_name="--text-file")
    data = path.read_bytes()
    decoded_text = _decode_text_bytes(path, data, allow_extension_hint=True)
    if decoded_text is None:
        raise ValueError(f"context compress --text-file could not decode `{path}` as text")
    text = decoded_text["text"]
    summary = _text_summary(text, label=path.name)
    summary["source_encoding"] = decoded_text["encoding"]
    summary["encoding_confidence"] = decoded_text["confidence"]
    return {
        "compression_mode": "text",
        "source_kind": summary["source_kind"],
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": summary,
        "restore_blob": {
            "mode": "text",
            "source_label": path.name,
            "source_kind": summary["source_kind"],
            "text": text,
            "content_b64": base64.b64encode(data).decode("ascii"),
            "sha256": _sha256_bytes(data),
            "source_encoding": decoded_text["encoding"],
        },
    }


def _build_file_source(path: Path) -> dict[str, Any]:
    path = _resolve_existing_context_file(path, field_name="--input-file")
    data = path.read_bytes()
    decoded_text = _decode_text_bytes(path, data, allow_extension_hint=True)
    if decoded_text is not None:
        text = decoded_text["text"]
        source_kind = "code" if _is_code_path(path) else "text"
        summary = _code_summary(text, path.name) if source_kind == "code" else _text_summary(text, label=path.name)
        summary["source_encoding"] = decoded_text["encoding"]
        summary["encoding_confidence"] = decoded_text["confidence"]
    else:
        source_kind = "binary"
        summary = {
            "source_kind": "binary",
            "label": path.name,
            "bytes": len(data),
            "sha256": _sha256_bytes(data),
            "total_chars": 0,
            "notes": ["binary payload preserved for exact restore", "skeleton only exposes metadata for non-text content"],
        }
    return {
        "compression_mode": "file",
        "source_kind": source_kind,
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": summary,
        "restore_blob": {
            "mode": "file",
            "source_label": path.name,
            "source_kind": source_kind,
            "file_name": path.name,
            "content_b64": base64.b64encode(data).decode("ascii"),
            "sha256": _sha256_bytes(data),
        },
    }


def _build_context_path_filter(root: Path, *, exclude_patterns: list[str] | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve()
    ignore_file = root / ".mcp-skeletonignore"
    ignore_patterns = _read_context_ignore_patterns(ignore_file)
    cli_patterns = _normalize_context_filter_patterns(exclude_patterns or [])
    patterns = [*ignore_patterns, *cli_patterns]
    return {
        "patterns": patterns,
        "ignore_file": str(ignore_file) if ignore_file.exists() else "",
    }


def _resolve_existing_context_file(path: Path, *, field_name: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"context input {field_name} does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"context input {field_name} must be a file: {resolved}")
    return resolved


def _resolve_existing_context_directory(path: Path, *, field_name: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"context input {field_name} does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"context input {field_name} must be a directory: {resolved}")
    return resolved


def _read_context_ignore_patterns(ignore_file: Path) -> list[str]:
    if not ignore_file.exists():
        return []
    patterns: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return _normalize_context_filter_patterns(patterns)


def _normalize_context_filter_patterns(patterns: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        value = str(pattern or "").strip().replace("\\", "/")
        if not value or value.startswith("#"):
            continue
        while value.startswith("./"):
            value = value[2:]
        value = value.lstrip("/")
        if not value:
            continue
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _context_path_is_filtered(rel_path: str, path_filter: dict[str, Any], *, is_dir: bool) -> bool:
    normalized = str(rel_path or "").strip().replace("\\", "/").strip("/")
    if not normalized:
        return False
    for pattern in path_filter.get("patterns") or []:
        if _context_filter_pattern_matches(normalized, str(pattern), is_dir=is_dir):
            return True
    return False


def _context_filter_pattern_matches(rel_path: str, pattern: str, *, is_dir: bool) -> bool:
    pattern = pattern.strip().replace("\\", "/")
    if not pattern:
        return False
    dir_only = pattern.endswith("/")
    if dir_only and not is_dir:
        pattern = pattern.rstrip("/")
        return rel_path == pattern or rel_path.startswith(f"{pattern}/")
    pattern = pattern.rstrip("/")
    if not pattern:
        return False
    candidates = [rel_path]
    if "/" not in pattern:
        candidates.extend(part for part in rel_path.split("/") if part)
        candidates.append(Path(rel_path).name)
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates)


def _build_directory_source(
    path: Path,
    *,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> dict[str, Any]:
    path = _resolve_existing_context_directory(path, field_name="--input-dir")
    path_filter = _build_context_path_filter(path, exclude_patterns=exclude_patterns)
    files: list[dict[str, Any]] = []
    symlinks: list[dict[str, Any]] = []
    empty_dirs: list[str] = []
    text_files = 0
    code_files = 0
    binary_files = 0
    total_bytes = 0
    total_chars = 0
    skeleton_entries: list[dict[str, Any]] = []
    skipped_dirs: list[str] = []
    filtered_dirs: list[str] = []
    filtered_files: list[str] = []
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    tokenizer_encoder = None
    tokenizer_encoding_name = ""
    tokenizer_error = ""
    tokenizer_source_count = 0
    if requested_backend != "heuristic":
        try:
            tokenizer_encoder, tokenizer_encoding_name = _resolve_tiktoken_encoder(requested_model)
        except Exception as exc:
            tokenizer_error = f"{type(exc).__name__}: {exc}"

    for current_root, dirnames, filenames in os.walk(path):
        current_path = Path(current_root)
        skipped_here = sorted(name for name in dirnames if name in SKIP_DIR_NAMES)
        for dirname in skipped_here:
            skipped_dirs.append((current_path / dirname).relative_to(path).as_posix())
        kept_dirnames = []
        for dirname in sorted(name for name in dirnames if name not in SKIP_DIR_NAMES):
            rel_child_dir = (current_path / dirname).relative_to(path).as_posix()
            if _context_path_is_filtered(rel_child_dir, path_filter, is_dir=True):
                filtered_dirs.append(rel_child_dir)
            else:
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        rel_dir = "." if current_path == path else current_path.relative_to(path).as_posix()
        if not filenames and not dirnames and rel_dir != ".":
            empty_dirs.append(rel_dir)
        for filename in sorted(filenames):
            item_path = current_path / filename
            rel_path = item_path.relative_to(path).as_posix()
            if _context_path_is_filtered(rel_path, path_filter, is_dir=False):
                filtered_files.append(rel_path)
                continue
            if item_path.is_symlink():
                symlinks.append({"relative_path": rel_path, "link_target": os.readlink(item_path)})
                skeleton_entries.append({"relative_path": rel_path, "kind": "symlink", "summary": {"target": os.readlink(item_path)}})
                continue
            data = item_path.read_bytes()
            total_bytes += len(data)
            file_record = {
                "relative_path": rel_path,
                "content_b64": base64.b64encode(data).decode("ascii"),
                "sha256": _sha256_bytes(data),
            }
            files.append(file_record)
            decoded_text = _decode_text_bytes(item_path, data, allow_extension_hint=True)
            if decoded_text is not None:
                text = decoded_text["text"]
                file_record["source_encoding"] = decoded_text["encoding"]
                total_chars += len(text)
                if tokenizer_encoder is not None:
                    tokenizer_source_count += len(tokenizer_encoder.encode(text))
                if _is_code_path(item_path):
                    code_files += 1
                    summary = _code_summary(text, rel_path)
                    kind = "code"
                else:
                    text_files += 1
                    summary = _text_summary(text, label=rel_path)
                    kind = "text"
                summary["source_encoding"] = decoded_text["encoding"]
                summary["encoding_confidence"] = decoded_text["confidence"]
            else:
                binary_files += 1
                kind = "binary"
                summary = {
                    "source_kind": "binary",
                    "label": rel_path,
                    "bytes": len(data),
                    "sha256": _sha256_bytes(data),
                    "total_chars": 0,
                    "notes": ["binary payload preserved for exact restore"],
                }
            skeleton_entries.append({"relative_path": rel_path, "kind": kind, "summary": summary})

    directory_overview = _build_directory_overview(sorted(skeleton_entries, key=lambda item: item["relative_path"]))
    source_summary = {
        "source_kind": "directory",
        "label": path.name,
        "root_path": str(path),
        "total_files": len(files) + len(symlinks),
        "text_files": text_files,
        "code_files": code_files,
        "binary_files": binary_files,
        "symlink_count": len(symlinks),
        "empty_dir_count": len(empty_dirs),
        "skip_dir_names": sorted(SKIP_DIR_NAMES),
        "skipped_dir_count": len(skipped_dirs),
        "skipped_dirs": skipped_dirs,
        "filter_patterns": path_filter["patterns"],
        "ignore_file": path_filter["ignore_file"],
        "filtered_dir_count": len(filtered_dirs),
        "filtered_file_count": len(filtered_files),
        "filtered_path_count": len(filtered_dirs) + len(filtered_files),
        "filtered_paths_preview": sorted(filtered_dirs + filtered_files)[:80],
        "default_noise_protection": {
            "status": "active",
            "skipped_dir_names": sorted(SKIP_DIR_NAMES),
            "skipped_dir_count": len(skipped_dirs),
            "skipped_dirs_preview": sorted(skipped_dirs)[:80],
        },
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "tree": [entry["relative_path"] for entry in sorted(skeleton_entries, key=lambda item: item["relative_path"])],
        "entries": sorted(skeleton_entries, key=lambda item: item["relative_path"]),
        **directory_overview,
    }
    source_token_hints = {
        "heuristic_token_count_source": _estimate_token_count(total_chars),
        "tokenizer_requested_backend": requested_backend,
        "tokenizer_available": tokenizer_encoder is not None,
        "tokenizer_model": requested_model if requested_backend != "heuristic" else "",
        "tokenizer_token_basis": f"tiktoken:{tokenizer_encoding_name}" if tokenizer_encoder is not None else "",
        "tokenizer_token_count_source": tokenizer_source_count if tokenizer_encoder is not None else None,
        "tokenizer_error": tokenizer_error,
    }
    return {
        "compression_mode": "directory",
        "source_kind": "mixed_project",
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": source_summary,
        "source_token_hints": source_token_hints,
        "restore_blob": {
            "mode": "directory",
            "source_label": path.name,
            "source_kind": "mixed_project",
            "root_name": path.name,
            "files": files,
            "symlinks": symlinks,
            "empty_dirs": empty_dirs,
        },
    }


def _run_git_stdout(args: list[str], *, cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ValueError(
            f"context incremental mode requires a working git repository.\n"
            f"git {' '.join(args)} failed in {cwd}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout


def _git_repo_root_for(path: Path) -> Path:
    repo_root = _run_git_stdout(["rev-parse", "--show-toplevel"], cwd=path).strip()
    if not repo_root:
        raise ValueError("context incremental mode could not resolve the git repository root")
    return Path(repo_root).expanduser().resolve()


def _parse_git_name_status_z(raw: bytes) -> tuple[set[str], set[str], set[str]]:
    tokens = raw.split(b"\x00")
    added: set[str] = set()
    changed: set[str] = set()
    removed: set[str] = set()
    i = 0
    while i < len(tokens):
        if not tokens[i]:
            i += 1
            continue
        status = tokens[i].decode("utf-8", errors="replace")
        code = status[:1]
        if code in {"R", "C"}:
            if i + 2 >= len(tokens):
                break
            old_path = tokens[i + 1].decode("utf-8", errors="replace")
            new_path = tokens[i + 2].decode("utf-8", errors="replace")
            removed.add(old_path)
            added.add(new_path)
            i += 3
            continue
        if i + 1 >= len(tokens):
            break
        path = tokens[i + 1].decode("utf-8", errors="replace")
        if code == "A":
            added.add(path)
        elif code == "D":
            removed.add(path)
        else:
            changed.add(path)
        i += 2
    return added, changed, removed


def _scope_rel_from_repo_rel(repo_rel: str, scope_rel: PurePosixPath) -> str:
    repo_path = PurePosixPath(str(repo_rel).replace("\\", "/"))
    if str(scope_rel) == ".":
        return repo_path.as_posix()
    return repo_path.relative_to(scope_rel).as_posix()


def _collect_incremental_repo_paths(path: Path, *, base_commit: str | None) -> dict[str, Any]:
    repo_root = _git_repo_root_for(path)
    try:
        scope_rel = path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError("context incremental mode requires --input-dir to stay inside the git repository root") from exc
    scope_rel_path = PurePosixPath(scope_rel if scope_rel else ".")
    git_cwd = repo_root

    added_repo: set[str] = set()
    changed_repo: set[str] = set()
    removed_repo: set[str] = set()

    if base_commit:
        proc = subprocess.run(
            ["git", "diff", "--name-status", "-z", "--find-renames", base_commit, "--", scope_rel if scope_rel else "."],
            cwd=str(git_cwd),
            capture_output=True,
        )
        if proc.returncode != 0:
            raise ValueError(
                f"context incremental mode could not diff against base commit `{base_commit}`.\n"
                f"STDOUT:\n{proc.stdout.decode('utf-8', errors='replace')}\n"
                f"STDERR:\n{proc.stderr.decode('utf-8', errors='replace')}"
            )
        added_part, changed_part, removed_part = _parse_git_name_status_z(proc.stdout)
        added_repo |= added_part
        changed_repo |= changed_part
        removed_repo |= removed_part
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", scope_rel if scope_rel else "."],
            cwd=str(git_cwd),
            capture_output=True,
        )
        if untracked.returncode == 0:
            added_repo |= {
                item.decode("utf-8", errors="replace")
                for item in untracked.stdout.split(b"\x00")
                if item
            }
    else:
        for args in [
            ["diff", "--name-status", "-z", "--cached", "--find-renames", "--", scope_rel if scope_rel else "."],
            ["diff", "--name-status", "-z", "--find-renames", "--", scope_rel if scope_rel else "."],
        ]:
            proc = subprocess.run(["git", *args], cwd=str(git_cwd), capture_output=True)
            if proc.returncode != 0:
                raise ValueError(
                    "context incremental mode could not read git working tree changes.\n"
                    f"STDOUT:\n{proc.stdout.decode('utf-8', errors='replace')}\n"
                    f"STDERR:\n{proc.stderr.decode('utf-8', errors='replace')}"
                )
            added_part, changed_part, removed_part = _parse_git_name_status_z(proc.stdout)
            added_repo |= added_part
            changed_repo |= changed_part
            removed_repo |= removed_part
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z", "--", scope_rel if scope_rel else "."],
            cwd=str(git_cwd),
            capture_output=True,
        )
        if untracked.returncode == 0:
            added_repo |= {
                item.decode("utf-8", errors="replace")
                for item in untracked.stdout.split(b"\x00")
                if item
            }

    if str(scope_rel_path) != ".":
        added_repo = {path for path in added_repo if PurePosixPath(path).is_relative_to(scope_rel_path)}
        changed_repo = {path for path in changed_repo if PurePosixPath(path).is_relative_to(scope_rel_path)}
        removed_repo = {path for path in removed_repo if PurePosixPath(path).is_relative_to(scope_rel_path)}

    existing_added = {path for path in added_repo if (repo_root / Path(*PurePosixPath(path).parts)).exists()}
    existing_changed = {path for path in changed_repo if (repo_root / Path(*PurePosixPath(path).parts)).exists()}
    removed_only = {path for path in removed_repo if not (repo_root / Path(*PurePosixPath(path).parts)).exists()}

    conflicting = (existing_added | existing_changed) & removed_only
    if conflicting:
        existing_changed |= conflicting
        removed_only -= conflicting

    return {
        "repo_root": repo_root,
        "scope_rel": scope_rel,
        "base_commit": str(base_commit or ""),
        "scope": "base_commit_diff" if base_commit else "working_tree",
        "added_repo_paths": sorted(existing_added),
        "changed_repo_paths": sorted(existing_changed - existing_added),
        "removed_repo_paths": sorted(removed_only),
    }


def _build_incremental_directory_source(
    path: Path,
    *,
    base_commit: str | None = None,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> dict[str, Any]:
    path = _resolve_existing_context_directory(path, field_name="--input-dir")
    path_filter = _build_context_path_filter(path, exclude_patterns=exclude_patterns)
    change_set = _collect_incremental_repo_paths(path, base_commit=base_commit)
    repo_root = change_set["repo_root"]
    scope_rel = PurePosixPath(change_set["scope_rel"] or ".")
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    tokenizer_encoder = None
    tokenizer_encoding_name = ""
    tokenizer_error = ""
    tokenizer_source_count = 0
    if requested_backend != "heuristic":
        try:
            tokenizer_encoder, tokenizer_encoding_name = _resolve_tiktoken_encoder(requested_model)
        except Exception as exc:
            tokenizer_error = f"{type(exc).__name__}: {exc}"

    files: list[dict[str, Any]] = []
    symlinks: list[dict[str, Any]] = []
    text_files = 0
    code_files = 0
    binary_files = 0
    total_bytes = 0
    total_chars = 0
    skeleton_entries: list[dict[str, Any]] = []

    added_paths: list[str] = []
    changed_paths: list[str] = []
    removed_paths = [
        _scope_rel_from_repo_rel(repo_rel, scope_rel)
        for repo_rel in change_set["removed_repo_paths"]
        if not _context_path_is_filtered(_scope_rel_from_repo_rel(repo_rel, scope_rel), path_filter, is_dir=False)
    ]
    filtered_incremental_paths = [
        _scope_rel_from_repo_rel(repo_rel, scope_rel)
        for repo_rel in (
            list(change_set["added_repo_paths"])
            + list(change_set["changed_repo_paths"])
            + list(change_set["removed_repo_paths"])
        )
        if _context_path_is_filtered(_scope_rel_from_repo_rel(repo_rel, scope_rel), path_filter, is_dir=False)
    ]
    incremental_diagnostics = {
        "git_root": str(repo_root),
        "scope": change_set["scope"],
        "scope_rel": scope_rel.as_posix(),
        "base_commit": change_set["base_commit"],
        "raw_changed_count": len(change_set["changed_repo_paths"]),
        "raw_added_count": len(change_set["added_repo_paths"]),
        "raw_removed_count": len(change_set["removed_repo_paths"]),
        "filtered_incremental_path_count": len(filtered_incremental_paths),
        "effective_changed_count": 0,
        "effective_added_count": 0,
        "effective_removed_count": len(removed_paths),
        "no_changes_detected": False,
        "notes": [],
    }

    existing_repo_paths = [
        ("added", repo_rel) for repo_rel in change_set["added_repo_paths"]
        if not _context_path_is_filtered(_scope_rel_from_repo_rel(repo_rel, scope_rel), path_filter, is_dir=False)
    ] + [
        ("changed", repo_rel) for repo_rel in change_set["changed_repo_paths"]
        if not _context_path_is_filtered(_scope_rel_from_repo_rel(repo_rel, scope_rel), path_filter, is_dir=False)
    ]

    for path_kind, repo_rel in sorted(existing_repo_paths, key=lambda item: item[1]):
        rel_path = _scope_rel_from_repo_rel(repo_rel, scope_rel)
        item_path = repo_root / Path(*PurePosixPath(repo_rel).parts)
        if item_path.is_symlink():
            symlinks.append({"relative_path": rel_path, "link_target": os.readlink(item_path)})
            skeleton_entries.append(
                {
                    "relative_path": rel_path,
                    "kind": "symlink",
                    "summary": {"target": os.readlink(item_path), "change_kind": path_kind},
                }
            )
        else:
            data = item_path.read_bytes()
            total_bytes += len(data)
            file_record = {
                "relative_path": rel_path,
                "content_b64": base64.b64encode(data).decode("ascii"),
                "sha256": _sha256_bytes(data),
            }
            files.append(file_record)
            decoded_text = _decode_text_bytes(item_path, data, allow_extension_hint=True)
            if decoded_text is not None:
                text = decoded_text["text"]
                file_record["source_encoding"] = decoded_text["encoding"]
                total_chars += len(text)
                if tokenizer_encoder is not None:
                    tokenizer_source_count += len(tokenizer_encoder.encode(text))
                if _is_code_path(item_path):
                    code_files += 1
                    summary = _code_summary(text, rel_path)
                    kind = "code"
                else:
                    text_files += 1
                    summary = _text_summary(text, label=rel_path)
                    kind = "text"
                summary["source_encoding"] = decoded_text["encoding"]
                summary["encoding_confidence"] = decoded_text["confidence"]
            else:
                binary_files += 1
                kind = "binary"
                summary = {
                    "source_kind": "binary",
                    "label": rel_path,
                    "bytes": len(data),
                    "sha256": _sha256_bytes(data),
                    "total_chars": 0,
                    "notes": ["binary incremental payload preserved for exact restore"],
                }
            summary["change_kind"] = path_kind
            skeleton_entries.append({"relative_path": rel_path, "kind": kind, "summary": summary})
        if path_kind == "added":
            added_paths.append(rel_path)
        else:
            changed_paths.append(rel_path)

    incremental_diagnostics["effective_changed_count"] = len(changed_paths)
    incremental_diagnostics["effective_added_count"] = len(added_paths)
    incremental_diagnostics["effective_removed_count"] = len(removed_paths)
    incremental_diagnostics["no_changes_detected"] = len(changed_paths) + len(added_paths) + len(removed_paths) == 0
    if incremental_diagnostics["no_changes_detected"]:
        incremental_diagnostics["notes"].append(
            "No git changes were detected for the requested input directory scope; modify, stage, add, or delete files under this directory, or provide --base-commit for commit-to-working-tree diffs."
        )
    if filtered_incremental_paths:
        incremental_diagnostics["notes"].append(
            "Some git changes were excluded by .mcp-skeletonignore or --exclude patterns."
        )

    directory_overview = _build_directory_overview(sorted(skeleton_entries, key=lambda item: item["relative_path"]))
    source_summary = {
        "source_kind": "directory",
        "label": path.name,
        "root_path": str(path),
        "total_files": len(files) + len(symlinks),
        "text_files": text_files,
        "code_files": code_files,
        "binary_files": binary_files,
        "symlink_count": len(symlinks),
        "empty_dir_count": 0,
        "filter_patterns": path_filter["patterns"],
        "ignore_file": path_filter["ignore_file"],
        "filtered_incremental_path_count": len(filtered_incremental_paths),
        "filtered_paths_preview": sorted(filtered_incremental_paths)[:80],
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "tree": [entry["relative_path"] for entry in sorted(skeleton_entries, key=lambda item: item["relative_path"])],
        "entries": sorted(skeleton_entries, key=lambda item: item["relative_path"]),
        **directory_overview,
        "changed_file_count": len(changed_paths),
        "added_file_count": len(added_paths),
        "removed_path_count": len(removed_paths),
        "incremental_path_count": len(changed_paths) + len(added_paths) + len(removed_paths),
        "incremental_scope": change_set["scope"],
        "base_commit": change_set["base_commit"],
        "git_root": str(repo_root),
    }
    source_token_hints = {
        "heuristic_token_count_source": _estimate_token_count(total_chars),
        "tokenizer_requested_backend": requested_backend,
        "tokenizer_available": tokenizer_encoder is not None,
        "tokenizer_model": requested_model if requested_backend != "heuristic" else "",
        "tokenizer_token_basis": f"tiktoken:{tokenizer_encoding_name}" if tokenizer_encoder is not None else "",
        "tokenizer_token_count_source": tokenizer_source_count if tokenizer_encoder is not None else None,
        "tokenizer_error": tokenizer_error,
    }
    return {
        "compression_mode": "directory_incremental",
        "source_kind": "mixed_project",
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": source_summary,
        "source_token_hints": source_token_hints,
        "incremental_mode": True,
        "incremental_scope": change_set["scope"],
        "incremental_base_commit": change_set["base_commit"],
        "incremental_git_root": str(repo_root),
        "incremental_changed_paths": changed_paths,
        "incremental_added_paths": added_paths,
        "incremental_removed_paths": removed_paths,
        "incremental_path_count": len(changed_paths) + len(added_paths) + len(removed_paths),
        "incremental_diagnostics": incremental_diagnostics,
        "restore_blob": {
            "mode": "directory_incremental",
            "source_label": path.name,
            "source_kind": "mixed_project",
            "root_name": path.name,
            "files": files,
            "symlinks": symlinks,
            "empty_dirs": [],
            "removed_paths": removed_paths,
            "incremental_scope": change_set["scope"],
            "base_commit": change_set["base_commit"],
            "git_root": str(repo_root),
        },
    }


def _read_incremental_removed_manifest(path: Path) -> list[str] | None:
    manifest_path = path.expanduser().resolve() / ".ail_incremental_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid incremental manifest at {manifest_path}: {exc}") from exc
    removed_paths = payload.get("removed_paths")
    if removed_paths is None:
        return []
    if not isinstance(removed_paths, list):
        raise ValueError(f"Invalid incremental manifest at {manifest_path}: removed_paths must be an array")
    return [
        _normalize_context_relpath(str(item or ""), field_name="removed_paths")
        for item in removed_paths
        if str(item or "").strip()
    ]


def _build_incremental_candidate_directory_source(
    path: Path,
    *,
    package_payload: dict[str, Any],
) -> dict[str, Any]:
    source = _build_directory_source(path)
    inherited_removed_paths = [
        _normalize_context_relpath(str(item or ""), field_name="incremental_removed_paths")
        for item in (package_payload.get("incremental_removed_paths") or [])
        if str(item or "").strip()
    ]
    manifest_removed_paths = _read_incremental_removed_manifest(path)
    control_removed_paths = list(manifest_removed_paths) if manifest_removed_paths is not None else list(inherited_removed_paths)

    allowed_paths = {
        _normalize_context_relpath(str(item or ""), field_name="incremental_changed_paths")
        for item in (package_payload.get("incremental_changed_paths") or [])
        if str(item or "").strip()
    } | {
        _normalize_context_relpath(str(item or ""), field_name="incremental_added_paths")
        for item in (package_payload.get("incremental_added_paths") or [])
        if str(item or "").strip()
    } | set(inherited_removed_paths)

    raw_entries = {
        _normalize_context_relpath(str(item.get("relative_path") or ""), field_name="relative_path"): item
        for item in (source.get("source_summary") or {}).get("entries", [])
        if str(item.get("relative_path") or "").strip()
    }
    filtered_entries = [raw_entries[path] for path in sorted(raw_entries) if path in allowed_paths]
    filtered_tree = [entry["relative_path"] for entry in filtered_entries]

    raw_files = {
        _normalize_context_relpath(str(item.get("relative_path") or ""), field_name="relative_path"): item
        for item in (source.get("restore_blob") or {}).get("files", [])
        if str(item.get("relative_path") or "").strip()
    }
    raw_symlinks = {
        _normalize_context_relpath(str(item.get("relative_path") or ""), field_name="relative_path"): item
        for item in (source.get("restore_blob") or {}).get("symlinks", [])
        if str(item.get("relative_path") or "").strip()
    }
    filtered_files = [raw_files[path] for path in sorted(raw_files) if path in allowed_paths]
    filtered_symlinks = [raw_symlinks[path] for path in sorted(raw_symlinks) if path in allowed_paths]
    candidate_paths = {item["relative_path"] for item in filtered_entries}

    revived_removed_paths = sorted(path for path in inherited_removed_paths if path in candidate_paths)
    effective_removed_paths = sorted(
        (set(control_removed_paths) - set(revived_removed_paths))
    )

    total_bytes = 0
    total_chars = 0
    text_files = 0
    code_files = 0
    binary_files = 0
    for rel_path in sorted(raw_files):
        if rel_path not in allowed_paths:
            continue
        entry = raw_entries.get(rel_path) or {}
        kind = str(entry.get("kind") or "")
        file_record = raw_files[rel_path]
        data = base64.b64decode(str(file_record.get("content_b64") or "").encode("ascii"))
        total_bytes += len(data)
        total_chars += int(((entry.get("summary") or {}).get("total_chars", 0) or 0))
        if kind == "code":
            code_files += 1
        elif kind == "text":
            text_files += 1
        elif kind == "binary":
            binary_files += 1

    incremental_changed_paths = [
        _normalize_context_relpath(str(item or ""), field_name="incremental_changed_paths")
        for item in (package_payload.get("incremental_changed_paths") or [])
        if str(item or "").strip() and _normalize_context_relpath(str(item or ""), field_name="incremental_changed_paths") in candidate_paths
    ]
    original_added_paths = [
        _normalize_context_relpath(str(item or ""), field_name="incremental_added_paths")
        for item in (package_payload.get("incremental_added_paths") or [])
        if str(item or "").strip() and _normalize_context_relpath(str(item or ""), field_name="incremental_added_paths") in candidate_paths
    ]
    revived_as_added_paths = [path for path in revived_removed_paths if path in candidate_paths]
    incremental_added_paths = sorted(set(original_added_paths) | set(revived_as_added_paths))
    directory_overview = _build_directory_overview(filtered_entries)

    return {
        "compression_mode": "directory_incremental",
        "source_kind": "mixed_project",
        "source_label": source.get("source_label", path.name),
        "source_path": source.get("source_path", str(path.expanduser().resolve())),
        "source_summary": {
            "source_kind": "directory",
            "label": source.get("source_label", path.name),
            "root_path": source.get("source_path", str(path.expanduser().resolve())),
            "total_files": len(filtered_files) + len(filtered_symlinks),
            "text_files": text_files,
            "code_files": code_files,
            "binary_files": binary_files,
            "symlink_count": len(filtered_symlinks),
            "empty_dir_count": 0,
            "total_bytes": total_bytes,
            "total_chars": total_chars,
            "tree": filtered_tree,
            "entries": filtered_entries,
            **directory_overview,
            "changed_file_count": len(incremental_changed_paths),
            "added_file_count": len(incremental_added_paths),
            "removed_path_count": len(effective_removed_paths),
            "incremental_path_count": len(incremental_changed_paths) + len(incremental_added_paths) + len(effective_removed_paths),
            "incremental_scope": package_payload.get("incremental_scope", ""),
            "base_commit": package_payload.get("incremental_base_commit", ""),
            "git_root": package_payload.get("incremental_git_root", ""),
        },
        "incremental_mode": True,
        "incremental_scope": package_payload.get("incremental_scope", ""),
        "incremental_base_commit": package_payload.get("incremental_base_commit", ""),
        "incremental_git_root": package_payload.get("incremental_git_root", ""),
        "incremental_changed_paths": incremental_changed_paths,
        "incremental_added_paths": incremental_added_paths,
        "incremental_removed_paths": effective_removed_paths,
        "incremental_path_count": len(incremental_changed_paths) + len(incremental_added_paths) + len(effective_removed_paths),
        "restore_blob": {
            "mode": "directory_incremental",
            "source_label": source.get("source_label", path.name),
            "source_kind": "mixed_project",
            "root_name": source.get("source_label", path.name),
            "files": filtered_files,
            "symlinks": filtered_symlinks,
            "empty_dirs": [],
            "removed_paths": effective_removed_paths,
            "incremental_scope": package_payload.get("incremental_scope", ""),
            "base_commit": package_payload.get("incremental_base_commit", ""),
            "git_root": package_payload.get("incremental_git_root", ""),
        },
    }


def _build_directory_overview(
    entries: list[dict[str, Any]],
    *,
    max_groups: int = 12,
    max_extensions: int = 10,
) -> dict[str, Any]:
    directory_buckets: dict[str, dict[str, Any]] = {}
    extension_counts: Counter[str] = Counter()
    for entry in entries:
        rel_path = str(entry.get("relative_path") or "")
        if not rel_path:
            continue
        kind = str(entry.get("kind") or "")
        summary = entry.get("summary") or {}
        parts = PurePosixPath(rel_path).parts
        group_name = parts[0] if len(parts) > 1 else "."
        bucket = directory_buckets.setdefault(
            group_name,
            {
                "group": group_name,
                "file_count": 0,
                "code_files": 0,
                "text_files": 0,
                "binary_files": 0,
                "symlink_count": 0,
                "total_chars": 0,
                "top_terms": Counter(),
                "sample_paths": [],
                "subtree_roots": Counter(),
            },
        )
        bucket["file_count"] += 1
        bucket["total_chars"] += int(summary.get("total_chars", 0) or 0)
        if kind == "code":
            bucket["code_files"] += 1
        elif kind == "text":
            bucket["text_files"] += 1
        elif kind == "binary":
            bucket["binary_files"] += 1
        elif kind == "symlink":
            bucket["symlink_count"] += 1
        bucket["top_terms"].update(str(term) for term in (summary.get("top_terms") or []) if str(term).strip())
        if len(bucket["sample_paths"]) < 4:
            bucket["sample_paths"].append(rel_path)
        if len(parts) >= 2:
            subtree_root = parts[1] if len(parts) > 2 else "[files]"
            bucket["subtree_roots"][subtree_root] += 1
        suffix = PurePosixPath(rel_path).suffix.lower()
        extension_counts[suffix if suffix else "[no_ext]"] += 1

    groups = sorted(
        (
            {
                "group": bucket["group"],
                "file_count": bucket["file_count"],
                "code_files": bucket["code_files"],
                "text_files": bucket["text_files"],
                "binary_files": bucket["binary_files"],
                "symlink_count": bucket["symlink_count"],
                "total_chars": bucket["total_chars"],
                "top_terms": [term for term, _count in bucket["top_terms"].most_common(4)],
                "sample_paths": list(bucket["sample_paths"][:3]),
                "subtree_roots": [
                    root_name for root_name, _count in bucket["subtree_roots"].most_common(3)
                ],
                "priority_score": round(
                    (bucket["code_files"] * 4.0)
                    + (bucket["text_files"] * 2.0)
                    + (bucket["file_count"] * 1.2)
                    + min(bucket["total_chars"] / 4_000.0, 20.0),
                    2,
                ),
            }
            for bucket in directory_buckets.values()
        ),
        key=lambda item: (-float(item["priority_score"]), -int(item["file_count"]), item["group"]),
    )
    extension_mix = [
        {"extension": extension, "file_count": count}
        for extension, count in extension_counts.most_common(max_extensions)
    ]
    return {
        "directory_groups": groups[:max_groups],
        "directory_group_count": len(groups),
        "extension_mix": extension_mix,
        "extension_group_count": len(extension_counts),
    }


def _write_context_package(output_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "manifest_file": output_dir / "context_manifest.json",
        "skeleton_file": output_dir / "context_skeleton.mcp",
        "restore_file": output_dir / "context_restore.json",
        "readme_file": output_dir / "README.txt",
    }
    _write_json(files["manifest_file"], payload)
    _write_text_file(files["skeleton_file"], str(payload.get("skeleton_text") or ""))
    _write_json(files["restore_file"], payload.get("restore_package") or {})
    _write_text_file(files["readme_file"], _build_context_readme_text(payload, files))
    return files


def _build_context_readme_text(payload: dict[str, Any], files: dict[str, Path]) -> str:
    return "\n".join(
        [
            "AIL Builder Context Compression Bundle",
            "",
            f"manifest_version: {payload.get('manifest_version', MANIFEST_VERSION)}",
            f"bundle_created_at: {payload.get('bundle_created_at', '')}",
            f"preset_id: {payload.get('preset_id', 'generic')}",
            f"preset_label: {payload.get('preset_label', CONTEXT_PRESETS['generic']['label'])}",
            f"focus_mode: {payload.get('focus_mode', 'full')}",
            f"compression_mode: {payload.get('compression_mode', '')}",
            f"source_kind: {payload.get('source_kind', '')}",
            f"source_label: {payload.get('source_label', '')}",
            f"skeleton_language: {payload.get('skeleton_language', SKELETON_LANGUAGE)}",
            "",
            "Preset focus:",
            *[f"- {item}" for item in (payload.get("preset_focus") or CONTEXT_PRESETS["generic"]["focus"])],
            "",
            "Files:",
            f"- context_manifest.json: full machine-readable compression bundle and restore package",
            f"- context_skeleton.mcp: AI-facing high-density skeleton language output",
            f"- context_restore.json: restore blob only",
            f"- README.txt: this usage note",
            "",
            "Suggested flow:",
            f"1. feed {files['skeleton_file']} to the target AI or IDE instead of the raw long context",
            "2. keep the manifest and restore blob together so exact restoration stays possible",
            "3. run context restore when you need the original text, file, or project tree back",
        ]
    ) + "\n"


def _build_context_inspect_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"preset_id: {payload.get('preset_id', '')}",
        f"focus_mode: {payload.get('focus_mode', 'full')}",
        f"skeleton_density: {payload.get('skeleton_density', 'adaptive')}",
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"restore_mode: {payload.get('restore_mode', '')}",
        f"skeleton_language: {payload.get('skeleton_language', '')}",
        f"skeleton_char_count: {payload.get('skeleton_char_count', 0)}",
        f"restore_encoding: {payload.get('restore_encoding', '')}",
        f"restore_raw_byte_count: {payload.get('restore_raw_byte_count', 0)}",
        f"restore_compressed_byte_count: {payload.get('restore_compressed_byte_count', 0)}",
        f"compression_ratio: {payload.get('compression_ratio', 0)}",
    ]
    source_summary = payload.get("source_summary") or {}
    for key in ["total_files", "text_files", "code_files", "binary_files", "total_bytes", "total_chars", "paragraph_count", "lines"]:
        if key in source_summary:
            lines.append(f"{key}: {source_summary.get(key)}")
    if payload.get("incremental_mode"):
        lines.append(f"incremental_scope: {payload.get('incremental_scope', '')}")
        if payload.get("incremental_base_commit"):
            lines.append(f"incremental_base_commit: {payload.get('incremental_base_commit', '')}")
        lines.append(f"incremental_changed_count: {len(payload.get('incremental_changed_paths') or [])}")
        lines.append(f"incremental_added_count: {len(payload.get('incremental_added_paths') or [])}")
        lines.append(f"incremental_removed_count: {len(payload.get('incremental_removed_paths') or [])}")
        if payload.get("incremental_removed_paths"):
            lines.append(f"first_incremental_removed_path: {(payload.get('incremental_removed_paths') or [''])[0]}")
    tree_preview = payload.get("tree_preview") or []
    if tree_preview:
        lines.append(f"tree_preview_count: {len(tree_preview)}")
        lines.append(f"first_tree_item: {tree_preview[0]}")
    metrics = payload.get("metrics") or {}
    for key in [
        "source_char_count",
        "skeleton_char_count",
        "estimated_token_count_source",
        "estimated_token_count_skeleton",
        "token_estimate_backend",
        "token_estimate_basis",
        "token_estimate_model",
        "estimated_token_direction",
        "estimated_token_delta_from_source",
        "estimated_token_reduction_ratio",
        "estimated_tokens_saved",
    ]:
        if key in metrics:
            lines.append(f"{key}: {metrics.get(key)}")
    return "\n".join(lines)


def _build_context_compress_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"preset_id: {payload.get('preset_id', '')}",
        f"focus_mode: {payload.get('focus_mode', 'full')}",
        f"skeleton_density: {payload.get('skeleton_density', 'adaptive')}",
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"skeleton_char_count: {payload.get('skeleton_char_count', 0)}",
        f"compression_ratio: {payload.get('compression_ratio', 0)}",
    ]
    metrics = payload.get("metrics") or {}
    for key in [
        "estimated_token_count_source",
        "estimated_token_count_skeleton",
        "estimated_token_direction",
        "estimated_token_reduction_ratio",
        "estimated_tokens_saved",
        "token_estimate_backend",
    ]:
        if key in metrics:
            lines.append(f"{key}: {metrics.get(key)}")
    warnings = list(payload.get("compression_warnings") or [])
    recommendations = list(payload.get("compression_recommendations") or [])
    explanations = list(payload.get("compression_explanations") or [])
    scale_profile = payload.get("source_scale_profile") or {}
    if scale_profile:
        lines.append(f"source_scale_class: {scale_profile.get('scale_class', '')}")
        if scale_profile.get("total_files"):
            lines.append(f"source_scale_total_files: {scale_profile.get('total_files')}")
    if warnings:
        lines.append(f"compression_warning_count: {len(warnings)}")
        lines.append(f"first_compression_warning: {warnings[0].get('message', '')}")
    if recommendations:
        lines.append(f"compression_recommendation_count: {len(recommendations)}")
        first = recommendations[0]
        lines.append(f"first_recommendation: {first.get('message', '')}")
        if first.get("suggested_focus_mode"):
            lines.append(f"recommended_focus_mode: {first.get('suggested_focus_mode')}")
        if first.get("suggested_skeleton_density"):
            lines.append(f"recommended_skeleton_density: {first.get('suggested_skeleton_density')}")
    if explanations:
        lines.append(f"compression_explanation_count: {len(explanations)}")
        lines.append(f"first_compression_explanation: {explanations[0].get('message', '')}")
        noise = next((item for item in explanations if item.get("code") == "default_noise_protection"), None)
        if noise:
            lines.append(f"default_noise_protection: {noise.get('message', '')}")
    recommended_command_args = list(payload.get("recommended_command_args") or [])
    if recommended_command_args:
        lines.append(f"recommended_command_arg_count: {len(recommended_command_args)}")
        lines.append(f"recommended_command_first_arg: {recommended_command_args[0]}")
    return "\n".join(lines)


def _build_context_apply_check_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"apply_check_mode: {payload.get('apply_check_mode', '')}",
        f"apply_check_passed: {payload.get('apply_check_passed', False)}",
        f"preset_id: {payload.get('preset_id', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"candidate_source_kind: {payload.get('candidate_source_kind', '')}",
        f"candidate_source_label: {payload.get('candidate_source_label', '')}",
        f"alignment_score: {payload.get('alignment_score', 0)}",
        f"alignment_band: {payload.get('alignment_band', '')}",
        f"drift_count: {len(payload.get('drift_findings') or [])}",
        f"revision_target_count: {len(payload.get('revision_targets') or [])}",
    ]
    if payload.get("incremental_mode"):
        lines.append("incremental_mode: True")
        lines.append(f"incremental_scope: {payload.get('incremental_scope', '')}")
        if payload.get("incremental_base_commit"):
            lines.append(f"incremental_base_commit: {payload.get('incremental_base_commit', '')}")
        lines.append(f"incremental_changed_count: {len(payload.get('incremental_changed_paths') or [])}")
        lines.append(f"incremental_added_count: {len(payload.get('incremental_added_paths') or [])}")
        lines.append(f"incremental_removed_count: {len(payload.get('incremental_removed_paths') or [])}")
    if payload.get("revision_targets"):
        lines.append(f"first_revision_target: {(payload.get('revision_targets') or [''])[0]}")
    elif payload.get("drift_findings"):
        lines.append(f"first_drift_finding: {(payload.get('drift_findings') or [''])[0]}")
    elif payload.get("strengths"):
        lines.append(f"first_strength: {(payload.get('strengths') or [''])[0]}")
    return "\n".join(lines)


def _build_context_bundle_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"preset_id: {payload.get('preset_id', '')}",
        f"focus_mode: {payload.get('focus_mode', 'full')}",
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"bundle_root: {payload.get('bundle_root', '')}",
        f"zip_enabled: {payload.get('zip_enabled', False)}",
        f"apply_check_included: {payload.get('apply_check_included', False)}",
        f"file_count: {payload.get('file_count', 0)}",
    ]
    if payload.get("incremental_mode"):
        lines.append("incremental_mode: True")
        lines.append(f"incremental_scope: {payload.get('incremental_scope', '')}")
        if payload.get("incremental_base_commit"):
            lines.append(f"incremental_base_commit: {payload.get('incremental_base_commit', '')}")
        lines.append(f"incremental_changed_count: {len(payload.get('incremental_changed_paths') or [])}")
        lines.append(f"incremental_added_count: {len(payload.get('incremental_added_paths') or [])}")
        lines.append(f"incremental_removed_count: {len(payload.get('incremental_removed_paths') or [])}")
    if payload.get("archive_path"):
        lines.append(f"archive_path: {payload.get('archive_path', '')}")
    files = payload.get("files") or {}
    if files:
        lines.append(f"skeleton_file: {files.get('skeleton_file', '')}")
        lines.append(f"inspect_summary_txt: {files.get('inspect_summary_txt', '')}")
        if files.get("apply_check_summary_txt"):
            lines.append(f"apply_check_summary_txt: {files.get('apply_check_summary_txt', '')}")
    return "\n".join(lines)


def _build_context_patch_summary_text(payload: dict[str, Any]) -> str:
    counts = payload.get("change_counts") or {}
    lines = [
        f"status: {payload.get('status', '')}",
        f"patch_mode: {payload.get('patch_mode', '')}",
        f"preset_id: {payload.get('preset_id', '')}",
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"candidate_source_kind: {payload.get('candidate_source_kind', '')}",
        f"candidate_source_label: {payload.get('candidate_source_label', '')}",
        f"patch_root: {payload.get('patch_root', '')}",
        f"zip_enabled: {payload.get('zip_enabled', False)}",
        f"apply_check_passed: {payload.get('apply_check_passed', False)}",
        f"file_count: {payload.get('file_count', 0)}",
    ]
    if payload.get("incremental_mode"):
        lines.append("incremental_mode: True")
        lines.append(f"incremental_scope: {payload.get('incremental_scope', '')}")
        if payload.get("incremental_base_commit"):
            lines.append(f"incremental_base_commit: {payload.get('incremental_base_commit', '')}")
        lines.append(f"incremental_changed_count: {len(payload.get('incremental_changed_paths') or [])}")
        lines.append(f"incremental_added_count: {len(payload.get('incremental_added_paths') or [])}")
        lines.append(f"incremental_removed_count: {len(payload.get('incremental_removed_paths') or [])}")
    for key in [
        "changed_paths",
        "added_paths",
        "removed_paths",
        "unchanged_paths",
        "text_patch_files",
        "binary_snapshot_files",
        "added_lines",
        "removed_lines",
    ]:
        if key in counts:
            lines.append(f"{key}: {counts.get(key, 0)}")
    if payload.get("archive_path"):
        lines.append(f"archive_path: {payload.get('archive_path', '')}")
    files = payload.get("files") or {}
    for label in ["patch_summary_txt", "apply_check_summary_txt", "patch_preview_diff", "patch_diff", "patches_root", "candidate_snapshot_root"]:
        if files.get(label):
            lines.append(f"{label}: {files.get(label, '')}")
    return "\n".join(lines)


def _build_context_patch_apply_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"apply_mode: {payload.get('apply_mode', '')}",
        f"patch_mode: {payload.get('patch_mode', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"dry_run: {payload.get('dry_run', False)}",
        f"merge_mode: {payload.get('merge_mode', 'overwrite')}",
        f"merge_check_passed: {payload.get('merge_check_passed', True)}",
        f"policy_mode: {payload.get('policy_mode', '')}",
        f"policy_passed: {payload.get('policy_passed', True)}",
        f"applied_path_count: {len(payload.get('applied_paths') or [])}",
        f"removed_path_count: {len(payload.get('removed_paths_applied') or [])}",
    ]
    if payload.get("incremental_mode"):
        lines.append("incremental_mode: True")
        lines.append(f"incremental_scope: {payload.get('incremental_scope', '')}")
        if payload.get("incremental_base_commit"):
            lines.append(f"incremental_base_commit: {payload.get('incremental_base_commit', '')}")
        lines.append(f"incremental_changed_count: {len(payload.get('incremental_changed_paths') or [])}")
        lines.append(f"incremental_added_count: {len(payload.get('incremental_added_paths') or [])}")
        lines.append(f"incremental_removed_count: {len(payload.get('incremental_removed_paths') or [])}")
        if payload.get("incremental_changed_paths"):
            lines.append(f"first_incremental_changed_path: {(payload.get('incremental_changed_paths') or [''])[0]}")
        if payload.get("incremental_added_paths"):
            lines.append(f"first_incremental_added_path: {(payload.get('incremental_added_paths') or [''])[0]}")
        if payload.get("incremental_removed_paths"):
            lines.append(f"first_incremental_removed_path: {(payload.get('incremental_removed_paths') or [''])[0]}")
    applied_paths = payload.get("applied_paths") or []
    if applied_paths:
        lines.append(f"first_applied_path: {applied_paths[0]}")
    removed_paths = payload.get("removed_paths_applied") or []
    if removed_paths:
        lines.append(f"first_removed_path: {removed_paths[0]}")
    preview_manifest = payload.get("preview_manifest") or {}
    if preview_manifest:
        total_surface = _context_patch_preview_surface_size(preview_manifest)
        lines.append(f"changed_path_count: {len(preview_manifest.get('changed_paths') or [])}")
        lines.append(f"added_path_count: {len(preview_manifest.get('added_paths') or [])}")
        lines.append(f"preview_remove_count: {len(preview_manifest.get('remove_targets') or [])}")
        lines.append(f"preview_write_count: {len(preview_manifest.get('write_targets') or [])}")
        lines.append(f"surface_size: {total_surface}")
        lines.append(f"risk_band: {_context_patch_preview_risk_band(total_surface)}")
    policy_findings = payload.get("policy_findings") or []
    if policy_findings:
        lines.append(f"policy_finding_count: {len(policy_findings)}")
        lines.append(f"first_policy_finding: {policy_findings[0]}")
    merge_conflicts = payload.get("merge_conflicts") or []
    if merge_conflicts:
        lines.append(f"merge_conflict_count: {len(merge_conflicts)}")
        lines.append(f"first_merge_conflict: {merge_conflicts[0]}")
    return "\n".join(lines)


def _encode_restore_blob(payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return {
        "encoding": "zlib+base64+json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "raw_byte_count": len(raw),
        "compressed_byte_count": len(compressed),
        "payload": base64.b64encode(compressed).decode("ascii"),
    }


def _decode_restore_blob(payload: dict[str, Any]) -> dict[str, Any]:
    if str(payload.get("encoding") or "") != "zlib+base64+json":
        raise ValueError("Unsupported context restore encoding")
    compressed = base64.b64decode(str(payload.get("payload") or "").encode("ascii"))
    raw = zlib.decompress(compressed)
    decoded = json.loads(raw.decode("utf-8"))
    expected_sha = str(payload.get("sha256") or "")
    actual_sha = hashlib.sha256(raw).hexdigest()
    if expected_sha and expected_sha != actual_sha:
        raise ValueError("Context restore blob checksum mismatch")
    return decoded


def _render_skeleton_text(
    source: dict[str, Any],
    *,
    preset: dict[str, Any],
    focus_mode: str,
    skeleton_density: str,
) -> str:
    density_profile = _resolve_skeleton_density_profile(
        source["source_summary"],
        focus_mode=focus_mode,
        skeleton_density=skeleton_density,
        preset_id=str(preset.get("preset_id") or "generic"),
    )
    lines = [
        SKELETON_LANGUAGE,
        f"PRESET: {preset['preset_id']}",
        f"PRESET_LABEL: {preset['label']}",
        f"FOCUS_MODE: {focus_mode}",
        f"SKELETON_DENSITY: {skeleton_density}",
        f"MODE: {source['compression_mode']}",
        f"SOURCE_KIND: {source['source_kind']}",
        f"SOURCE_LABEL: {source['source_label']}",
    ]
    if source.get("source_path"):
        lines.append(f"SOURCE_PATH: {source['source_path']}")
    lines.append("PRESET_FOCUS:")
    lines.extend([f"  - {item}" for item in preset["focus"]])
    if preset.get("skeleton_strategy"):
        lines.append("PRESET_STRATEGY:")
        lines.extend([f"  - {item}" for item in preset.get("skeleton_strategy", [])])
    if preset.get("suggested_excludes"):
        lines.append("PRESET_EXCLUDE_HINTS:")
        lines.extend([f"  - {item}" for item in preset.get("suggested_excludes", [])])
    lines.append("CORE:")
    lines.extend(
        _render_core_summary_lines(
            source["source_summary"],
            indent="  ",
            top_terms_limit=density_profile["top_terms_limit"],
        )
    )
    if source.get("incremental_mode"):
        lines.append("INCREMENTAL:")
        lines.append(f"  - scope: {source.get('incremental_scope', '')}")
        if source.get("incremental_base_commit"):
            lines.append(f"  - base_commit: {source.get('incremental_base_commit', '')}")
        lines.append(f"  - changed_paths: {len(source.get('incremental_changed_paths') or [])}")
        lines.append(f"  - added_paths: {len(source.get('incremental_added_paths') or [])}")
        lines.append(f"  - removed_paths: {len(source.get('incremental_removed_paths') or [])}")
        if source.get("incremental_removed_paths"):
            lines.append("  REMOVED_PATHS:")
            lines.extend([f"    - {item}" for item in source.get("incremental_removed_paths", [])])
    lines.append("SKELETON:")
    lines.extend(
        _render_structural_lines(
            source["source_summary"],
            indent="  ",
            focus_mode=focus_mode,
            density_profile=density_profile,
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def _resolve_context_input_source(
    *,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    command_label: str,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> dict[str, Any]:
    source_count = sum(1 for item in [inline_text.strip() if inline_text else "", text_file, input_file, input_dir] if item)
    if source_count != 1:
        raise ValueError(f"{command_label} requires exactly one input source: --text, --text-file, --input-file, or --input-dir")
    if inline_text is not None and inline_text.strip():
        return _build_inline_text_source(inline_text)
    if text_file is not None:
        return _build_text_file_source(text_file)
    if input_file is not None:
        return _build_file_source(input_file)
    if input_dir is not None:
        return _build_directory_source(
            input_dir,
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
            exclude_patterns=exclude_patterns,
        )
    raise ValueError(f"{command_label} did not receive a usable input source")


def _resolve_context_candidate_source_for_package(
    *,
    package_payload: dict[str, Any],
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    command_label: str,
) -> dict[str, Any]:
    original_mode = str(package_payload.get("compression_mode") or "")
    if (
        original_mode == "directory_incremental"
        and input_dir is not None
        and not (inline_text and inline_text.strip())
        and text_file is None
        and input_file is None
    ):
        return _build_incremental_candidate_directory_source(input_dir, package_payload=package_payload)
    return _resolve_context_input_source(
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
        command_label=command_label,
    )


def resolve_context_preset(preset_id: str | None) -> dict[str, Any]:
    normalized = str(preset_id or "generic").strip().lower() or "generic"
    preset = CONTEXT_PRESETS.get(normalized)
    if preset is None:
        supported = ", ".join(sorted(CONTEXT_PRESETS.keys()))
        raise ValueError(f"Unsupported context preset `{normalized}`. Supported presets: {supported}")
    return {
        "preset_id": preset["preset_id"],
        "label": preset["label"],
        "focus": list(preset["focus"]),
        "best_for": list(preset["best_for"]),
        "skeleton_strategy": list(preset.get("skeleton_strategy") or []),
        "suggested_excludes": list(preset.get("suggested_excludes") or []),
    }


def _normalize_context_focus_mode(focus_mode: str | None) -> str:
    normalized = str(focus_mode or "full").strip().lower() or "full"
    if normalized not in CONTEXT_FOCUS_MODES:
        supported = ", ".join(sorted(CONTEXT_FOCUS_MODES))
        raise ValueError(f"Unsupported context focus mode `{normalized}`. Supported focus modes: {supported}")
    return normalized


def _normalize_skeleton_density(skeleton_density: str | None) -> str:
    normalized = str(skeleton_density or "adaptive").strip().lower() or "adaptive"
    if normalized not in SKELETON_DENSITY_MODES:
        supported = ", ".join(sorted(SKELETON_DENSITY_MODES))
        raise ValueError(f"Unsupported skeleton density `{normalized}`. Supported densities: {supported}")
    return normalized


def _resolve_skeleton_density_profile(
    summary: dict[str, Any],
    *,
    focus_mode: str,
    skeleton_density: str,
    preset_id: str = "generic",
) -> dict[str, Any]:
    source_kind = str(summary.get("source_kind") or "")
    total_files = int(summary.get("total_files", 0) or 0)
    total_chars = int(summary.get("total_chars", 0) or summary.get("total_bytes", 0) or 0)
    paragraph_count = int(summary.get("paragraph_count", 0) or 0)
    heading_count = int(summary.get("heading_count", 0) or 0)
    large_directory = source_kind == "directory" and (total_files >= 120 or total_chars >= 250_000)
    huge_directory = source_kind == "directory" and (total_files >= 400 or total_chars >= 1_000_000)
    large_text = source_kind in {"text", "markdown"} and (paragraph_count >= 80 or heading_count >= 40 or total_chars >= 60_000)
    huge_text = source_kind in {"text", "markdown"} and (paragraph_count >= 240 or heading_count >= 120 or total_chars >= 250_000)

    standard = {
        "top_terms_limit": 8,
        "imports_limit": 24,
        "symbols_limit": 40,
        "relationships_limit": 30,
        "headings_limit": 24,
        "sections_limit": 10,
        "chapter_fold_limit": 18,
        "chapter_fold_heading_limit": 3,
        "tree_limit": 2_000,
        "directory_entry_limit": 2_000,
        "directory_group_limit": 12,
        "extension_mix_limit": 10,
        "hot_subtree_limit": 12,
        "collapsed_subtree_limit": 0,
        "hot_subtree_seed_limit": 999,
        "hot_subtree_entry_limit": 999,
        "directory_entry_core_fields": [
            "source_kind", "lines", "paragraph_count", "heading_count", "total_chars", "sha256",
        ],
        "directory_entry_top_terms_limit": 8,
    }
    standard_large_directory = {
        "top_terms_limit": 6,
        "imports_limit": 14,
        "symbols_limit": 22,
        "relationships_limit": 10,
        "headings_limit": 18,
        "sections_limit": 8,
        "chapter_fold_limit": 14,
        "chapter_fold_heading_limit": 3,
        "tree_limit": 220 if focus_mode in {"full", "tree"} else 0,
        "directory_entry_limit": 96,
        "directory_group_limit": 12,
        "extension_mix_limit": 10,
        "hot_subtree_limit": 4,
        "collapsed_subtree_limit": 6,
        "hot_subtree_seed_limit": 3,
        "hot_subtree_entry_limit": 16,
        "directory_entry_core_fields": [
            "source_kind", "lines", "paragraph_count", "heading_count", "total_chars",
        ],
        "directory_entry_top_terms_limit": 0,
    }
    adaptive_medium = {
        "top_terms_limit": 6,
        "imports_limit": 12,
        "symbols_limit": 20,
        "relationships_limit": 10,
        "headings_limit": 16,
        "sections_limit": 8,
        "chapter_fold_limit": 12,
        "chapter_fold_heading_limit": 3,
        "tree_limit": 240 if focus_mode in {"full", "tree"} else 0,
        "directory_entry_limit": 120,
        "directory_group_limit": 10,
        "extension_mix_limit": 8,
        "hot_subtree_limit": 4,
        "collapsed_subtree_limit": 4,
        "hot_subtree_seed_limit": 3,
        "hot_subtree_entry_limit": 18,
        "directory_entry_core_fields": [
            "source_kind", "lines", "paragraph_count", "heading_count", "total_chars",
        ],
        "directory_entry_top_terms_limit": 0,
    }
    adaptive_large = {
        "top_terms_limit": 5,
        "imports_limit": 8,
        "symbols_limit": 12,
        "relationships_limit": 6,
        "headings_limit": 12,
        "sections_limit": 6,
        "chapter_fold_limit": 8,
        "chapter_fold_heading_limit": 2,
        "tree_limit": 160 if focus_mode in {"full", "tree"} else 0,
        "directory_entry_limit": 80,
        "directory_group_limit": 8,
        "extension_mix_limit": 6,
        "hot_subtree_limit": 3,
        "collapsed_subtree_limit": 4,
        "hot_subtree_seed_limit": 3,
        "hot_subtree_entry_limit": 14,
        "directory_entry_core_fields": [
            "source_kind", "lines", "heading_count", "total_chars",
        ],
        "directory_entry_top_terms_limit": 0,
    }
    compact = {
        "top_terms_limit": 4,
        "imports_limit": 6,
        "symbols_limit": 8,
        "relationships_limit": 4,
        "headings_limit": 10,
        "sections_limit": 5,
        "chapter_fold_limit": 6,
        "chapter_fold_heading_limit": 2,
        "tree_limit": 80 if focus_mode in {"full", "tree"} else 0,
        "directory_entry_limit": 40,
        "directory_group_limit": 6,
        "extension_mix_limit": 5,
        "hot_subtree_limit": 2,
        "collapsed_subtree_limit": 4,
        "hot_subtree_seed_limit": 2,
        "hot_subtree_entry_limit": 8,
        "directory_entry_core_fields": [
            "source_kind", "lines", "total_chars",
        ],
        "directory_entry_top_terms_limit": 0,
    }

    if skeleton_density == "standard":
        if large_directory or huge_directory:
            return _apply_preset_density_profile(standard_large_directory, preset_id=preset_id, source_kind=source_kind)
        return _apply_preset_density_profile(standard, preset_id=preset_id, source_kind=source_kind)
    if skeleton_density == "compact":
        return _apply_preset_density_profile(compact, preset_id=preset_id, source_kind=source_kind)
    if huge_directory or huge_text:
        return _apply_preset_density_profile(compact, preset_id=preset_id, source_kind=source_kind)
    if large_directory or large_text:
        return _apply_preset_density_profile(adaptive_large, preset_id=preset_id, source_kind=source_kind)
    if source_kind == "directory" and (total_files >= 40 or total_chars >= 100_000):
        return _apply_preset_density_profile(adaptive_medium, preset_id=preset_id, source_kind=source_kind)
    if source_kind in {"text", "markdown"} and (paragraph_count >= 30 or total_chars >= 20_000):
        return _apply_preset_density_profile(adaptive_medium, preset_id=preset_id, source_kind=source_kind)
    return _apply_preset_density_profile(standard, preset_id=preset_id, source_kind=source_kind)


def _apply_preset_density_profile(profile: dict[str, Any], *, preset_id: str, source_kind: str) -> dict[str, Any]:
    tuned = dict(profile)
    preset = str(preset_id or "generic").strip().lower()
    if preset == "codebase":
        tuned["imports_limit"] = max(int(tuned.get("imports_limit", 0) or 0), 16)
        tuned["symbols_limit"] = max(int(tuned.get("symbols_limit", 0) or 0), 28)
        tuned["relationships_limit"] = max(int(tuned.get("relationships_limit", 0) or 0), 14)
        tuned["directory_kind_priority"] = ["code", "symlink", "text", "markdown", "binary"]
        if source_kind == "directory":
            tuned["hot_subtree_entry_limit"] = max(int(tuned.get("hot_subtree_entry_limit", 0) or 0), 20)
        return tuned
    if preset == "writing":
        tuned["directory_kind_priority"] = ["text", "markdown", "code", "symlink", "binary"]
        if source_kind == "directory":
            tuned["headings_limit"] = max(int(tuned.get("headings_limit", 0) or 0), 28)
            tuned["sections_limit"] = max(int(tuned.get("sections_limit", 0) or 0), 14)
            tuned["chapter_fold_limit"] = max(int(tuned.get("chapter_fold_limit", 0) or 0), 20)
            tuned["chapter_fold_heading_limit"] = max(int(tuned.get("chapter_fold_heading_limit", 0) or 0), 4)
            tuned["directory_entry_top_terms_limit"] = max(int(tuned.get("directory_entry_top_terms_limit", 0) or 0), 4)
        return tuned
    if preset in {"website", "ecommerce"}:
        tuned["relationships_limit"] = max(int(tuned.get("relationships_limit", 0) or 0), 18)
        tuned["directory_kind_priority"] = ["code", "text", "markdown", "symlink", "binary"]
    return tuned


def _render_core_summary_lines(
    summary: dict[str, Any],
    *,
    indent: str,
    field_names: list[str] | None = None,
    top_terms_limit: int = 8,
) -> list[str]:
    lines = []
    for key in field_names or [
        "label", "root_path", "source_kind", "total_files", "text_files", "code_files", "binary_files", "symlink_count",
        "empty_dir_count", "bytes", "total_bytes", "lines", "paragraph_count", "bullet_count", "heading_count", "total_chars", "sha256",
        "chapter_group_count", "changed_file_count", "added_file_count", "removed_path_count", "incremental_path_count", "incremental_scope", "base_commit",
    ]:
        if key in summary and summary[key] not in (None, "", [], {}):
            lines.append(f"{indent}- {key}: {summary[key]}")
    if top_terms_limit > 0 and summary.get("top_terms"):
        top_terms = list(summary["top_terms"][:top_terms_limit])
        rendered_terms = ", ".join(top_terms)
        remaining = max(0, len(summary["top_terms"]) - len(top_terms))
        if remaining:
            rendered_terms = f"{rendered_terms} (+{remaining} more)"
        lines.append(f"{indent}- top_terms: {rendered_terms}")
    return lines


def _render_list_block(
    lines: list[str],
    *,
    title: str,
    items: list[str],
    indent: str,
    limit: int,
) -> None:
    if not items or limit == 0:
        return
    lines.append(f"{indent}{title}:")
    visible_items = list(items[:limit])
    lines.extend([f"{indent}  - {item}" for item in visible_items])
    remaining = len(items) - len(visible_items)
    if remaining > 0:
        lines.append(f"{indent}  - ... (+{remaining} more)")


def _render_directory_overview_lines(
    summary: dict[str, Any],
    *,
    indent: str,
    density_profile: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    directory_groups = list(summary.get("directory_groups") or [])
    hot_group_limit = int(density_profile.get("hot_subtree_limit", len(directory_groups)))
    collapsed_group_limit = int(density_profile.get("collapsed_subtree_limit", 0))
    hot_groups = directory_groups[:hot_group_limit]
    collapsed_groups = directory_groups[hot_group_limit: hot_group_limit + collapsed_group_limit]
    if directory_groups:
        lines.append(f"{indent}DIRECTORY_GROUPS:")
        visible_groups = directory_groups[: int(density_profile["directory_group_limit"])]
        for group in visible_groups:
            descriptor = (
                f"group={group.get('group', '')} files={group.get('file_count', 0)} "
                f"code={group.get('code_files', 0)} text={group.get('text_files', 0)} "
                f"binary={group.get('binary_files', 0)} symlinks={group.get('symlink_count', 0)} "
                f"chars={group.get('total_chars', 0)}"
            )
            top_terms = [str(term) for term in (group.get("top_terms") or []) if str(term).strip()]
            if top_terms:
                descriptor = f"{descriptor} top_terms={', '.join(top_terms)}"
            subtree_roots = [str(root) for root in (group.get("subtree_roots") or []) if str(root).strip()]
            if subtree_roots:
                descriptor = f"{descriptor} roots={', '.join(subtree_roots)}"
            lines.append(f"{indent}  - {descriptor}")
        remaining_groups = int(summary.get("directory_group_count", len(directory_groups))) - len(visible_groups)
        if remaining_groups > 0:
            lines.append(f"{indent}  - ... (+{remaining_groups} more groups)")
    if hot_groups and len(directory_groups) > hot_group_limit:
        lines.append(f"{indent}HOT_SUBTREES:")
        for group in hot_groups:
            sample_paths = [str(path) for path in (group.get("sample_paths") or []) if str(path).strip()]
            descriptor = (
                f"group={group.get('group', '')} priority={group.get('priority_score', 0)} "
                f"files={group.get('file_count', 0)}"
            )
            if sample_paths:
                descriptor = f"{descriptor} sample_paths={', '.join(sample_paths)}"
            lines.append(f"{indent}  - {descriptor}")
    if collapsed_groups:
        lines.append(f"{indent}COLLAPSED_SUBTREES:")
        for group in collapsed_groups:
            sample_paths = [str(path) for path in (group.get("sample_paths") or []) if str(path).strip()]
            descriptor = (
                f"group={group.get('group', '')} files={group.get('file_count', 0)} "
                f"chars={group.get('total_chars', 0)}"
            )
            if sample_paths:
                descriptor = f"{descriptor} sample_paths={', '.join(sample_paths)}"
            lines.append(f"{indent}  - {descriptor}")
        remaining_collapsed = len(directory_groups) - hot_group_limit - len(collapsed_groups)
        if remaining_collapsed > 0:
            lines.append(f"{indent}  - ... (+{remaining_collapsed} more folded subtrees)")
    extension_mix = list(summary.get("extension_mix") or [])
    if extension_mix:
        lines.append(f"{indent}EXTENSION_MIX:")
        visible_extensions = extension_mix[: int(density_profile["extension_mix_limit"])]
        for item in visible_extensions:
            lines.append(
                f"{indent}  - extension={item.get('extension', '')} files={item.get('file_count', 0)}"
            )
        remaining_extensions = int(summary.get("extension_group_count", len(extension_mix))) - len(visible_extensions)
        if remaining_extensions > 0:
            lines.append(f"{indent}  - ... (+{remaining_extensions} more extension groups)")
    return lines


def _render_text_chapter_fold_lines(
    summary: dict[str, Any],
    *,
    indent: str,
    density_profile: dict[str, Any],
) -> list[str]:
    chapter_groups = list(summary.get("chapter_groups") or [])
    if not chapter_groups:
        return []
    lines = [f"{indent}CHAPTER_FOLDS:"]
    visible_groups = chapter_groups[: int(density_profile.get("chapter_fold_limit", len(chapter_groups)))]
    sample_heading_limit = int(density_profile.get("chapter_fold_heading_limit", 2))
    for idx, group in enumerate(visible_groups, start=1):
        descriptor = (
            f"chapter[{idx}] title={json.dumps(str(group.get('title') or ''), ensure_ascii=False)} "
            f"level={group.get('level', 1)} headings={group.get('heading_count', 0)} "
            f"paragraphs={group.get('paragraph_count', 0)}"
        )
        sample_headings = [
            str(item) for item in (group.get("sample_headings") or [])[:sample_heading_limit]
            if str(item).strip()
        ]
        if sample_headings:
            descriptor = f"{descriptor} sample_headings={json.dumps(sample_headings, ensure_ascii=False)}"
        first_sentence = str(group.get("first_sentence") or "").strip()
        if first_sentence:
            descriptor = f"{descriptor} first_sentence={json.dumps(first_sentence, ensure_ascii=False)}"
        lines.append(f"{indent}  - {descriptor}")
    remaining_groups = int(summary.get("chapter_group_count", len(chapter_groups))) - len(visible_groups)
    if remaining_groups > 0:
        lines.append(f"{indent}  - ... (+{remaining_groups} more folded chapters)")
    return lines


def _directory_entry_matches_focus(entry_kind: str, focus_mode: str) -> bool:
    if focus_mode == "tree":
        return False
    if focus_mode == "imports":
        return entry_kind == "code"
    if focus_mode == "symbols":
        return entry_kind == "code"
    if focus_mode == "writing-outline":
        return entry_kind in {"text", "markdown"}
    return True


def _select_directory_entries(
    summary: dict[str, Any],
    *,
    density_profile: dict[str, Any],
    focus_mode: str,
) -> list[dict[str, Any]]:
    entries = list(summary.get("entries") or [])
    entry_limit = int(density_profile.get("directory_entry_limit", len(entries)))
    if entry_limit <= 0 or not entries:
        return []
    if len(entries) <= entry_limit:
        return entries

    eligible_entries = [
        entry for entry in entries
        if _directory_entry_matches_focus(str(entry.get("kind") or ""), focus_mode)
    ]
    kind_priority = {
        kind: index
        for index, kind in enumerate(density_profile.get("directory_kind_priority") or [])
    }
    if kind_priority:
        eligible_entries = sorted(
            eligible_entries,
            key=lambda entry: (
                kind_priority.get(str(entry.get("kind") or ""), 99),
                str(entry.get("relative_path") or ""),
            ),
        )
    if focus_mode != "full":
        tree_fill_entries = [entry for entry in entries if entry not in eligible_entries]
    else:
        tree_fill_entries = []
    if not eligible_entries and focus_mode != "full":
        eligible_entries = list(entries)
        tree_fill_entries = []

    group_candidates = [
        group for group in (summary.get("directory_groups") or [])
        if str(group.get("group") or "").strip()
    ]
    if kind_priority:
        group_candidates = sorted(
            group_candidates,
            key=lambda group: (
                _directory_group_kind_rank(group, kind_priority),
                -int(group.get("priority_score", 0) or 0),
                str(group.get("group") or ""),
            ),
        )
    group_priority = [
        str(group.get("group") or "")
        for group in group_candidates[: int(density_profile.get("hot_subtree_limit", 0))]
    ]
    group_to_entries: dict[str, list[dict[str, Any]]] = {}
    for entry in eligible_entries:
        rel_path = str(entry.get("relative_path") or "")
        parts = PurePosixPath(rel_path).parts
        group_name = parts[0] if len(parts) > 1 else "."
        group_to_entries.setdefault(group_name, []).append(entry)

    selected: list[dict[str, Any]] = []
    selected_paths: set[str] = set()

    def _append(entry: dict[str, Any]) -> bool:
        rel_path = str(entry.get("relative_path") or "")
        if not rel_path or rel_path in selected_paths or len(selected) >= entry_limit:
            return False
        selected.append(entry)
        selected_paths.add(rel_path)
        return True

    seed_limit = int(density_profile.get("hot_subtree_seed_limit", entry_limit))
    per_group_limit = int(density_profile.get("hot_subtree_entry_limit", entry_limit))
    group_counts: Counter[str] = Counter()

    for group_name in group_priority:
        for entry in group_to_entries.get(group_name, [])[:seed_limit]:
            if _append(entry):
                group_counts[group_name] += 1

    for group_name in group_priority:
        for entry in group_to_entries.get(group_name, []):
            if group_counts[group_name] >= per_group_limit or len(selected) >= entry_limit:
                break
            if _append(entry):
                group_counts[group_name] += 1

    for entry in eligible_entries:
        if len(selected) >= entry_limit:
            break
        _append(entry)

    for entry in tree_fill_entries:
        if len(selected) >= entry_limit:
            break
        _append(entry)

    return selected


def _directory_group_kind_rank(group: dict[str, Any], kind_priority: dict[str, int]) -> int:
    candidates: list[tuple[int, str]] = [
        (int(group.get("code_files", 0) or 0), "code"),
        (int(group.get("text_files", 0) or 0), "text"),
        (int(group.get("symlink_count", 0) or 0), "symlink"),
        (int(group.get("binary_files", 0) or 0), "binary"),
    ]
    _count, dominant_kind = max(candidates, key=lambda item: item[0])
    return kind_priority.get(dominant_kind, 99)


def _select_directory_tree_items(
    summary: dict[str, Any],
    *,
    density_profile: dict[str, Any],
    focus_mode: str,
) -> list[str]:
    tree_items = [str(item) for item in (summary.get("tree") or []) if str(item).strip()]
    tree_limit = int(density_profile.get("tree_limit", len(tree_items)))
    if tree_limit <= 0 or not tree_items:
        return []
    if len(tree_items) <= tree_limit:
        return tree_items

    ordered: list[str] = []
    seen: set[str] = set()

    def _append(path: str) -> None:
        if path and path not in seen and len(ordered) < tree_limit:
            ordered.append(path)
            seen.add(path)

    for entry in _select_directory_entries(summary, density_profile=density_profile, focus_mode=focus_mode):
        _append(str(entry.get("relative_path") or ""))

    for group in (summary.get("directory_groups") or [])[: int(density_profile.get("directory_group_limit", 0))]:
        for sample_path in group.get("sample_paths") or []:
            _append(str(sample_path))

    for path in tree_items:
        if len(ordered) >= tree_limit:
            break
        _append(path)

    return ordered


def _render_structural_lines(
    summary: dict[str, Any],
    *,
    indent: str,
    focus_mode: str = "full",
    density_profile: dict[str, Any] | None = None,
) -> list[str]:
    density_profile = density_profile or _resolve_skeleton_density_profile(
        summary,
        focus_mode=focus_mode,
        skeleton_density="adaptive",
    )
    source_kind = str(summary.get("source_kind") or "")
    if source_kind == "code":
        lines = []
        if focus_mode in {"full", "imports"}:
            _render_list_block(
                lines,
                title="IMPORTS",
                items=list(summary.get("imports") or []),
                indent=indent,
                limit=int(density_profile["imports_limit"]),
            )
        if focus_mode in {"full", "symbols"}:
            _render_list_block(
                lines,
                title="SYMBOLS",
                items=list(summary.get("symbols") or []),
                indent=indent,
                limit=int(density_profile["symbols_limit"]),
            )
        if focus_mode == "full":
            _render_list_block(
                lines,
                title="RELATIONSHIPS",
                items=list(summary.get("relationships") or []),
                indent=indent,
                limit=int(density_profile["relationships_limit"]),
            )
        if lines:
            return lines
        if focus_mode in {"imports", "symbols"}:
            return [f"{indent}- no {focus_mode} markers were extracted"]
        return [f"{indent}- no structural code markers were extracted"]
    if source_kind in {"text", "markdown"}:
        lines = []
        if focus_mode in {"full", "writing-outline"}:
            lines.extend(
                _render_text_chapter_fold_lines(
                    summary,
                    indent=indent,
                    density_profile=density_profile,
                )
            )
            _render_list_block(
                lines,
                title="HEADINGS",
                items=list(summary.get("headings") or []),
                indent=indent,
                limit=int(density_profile["headings_limit"]),
            )
            _render_list_block(
                lines,
                title="SECTIONS",
                items=list(summary.get("sections") or []),
                indent=indent,
                limit=int(density_profile["sections_limit"]),
            )
        if lines:
            return lines
        if focus_mode == "writing-outline":
            return [f"{indent}- no writing outline markers were extracted"]
        return [f"{indent}- no section markers were extracted"]
    if source_kind == "directory":
        lines: list[str] = []
        lines.extend(
            _render_directory_overview_lines(
                summary,
                indent=indent,
                density_profile=density_profile,
            )
        )
        if focus_mode in {"full", "tree"}:
            _render_list_block(
                lines,
                title="TREE",
                items=_select_directory_tree_items(
                    summary,
                    density_profile=density_profile,
                    focus_mode=focus_mode,
                ),
                indent=indent,
                limit=int(density_profile["tree_limit"]),
            )
        entry_blocks = []
        visible_entries = _select_directory_entries(
            summary,
            density_profile=density_profile,
            focus_mode=focus_mode,
        )
        for entry in visible_entries:
            entry_kind = entry.get("kind")
            if focus_mode == "tree":
                continue
            if focus_mode == "imports" and entry_kind != "code":
                continue
            if focus_mode == "symbols" and entry_kind != "code":
                continue
            if focus_mode == "writing-outline" and entry_kind not in {"text", "markdown"}:
                continue
            structural = []
            if entry_kind in {"code", "text", "markdown"}:
                structural = _render_structural_lines(
                    entry.get("summary") or {},
                    indent=f"{indent}  ",
                    focus_mode=focus_mode,
                    density_profile=density_profile,
                )
            if focus_mode == "full":
                entry_blocks.append(f"{indent}FILE[{entry_kind}]: {entry['relative_path']}")
                entry_blocks.extend(
                    _render_core_summary_lines(
                        entry.get("summary") or {},
                        indent=f"{indent}  ",
                        field_names=list(density_profile["directory_entry_core_fields"]),
                        top_terms_limit=int(density_profile["directory_entry_top_terms_limit"]),
                    )
                )
                entry_blocks.extend(structural)
                continue
            if structural and not (len(structural) == 1 and structural[0].strip().startswith("- no ")):
                entry_blocks.append(f"{indent}FILE[{entry_kind}]: {entry['relative_path']}")
                entry_blocks.extend(structural)
        omitted_entries = len(summary.get("entries", [])) - len(visible_entries)
        if omitted_entries > 0 and focus_mode != "tree":
            entry_blocks.append(f"{indent}- ... (+{omitted_entries} more entries)")
        if lines or entry_blocks:
            return lines + entry_blocks
        if focus_mode == "tree":
            return [f"{indent}- no tree markers were extracted"]
        if focus_mode in {"imports", "symbols", "writing-outline"}:
            return [f"{indent}- no {focus_mode} markers were extracted at directory scope"]
        return [f"{indent}- no structural directory markers were extracted"]
    if source_kind == "binary":
        return [f"{indent}- binary payload preserved for exact restore; skeleton intentionally exposes metadata only"]
    return [f"{indent}- no structural renderer available for source_kind={source_kind}"]


def _build_text_apply_check(original: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    strengths: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 84

    original_headings = set(original.get("headings") or [])
    candidate_headings = set(candidate.get("headings") or [])
    if original_headings:
        overlap = len(original_headings & candidate_headings) / max(1, len(original_headings))
        if overlap >= 0.6:
            strengths.append("The candidate preserved most of the original heading structure.")
            score += 4
        else:
            drift_findings.append("The candidate dropped too much of the original heading structure.")
            revision_targets.append("Restore the major headings or section anchors from the original context.")
            score -= 18

    original_paragraphs = int(original.get("paragraph_count", 0) or 0)
    candidate_paragraphs = int(candidate.get("paragraph_count", 0) or 0)
    if original_paragraphs and candidate_paragraphs < max(1, int(original_paragraphs * 0.4)):
        drift_findings.append("The candidate is much thinner than the original paragraph structure.")
        revision_targets.append("Bring back more of the original section development before handing it to another model.")
        score -= 12
    else:
        strengths.append("The candidate still carries a comparable amount of section development.")

    original_terms = set(original.get("top_terms") or [])
    candidate_terms = set(candidate.get("top_terms") or [])
    if original_terms:
        term_overlap = len(original_terms & candidate_terms) / max(1, len(original_terms))
        if term_overlap >= 0.35:
            strengths.append("The candidate still keeps the core topic vocabulary visible.")
            score += 4
        else:
            drift_findings.append("The candidate topic vocabulary drifted away from the original emphasis.")
            revision_targets.append("Reintroduce the original core terms and domain anchors.")
            score -= 16

    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
    }


def _build_file_apply_check(original: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    strengths: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 84
    original_kind = str(original.get("source_kind") or "")
    candidate_kind = str(candidate.get("source_kind") or "")
    if original_kind != candidate_kind:
        drift_findings.append(f"The candidate file kind `{candidate_kind}` does not match the original `{original_kind}`.")
        revision_targets.append("Keep the candidate in the same file lane as the original bundle.")
        score -= 24

    if original_kind == "code":
        original_symbols = set(original.get("symbols") or [])
        candidate_symbols = set(candidate.get("symbols") or [])
        original_imports = set(original.get("imports") or [])
        candidate_imports = set(candidate.get("imports") or [])
        symbol_overlap = len(original_symbols & candidate_symbols) / max(1, len(original_symbols)) if original_symbols else 1.0
        import_overlap = len(original_imports & candidate_imports) / max(1, len(original_imports)) if original_imports else 1.0
        if symbol_overlap >= 0.45:
            strengths.append("The candidate kept a workable share of the original symbol surface.")
            score += 4
        else:
            drift_findings.append("The candidate lost too many of the original code symbols.")
            revision_targets.append("Restore the main exported functions, classes, or component definitions.")
            score -= 20
        if import_overlap < 0.35:
            drift_findings.append("The candidate import surface drifted away from the original dependencies.")
            revision_targets.append("Bring back the original dependency surface or explain the dependency rewrite elsewhere.")
            score -= 12
        else:
            strengths.append("The dependency surface still looks broadly related to the original file.")
    else:
        text_review = _build_text_apply_check(original, candidate)
        score = min(score, text_review["score"])
        strengths.extend(text_review["strengths"])
        drift_findings.extend(text_review["drift_findings"])
        revision_targets.extend(text_review["revision_targets"])

    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
    }


def _build_directory_apply_check(original: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    strengths: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 86

    original_entries = {item["relative_path"]: item for item in (original.get("entries") or []) if item.get("relative_path")}
    candidate_entries = {item["relative_path"]: item for item in (candidate.get("entries") or []) if item.get("relative_path")}
    original_paths = set(original_entries.keys())
    candidate_paths = set(candidate_entries.keys())
    missing_paths = sorted(original_paths - candidate_paths)
    extra_paths = sorted(candidate_paths - original_paths)
    path_overlap = len(original_paths & candidate_paths) / max(1, len(original_paths)) if original_paths else 1.0

    if path_overlap >= 0.8:
        strengths.append("The candidate kept most of the original file tree.")
        score += 4
    else:
        drift_findings.append("The candidate file tree dropped too much of the original project surface.")
        revision_targets.append("Restore the missing files or re-run the edit on a fuller project copy.")
        score -= 22

    if missing_paths:
        drift_findings.append(f"Missing files: {', '.join(missing_paths[:6])}")
    if extra_paths:
        strengths.append("The candidate added files beyond the original tree, which may be acceptable if the core tree stayed intact.")
        if len(extra_paths) > max(3, int(len(original_paths) * 0.5)):
            drift_findings.append(f"The candidate added a large number of files beyond the original project surface: {len(extra_paths)} added paths.")
            revision_targets.append("Review the added files and compress a narrower candidate if the additions are not intentional.")
            score -= 10

    if int(candidate.get("code_files", 0) or 0) < max(0, int(original.get("code_files", 0) or 0) - 2):
        drift_findings.append("The candidate now exposes notably fewer code files than the original bundle.")
        revision_targets.append("Recover the dropped code files or compress a narrower subdirectory before editing.")
        score -= 12
    else:
        strengths.append("The code-file footprint still looks close to the original bundle.")

    mismatched_kinds = []
    for relpath in sorted(original_paths & candidate_paths):
        original_kind = str(original_entries[relpath].get("kind") or "")
        candidate_kind = str(candidate_entries[relpath].get("kind") or "")
        if original_kind != candidate_kind:
            mismatched_kinds.append(f"{relpath} ({original_kind} -> {candidate_kind})")
    if mismatched_kinds:
        drift_findings.append(f"File kinds changed unexpectedly: {', '.join(mismatched_kinds[:4])}")
        revision_targets.append("Keep file roles stable when possible so the original project structure stays legible.")
        score -= 10

    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
    }


def _alignment_band(score: int) -> str:
    if score >= ALIGNMENT_STRONG_THRESHOLD:
        return "strong"
    if score >= ALIGNMENT_WORKABLE_THRESHOLD:
        return "workable"
    return "drifting"


def _text_summary(text: str, *, label: str) -> dict[str, Any]:
    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
    lines = text.splitlines()
    headings = []
    heading_records: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            headings.append(title)
            heading_records.append(
                {
                    "title": title,
                    "level": max(1, len(stripped) - len(stripped.lstrip("#"))),
                }
            )
        elif re.fullmatch(r"[A-Z][A-Z0-9 \-_/]{4,}", stripped):
            headings.append(stripped)
            heading_records.append({"title": stripped, "level": 1})
    sections = []
    for idx, paragraph in enumerate(paragraphs[:10], start=1):
        first_sentence = _first_sentence(paragraph)
        sections.append(f"section[{idx}] paragraphs=1 first_sentence={json.dumps(first_sentence, ensure_ascii=False)}")
    source_kind = "markdown" if label.lower().endswith((".md", ".mdx", ".rst")) or any(line.strip().startswith("#") for line in lines) else "text"
    chapter_groups = _build_text_chapter_groups(
        text=text,
        paragraphs=paragraphs,
        heading_records=heading_records,
    )
    return {
        "source_kind": source_kind,
        "label": label,
        "lines": len(lines),
        "paragraph_count": len(paragraphs),
        "bullet_count": sum(1 for line in lines if line.strip().startswith(("- ", "* ", "+ "))),
        "heading_count": len(headings),
        "chapter_group_count": len(chapter_groups),
        "headings": headings[:24],
        "sections": sections,
        "chapter_groups": chapter_groups[:32],
        "top_terms": _top_terms(text),
        "sha256": _sha256_text(text),
        "total_chars": len(text),
    }


def _code_summary(text: str, label: str) -> dict[str, Any]:
    lines = text.splitlines()
    imports = []
    symbols = []
    relationships = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(from\s+\S+\s+import\s+.+|import\s+.+|const\s+\w+\s*=\s*require\(|#include\s+.+|use\s+\S+;)", stripped):
            imports.append(stripped)
        if re.match(r"^(export\s+default\s+function\s+\w+|export\s+function\s+\w+|function\s+\w+|async\s+function\s+\w+|class\s+\w+|def\s+\w+|async\s+def\s+\w+|interface\s+\w+|type\s+\w+\s*=|const\s+\w+\s*=\s*\(?[^=]*=>)", stripped):
            symbols.append(stripped)
        if "@PAGE[" in stripped or "router" in stripped.lower() or "route" in stripped.lower() or re.search(r"['\"]/[A-Za-z0-9_\-/{}:]+['\"]", stripped):
            relationships.append(stripped)
        if "<template>" in stripped or "<script" in stripped or "<style" in stripped:
            relationships.append(stripped)
    return {
        "source_kind": "code",
        "label": label,
        "lines": len(lines),
        "imports": imports[:24],
        "symbols": symbols[:40],
        "relationships": relationships[:30],
        "top_terms": _top_terms(text),
        "sha256": _sha256_text(text),
        "total_chars": len(text),
    }


def _build_text_chapter_groups(
    *,
    text: str,
    paragraphs: list[str],
    heading_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if heading_records:
        anchor_level = 1 if any(int(item.get("level", 1) or 1) == 1 for item in heading_records) else 2
        groups: list[dict[str, Any]] = []
        current_group: dict[str, Any] | None = None
        for record in heading_records:
            title = str(record.get("title") or "").strip()
            level = int(record.get("level", 1) or 1)
            if not title:
                continue
            if current_group is None or level <= anchor_level:
                current_group = {
                    "title": title,
                    "level": level,
                    "heading_count": 1,
                    "sample_headings": [],
                }
                groups.append(current_group)
                continue
            current_group["heading_count"] = int(current_group.get("heading_count", 0) or 0) + 1
            sample_headings = list(current_group.get("sample_headings") or [])
            if len(sample_headings) < 3:
                sample_headings.append(title)
                current_group["sample_headings"] = sample_headings
        if groups:
            paragraph_budget = max(1, len(paragraphs))
            avg_group_paragraphs = max(1, round(paragraph_budget / max(1, len(groups))))
            paragraph_cursor = 0
            for group in groups:
                group_heading_count = max(1, int(group.get("heading_count", 1) or 1))
                remaining_paragraphs = max(0, paragraph_budget - paragraph_cursor)
                group_paragraphs = min(
                    max(avg_group_paragraphs, group_heading_count),
                    max(1, remaining_paragraphs) if remaining_paragraphs else 1,
                )
                paragraph_slice = paragraphs[paragraph_cursor: paragraph_cursor + group_paragraphs]
                paragraph_cursor += len(paragraph_slice)
                first_sentence = _first_sentence(" ".join(paragraph_slice[:2])) if paragraph_slice else ""
                group["paragraph_count"] = len(paragraph_slice)
                group["first_sentence"] = first_sentence
            if paragraph_cursor < paragraph_budget and groups:
                groups[-1]["paragraph_count"] = int(groups[-1].get("paragraph_count", 0) or 0) + (paragraph_budget - paragraph_cursor)
            return groups

    groups = []
    chunk_size = 8 if len(paragraphs) >= 24 else 5
    for idx in range(0, len(paragraphs), chunk_size):
        chunk = paragraphs[idx: idx + chunk_size]
        if not chunk:
            continue
        groups.append(
            {
                "title": f"chunk[{len(groups) + 1}]",
                "level": 1,
                "heading_count": 0,
                "sample_headings": [],
                "paragraph_count": len(chunk),
                "first_sentence": _first_sentence(" ".join(chunk[:2])),
            }
        )
    return groups


def _decode_text_bytes(path: Path, data: bytes, *, allow_extension_hint: bool = False) -> dict[str, Any] | None:
    extension_hint = allow_extension_hint and path.suffix.lower() in TEXT_EXTENSIONS
    bom_decoded = _decode_text_bytes_from_bom(data)
    if bom_decoded is not None:
        return bom_decoded
    utf16_decoded = _decode_utf16_without_bom(data, extension_hint=extension_hint)
    if utf16_decoded is not None:
        return utf16_decoded
    if b"\x00" in data[:4096]:
        return None
    for encoding in TEXT_DECODE_CANDIDATES:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        score = _decoded_text_printable_score(text)
        if score >= 0.92 or (extension_hint and score >= 0.82):
            return {
                "text": text,
                "encoding": encoding,
                "confidence": "high" if encoding.startswith("utf") or score >= 0.98 else "medium",
                "printable_score": round(score, 4),
            }
    return None


def _decode_text_bytes_from_bom(data: bytes) -> dict[str, Any] | None:
    bom_candidates = [
        (b"\xff\xfe", "utf-16-le-bom", "utf-16"),
        (b"\xfe\xff", "utf-16-be-bom", "utf-16"),
        (b"\xef\xbb\xbf", "utf-8-sig", "utf-8-sig"),
    ]
    for bom, label, codec in bom_candidates:
        if data.startswith(bom):
            try:
                text = data.decode(codec)
            except UnicodeDecodeError:
                return None
            score = _decoded_text_printable_score(text)
            if score >= 0.9:
                return {
                    "text": text,
                    "encoding": label,
                    "confidence": "high",
                    "printable_score": round(score, 4),
                }
    return None


def _decode_utf16_without_bom(data: bytes, *, extension_hint: bool) -> dict[str, Any] | None:
    if len(data) < 4:
        return None
    sample = data[:4096]
    even_nuls = sample[0::2].count(0)
    odd_nuls = sample[1::2].count(0)
    pair_count = max(1, len(sample) // 2)
    candidates: list[tuple[str, str]] = []
    if odd_nuls / pair_count >= 0.35 and even_nuls / pair_count <= 0.1:
        candidates.append(("utf-16-le", "utf-16-le"))
    if even_nuls / pair_count >= 0.35 and odd_nuls / pair_count <= 0.1:
        candidates.append(("utf-16-be", "utf-16-be"))
    if not candidates:
        return None
    for label, codec in candidates:
        try:
            text = data.decode(codec)
        except UnicodeDecodeError:
            continue
        score = _decoded_text_printable_score(text)
        if score >= 0.9 or (extension_hint and score >= 0.82):
            return {
                "text": text,
                "encoding": label,
                "confidence": "high" if score >= 0.96 else "medium",
                "printable_score": round(score, 4),
            }
    return None


def _looks_like_text(path: Path, data: bytes) -> bool:
    return _decode_text_bytes(path, data, allow_extension_hint=True) is not None


def _decoded_text_printable_score(text: str) -> float:
    if not text:
        return 1.0
    printable = 0
    for char in text:
        if char in "\n\r\t" or char.isprintable():
            printable += 1
    return printable / max(1, len(text))


def _is_code_path(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def _top_terms(text: str, *, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [term for term, _count in counts.most_common(limit)]


def _build_context_metrics(
    source_summary: dict[str, Any],
    *,
    skeleton_text: str,
    source_token_text: str | None,
    source_token_hints: dict[str, Any] | None = None,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
) -> dict[str, Any]:
    source_char_count = _int_metric(
        source_summary.get("total_chars"),
        fallback=source_summary.get("bytes") or source_summary.get("total_bytes") or 0,
    )
    skeleton_char_count = len(skeleton_text)
    heuristic_token_count_source = _int_metric(
        (source_token_hints or {}).get("heuristic_token_count_source"),
        fallback=_estimate_token_count(source_char_count),
    )
    heuristic_token_count_skeleton = _estimate_token_count(skeleton_char_count)
    heuristic_metrics = _build_token_delta_metrics(heuristic_token_count_source, heuristic_token_count_skeleton)
    primary_metrics = _resolve_primary_token_metrics(
        source_text=source_token_text,
        source_token_hints=source_token_hints or {},
        skeleton_text=skeleton_text,
        heuristic_source_tokens=heuristic_token_count_source,
        heuristic_skeleton_tokens=heuristic_token_count_skeleton,
        tokenizer_backend=tokenizer_backend,
        tokenizer_model=tokenizer_model,
    )
    char_reduction_ratio = round(skeleton_char_count / max(1, source_char_count), 4) if source_char_count > 0 else 0.0
    metrics = {
        "source_char_count": source_char_count,
        "skeleton_char_count": skeleton_char_count,
        "estimated_token_count_source": primary_metrics["token_count_source"],
        "estimated_token_count_skeleton": primary_metrics["token_count_skeleton"],
        "estimated_tokens_saved": primary_metrics["tokens_saved"],
        "estimated_token_delta_from_source": primary_metrics["token_delta_from_source"],
        "estimated_token_reduction_ratio": primary_metrics["token_ratio"],
        "estimated_token_size_ratio": primary_metrics["token_ratio"],
        "estimated_token_direction": primary_metrics["token_direction"],
        "char_reduction_ratio": char_reduction_ratio,
        "token_estimate_basis": primary_metrics["token_basis"],
        "token_estimate_backend": primary_metrics["token_backend"],
        "token_estimate_model": primary_metrics["token_model"],
        "token_estimate_requested_backend": primary_metrics["requested_backend"],
        "token_estimate_fallback_used": primary_metrics["fallback_used"],
        "heuristic_token_count_source": heuristic_token_count_source,
        "heuristic_token_count_skeleton": heuristic_token_count_skeleton,
        "heuristic_tokens_saved": heuristic_metrics["tokens_saved"],
        "heuristic_token_delta_from_source": heuristic_metrics["token_delta_from_source"],
        "heuristic_token_reduction_ratio": heuristic_metrics["token_ratio"],
        "heuristic_token_direction": heuristic_metrics["token_direction"],
        "heuristic_token_basis": "heuristic_chars_div_4",
        "tokenizer_available": primary_metrics["tokenizer_available"],
    }
    if primary_metrics.get("tokenizer_token_count_source") is not None:
        metrics["tokenizer_token_count_source"] = primary_metrics["tokenizer_token_count_source"]
        metrics["tokenizer_token_count_skeleton"] = primary_metrics["tokenizer_token_count_skeleton"]
        metrics["tokenizer_tokens_saved"] = primary_metrics["tokenizer_tokens_saved"]
        metrics["tokenizer_token_delta_from_source"] = primary_metrics["tokenizer_token_delta_from_source"]
        metrics["tokenizer_token_reduction_ratio"] = primary_metrics["tokenizer_token_reduction_ratio"]
        metrics["tokenizer_token_direction"] = primary_metrics["tokenizer_token_direction"]
        metrics["tokenizer_token_basis"] = primary_metrics["tokenizer_token_basis"]
    if primary_metrics.get("tokenizer_error"):
        metrics["tokenizer_error"] = primary_metrics["tokenizer_error"]
    return metrics


def _build_compression_advice(
    *,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    focus_mode: str,
    skeleton_density: str,
    preset_id: str,
) -> dict[str, Any]:
    source_kind = str(source_summary.get("source_kind") or "")
    token_ratio = float(metrics.get("estimated_token_reduction_ratio") or 0.0)
    token_direction = str(metrics.get("estimated_token_direction") or "")
    source_tokens = int(metrics.get("estimated_token_count_source") or 0)
    skeleton_tokens = int(metrics.get("estimated_token_count_skeleton") or 0)
    tokens_saved = int(metrics.get("estimated_tokens_saved") or 0)
    savings_percent = round((tokens_saved / source_tokens) * 100, 2) if source_tokens else 0.0
    total_files = int(source_summary.get("total_files", 0) or 0)
    total_chars = int(source_summary.get("total_chars", 0) or source_summary.get("total_bytes", 0) or 0)
    filter_patterns = [str(item) for item in (source_summary.get("filter_patterns") or []) if str(item).strip()]
    preset_excludes = list((CONTEXT_PRESETS.get(preset_id) or CONTEXT_PRESETS["generic"]).get("suggested_excludes") or [])
    scale_profile = _build_source_scale_profile(source_summary, metrics=metrics)
    warnings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []

    if token_direction == "expanded" or token_ratio > 1.0:
        warnings.append(
            {
                "code": "token_expansion",
                "severity": "warning",
                "message": f"estimated token ratio is {token_ratio}; the skeleton is larger than the source token estimate",
                "estimated_source_tokens": source_tokens,
                "estimated_skeleton_tokens": skeleton_tokens,
            }
        )
    elif token_ratio >= 0.75:
        warnings.append(
            {
                "code": "low_token_savings",
                "severity": "notice",
                "message": f"estimated token ratio is {token_ratio}; consider a more compact focus or density for stronger savings",
                "estimated_savings_percent": savings_percent,
            }
        )

    suggested_focus = focus_mode
    suggested_density = skeleton_density
    if source_kind == "directory":
        if scale_profile["scale_class"] in {"large", "huge"} and focus_mode == "full":
            warnings.append(
                {
                    "code": "large_directory_full_focus",
                    "severity": "notice",
                    "message": f"{scale_profile['scale_class']} directory detected; imports/tree focus usually gives stronger AI-facing token savings",
                    "total_files": total_files,
                    "total_chars": total_chars,
                }
            )
        if scale_profile["scale_class"] in {"medium", "large", "huge"} and not filter_patterns:
            warnings.append(
                {
                    "code": "no_directory_filters",
                    "severity": "notice",
                    "message": "no directory filters are active; consider excluding dependency, build, cache, and generated paths",
                    "suggested_excludes": preset_excludes,
                }
            )
        if focus_mode == "full":
            suggested_focus = "imports" if preset_id == "codebase" else "tree"
        if skeleton_density == "standard":
            suggested_density = "adaptive"
        if scale_profile["scale_class"] == "huge":
            suggested_density = "compact"
    elif source_kind in {"text", "markdown"}:
        if focus_mode == "full" and token_ratio >= 0.75:
            suggested_focus = "writing-outline"
        if skeleton_density == "standard":
            suggested_density = "adaptive"
        elif token_ratio >= 0.75:
            suggested_density = "compact"

    if warnings or suggested_focus != focus_mode or suggested_density != skeleton_density:
        recommendations.append(
            {
                "code": "try_more_compact_skeleton",
                "message": "try a more compact AI-facing skeleton while keeping the restore package byte-exact",
                "current_focus_mode": focus_mode,
                "current_skeleton_density": skeleton_density,
                "suggested_focus_mode": suggested_focus,
                "suggested_skeleton_density": suggested_density,
                "estimated_token_ratio": token_ratio,
                "estimated_savings_percent": savings_percent,
                "source_scale_class": scale_profile["scale_class"],
            }
        )
    elif savings_percent >= 30:
        recommendations.append(
            {
                "code": "current_config_ok",
                "message": "current skeleton settings already provide meaningful estimated token savings",
                "current_focus_mode": focus_mode,
                "current_skeleton_density": skeleton_density,
                "estimated_token_ratio": token_ratio,
                "estimated_savings_percent": savings_percent,
                "source_scale_class": scale_profile["scale_class"],
            }
        )

    recommended_config = {
        "preset_id": preset_id,
        "focus_mode": suggested_focus,
        "skeleton_density": suggested_density,
        "exclude": preset_excludes if source_kind == "directory" else [],
        "reason": recommendations[0]["message"] if recommendations else "",
    }
    if source_kind == "directory":
        directory_groups = list(source_summary.get("directory_groups") or [])
        top_group = directory_groups[0] if directory_groups else {}
        explanations.append(
            {
                "code": "directory_scale",
                "message": f"{scale_profile['scale_class']} directory profile based on {total_files} files and {total_chars} chars",
                "scale_class": scale_profile["scale_class"],
                "total_files": total_files,
                "total_chars": total_chars,
            }
        )
        if top_group:
            group_name = str(top_group.get("group") or top_group.get("root") or "")
            group_chars = int(top_group.get("total_chars", top_group.get("char_count", 0)) or 0)
            explanations.append(
                {
                    "code": "largest_directory_group",
                    "message": f"largest visible group is `{group_name}` with {top_group.get('file_count', 0)} files",
                    "root": group_name,
                    "file_count": top_group.get("file_count", 0),
                    "char_count": group_chars,
                }
            )
        if preset_excludes and not filter_patterns:
            explanations.append(
                {
                    "code": "exclude_rationale",
                    "message": "recommended excludes target dependency, build, cache, virtualenv, and generated artifact paths before compression",
                    "suggested_excludes": preset_excludes,
                }
            )
        skipped_dir_count = int(source_summary.get("skipped_dir_count", 0) or 0)
        if skipped_dir_count:
            explanations.append(
                {
                    "code": "default_noise_protection",
                    "message": f"default noise protection skipped {skipped_dir_count} dependency, build, cache, or VCS directories before compression",
                    "skipped_dir_count": skipped_dir_count,
                    "skipped_dirs_preview": list(source_summary.get("skipped_dirs") or [])[:20],
                    "skipped_dir_names": list(source_summary.get("skip_dir_names") or []),
                }
            )
        if suggested_focus != focus_mode or suggested_density != skeleton_density:
            explanations.append(
                {
                    "code": "focus_density_rationale",
                    "message": f"recommended `{suggested_focus}` + `{suggested_density}` to reduce AI-facing skeleton size while keeping restore bytes exact",
                    "current_focus_mode": focus_mode,
                    "current_skeleton_density": skeleton_density,
                    "suggested_focus_mode": suggested_focus,
                    "suggested_skeleton_density": suggested_density,
                }
            )
    elif source_kind in {"text", "markdown"}:
        explanations.append(
            {
                "code": "text_scale",
                "message": f"text profile based on {total_chars} chars and estimated token ratio {token_ratio}",
                "total_chars": total_chars,
                "estimated_token_ratio": token_ratio,
            }
        )
    return {
        "warnings": warnings,
        "recommendations": recommendations,
        "explanations": explanations,
        "recommended_config": recommended_config,
        "source_scale_profile": scale_profile,
    }


def _build_recommended_context_compress_args(
    *,
    source: dict[str, Any],
    recommended_config: dict[str, Any],
) -> list[str]:
    source_path = str(source.get("source_path") or "")
    compression_mode = str(source.get("compression_mode") or "")
    if not source_path:
        return []

    if compression_mode in {"directory", "directory_incremental"}:
        args = ["context", "compress", "--input-dir", source_path]
        if compression_mode == "directory_incremental":
            args.append("--incremental")
            base_commit = str(source.get("incremental_base_commit") or "")
            if base_commit:
                args.extend(["--base-commit", base_commit])
    elif compression_mode == "file":
        args = ["context", "compress", "--input-file", source_path]
    elif compression_mode == "text":
        args = ["context", "compress", "--text-file", source_path]
    else:
        return []

    preset_id = str(recommended_config.get("preset_id") or "")
    focus_mode = str(recommended_config.get("focus_mode") or "")
    skeleton_density = str(recommended_config.get("skeleton_density") or "")
    if preset_id:
        args.extend(["--preset", preset_id])
    if focus_mode:
        args.extend(["--focus-mode", focus_mode])
    if skeleton_density:
        args.extend(["--skeleton-density", skeleton_density])
    for pattern in recommended_config.get("exclude") or []:
        pattern_text = str(pattern).strip()
        if pattern_text:
            args.extend(["--exclude", pattern_text])
    args.append("--json")
    return args


def _build_source_scale_profile(source_summary: dict[str, Any], *, metrics: dict[str, Any]) -> dict[str, Any]:
    source_kind = str(source_summary.get("source_kind") or "")
    total_files = int(source_summary.get("total_files", 0) or 0)
    total_chars = int(source_summary.get("total_chars", 0) or source_summary.get("total_bytes", 0) or 0)
    paragraph_count = int(source_summary.get("paragraph_count", 0) or 0)
    estimated_source_tokens = int(metrics.get("estimated_token_count_source") or 0)
    if source_kind == "directory":
        if total_files >= 400 or total_chars >= 1_000_000:
            scale_class = "huge"
        elif total_files >= 120 or total_chars >= 250_000:
            scale_class = "large"
        elif total_files >= 40 or total_chars >= 100_000:
            scale_class = "medium"
        else:
            scale_class = "small"
    elif source_kind in {"text", "markdown"}:
        if total_chars >= 250_000 or paragraph_count >= 240:
            scale_class = "huge"
        elif total_chars >= 60_000 or paragraph_count >= 80:
            scale_class = "large"
        elif total_chars >= 20_000 or paragraph_count >= 30:
            scale_class = "medium"
        else:
            scale_class = "small"
    else:
        scale_class = "small"
    return {
        "source_kind": source_kind,
        "scale_class": scale_class,
        "total_files": total_files,
        "total_chars": total_chars,
        "paragraph_count": paragraph_count,
        "estimated_source_tokens": estimated_source_tokens,
        "active_filter_count": len(source_summary.get("filter_patterns") or []),
        "filtered_path_count": int(source_summary.get("filtered_path_count", 0) or 0),
    }


def _estimate_token_count(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, (char_count + 3) // 4)


def _build_token_delta_metrics(source_tokens: int, skeleton_tokens: int) -> dict[str, Any]:
    token_delta_from_source = skeleton_tokens - source_tokens
    tokens_saved = max(0, source_tokens - skeleton_tokens)
    token_ratio = round(skeleton_tokens / max(1, source_tokens), 4) if source_tokens > 0 else 0.0
    if skeleton_tokens < source_tokens:
        token_direction = "reduced"
    elif skeleton_tokens > source_tokens:
        token_direction = "expanded"
    else:
        token_direction = "flat"
    return {
        "token_count_source": source_tokens,
        "token_count_skeleton": skeleton_tokens,
        "token_delta_from_source": token_delta_from_source,
        "tokens_saved": tokens_saved,
        "token_ratio": token_ratio,
        "token_direction": token_direction,
    }


def _resolve_primary_token_metrics(
    *,
    source_text: str | None,
    source_token_hints: dict[str, Any],
    skeleton_text: str,
    heuristic_source_tokens: int,
    heuristic_skeleton_tokens: int,
    tokenizer_backend: str | None,
    tokenizer_model: str | None,
) -> dict[str, Any]:
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    skeleton_token_metrics = _compute_tiktoken_count(
        text=skeleton_text,
        tokenizer_model=tokenizer_model,
    )
    tokenizer_source_hint = _resolve_source_tokenizer_hint(
        source_token_hints,
        tokenizer_model=requested_model,
    )
    tokenizer_source_count = tokenizer_source_hint.get("token_count_source")
    tokenizer_basis = str(tokenizer_source_hint.get("token_basis") or "")
    tokenizer_error = str(skeleton_token_metrics.get("error") or "")
    tokenizer_available = bool(skeleton_token_metrics.get("available"))
    skeleton_token_count = skeleton_token_metrics.get("token_count")
    if not tokenizer_basis and skeleton_token_metrics.get("token_basis"):
        tokenizer_basis = str(skeleton_token_metrics.get("token_basis") or "")
    if tokenizer_source_count is None and source_text is not None:
        tokenizer_metrics = _compute_tiktoken_metrics(
            source_text=source_text,
            skeleton_text=skeleton_text,
            tokenizer_model=tokenizer_model,
        )
        tokenizer_available = bool(tokenizer_metrics.get("available"))
        tokenizer_error = str(tokenizer_metrics.get("error") or tokenizer_error)
        tokenizer_source_count = tokenizer_metrics.get("token_count_source")
        skeleton_token_count = tokenizer_metrics.get("token_count_skeleton")
        if tokenizer_metrics.get("token_basis"):
            tokenizer_basis = str(tokenizer_metrics.get("token_basis") or "")
    tokenizer_delta = (
        _build_token_delta_metrics(int(tokenizer_source_count), int(skeleton_token_count))
        if tokenizer_source_count is not None and skeleton_token_count is not None
        else None
    )
    if requested_backend != "heuristic" and tokenizer_available and tokenizer_delta is not None:
        primary = _build_token_delta_metrics(
            int(tokenizer_source_count),
            int(skeleton_token_count),
        )
        return {
            **primary,
            "token_backend": "tiktoken",
            "token_basis": tokenizer_basis,
            "token_model": requested_model,
            "requested_backend": requested_backend,
            "fallback_used": False,
            "tokenizer_available": True,
            "tokenizer_error": tokenizer_error,
            "tokenizer_token_count_source": primary["token_count_source"],
            "tokenizer_token_count_skeleton": primary["token_count_skeleton"],
            "tokenizer_tokens_saved": primary["tokens_saved"],
            "tokenizer_token_delta_from_source": primary["token_delta_from_source"],
            "tokenizer_token_reduction_ratio": primary["token_ratio"],
            "tokenizer_token_direction": primary["token_direction"],
            "tokenizer_token_basis": tokenizer_basis,
        }
    heuristic = _build_token_delta_metrics(heuristic_source_tokens, heuristic_skeleton_tokens)
    return {
        **heuristic,
        "token_backend": "heuristic",
        "token_basis": "heuristic_chars_div_4",
        "token_model": "",
        "requested_backend": requested_backend,
        "fallback_used": requested_backend != "heuristic",
        "tokenizer_available": tokenizer_available,
        "tokenizer_error": tokenizer_error,
        "tokenizer_token_count_source": tokenizer_source_count,
        "tokenizer_token_count_skeleton": skeleton_token_count,
        "tokenizer_tokens_saved": tokenizer_delta["tokens_saved"] if tokenizer_delta is not None else None,
        "tokenizer_token_delta_from_source": tokenizer_delta["token_delta_from_source"] if tokenizer_delta is not None else None,
        "tokenizer_token_reduction_ratio": tokenizer_delta["token_ratio"] if tokenizer_delta is not None else None,
        "tokenizer_token_direction": tokenizer_delta["token_direction"] if tokenizer_delta is not None else None,
        "tokenizer_token_basis": tokenizer_basis,
    }


def _normalize_tokenizer_backend(tokenizer_backend: str | None) -> str:
    normalized = str(tokenizer_backend or "auto").strip().lower() or "auto"
    if normalized not in TOKENIZER_BACKENDS:
        supported = ", ".join(sorted(TOKENIZER_BACKENDS))
        raise ValueError(f"Unsupported tokenizer backend `{normalized}`. Supported backends: {supported}")
    return normalized


@lru_cache(maxsize=1)
def _load_tiktoken_module() -> tuple[Any | None, str]:
    try:
        import tiktoken  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on host env
        return None, f"{type(exc).__name__}: {exc}"
    return tiktoken, ""


@lru_cache(maxsize=16)
def _resolve_tiktoken_encoder(tokenizer_model: str) -> tuple[Any, str]:
    tiktoken, error = _load_tiktoken_module()
    if tiktoken is None:
        raise RuntimeError(error or "tiktoken unavailable")
    model_name = tokenizer_model.strip() or "cl100k_base"
    try:
        encoding = tiktoken.encoding_for_model(model_name)
        encoding_name = str(getattr(encoding, "name", model_name) or model_name)
        return encoding, encoding_name
    except Exception:
        encoding = tiktoken.get_encoding(model_name)
        return encoding, model_name


def _compute_tiktoken_metrics(
    *,
    source_text: str,
    skeleton_text: str,
    tokenizer_model: str | None,
) -> dict[str, Any]:
    tiktoken, error = _load_tiktoken_module()
    if tiktoken is None:
        return {"available": False, "error": error}
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    try:
        encoder, encoding_name = _resolve_tiktoken_encoder(requested_model)
        source_tokens = len(encoder.encode(source_text or ""))
        skeleton_tokens = len(encoder.encode(skeleton_text or ""))
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "token_model": requested_model,
        }
    return {
        "available": True,
        "token_model": requested_model,
        "token_basis": f"tiktoken:{encoding_name}",
        **_build_token_delta_metrics(source_tokens, skeleton_tokens),
    }


def _compute_tiktoken_count(
    *,
    text: str,
    tokenizer_model: str | None,
) -> dict[str, Any]:
    tiktoken, error = _load_tiktoken_module()
    if tiktoken is None:
        return {"available": False, "error": error}
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    try:
        encoder, encoding_name = _resolve_tiktoken_encoder(requested_model)
        token_count = len(encoder.encode(text or ""))
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "token_model": requested_model,
        }
    return {
        "available": True,
        "token_model": requested_model,
        "token_basis": f"tiktoken:{encoding_name}",
        "token_count": token_count,
    }


def _resolve_source_tokenizer_hint(
    source_token_hints: dict[str, Any],
    *,
    tokenizer_model: str,
) -> dict[str, Any]:
    tokenizer_count_source = source_token_hints.get("tokenizer_token_count_source")
    hint_model = str(source_token_hints.get("tokenizer_model") or "").strip() or "cl100k_base"
    if tokenizer_count_source is None or hint_model != tokenizer_model:
        return {}
    return {
        "token_count_source": int(tokenizer_count_source),
        "token_basis": str(source_token_hints.get("tokenizer_token_basis") or ""),
        "token_model": hint_model,
    }


def _can_reuse_source_token_hints(
    source_token_hints: dict[str, Any],
    *,
    tokenizer_backend: str | None,
    tokenizer_model: str | None,
) -> bool:
    if not source_token_hints:
        return False
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    if requested_backend == "heuristic":
        return source_token_hints.get("heuristic_token_count_source") is not None
    requested_model = str(tokenizer_model or "").strip() or "cl100k_base"
    return (
        source_token_hints.get("tokenizer_token_count_source") is not None
        and str(source_token_hints.get("tokenizer_model") or "").strip() == requested_model
    )


def _build_token_source_text_from_source(source: dict[str, Any]) -> str:
    return _build_token_source_text_from_restore_blob(source.get("restore_blob") or {})


def _build_token_source_text_from_restore_blob(restore_blob: dict[str, Any]) -> str:
    mode = str(restore_blob.get("mode") or "")
    if mode == "text":
        return str(restore_blob.get("text") or "")
    if mode == "file":
        if str(restore_blob.get("source_kind") or "") == "binary":
            return ""
        raw_bytes = _decode_restore_content_b64(restore_blob.get("content_b64"))
        file_name = str(restore_blob.get("file_name") or restore_blob.get("source_label") or "context-file")
        decoded_text = _decode_text_bytes(Path(file_name), raw_bytes, allow_extension_hint=True)
        if decoded_text is not None:
            return str(decoded_text["text"])
        return ""
    if mode in {"directory", "directory_incremental"}:
        parts: list[str] = []
        for item in sorted(restore_blob.get("files") or [], key=lambda entry: str(entry.get("relative_path") or "")):
            rel_path = str(item.get("relative_path") or "")
            raw_bytes = _decode_restore_content_b64(item.get("content_b64"))
            decoded_text = _decode_text_bytes(Path(rel_path), raw_bytes, allow_extension_hint=True)
            if decoded_text is not None:
                parts.append(str(decoded_text["text"]))
        return "\n\n".join(part for part in parts if part)
    return ""


def _decode_restore_content_b64(content_b64: Any) -> bytes:
    encoded = str(content_b64 or "").strip()
    if not encoded:
        return b""
    return base64.b64decode(encoded.encode("ascii"))


def _resolve_patch_apply_policy(
    *,
    policy_mode: str | None,
    sample_policy: str | None,
    policy_file: Path | None,
    allow_roots: list[str] | None,
    forbid_roots: list[str] | None,
    block_removals: bool,
    block_additions: bool,
    require_apply_check_passed: bool,
    max_changed_paths: int | None,
) -> dict[str, Any]:
    normalized_sample = str(sample_policy or "").strip().lower()
    if normalized_sample:
        if normalized_sample not in PATCH_POLICY_SAMPLES:
            supported = ", ".join(sorted(PATCH_POLICY_SAMPLES.keys()))
            raise ValueError(f"Unsupported context patch-apply sample policy `{normalized_sample}`. Supported samples: {supported}")
        policy = dict(PATCH_POLICY_SAMPLES[normalized_sample])
    else:
        normalized_mode = str(policy_mode or "open").strip().lower() or "open"
        if normalized_mode not in PATCH_POLICY_MODES:
            supported = ", ".join(sorted(PATCH_POLICY_MODES.keys()))
            raise ValueError(f"Unsupported context patch-apply policy mode `{normalized_mode}`. Supported modes: {supported}")
        policy = dict(PATCH_POLICY_MODES[normalized_mode])
    if policy_file is not None:
        loaded = json.loads(policy_file.expanduser().read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("context patch-apply policy file must contain one JSON object")
        for key in ["require_apply_check_passed", "block_removals", "block_additions", "max_changed_paths"]:
            if key in loaded:
                policy[key] = loaded[key]
        for key in ["allow_roots", "forbid_roots"]:
            if key in loaded:
                value = loaded.get(key) or []
                if not isinstance(value, list):
                    raise ValueError(f"context patch-apply policy field `{key}` must be a JSON array")
                policy[key] = [str(item) for item in value if str(item).strip()]
    if allow_roots:
        policy["allow_roots"] = [str(item) for item in allow_roots if str(item).strip()]
    if forbid_roots:
        policy["forbid_roots"] = [str(item) for item in forbid_roots if str(item).strip()]
    if block_removals:
        policy["block_removals"] = True
    if block_additions:
        policy["block_additions"] = True
    if require_apply_check_passed:
        policy["require_apply_check_passed"] = True
    if max_changed_paths is not None:
        if int(max_changed_paths) < 0:
            raise ValueError("context patch-apply --max-changed-paths must be zero or greater")
        policy["max_changed_paths"] = int(max_changed_paths)
    policy["allow_roots"] = [_normalize_patch_relpath(item) for item in (policy.get("allow_roots") or []) if _normalize_patch_relpath(item)]
    policy["forbid_roots"] = [_normalize_patch_relpath(item) for item in (policy.get("forbid_roots") or []) if _normalize_patch_relpath(item)]
    return policy


def build_context_patch_policy_template_payload(
    *,
    policy_mode: str | None,
    sample_policy: str | None,
    policy_file: Path | None,
    allow_roots: list[str] | None,
    forbid_roots: list[str] | None,
    block_removals: bool,
    block_additions: bool,
    require_apply_check_passed: bool,
    max_changed_paths: int | None,
) -> dict[str, Any]:
    policy = _resolve_patch_apply_policy(
        policy_mode=policy_mode,
        sample_policy=sample_policy,
        policy_file=policy_file,
        allow_roots=allow_roots,
        forbid_roots=forbid_roots,
        block_removals=block_removals,
        block_additions=block_additions,
        require_apply_check_passed=require_apply_check_passed,
        max_changed_paths=max_changed_paths,
    )
    return {
        "status": "ok",
        "entrypoint": "context-patch-apply-policy-template",
        "sample_policy": str(sample_policy or "").strip().lower() or None,
        "policy_mode": str(policy.get("policy_mode") or "open"),
        "policy_template": policy,
        "summary_text": json.dumps(policy, ensure_ascii=False, indent=2),
        "next_steps": [
            "save this JSON as a reusable context patch-apply policy file",
            "pass it back through --policy-file when replaying one patch bundle",
        ],
    }


def _evaluate_patch_apply_merge(
    *,
    patch_payload: dict[str, Any],
    source_package_payload: dict[str, Any] | None,
    patch_mode: str,
    source_label: str,
    output_dir: Path | None,
    output_file: Path | None,
    merge_mode: str,
) -> dict[str, Any]:
    if merge_mode == "overwrite":
        return {"passed": True, "conflicts": [], "conflict_records": []}
    if source_package_payload is None:
        return {
            "passed": False,
            "conflicts": ["Merge-aware replay requires the original source package so the current target can be compared to the original base."],
            "conflict_records": [
                {
                    "path": "",
                    "conflict_kind": "missing_source_package_base",
                    "message": "Merge-aware replay requires the original source package so the current target can be compared to the original base.",
                }
            ],
        }
    decoded = _decode_restore_blob(source_package_payload.get("restore_package") or {})
    conflicts: list[str] = []
    conflict_records: list[dict[str, str]] = []
    if patch_mode == "text_unified_diff":
        if output_file is not None:
            target_path = _resolve_output_target_file(output_file)
        elif output_dir is not None:
            target_path = output_dir.expanduser().resolve() / source_label
        else:
            message = "Merge-aware text replay requires --output-file or --output-dir."
            return {
                "passed": False,
                "conflicts": [message],
                "conflict_records": [{"path": source_label, "conflict_kind": "missing_replay_target", "message": message}],
            }
        if target_path.exists():
            current_text = target_path.read_text(encoding="utf-8")
            base_text = str(decoded.get("text") or "")
            if current_text != base_text:
                message = f"Target file already diverged from the original base: {target_path}"
                conflicts.append(message)
                conflict_records.append(
                    {
                        "path": str(target_path),
                        "conflict_kind": "target_diverged_from_base",
                        "message": message,
                    }
                )
        return {"passed": not conflicts, "conflicts": conflicts, "conflict_records": conflict_records}
    if patch_mode in {"file_unified_diff", "file_binary_replace"}:
        if output_file is not None:
            target_path = _resolve_output_target_file(output_file)
        elif output_dir is not None:
            target_path = output_dir.expanduser().resolve() / str(decoded.get("file_name") or source_label)
        else:
            message = "Merge-aware file replay requires --output-file or --output-dir."
            return {
                "passed": False,
                "conflicts": [message],
                "conflict_records": [{"path": source_label, "conflict_kind": "missing_replay_target", "message": message}],
            }
        if target_path.exists():
            current_bytes = target_path.read_bytes()
            base_bytes = _decode_restore_content_b64(decoded.get("content_b64"))
            if current_bytes != base_bytes:
                message = f"Target file already diverged from the original base: {target_path}"
                conflicts.append(message)
                conflict_records.append(
                    {
                        "path": str(target_path),
                        "conflict_kind": "target_diverged_from_base",
                        "message": message,
                    }
                )
        return {"passed": not conflicts, "conflicts": conflicts, "conflict_records": conflict_records}
    if patch_mode == "directory_structural_patch":
        if output_dir is None:
            message = "Merge-aware directory replay requires --output-dir."
            return {
                "passed": False,
                "conflicts": [message],
                "conflict_records": [{"path": source_label, "conflict_kind": "missing_replay_target", "message": message}],
            }
        root_name = str(decoded.get("root_name") or source_label or "restored-context")
        target_root = output_dir.expanduser().resolve() / root_name
        if not target_root.exists():
            return {"passed": True, "conflicts": [], "conflict_records": []}
        original_files = {str(item.get("relative_path") or ""): _decode_restore_content_b64(item.get("content_b64")) for item in (decoded.get("files") or [])}
        changed_paths = [str(item) for item in (patch_payload.get("changed_paths") or []) if str(item).strip()]
        added_paths = [str(item) for item in (patch_payload.get("added_paths") or []) if str(item).strip()]
        removed_paths = [str(item) for item in (patch_payload.get("removed_paths") or []) if str(item).strip()]
        for rel_path in changed_paths + removed_paths:
            base_bytes = original_files.get(rel_path)
            target_path = target_root / rel_path
            if target_path.exists():
                current_bytes = target_path.read_bytes()
                if base_bytes is None or current_bytes != base_bytes:
                    message = f"Target path already diverged from the original base: {target_path}"
                    conflicts.append(message)
                    conflict_records.append(
                        {
                            "path": rel_path,
                            "conflict_kind": "target_diverged_from_base",
                            "message": message,
                        }
                    )
            elif base_bytes is not None:
                message = f"Target path is already missing before replay: {target_path}"
                conflicts.append(message)
                conflict_records.append(
                    {
                        "path": rel_path,
                        "conflict_kind": "target_missing_before_replay",
                        "message": message,
                    }
                )
        for rel_path in added_paths:
            target_path = target_root / rel_path
            if target_path.exists():
                message = f"Target path already exists where this patch wants to add content: {target_path}"
                conflicts.append(message)
                conflict_records.append(
                    {
                        "path": rel_path,
                        "conflict_kind": "target_exists_for_added_path",
                        "message": message,
                    }
                )
        return {"passed": not conflicts, "conflicts": conflicts, "conflict_records": conflict_records}
    return {"passed": True, "conflicts": [], "conflict_records": []}


def build_context_patch_merge_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status", ""),
        "entrypoint": "context-patch-apply-merge-report",
        "apply_mode": payload.get("apply_mode", ""),
        "patch_mode": payload.get("patch_mode", ""),
        "source_label": payload.get("source_label", ""),
        "dry_run": bool(payload.get("dry_run", False)),
        "merge_mode": payload.get("merge_mode", "overwrite"),
        "merge_check_passed": bool(payload.get("merge_check_passed", True)),
        "merge_conflict_count": len(payload.get("merge_conflicts") or []),
        "merge_conflicts": list(payload.get("merge_conflicts") or []),
        "merge_conflict_records": list(payload.get("merge_conflict_records") or []),
    }


def build_context_patch_dry_run_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    preview_manifest = dict(payload.get("preview_manifest") or {})
    changed_paths = list(preview_manifest.get("changed_paths") or [])
    added_paths = list(preview_manifest.get("added_paths") or [])
    removed_paths = list(preview_manifest.get("removed_paths") or [])
    write_targets = list(preview_manifest.get("write_targets") or [])
    remove_targets = list(preview_manifest.get("remove_targets") or [])
    surface_size = _context_patch_preview_surface_size(preview_manifest)
    report = {
        "status": payload.get("status", ""),
        "entrypoint": "context-patch-apply-dry-run-report",
        "apply_mode": payload.get("apply_mode", ""),
        "patch_mode": payload.get("patch_mode", ""),
        "source_label": payload.get("source_label", ""),
        "dry_run": bool(payload.get("dry_run", False)),
        "merge_mode": payload.get("merge_mode", "overwrite"),
        "merge_check_passed": bool(payload.get("merge_check_passed", True)),
        "policy_mode": payload.get("policy_mode", ""),
        "policy_passed": bool(payload.get("policy_passed", True)),
        "surface_size": surface_size,
        "risk_band": _context_patch_preview_risk_band(surface_size),
        "change_counts": {
            "changed_paths": len(changed_paths),
            "added_paths": len(added_paths),
            "removed_paths": len(removed_paths),
            "write_targets": len(write_targets),
            "remove_targets": len(remove_targets),
        },
        "first_changed_path": changed_paths[0] if changed_paths else "",
        "first_added_path": added_paths[0] if added_paths else "",
        "first_removed_path": removed_paths[0] if removed_paths else "",
        "first_write_target": write_targets[0] if write_targets else "",
        "first_remove_target": remove_targets[0] if remove_targets else "",
        "preview_manifest": preview_manifest,
    }
    if payload.get("incremental_mode"):
        incremental_changed_paths = list(payload.get("incremental_changed_paths") or [])
        incremental_added_paths = list(payload.get("incremental_added_paths") or [])
        incremental_removed_paths = list(payload.get("incremental_removed_paths") or [])
        report.update(
            {
                "incremental_mode": True,
                "incremental_scope": payload.get("incremental_scope", ""),
                "incremental_base_commit": payload.get("incremental_base_commit", ""),
                "incremental_path_count": int(payload.get("incremental_path_count") or 0),
                "incremental_change_counts": {
                    "changed_paths": len(incremental_changed_paths),
                    "added_paths": len(incremental_added_paths),
                    "removed_paths": len(incremental_removed_paths),
                },
                "incremental_changed_paths": incremental_changed_paths,
                "incremental_added_paths": incremental_added_paths,
                "incremental_removed_paths": incremental_removed_paths,
                "first_incremental_changed_path": incremental_changed_paths[0] if incremental_changed_paths else "",
                "first_incremental_added_path": incremental_added_paths[0] if incremental_added_paths else "",
                "first_incremental_removed_path": incremental_removed_paths[0] if incremental_removed_paths else "",
            }
        )
    return report


def _context_patch_preview_surface_size(preview_manifest: dict[str, Any]) -> int:
    changed_paths = list(preview_manifest.get("changed_paths") or [])
    added_paths = list(preview_manifest.get("added_paths") or [])
    removed_paths = list(preview_manifest.get("removed_paths") or [])
    return len(set(changed_paths + added_paths + removed_paths))


def _context_patch_preview_risk_band(surface_size: int) -> str:
    if surface_size <= 1:
        return "small"
    if surface_size <= 5:
        return "medium"
    return "large"


def _build_context_patch_apply_preview_manifest(
    *,
    patch_payload: dict[str, Any],
    patch_mode: str,
    applied_root_or_file: Path,
    directory_root: Path | None,
) -> dict[str, Any]:
    changed_paths = [str(item) for item in (patch_payload.get("changed_paths") or []) if str(item).strip()]
    added_paths = [str(item) for item in (patch_payload.get("added_paths") or []) if str(item).strip()]
    removed_paths = [str(item) for item in (patch_payload.get("removed_paths") or []) if str(item).strip()]
    write_targets: list[str] = []
    remove_targets: list[str] = []
    if patch_mode in {"text_unified_diff", "file_unified_diff", "file_binary_replace"}:
        write_targets = [str(applied_root_or_file.resolve())] if (changed_paths or added_paths or not removed_paths) else []
    elif patch_mode == "directory_structural_patch" and directory_root is not None:
        directory_root = directory_root.resolve()
        write_targets = [
            str(_safe_context_target_path(directory_root, rel_path, field_name="preview_write_targets"))
            for rel_path in sorted(set(changed_paths + added_paths))
        ]
        remove_targets = [
            str(_safe_context_target_path(directory_root, rel_path, field_name="preview_remove_targets"))
            for rel_path in removed_paths
        ]
    return {
        "changed_paths": changed_paths,
        "added_paths": added_paths,
        "removed_paths": removed_paths,
        "write_targets": write_targets,
        "remove_targets": remove_targets,
    }


def _evaluate_patch_apply_policy(*, patch_payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    changed_paths = [_normalize_patch_relpath(item) for item in (patch_payload.get("changed_paths") or []) if _normalize_patch_relpath(item)]
    added_paths = [_normalize_patch_relpath(item) for item in (patch_payload.get("added_paths") or []) if _normalize_patch_relpath(item)]
    removed_paths = [_normalize_patch_relpath(item) for item in (patch_payload.get("removed_paths") or []) if _normalize_patch_relpath(item)]
    affected_paths = sorted(set(changed_paths + added_paths + removed_paths))
    findings: list[str] = []
    if policy.get("require_apply_check_passed") and not bool(patch_payload.get("apply_check_passed")):
        findings.append("Patch policy requires a passing apply-check result before replay.")
    if policy.get("block_removals") and removed_paths:
        findings.append("Patch policy blocks removed paths during replay.")
    if policy.get("block_additions") and added_paths:
        findings.append("Patch policy blocks added paths during replay.")
    max_changed = policy.get("max_changed_paths")
    if max_changed not in (None, "") and len(affected_paths) > int(max_changed):
        findings.append(f"Patch policy allows at most {int(max_changed)} affected paths, but this patch touches {len(affected_paths)}.")
    allow_roots = policy.get("allow_roots") or []
    if allow_roots:
        disallowed = [path for path in affected_paths if not any(_path_matches_policy_root(path, root) for root in allow_roots)]
        if disallowed:
            findings.append(f"Patch policy only allows these roots: {', '.join(allow_roots)}.")
    forbid_roots = policy.get("forbid_roots") or []
    if forbid_roots:
        blocked = [path for path in affected_paths if any(_path_matches_policy_root(path, root) for root in forbid_roots)]
        if blocked:
            findings.append(f"Patch policy forbids these roots: {', '.join(forbid_roots)}.")
    return {
        "passed": not findings,
        "findings": findings,
        "affected_paths": affected_paths,
        "policy_mode": str(policy.get("policy_mode") or "open"),
        "policy_payload": {
            "policy_mode": str(policy.get("policy_mode") or "open"),
            "require_apply_check_passed": bool(policy.get("require_apply_check_passed")),
            "block_removals": bool(policy.get("block_removals")),
            "block_additions": bool(policy.get("block_additions")),
            "max_changed_paths": policy.get("max_changed_paths"),
            "allow_roots": list(allow_roots),
            "forbid_roots": list(forbid_roots),
        },
    }


def _normalize_patch_relpath(path: str) -> str:
    normalized = str(path or "").strip().replace("\\", "/")
    normalized = re.sub(r"^\./+", "", normalized)
    normalized = normalized.lstrip("/")
    return normalized.rstrip("/")


def _path_matches_policy_root(path: str, root: str) -> bool:
    normalized_path = _normalize_patch_relpath(path)
    normalized_root = _normalize_patch_relpath(root)
    if not normalized_root:
        return False
    return normalized_path == normalized_root or normalized_path.startswith(f"{normalized_root}/")


def _int_metric(value: Any, *, fallback: Any = 0) -> int:
    candidate = value if value not in (None, "") else fallback
    try:
        return int(candidate or 0)
    except (TypeError, ValueError):
        return int(fallback or 0)


def _first_sentence(text: str) -> str:
    stripped = re.sub(r"\s+", " ", text.strip())
    if not stripped:
        return ""
    match = re.split(r"(?<=[。！？.!?])\s+", stripped, maxsplit=1)
    return match[0][:160]


def _resolve_restore_file_path(*, output_dir: Path | None, output_file: Path | None, suggested_name: str) -> Path:
    if output_file is not None:
        path = output_file.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    if output_dir is None:
        raise ValueError("context restore requires --output-file or --output-dir when restoring a file package")
    return output_dir.expanduser().resolve() / suggested_name


def _resolve_output_target_file(path: Path) -> Path:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    return target


def _normalize_context_relpath(rel_path: str, *, field_name: str = "relative_path") -> str:
    normalized = str(rel_path or "").replace("\\", "/").strip()
    if not normalized:
        raise ValueError(f"context path field `{field_name}` must not be empty")
    if re.match(r"^[A-Za-z]:($|/)", normalized):
        raise ValueError(f"context path field `{field_name}` must stay relative, got drive-qualified path `{rel_path}`")
    pure = PurePosixPath(normalized)
    if pure.is_absolute():
        raise ValueError(f"context path field `{field_name}` must stay relative, got absolute path `{rel_path}`")
    cleaned_parts: list[str] = []
    for part in pure.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"context path field `{field_name}` must not traverse upward: `{rel_path}`")
        cleaned_parts.append(part)
    if not cleaned_parts:
        raise ValueError(f"context path field `{field_name}` must resolve to a non-empty relative path")
    return "/".join(cleaned_parts)


def _safe_context_target_path(root: Path, rel_path: str, *, field_name: str = "relative_path") -> Path:
    normalized_rel_path = _normalize_context_relpath(rel_path, field_name=field_name)
    root_resolved = root.expanduser().resolve()
    candidate = (root_resolved / Path(*normalized_rel_path.split("/"))).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"context path field `{field_name}` escapes the target root: `{rel_path}`")
    return candidate


def _restore_file_blob(target_path: Path, decoded: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(str(decoded.get("content_b64") or "").encode("ascii"))
    target_path.write_bytes(data)


def _restore_directory_blob(restore_root: Path, decoded: dict[str, Any]) -> None:
    restore_root.mkdir(parents=True, exist_ok=True)
    for rel_dir in decoded.get("empty_dirs") or []:
        _safe_context_target_path(restore_root, str(rel_dir), field_name="empty_dirs").mkdir(parents=True, exist_ok=True)
    for item in decoded.get("files") or []:
        target_path = _safe_context_target_path(restore_root, str(item.get("relative_path") or ""), field_name="relative_path")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(base64.b64decode(str(item.get("content_b64") or "").encode("ascii")))
    for item in decoded.get("symlinks") or []:
        target_path = _safe_context_target_path(restore_root, str(item.get("relative_path") or ""), field_name="relative_path")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.symlink_to(str(item.get("link_target") or ""))


def _write_incremental_restore_manifest(
    manifest_path: Path,
    *,
    incremental_scope: str,
    base_commit: str,
    removed_paths: list[str],
) -> None:
    removed_manifest = {
        "status": "ok",
        "entrypoint": "context-incremental-restore-manifest",
        "incremental_scope": incremental_scope,
        "base_commit": base_commit,
        "removed_paths": list(removed_paths),
        "removed_path_count": len(removed_paths),
    }
    _write_json(manifest_path, removed_manifest)


def _build_context_patch_artifacts(
    *,
    package_payload: dict[str, Any],
    candidate: dict[str, Any],
    patch_root: Path,
) -> dict[str, Any]:
    original_decoded = _decode_restore_blob(package_payload.get("restore_package") or {})
    candidate_restore = candidate.get("restore_blob") or {}
    mode = str(package_payload.get("compression_mode") or "")
    if mode == "text":
        return _build_text_patch_artifacts(
            original_decoded=original_decoded,
            candidate_restore=candidate_restore,
            patch_root=patch_root,
            source_label=str(package_payload.get("source_label") or "context.txt"),
            candidate_label=str(candidate.get("source_label") or "candidate.txt"),
        )
    if mode == "file":
        return _build_file_patch_artifacts(
            original_decoded=original_decoded,
            candidate_restore=candidate_restore,
            patch_root=patch_root,
            source_label=str(package_payload.get("source_label") or "context-file"),
        )
    if mode in {"directory", "directory_incremental"}:
        return _build_directory_patch_artifacts(
            original_decoded=original_decoded,
            candidate_restore=candidate_restore,
            patch_root=patch_root,
        )
    raise ValueError(f"Unsupported context patch mode: {mode}")


def _build_text_patch_artifacts(
    *,
    original_decoded: dict[str, Any],
    candidate_restore: dict[str, Any],
    patch_root: Path,
    source_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    original_text = str(original_decoded.get("text") or "")
    candidate_text = str(candidate_restore.get("text") or "")
    candidate_bytes = (
        base64.b64decode(str(candidate_restore.get("content_b64") or "").encode("ascii"))
        if str(candidate_restore.get("content_b64") or "").strip()
        else candidate_text.encode("utf-8")
    )
    diff_lines = list(
        difflib.unified_diff(
            original_text.splitlines(),
            candidate_text.splitlines(),
            fromfile=f"original/{source_label}",
            tofile=f"candidate/{candidate_label}",
            lineterm="",
        )
    )
    diff_text = "\n".join(diff_lines).rstrip() + ("\n" if diff_lines else "")
    if not diff_text:
        diff_text = "# No textual changes detected.\n"
    added_lines, removed_lines = _diff_line_counts(diff_lines)
    files = {
        "patch_diff": patch_root / "patch.diff",
        "candidate_snapshot_file": patch_root / "candidate_snapshot.txt",
    }
    _write_text_file(files["patch_diff"], diff_text)
    _write_bytes_file(files["candidate_snapshot_file"], candidate_bytes)
    changed = original_text != candidate_text
    return {
        "patch_mode": "text_unified_diff",
        "files": files,
        "change_counts": {
            "changed_paths": 1 if changed else 0,
            "added_paths": 0,
            "removed_paths": 0,
            "unchanged_paths": 0 if changed else 1,
            "text_patch_files": 1,
            "binary_snapshot_files": 0,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
        },
        "changed_paths": [candidate_label] if changed else [],
        "added_paths": [],
        "removed_paths": [],
    }


def _build_file_patch_artifacts(
    *,
    original_decoded: dict[str, Any],
    candidate_restore: dict[str, Any],
    patch_root: Path,
    source_label: str,
) -> dict[str, Any]:
    file_name = str(candidate_restore.get("file_name") or original_decoded.get("file_name") or source_label)
    original_bytes = base64.b64decode(str(original_decoded.get("content_b64") or "").encode("ascii"))
    candidate_bytes = base64.b64decode(str(candidate_restore.get("content_b64") or "").encode("ascii"))
    snapshot_root = patch_root / "candidate_snapshot"
    snapshot_file = snapshot_root / file_name
    _write_bytes_file(snapshot_file, candidate_bytes)

    original_decoded_text = _decode_text_bytes(Path(file_name), original_bytes, allow_extension_hint=True)
    candidate_decoded_text = _decode_text_bytes(Path(file_name), candidate_bytes, allow_extension_hint=True)
    is_text = original_decoded_text is not None and candidate_decoded_text is not None
    files: dict[str, Path] = {"candidate_snapshot_file": snapshot_file}
    added_lines = 0
    removed_lines = 0
    patch_mode = "file_binary_replace"
    if is_text:
        original_text = str(original_decoded_text["text"])
        candidate_text = str(candidate_decoded_text["text"])
        diff_lines = list(
            difflib.unified_diff(
                original_text.splitlines(),
                candidate_text.splitlines(),
                fromfile=f"original/{file_name}",
                tofile=f"candidate/{file_name}",
                lineterm="",
            )
        )
        diff_text = "\n".join(diff_lines).rstrip() + ("\n" if diff_lines else "")
        if not diff_text:
            diff_text = "# No textual changes detected.\n"
        added_lines, removed_lines = _diff_line_counts(diff_lines)
        files["patch_diff"] = patch_root / "patch.diff"
        _write_text_file(files["patch_diff"], diff_text)
        patch_mode = "file_unified_diff"
    else:
        files["binary_change_note"] = patch_root / "binary_change_note.txt"
        note_lines = [
            "Binary replacement patch",
            "",
            f"source_label: {source_label}",
            f"file_name: {file_name}",
            f"original_sha256: {original_decoded.get('sha256', '')}",
            f"candidate_sha256: {candidate_restore.get('sha256', '')}",
            "",
            "Use the candidate snapshot file as the replacement payload.",
        ]
        _write_text_file(files["binary_change_note"], "\n".join(note_lines) + "\n")

    changed = original_bytes != candidate_bytes
    return {
        "patch_mode": patch_mode,
        "files": files,
        "change_counts": {
            "changed_paths": 1 if changed else 0,
            "added_paths": 0,
            "removed_paths": 0,
            "unchanged_paths": 0 if changed else 1,
            "text_patch_files": 1 if is_text else 0,
            "binary_snapshot_files": 0 if is_text else 1,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
        },
        "changed_paths": [file_name] if changed else [],
        "added_paths": [],
        "removed_paths": [],
    }


def _build_directory_patch_artifacts(
    *,
    original_decoded: dict[str, Any],
    candidate_restore: dict[str, Any],
    patch_root: Path,
) -> dict[str, Any]:
    original_files = {
        _normalize_context_relpath(str(item.get("relative_path") or ""), field_name="relative_path"): base64.b64decode(str(item.get("content_b64") or "").encode("ascii"))
        for item in (original_decoded.get("files") or [])
        if str(item.get("relative_path") or "").strip()
    }
    candidate_files = {
        _normalize_context_relpath(str(item.get("relative_path") or ""), field_name="relative_path"): base64.b64decode(str(item.get("content_b64") or "").encode("ascii"))
        for item in (candidate_restore.get("files") or [])
        if str(item.get("relative_path") or "").strip()
    }
    original_paths = set(path for path in original_files.keys() if path)
    candidate_paths = set(path for path in candidate_files.keys() if path)
    added_paths = sorted(candidate_paths - original_paths)
    removed_paths = sorted(original_paths - candidate_paths)
    common_paths = sorted(original_paths & candidate_paths)
    changed_paths = sorted(path for path in common_paths if original_files[path] != candidate_files[path])
    unchanged_paths = sorted(path for path in common_paths if original_files[path] == candidate_files[path])

    patches_root = patch_root / "patches"
    candidate_snapshot_root = patch_root / "candidate_snapshot"
    patch_preview_diff = patch_root / "patch_preview.diff"
    binary_notes_root = patch_root / "binary_notes"
    preview_chunks: list[str] = []
    text_patch_files = 0
    binary_snapshot_files = 0
    added_lines_total = 0
    removed_lines_total = 0

    def _write_candidate_snapshot(rel_path: str, data: bytes) -> None:
        _write_bytes_file(_safe_context_target_path(candidate_snapshot_root, rel_path, field_name="candidate_snapshot"), data)

    for rel_path in sorted(set(added_paths + changed_paths)):
        _write_candidate_snapshot(rel_path, candidate_files[rel_path])

    for rel_path in sorted(set(added_paths + removed_paths + changed_paths)):
        original_bytes = original_files.get(rel_path)
        candidate_bytes = candidate_files.get(rel_path)
        original_decoded_text = _decode_text_bytes(Path(rel_path), original_bytes or b"", allow_extension_hint=True) if original_bytes is not None else None
        candidate_decoded_text = _decode_text_bytes(Path(rel_path), candidate_bytes or b"", allow_extension_hint=True) if candidate_bytes is not None else None
        if original_decoded_text is not None or candidate_decoded_text is not None:
            original_text = str(original_decoded_text["text"]) if original_decoded_text is not None else ""
            candidate_text = str(candidate_decoded_text["text"]) if candidate_decoded_text is not None else ""
            diff_lines = list(
                difflib.unified_diff(
                    original_text.splitlines(),
                    candidate_text.splitlines(),
                    fromfile=f"original/{rel_path}",
                    tofile=f"candidate/{rel_path}",
                    lineterm="",
                )
            )
            diff_text = "\n".join(diff_lines).rstrip() + ("\n" if diff_lines else "")
            if not diff_text:
                diff_text = "# No textual changes detected.\n"
            patch_file = _safe_context_target_path(patches_root, f"{rel_path}.diff", field_name="patch_diff")
            _write_text_file(patch_file, diff_text)
            text_patch_files += 1
            added_lines, removed_lines = _diff_line_counts(diff_lines)
            added_lines_total += added_lines
            removed_lines_total += removed_lines
            if len(preview_chunks) < 5:
                preview_chunks.append(diff_text.rstrip())
        else:
            note_file = _safe_context_target_path(binary_notes_root, f"{rel_path}.txt", field_name="binary_note")
            _write_text_file(
                note_file,
                "\n".join(
                    [
                        "Binary file patch note",
                        "",
                        f"relative_path: {rel_path}",
                        f"original_present: {original_bytes is not None}",
                        f"candidate_present: {candidate_bytes is not None}",
                        f"original_sha256: {_sha256_bytes(original_bytes) if original_bytes is not None else ''}",
                        f"candidate_sha256: {_sha256_bytes(candidate_bytes) if candidate_bytes is not None else ''}",
                    ]
                )
                + "\n",
            )
            if candidate_bytes is not None:
                binary_snapshot_files += 1

    preview_text = "\n\n".join(chunk for chunk in preview_chunks if chunk).rstrip() + ("\n" if preview_chunks else "")
    if not preview_text:
        preview_text = "# No textual diff preview available.\n"
    _write_text_file(patch_preview_diff, preview_text)

    files = {
        "patch_preview_diff": patch_preview_diff,
        "patches_root": patches_root,
        "candidate_snapshot_root": candidate_snapshot_root,
    }
    if binary_notes_root.exists():
        files["binary_notes_root"] = binary_notes_root
    return {
        "patch_mode": "directory_structural_patch",
        "files": files,
        "change_counts": {
            "changed_paths": len(changed_paths),
            "added_paths": len(added_paths),
            "removed_paths": len(removed_paths),
            "unchanged_paths": len(unchanged_paths),
            "text_patch_files": text_patch_files,
            "binary_snapshot_files": binary_snapshot_files,
            "added_lines": added_lines_total,
            "removed_lines": removed_lines_total,
        },
        "changed_paths": changed_paths,
        "added_paths": added_paths,
        "removed_paths": removed_paths,
    }


def _build_context_patch_readme_text(payload: dict[str, Any], files: dict[str, Path]) -> str:
    return "\n".join(
        [
            "AIL Builder Context Patch Bundle",
            "",
            f"manifest_version: {payload.get('manifest_version', 'context_patch.v1')}",
            f"bundle_created_at: {payload.get('bundle_created_at', '')}",
            f"preset_id: {payload.get('preset_id', 'generic')}",
            f"compression_mode: {payload.get('compression_mode', '')}",
            f"source_kind: {payload.get('source_kind', '')}",
            f"source_label: {payload.get('source_label', '')}",
            f"candidate_source_kind: {payload.get('candidate_source_kind', '')}",
            f"candidate_source_label: {payload.get('candidate_source_label', '')}",
            f"patch_mode: {payload.get('patch_mode', '')}",
            f"apply_check_passed: {payload.get('apply_check_passed', False)}",
            "",
            "Files:",
            "- patch_manifest.json: full machine-readable patch bundle",
            "- patch_summary.txt: compact patch summary",
            "- apply_check.json: structural continuity validation against the original bundle",
            "- apply_check_summary.txt: compact apply-check summary",
            "- patch diff or patch preview files: human-readable change surface",
            "- candidate snapshot files: exact edited payloads for changed or added content",
            "- README.txt: this usage note",
            "",
            "Suggested flow:",
            f"1. inspect {files['patch_summary_txt']} first",
            f"2. inspect {files['apply_check_summary_txt']} before handing the patch to another model or IDE",
            "3. use the candidate snapshot or diff files when you need to manually apply the edited surface",
        ]
    ) + "\n"


def _diff_line_counts(diff_lines: list[str]) -> tuple[int, int]:
    added = 0
    removed = 0
    for line in diff_lines:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def _write_text(path: Path, text: str) -> None:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _write_text_file(path: Path, text: str) -> None:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _context_bundle_root() -> Path:
    return (Path.cwd() / ".workspace_ail" / "context_bundles").resolve()


def _write_bytes_file(path: Path, data: bytes) -> None:
    target = path.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _resolve_context_bundle_dir(*, source_label: str, output_dir: Path | None) -> Path:
    if output_dir is not None:
        path = output_dir.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    _context_bundle_root().mkdir(parents=True, exist_ok=True)
    slug = _slugify_context_label(source_label)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _context_bundle_root() / f"{slug}-{stamp}"


def _context_patch_root() -> Path:
    return (Path.cwd() / ".workspace_ail" / "context_patches").resolve()


def _resolve_context_patch_dir(*, source_label: str, output_dir: Path | None) -> Path:
    if output_dir is not None:
        path = output_dir.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    _context_patch_root().mkdir(parents=True, exist_ok=True)
    slug = _slugify_context_label(source_label)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _context_patch_root() / f"{slug}-{stamp}"


def _slugify_context_label(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", (value or "context").strip().lower()).strip("-")
    return slug[:48] or "context"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
