from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import re
import shutil
import zlib
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

MANIFEST_VERSION = "mcp_context_bundle.v1"
SKELETON_LANGUAGE = "MCP-SKL.v1"
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache"}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".html", ".json", ".yaml", ".yml", ".toml", ".sh", ".bash", ".zsh", ".rb", ".php",
    ".swift", ".kt", ".sql", ".mdx",
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".scss", ".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".go", ".rs", ".java", ".sql",
}
STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "have", "will", "more", "than",
    "what", "when", "where", "which", "their", "them", "they", "about", "would", "could", "should",
    "write", "make", "build", "using", "into", "onto", "while", "include", "包含", "一个", "我们", "你们",
    "以及", "可以", "这个", "那个", "需要", "进行", "通过", "作为", "用于", "项目", "内容",
}
TOKENIZER_BACKENDS = {"auto", "heuristic", "tiktoken"}
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
) -> dict[str, Any]:
    preset = resolve_context_preset(preset_id)
    source = _resolve_context_input_source(
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
        command_label="context compress",
    )

    skeleton_text = _render_skeleton_text(source, preset=preset)
    restore_blob = _encode_restore_blob(source["restore_blob"])
    metrics = _build_context_metrics(
        source["source_summary"],
        skeleton_text=skeleton_text,
        source_token_text=_build_token_source_text_from_source(source),
        tokenizer_backend=tokenizer_backend,
        tokenizer_model=tokenizer_model,
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
        "compression_mode": source["compression_mode"],
        "source_kind": source["source_kind"],
        "source_label": source["source_label"],
        "source_path": source.get("source_path", ""),
        "source_summary": source["source_summary"],
        "skeleton_text": skeleton_text,
        "skeleton_char_count": len(skeleton_text),
        "restore_package": restore_blob,
        "compression_ratio": metrics["char_reduction_ratio"],
        "metrics": metrics,
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
) -> dict[str, Any]:
    compression_payload = build_context_compress_payload(
        inline_text=inline_text,
        text_file=text_file,
        input_file=input_file,
        input_dir=input_dir,
        preset_id=preset_id,
        output_dir=None,
        tokenizer_backend=tokenizer_backend,
        tokenizer_model=tokenizer_model,
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
        "skeleton_language": compression_payload.get("skeleton_language", SKELETON_LANGUAGE),
        "compression_mode": compression_payload.get("compression_mode", ""),
        "source_kind": compression_payload.get("source_kind", ""),
        "source_label": compression_payload.get("source_label", ""),
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
    candidate = _resolve_context_input_source(
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
    policy_mode: str | None = None,
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
    policy = _resolve_patch_apply_policy(
        policy_mode=policy_mode,
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
        text = snapshot_path.read_text(encoding="utf-8")
        _write_text(target_path, text)
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": "text_snapshot_replay",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "applied_paths": [str(target_path.resolve())],
            "removed_paths_applied": [],
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [f"open {target_path.resolve()}"],
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
        _write_bytes_file(target_path, snapshot_path.read_bytes())
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": "file_snapshot_replay",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "applied_paths": [str(target_path.resolve())],
            "removed_paths_applied": [],
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [f"open {target_path.resolve()}"],
        }
        payload["summary_text"] = _build_context_patch_apply_summary_text(payload)
        return payload

    if patch_mode == "directory_structural_patch":
        if output_dir is None:
            raise ValueError("context patch-apply requires --output-dir when replaying a directory patch")
        if source_package_payload is None:
            raise ValueError("context patch-apply requires --source-package-file for directory patch replay")
        _restore_summary, _ = restore_context_from_package(source_package_payload, output_dir=output_dir)
        applied_root = Path(str((_restore_summary.get("restored_paths") or [""])[0])).expanduser().resolve()
        snapshot_root = Path(str(files.get("candidate_snapshot_root") or "")).expanduser()
        if snapshot_root.exists():
            for item in sorted(snapshot_root.rglob("*")):
                if item.is_dir():
                    continue
                rel_path = item.relative_to(snapshot_root)
                _write_bytes_file(applied_root / rel_path, item.read_bytes())
        removed_paths = [str(item) for item in (patch_payload.get("removed_paths") or []) if str(item).strip()]
        removed_applied: list[str] = []
        for rel_path in removed_paths:
            target = applied_root / rel_path
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                removed_applied.append(str(target))
        payload = {
            "status": status,
            "entrypoint": "context-patch-apply",
            "apply_mode": "directory_restore_plus_overlay",
            "patch_mode": patch_mode,
            "source_label": source_label,
            "applied_paths": [str(applied_root)],
            "removed_paths_applied": removed_applied,
            "policy_mode": policy_review["policy_mode"],
            "policy_passed": True,
            "policy_findings": [],
            "policy_affected_paths": policy_review["affected_paths"],
            "policy": policy_review["policy_payload"],
            "next_steps": [f"open {applied_root}"],
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
    candidate = _resolve_context_input_source(
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
        payload["summary_text"] = _build_context_apply_check_summary_text(payload)
        return payload

    if original_mode == "text":
        review = _build_text_apply_check(original_summary, candidate_summary)
    elif original_mode == "file":
        review = _build_file_apply_check(original_summary, candidate_summary)
    elif original_mode == "directory":
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
            source_token_text=_build_token_source_text_from_restore_blob(decoded),
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
        "compression_mode": package_payload.get("compression_mode", restore_mode),
        "source_kind": package_payload.get("source_kind", decoded.get("source_kind", "")),
        "source_label": package_payload.get("source_label", decoded.get("source_label", "")),
        "source_path": package_payload.get("source_path", ""),
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
    text = path.read_text(encoding="utf-8")
    summary = _text_summary(text, label=path.name)
    return {
        "compression_mode": "text",
        "source_kind": summary["source_kind"],
        "source_label": path.name,
        "source_path": str(path.resolve()),
        "source_summary": summary,
        "restore_blob": {
            "mode": "text",
            "source_label": path.name,
            "source_kind": summary["source_kind"],
            "text": text,
        },
    }


def _build_file_source(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    data = path.read_bytes()
    is_text = _looks_like_text(path, data)
    if is_text:
        text = data.decode("utf-8")
        source_kind = "code" if _is_code_path(path) else "text"
        summary = _code_summary(text, path.name) if source_kind == "code" else _text_summary(text, label=path.name)
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


def _build_directory_source(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    files: list[dict[str, Any]] = []
    symlinks: list[dict[str, Any]] = []
    empty_dirs: list[str] = []
    text_files = 0
    code_files = 0
    binary_files = 0
    total_bytes = 0
    total_chars = 0
    skeleton_entries: list[dict[str, Any]] = []

    for current_root, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        current_path = Path(current_root)
        rel_dir = "." if current_path == path else current_path.relative_to(path).as_posix()
        if not filenames and not dirnames and rel_dir != ".":
            empty_dirs.append(rel_dir)
        for filename in sorted(filenames):
            item_path = current_path / filename
            rel_path = item_path.relative_to(path).as_posix()
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
            is_text = _looks_like_text(item_path, data)
            if is_text:
                text = data.decode("utf-8")
                total_chars += len(text)
                if _is_code_path(item_path):
                    code_files += 1
                    summary = _code_summary(text, rel_path)
                    kind = "code"
                else:
                    text_files += 1
                    summary = _text_summary(text, label=rel_path)
                    kind = "text"
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
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "tree": [entry["relative_path"] for entry in sorted(skeleton_entries, key=lambda item: item["relative_path"])],
        "entries": sorted(skeleton_entries, key=lambda item: item["relative_path"]),
    }
    return {
        "compression_mode": "directory",
        "source_kind": "mixed_project",
        "source_label": path.name,
        "source_path": str(path),
        "source_summary": source_summary,
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
        f"compression_mode: {payload.get('compression_mode', '')}",
        f"source_kind: {payload.get('source_kind', '')}",
        f"source_label: {payload.get('source_label', '')}",
        f"bundle_root: {payload.get('bundle_root', '')}",
        f"zip_enabled: {payload.get('zip_enabled', False)}",
        f"apply_check_included: {payload.get('apply_check_included', False)}",
        f"file_count: {payload.get('file_count', 0)}",
    ]
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
        f"policy_mode: {payload.get('policy_mode', '')}",
        f"policy_passed: {payload.get('policy_passed', True)}",
        f"applied_path_count: {len(payload.get('applied_paths') or [])}",
        f"removed_path_count: {len(payload.get('removed_paths_applied') or [])}",
    ]
    applied_paths = payload.get("applied_paths") or []
    if applied_paths:
        lines.append(f"first_applied_path: {applied_paths[0]}")
    removed_paths = payload.get("removed_paths_applied") or []
    if removed_paths:
        lines.append(f"first_removed_path: {removed_paths[0]}")
    policy_findings = payload.get("policy_findings") or []
    if policy_findings:
        lines.append(f"policy_finding_count: {len(policy_findings)}")
        lines.append(f"first_policy_finding: {policy_findings[0]}")
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


def _render_skeleton_text(source: dict[str, Any], *, preset: dict[str, Any]) -> str:
    lines = [
        SKELETON_LANGUAGE,
        f"PRESET: {preset['preset_id']}",
        f"PRESET_LABEL: {preset['label']}",
        f"MODE: {source['compression_mode']}",
        f"SOURCE_KIND: {source['source_kind']}",
        f"SOURCE_LABEL: {source['source_label']}",
    ]
    if source.get("source_path"):
        lines.append(f"SOURCE_PATH: {source['source_path']}")
    lines.append("PRESET_FOCUS:")
    lines.extend([f"  - {item}" for item in preset["focus"]])
    lines.append("CORE:")
    lines.extend(_render_core_summary_lines(source["source_summary"], indent="  "))
    lines.append("SKELETON:")
    lines.extend(_render_structural_lines(source["source_summary"], indent="  "))
    return "\n".join(lines).rstrip() + "\n"


def _resolve_context_input_source(
    *,
    inline_text: str | None,
    text_file: Path | None,
    input_file: Path | None,
    input_dir: Path | None,
    command_label: str,
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
        return _build_directory_source(input_dir)
    raise ValueError(f"{command_label} did not receive a usable input source")


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
    }


def _render_core_summary_lines(summary: dict[str, Any], *, indent: str) -> list[str]:
    lines = []
    for key in [
        "label", "root_path", "source_kind", "total_files", "text_files", "code_files", "binary_files", "symlink_count",
        "empty_dir_count", "bytes", "total_bytes", "lines", "paragraph_count", "bullet_count", "heading_count", "total_chars", "sha256",
    ]:
        if key in summary and summary[key] not in (None, "", [], {}):
            lines.append(f"{indent}- {key}: {summary[key]}")
    if summary.get("top_terms"):
        lines.append(f"{indent}- top_terms: {', '.join(summary['top_terms'])}")
    return lines


def _render_structural_lines(summary: dict[str, Any], *, indent: str) -> list[str]:
    source_kind = str(summary.get("source_kind") or "")
    if source_kind == "code":
        lines = []
        if summary.get("imports"):
            lines.append(f"{indent}IMPORTS:")
            lines.extend([f"{indent}  - {item}" for item in summary["imports"]])
        if summary.get("symbols"):
            lines.append(f"{indent}SYMBOLS:")
            lines.extend([f"{indent}  - {item}" for item in summary["symbols"]])
        if summary.get("relationships"):
            lines.append(f"{indent}RELATIONSHIPS:")
            lines.extend([f"{indent}  - {item}" for item in summary["relationships"]])
        return lines or [f"{indent}- no structural code markers were extracted"]
    if source_kind in {"text", "markdown"}:
        lines = []
        if summary.get("headings"):
            lines.append(f"{indent}HEADINGS:")
            lines.extend([f"{indent}  - {item}" for item in summary["headings"]])
        if summary.get("sections"):
            lines.append(f"{indent}SECTIONS:")
            lines.extend([f"{indent}  - {item}" for item in summary["sections"]])
        return lines or [f"{indent}- no section markers were extracted"]
    if source_kind == "directory":
        lines = [f"{indent}TREE:"]
        lines.extend([f"{indent}  - {item}" for item in summary.get("tree", [])])
        entry_blocks = []
        for entry in summary.get("entries", []):
            entry_blocks.append(f"{indent}FILE[{entry['kind']}]: {entry['relative_path']}")
            entry_blocks.extend(_render_core_summary_lines(entry.get("summary") or {}, indent=f"{indent}  "))
            if entry.get("kind") in {"code", "text"}:
                entry_blocks.extend(_render_structural_lines(entry.get("summary") or {}, indent=f"{indent}  "))
        return lines + entry_blocks
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
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
        elif re.fullmatch(r"[A-Z][A-Z0-9 \-_/]{4,}", stripped):
            headings.append(stripped)
    sections = []
    for idx, paragraph in enumerate(paragraphs[:10], start=1):
        first_sentence = _first_sentence(paragraph)
        sections.append(f"section[{idx}] paragraphs=1 first_sentence={json.dumps(first_sentence, ensure_ascii=False)}")
    source_kind = "markdown" if label.lower().endswith((".md", ".mdx", ".rst")) or any(line.strip().startswith("#") for line in lines) else "text"
    return {
        "source_kind": source_kind,
        "label": label,
        "lines": len(lines),
        "paragraph_count": len(paragraphs),
        "bullet_count": sum(1 for line in lines if line.strip().startswith(("- ", "* ", "+ "))),
        "heading_count": len(headings),
        "headings": headings[:24],
        "sections": sections,
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


def _looks_like_text(path: Path, data: bytes) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    if b"\x00" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


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
    source_token_text: str,
    tokenizer_backend: str | None = None,
    tokenizer_model: str | None = None,
) -> dict[str, Any]:
    source_char_count = _int_metric(
        source_summary.get("total_chars"),
        fallback=source_summary.get("bytes") or source_summary.get("total_bytes") or 0,
    )
    skeleton_char_count = len(skeleton_text)
    heuristic_token_count_source = _estimate_token_count(source_char_count)
    heuristic_token_count_skeleton = _estimate_token_count(skeleton_char_count)
    heuristic_metrics = _build_token_delta_metrics(heuristic_token_count_source, heuristic_token_count_skeleton)
    primary_metrics = _resolve_primary_token_metrics(
        source_text=source_token_text,
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
    source_text: str,
    skeleton_text: str,
    heuristic_source_tokens: int,
    heuristic_skeleton_tokens: int,
    tokenizer_backend: str | None,
    tokenizer_model: str | None,
) -> dict[str, Any]:
    requested_backend = _normalize_tokenizer_backend(tokenizer_backend)
    tokenizer_metrics = _compute_tiktoken_metrics(
        source_text=source_text,
        skeleton_text=skeleton_text,
        tokenizer_model=tokenizer_model,
    )
    if requested_backend != "heuristic" and tokenizer_metrics.get("available") and tokenizer_metrics.get("token_count_source") is not None:
        primary = _build_token_delta_metrics(
            int(tokenizer_metrics["token_count_source"]),
            int(tokenizer_metrics["token_count_skeleton"]),
        )
        return {
            **primary,
            "token_backend": "tiktoken",
            "token_basis": str(tokenizer_metrics.get("token_basis") or ""),
            "token_model": str(tokenizer_metrics.get("token_model") or ""),
            "requested_backend": requested_backend,
            "fallback_used": False,
            "tokenizer_available": True,
            "tokenizer_error": "",
            "tokenizer_token_count_source": primary["token_count_source"],
            "tokenizer_token_count_skeleton": primary["token_count_skeleton"],
            "tokenizer_tokens_saved": primary["tokens_saved"],
            "tokenizer_token_delta_from_source": primary["token_delta_from_source"],
            "tokenizer_token_reduction_ratio": primary["token_ratio"],
            "tokenizer_token_direction": primary["token_direction"],
            "tokenizer_token_basis": str(tokenizer_metrics.get("token_basis") or ""),
        }
    heuristic = _build_token_delta_metrics(heuristic_source_tokens, heuristic_skeleton_tokens)
    return {
        **heuristic,
        "token_backend": "heuristic",
        "token_basis": "heuristic_chars_div_4",
        "token_model": "",
        "requested_backend": requested_backend,
        "fallback_used": requested_backend != "heuristic",
        "tokenizer_available": bool(tokenizer_metrics.get("available")),
        "tokenizer_error": str(tokenizer_metrics.get("error") or ""),
        "tokenizer_token_count_source": tokenizer_metrics.get("token_count_source"),
        "tokenizer_token_count_skeleton": tokenizer_metrics.get("token_count_skeleton"),
        "tokenizer_tokens_saved": tokenizer_metrics.get("tokens_saved"),
        "tokenizer_token_delta_from_source": tokenizer_metrics.get("token_delta_from_source"),
        "tokenizer_token_reduction_ratio": tokenizer_metrics.get("token_ratio"),
        "tokenizer_token_direction": tokenizer_metrics.get("token_direction"),
        "tokenizer_token_basis": str(tokenizer_metrics.get("token_basis") or ""),
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
        if raw_bytes and _looks_like_text(Path(file_name), raw_bytes):
            try:
                return raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return ""
        return ""
    if mode == "directory":
        parts: list[str] = []
        for item in sorted(restore_blob.get("files") or [], key=lambda entry: str(entry.get("relative_path") or "")):
            rel_path = str(item.get("relative_path") or "")
            raw_bytes = _decode_restore_content_b64(item.get("content_b64"))
            if raw_bytes and _looks_like_text(Path(rel_path), raw_bytes):
                try:
                    parts.append(raw_bytes.decode("utf-8"))
                except UnicodeDecodeError:
                    continue
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
    policy_file: Path | None,
    allow_roots: list[str] | None,
    forbid_roots: list[str] | None,
    block_removals: bool,
    block_additions: bool,
    require_apply_check_passed: bool,
    max_changed_paths: int | None,
) -> dict[str, Any]:
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
        "policy_mode": str(policy.get("policy_mode") or "open"),
        "policy_template": policy,
        "summary_text": json.dumps(policy, ensure_ascii=False, indent=2),
        "next_steps": [
            "save this JSON as a reusable context patch-apply policy file",
            "pass it back through --policy-file when replaying one patch bundle",
        ],
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


def _restore_file_blob(target_path: Path, decoded: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(str(decoded.get("content_b64") or "").encode("ascii"))
    target_path.write_bytes(data)


def _restore_directory_blob(restore_root: Path, decoded: dict[str, Any]) -> None:
    restore_root.mkdir(parents=True, exist_ok=True)
    for rel_dir in decoded.get("empty_dirs") or []:
        (restore_root / rel_dir).mkdir(parents=True, exist_ok=True)
    for item in decoded.get("files") or []:
        target_path = restore_root / str(item.get("relative_path") or "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(base64.b64decode(str(item.get("content_b64") or "").encode("ascii")))
    for item in decoded.get("symlinks") or []:
        target_path = restore_root / str(item.get("relative_path") or "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.symlink_to(str(item.get("link_target") or ""))


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
    if mode == "directory":
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
    _write_text_file(files["candidate_snapshot_file"], candidate_text)
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

    is_text = _looks_like_text(Path(file_name), original_bytes) and _looks_like_text(Path(file_name), candidate_bytes)
    files: dict[str, Path] = {"candidate_snapshot_file": snapshot_file}
    added_lines = 0
    removed_lines = 0
    patch_mode = "file_binary_replace"
    if is_text:
        original_text = original_bytes.decode("utf-8")
        candidate_text = candidate_bytes.decode("utf-8")
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
    original_files = {str(item.get("relative_path") or ""): base64.b64decode(str(item.get("content_b64") or "").encode("ascii")) for item in (original_decoded.get("files") or [])}
    candidate_files = {str(item.get("relative_path") or ""): base64.b64decode(str(item.get("content_b64") or "").encode("ascii")) for item in (candidate_restore.get("files") or [])}
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
        _write_bytes_file(candidate_snapshot_root / rel_path, data)

    for rel_path in sorted(set(added_paths + changed_paths)):
        _write_candidate_snapshot(rel_path, candidate_files[rel_path])

    for rel_path in sorted(set(added_paths + removed_paths + changed_paths)):
        original_bytes = original_files.get(rel_path)
        candidate_bytes = candidate_files.get(rel_path)
        original_is_text = original_bytes is not None and _looks_like_text(Path(rel_path), original_bytes)
        candidate_is_text = candidate_bytes is not None and _looks_like_text(Path(rel_path), candidate_bytes)
        if original_is_text or candidate_is_text:
            original_text = original_bytes.decode("utf-8") if original_is_text and original_bytes is not None else ""
            candidate_text = candidate_bytes.decode("utf-8") if candidate_is_text and candidate_bytes is not None else ""
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
            patch_file = patches_root / f"{rel_path}.diff"
            _write_text_file(patch_file, diff_text)
            text_patch_files += 1
            added_lines, removed_lines = _diff_line_counts(diff_lines)
            added_lines_total += added_lines
            removed_lines_total += removed_lines
            if len(preview_chunks) < 5:
                preview_chunks.append(diff_text.rstrip())
        else:
            note_file = binary_notes_root / f"{rel_path}.txt"
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
