from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from .context_compression import (
    CONTEXT_FOCUS_MODES,
    CONTEXT_PRESETS,
    apply_context_patch_payload,
    build_context_apply_check_payload,
    build_context_bundle_payload,
    build_context_compress_payload,
    build_context_patch_dry_run_report_payload,
    build_context_patch_merge_report_payload,
    build_context_patch_payload,
    build_context_patch_policy_template_payload,
    build_context_preset_payload,
    inspect_context_package,
    load_context_package,
    restore_context_from_package,
    resolve_context_preset,
    SKELETON_DENSITY_MODES,
)

EXIT_OK = 0
EXIT_GENERAL_ERROR = 1
EXIT_USAGE = 2
EXIT_VALIDATION = 3

CONTEXT_CONFIG_KEYS = [
    "preset",
    "preset_id",
    "focus_mode",
    "skeleton_density",
    "density",
    "exclude",
    "excludes",
    "exclude_patterns",
]
CONTEXT_CONFIG_TEMPLATE = {
    "preset": "codebase",
    "focus_mode": "imports",
    "skeleton_density": "adaptive",
    "exclude": ["node_modules/", "dist/", "build/", "*.map"],
}
CONTEXT_CONFIG_FILENAMES = [".mcp-skeleton.json", ".mcp-skeleton.yaml", ".mcp-skeleton.yml"]


def _print_json_payload(payload: Any, *, file: Any = sys.stdout) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False), file=file)


def _print_json_error(
    code: str,
    message: str,
    *,
    exit_code: int,
    details: dict[str, Any] | None = None,
) -> None:
    error = {"code": code, "message": message, "exit_code": exit_code}
    if details:
        error["details"] = details
    _print_json_payload({"status": "error", "error": error})


def _json_enabled(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def _emit_command_error(args: argparse.Namespace, exit_code: int, code: str, message: str) -> int:
    if _json_enabled(args):
        _print_json_error(code, message, exit_code=exit_code)
    else:
        print(f"error: {message}", file=sys.stderr)
    return exit_code


def _write_cli_output_file(path: Path, payload: str | dict[str, Any], *, as_json: bool = False) -> None:
    path = path.expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")


def _strip_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index].rstrip()
    return line.rstrip()


def _parse_yaml_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_simple_yaml_config(text: str, *, path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_map = root
    active_list_key: str | None = None
    in_context = False
    for raw_line in text.splitlines():
        line = _strip_yaml_comment(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if stripped.startswith("- "):
            if active_list_key is None:
                raise ValueError(f"invalid YAML config list item in {path}: {raw_line.strip()}")
            current = current_map.setdefault(active_list_key, [])
            if not isinstance(current, list):
                raise ValueError(f"config field '{active_list_key}' must not mix scalar and list values")
            current.append(_parse_yaml_scalar(stripped[2:]))
            continue
        if ":" not in stripped:
            raise ValueError(f"invalid YAML config line in {path}: {raw_line.strip()}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid YAML config key in {path}: {raw_line.strip()}")
        if indent == 0 and key != "context":
            current_map = root
            in_context = False
        if key == "context" and indent == 0 and not raw_value.strip():
            context_payload = root.setdefault("context", {})
            if not isinstance(context_payload, dict):
                raise ValueError(f"config field 'context' must be an object: {path}")
            current_map = context_payload
            in_context = True
            active_list_key = None
            continue
        if indent > 0 and not in_context:
            raise ValueError(f"nested YAML config is only supported under 'context': {path}")
        value = raw_value.strip()
        if value:
            current_map[key] = _parse_yaml_scalar(value)
            active_list_key = None
        else:
            current_map[key] = []
            active_list_key = key
    return root


def _load_config_payload(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON config file {path}: {exc}") from exc
    elif suffix in {".yaml", ".yml"}:
        payload = _parse_simple_yaml_config(text, path=path)
    else:
        raise ValueError(f"unsupported config file extension for {path}; use .json, .yaml, or .yml")
    if not isinstance(payload, dict):
        raise ValueError(f"config file must contain an object: {path}")
    return payload


def _load_context_config(args: argparse.Namespace) -> tuple[Path | None, dict[str, Any]]:
    explicit = _opt_path(args, "config_file")
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    else:
        for attr in ["input_dir", "input_file", "text_file"]:
            path = _opt_path(args, attr)
            if path is None:
                continue
            config_dir = path if path.is_dir() else path.parent
            candidates.extend(config_dir / filename for filename in CONTEXT_CONFIG_FILENAMES)
            break
        candidates.extend(Path.cwd() / filename for filename in CONTEXT_CONFIG_FILENAMES)

    for path in candidates:
        if not path.exists():
            if explicit is not None:
                raise FileNotFoundError(str(path))
            continue
        payload = _load_config_payload(path)
        context_payload = payload.get("context", payload)
        if not isinstance(context_payload, dict):
            raise ValueError(f"config field 'context' must be an object: {path}")
        return path, context_payload
    return None, {}


def _config_string(config: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = config.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"config field '{key}' must be a string")
        stripped = value.strip()
        return stripped or None
    return None


def _config_list(config: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = config.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return [value]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return list(value)
        raise ValueError(f"config field '{key}' must be a string or list of strings")
    return []


def _normalize_config_choice(value: str | None, *, field: str, supported: set[str]) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in supported:
        supported_text = ", ".join(sorted(supported))
        raise ValueError(f"config field '{field}' must be one of: {supported_text}")
    return normalized


def _resolve_context_defaults(args: argparse.Namespace) -> tuple[Path | None, dict[str, Any], dict[str, Any]]:
    config_file, config = _load_context_config(args)
    cli_excludes = list(getattr(args, "exclude_patterns", None) or [])
    config_excludes = _config_list(config, "exclude", "excludes", "exclude_patterns")
    preset_id = getattr(args, "preset_id", None) or _config_string(config, "preset", "preset_id")
    if preset_id is not None:
        preset_id = resolve_context_preset(preset_id)["preset_id"]
    focus_mode = getattr(args, "focus_mode", None) or _config_string(config, "focus_mode")
    focus_mode = _normalize_config_choice(focus_mode, field="focus_mode", supported=CONTEXT_FOCUS_MODES)
    skeleton_density = getattr(args, "skeleton_density", None) or _config_string(config, "skeleton_density", "density")
    skeleton_density = _normalize_config_choice(skeleton_density, field="skeleton_density", supported=SKELETON_DENSITY_MODES)
    values = {
        "preset_id": preset_id,
        "focus_mode": focus_mode,
        "skeleton_density": skeleton_density,
        "exclude_patterns": [*config_excludes, *cli_excludes],
    }
    config_values = {
        key: config[key]
        for key in CONTEXT_CONFIG_KEYS
        if key in config
    }
    return config_file, config_values, values


def _write_context_config_file(output_file: Path | None, config: dict[str, Any], *, force: bool) -> tuple[str, bool]:
    if output_file is None:
        return "", False
    target = output_file.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if target.exists() and not force:
        raise ValueError(f"config file already exists; use --force to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() in {".yaml", ".yml"}:
        target.write_text(_render_context_config_yaml(config), encoding="utf-8")
    else:
        target.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target), True


def _render_context_config_yaml(config: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in config.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def _write_text_report_file(output_file: Path | None, report_text: str, *, force: bool) -> tuple[str, bool]:
    if output_file is None:
        return "", False
    target = output_file.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if target.exists() and not force:
        raise ValueError(f"report file already exists; use --force to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report_text, encoding="utf-8")
    return str(target), True


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compare_doctor_restore(package_payload: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    mode = str(package_payload.get("compression_mode") or "")
    source_path_text = str(package_payload.get("source_path") or "")
    source_path = Path(source_path_text) if source_path_text else None
    source_summary = package_payload.get("source_summary") or {}
    if mode == "text" and source_path is not None:
        restore_summary, emitted_text = restore_context_from_package(
            package_payload,
            output_file=output_dir / source_path.name,
        )
    else:
        restore_summary, emitted_text = restore_context_from_package(package_payload, output_dir=output_dir)
    missing: list[str] = []
    mismatched: list[str] = []
    checked = 0

    if mode == "text" and source_path is None:
        expected_hash = str(source_summary.get("sha256") or "")
        checked = 1
        restored_hash = hashlib.sha256(str(emitted_text or "").encode("utf-8")).hexdigest()
        if expected_hash and restored_hash != expected_hash:
            mismatched.append("inline-text")
    elif mode in {"text", "file"} and source_path is not None:
        restored_paths = [Path(item) for item in restore_summary.get("restored_paths") or []]
        restored_path = restored_paths[0] if restored_paths else None
        checked = 1
        if restored_path is None or not restored_path.exists():
            missing.append(source_path.name)
        elif _sha256_path(source_path) != _sha256_path(restored_path):
            mismatched.append(source_path.name)
    elif mode in {"directory", "directory_incremental"} and source_path is not None:
        restored_paths = [Path(item) for item in restore_summary.get("restored_paths") or []]
        restored_root = restored_paths[0] if restored_paths else None
        entries = list(source_summary.get("entries") or [])
        checked = len(entries)
        for entry in entries:
            rel_path = str(entry.get("relative_path") or "")
            if not rel_path:
                continue
            expected_hash = str((entry.get("summary") or {}).get("sha256") or "")
            restored_path = restored_root / rel_path if restored_root is not None else None
            if restored_path is None or not restored_path.exists():
                missing.append(rel_path)
                continue
            if expected_hash and _sha256_path(restored_path) != expected_hash:
                mismatched.append(rel_path)
    else:
        return {
            "status": "skipped",
            "message": f"restore comparison is not available for compression_mode={mode}",
            "checked_count": checked,
            "missing_count": 0,
            "mismatched_count": 0,
            "restore_summary": restore_summary,
        }

    status = "ok" if not missing and not mismatched else "error"
    return {
        "status": status,
        "checked_count": checked,
        "missing_count": len(missing),
        "mismatched_count": len(mismatched),
        "missing_paths": missing[:40],
        "mismatched_paths": mismatched[:40],
        "restore_summary": restore_summary,
    }


def _build_context_doctor_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    config_file, config_values, context_defaults = _resolve_context_defaults(args)
    compression_payload = build_context_compress_payload(
        inline_text=_inline_text(args),
        text_file=_opt_path(args, "text_file"),
        input_file=_opt_path(args, "input_file"),
        input_dir=_opt_path(args, "input_dir"),
        preset_id=context_defaults["preset_id"],
        tokenizer_backend=getattr(args, "tokenizer_backend", None),
        tokenizer_model=getattr(args, "tokenizer_model", None),
        incremental=bool(getattr(args, "incremental", False)),
        base_commit=getattr(args, "base_commit", None),
        focus_mode=context_defaults["focus_mode"],
        skeleton_density=context_defaults["skeleton_density"],
        exclude_patterns=context_defaults["exclude_patterns"],
        config_file=config_file,
        config_values=config_values,
    )
    with tempfile.TemporaryDirectory(prefix="mcp_skeleton_doctor.") as tmp:
        restore_check = _compare_doctor_restore(compression_payload, output_dir=Path(tmp))

    warnings = list(compression_payload.get("compression_warnings") or [])
    recommendations = list(compression_payload.get("compression_recommendations") or [])
    source_scale_profile = compression_payload.get("source_scale_profile") or {}
    blocking_checks = [
        {
            "name": "config_loaded_or_defaults_resolved",
            "passed": True,
            "severity": "block",
            "observed": str(config_file.resolve()) if config_file is not None else "defaults",
        },
        {
            "name": "compress_payload_ok",
            "passed": compression_payload.get("status") == "ok",
            "severity": "block",
            "observed": compression_payload.get("status"),
        },
        {
            "name": "restore_roundtrip_ok",
            "passed": restore_check.get("status") == "ok",
            "severity": "block",
            "observed": f"missing={restore_check.get('missing_count', 0)}, mismatched={restore_check.get('mismatched_count', 0)}",
        },
    ]
    watch_checks = [
        {
            "name": "no_compression_warnings",
            "passed": not warnings,
            "severity": "watch",
            "observed": len(warnings),
        },
        {
            "name": "recommended_command_available",
            "passed": bool(compression_payload.get("recommended_command_args")),
            "severity": "watch",
            "observed": len(compression_payload.get("recommended_command_args") or []),
        },
    ]
    failed_blocks = [item for item in blocking_checks if not item["passed"]]
    failed_watches = [item for item in watch_checks if not item["passed"]]
    readiness = "blocked" if failed_blocks else "watch" if failed_watches or warnings else "ready"
    payload = {
        "status": "ok" if not failed_blocks else "error",
        "entrypoint": "context-doctor",
        "readiness_status": readiness,
        "config_file": str(config_file.resolve()) if config_file is not None else "",
        "config_values": config_values,
        "compression_mode": compression_payload.get("compression_mode", ""),
        "source_kind": compression_payload.get("source_kind", ""),
        "source_label": compression_payload.get("source_label", ""),
        "source_path": compression_payload.get("source_path", ""),
        "source_scale_profile": source_scale_profile,
        "skeleton_char_count": compression_payload.get("skeleton_char_count", 0),
        "metrics": compression_payload.get("metrics") or {},
        "compression_warnings": warnings,
        "compression_recommendations": recommendations,
        "compression_explanations": compression_payload.get("compression_explanations") or [],
        "recommended_config": compression_payload.get("recommended_config") or {},
        "recommended_command_args": compression_payload.get("recommended_command_args") or [],
        "restore_check": restore_check,
        "checks": blocking_checks + watch_checks,
        "next_steps": [
            "if readiness_status is ready, this source is safe to use with MCP-Skeleton compression/restore",
            "if readiness_status is watch, review compression_warnings and recommended_command_args before long-running work",
            "if readiness_status is blocked, fix restore/config errors before relying on this bundle",
        ],
    }
    return payload, EXIT_OK if not failed_blocks else EXIT_VALIDATION


def _render_context_config_recommend_report(payload: dict[str, Any]) -> str:
    config = payload.get("config") or {}
    analysis = payload.get("analysis") or {}
    comparison = payload.get("comparison") or {}
    recommended_command_args = list(payload.get("recommended_command_args") or [])
    warnings = list(analysis.get("compression_warnings") or [])
    recommendations = list(analysis.get("compression_recommendations") or [])
    exclude_patterns = list(config.get("exclude") or [])
    lines = [
        "# MCP-Skeleton Config Recommendation",
        "",
        "## Source",
        f"- source_kind: {analysis.get('source_kind', '')}",
        f"- source_label: {analysis.get('source_label', '')}",
        f"- source_scale_class: {(analysis.get('source_scale_profile') or {}).get('scale_class', '')}",
        f"- source_total_files: {(analysis.get('source_scale_profile') or {}).get('total_files', '')}",
        f"- source_total_chars: {(analysis.get('source_scale_profile') or {}).get('total_chars', '')}",
        f"- current_preset: {analysis.get('preset_id', '')}",
        f"- current_focus_mode: {analysis.get('focus_mode', '')}",
        f"- current_skeleton_density: {analysis.get('skeleton_density', '')}",
        "",
        "## Recommended Config",
        f"- preset: {config.get('preset', '')}",
        f"- focus_mode: {config.get('focus_mode', '')}",
        f"- skeleton_density: {config.get('skeleton_density', '')}",
        f"- exclude_count: {len(exclude_patterns)}",
    ]
    if exclude_patterns:
        lines.append("- exclude:")
        lines.extend(f"  - {pattern}" for pattern in exclude_patterns)
    lines.extend(
        [
            "",
            "## Token Estimate",
            f"- estimated_token_reduction_ratio: {analysis.get('estimated_token_reduction_ratio', '')}",
            f"- estimated_token_direction: {analysis.get('estimated_token_direction', '')}",
            f"- estimated_tokens_saved: {analysis.get('estimated_tokens_saved', '')}",
            "",
            "## Recommendation Estimate",
            f"- current_token_ratio: {comparison.get('current_token_ratio', '')}",
            f"- recommended_token_ratio: {comparison.get('recommended_token_ratio', '')}",
            f"- estimated_token_ratio_delta: {comparison.get('estimated_token_ratio_delta', '')}",
            f"- recommended_skeleton_char_count: {comparison.get('recommended_skeleton_char_count', '')}",
            "",
            "## Recommended Command Args",
            json.dumps(recommended_command_args, ensure_ascii=False),
            "",
            "## Warnings",
        ]
    )
    if warnings:
        lines.extend(f"- {item.get('code', '')}: {item.get('message', '')}" for item in warnings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    if recommendations:
        lines.extend(f"- {item.get('code', '')}: {item.get('message', '')}" for item in recommendations)
    else:
        lines.append("- current config is acceptable")
    lines.extend(
        [
            "",
            "## Next Steps",
            "1. Review the generated `.mcp-skeleton.json` before committing it.",
            "2. Run `python3 -m cli context config --validate --config .mcp-skeleton.json --json`.",
            "3. Reuse `recommended_command_args` for a direct trial compression, or run `python3 -m cli context compress --input-dir . --json` and confirm the reported config file is used.",
            "",
        ]
    )
    return "\n".join(lines)


def _build_config_recommended_command_args(args: argparse.Namespace, recommended_config: dict[str, Any]) -> list[str]:
    command_args = ["context", "compress"]
    if _inline_text(args) is not None:
        return []
    if _opt_path(args, "input_dir") is not None:
        command_args.extend(["--input-dir", str(_opt_path(args, "input_dir").resolve())])
    elif _opt_path(args, "input_file") is not None:
        command_args.extend(["--input-file", str(_opt_path(args, "input_file").resolve())])
    elif _opt_path(args, "text_file") is not None:
        command_args.extend(["--text-file", str(_opt_path(args, "text_file").resolve())])
    else:
        return []

    preset = str(recommended_config.get("preset") or "")
    focus_mode = str(recommended_config.get("focus_mode") or "")
    skeleton_density = str(recommended_config.get("skeleton_density") or "")
    if preset:
        command_args.extend(["--preset", preset])
    if focus_mode:
        command_args.extend(["--focus-mode", focus_mode])
    if skeleton_density:
        command_args.extend(["--skeleton-density", skeleton_density])
    for pattern in recommended_config.get("exclude") or []:
        pattern_text = str(pattern).strip()
        if pattern_text:
            command_args.extend(["--exclude", pattern_text])
    tokenizer_backend = str(getattr(args, "tokenizer_backend", "") or "")
    tokenizer_model = str(getattr(args, "tokenizer_model", "") or "")
    if tokenizer_backend and tokenizer_backend != "auto":
        command_args.extend(["--tokenizer-backend", tokenizer_backend])
    if tokenizer_model:
        command_args.extend(["--tokenizer-model", tokenizer_model])
    command_args.append("--json")
    return command_args


def _build_config_recommendation_comparison(
    *,
    args: argparse.Namespace,
    current_payload: dict[str, Any],
    recommended_config: dict[str, Any],
) -> dict[str, Any]:
    current_metrics = dict(current_payload.get("metrics") or {})
    current_ratio = current_metrics.get("estimated_token_reduction_ratio")
    try:
        recommended_payload = build_context_compress_payload(
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
            preset_id=str(recommended_config.get("preset") or "generic"),
            tokenizer_backend=getattr(args, "tokenizer_backend", None),
            tokenizer_model=getattr(args, "tokenizer_model", None),
            focus_mode=str(recommended_config.get("focus_mode") or "full"),
            skeleton_density=str(recommended_config.get("skeleton_density") or "adaptive"),
            exclude_patterns=list(recommended_config.get("exclude") or []),
        )
    except Exception as exc:  # noqa: BLE001 - surface recommendation audit failures without blocking config output
        return {
            "status": "warning",
            "message": f"recommended config audit failed: {exc}",
            "current_token_ratio": current_ratio,
            "recommended_token_ratio": None,
            "estimated_token_ratio_delta": None,
        }
    recommended_metrics = dict(recommended_payload.get("metrics") or {})
    recommended_ratio = recommended_metrics.get("estimated_token_reduction_ratio")
    if isinstance(current_ratio, (int, float)) and isinstance(recommended_ratio, (int, float)):
        delta = round(float(recommended_ratio) - float(current_ratio), 4)
    else:
        delta = None
    return {
        "status": "ok",
        "current_focus_mode": current_payload.get("focus_mode", ""),
        "current_skeleton_density": current_payload.get("skeleton_density", ""),
        "current_token_ratio": current_ratio,
        "current_skeleton_char_count": current_payload.get("skeleton_char_count", 0),
        "recommended_focus_mode": recommended_payload.get("focus_mode", ""),
        "recommended_skeleton_density": recommended_payload.get("skeleton_density", ""),
        "recommended_token_ratio": recommended_ratio,
        "recommended_skeleton_char_count": recommended_payload.get("skeleton_char_count", 0),
        "estimated_token_ratio_delta": delta,
        "recommended_warning_count": len(recommended_payload.get("compression_warnings") or []),
    }


def _build_context_install_hook_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    hook_name = str(getattr(args, "hook_name", None) or "pre-commit").strip()
    if hook_name != "pre-commit":
        raise ValueError("only pre-commit hook installation is supported")
    repo_root = Path.cwd().resolve()
    git_dir = repo_root / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        raise ValueError("context install-hook must be run from a git repository root")
    hook_path = git_dir / "hooks" / hook_name
    hook_body = """#!/usr/bin/env sh
set -eu

REPO_ROOT="$(git rev-parse --show-toplevel)"
PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

cd "$REPO_ROOT"

for config_file in .mcp-skeleton.json .mcp-skeleton.yaml .mcp-skeleton.yml; do
  if [ -f "$config_file" ]; then
    "$PYTHON_BIN" -m cli context config --validate --config "$config_file" --json >/dev/null
  fi
done

if [ -f cli/ail_cli.py ] && [ -f cli/context_compression.py ]; then
  "$PYTHON_BIN" -m py_compile cli/ail_cli.py cli/context_compression.py
fi
"""
    payload = {
        "status": "ok",
        "entrypoint": "context-install-hook",
        "hook": hook_name,
        "hook_path": str(hook_path),
        "installed": False,
        "dry_run": bool(getattr(args, "dry_run", False)),
        "checks": ["config_validate_if_present", "py_compile_cli_if_present"],
    }
    if payload["dry_run"]:
        payload["hook_preview"] = hook_body
        return payload, EXIT_OK
    if hook_path.exists() and not bool(getattr(args, "force", False)):
        raise ValueError(f"hook already exists; use --force to overwrite: {hook_path}")
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(hook_body, encoding="utf-8")
    hook_path.chmod(0o755)
    payload["installed"] = True
    return payload, EXIT_OK


def _build_context_config_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    supported = {
        "presets": sorted(CONTEXT_PRESETS.keys()),
        "focus_modes": sorted(CONTEXT_FOCUS_MODES),
        "skeleton_densities": sorted(SKELETON_DENSITY_MODES),
        "config_keys": list(CONTEXT_CONFIG_KEYS),
    }
    output_file = _opt_path(args, "output_file")
    force = bool(getattr(args, "force", False))
    config_action = str(getattr(args, "config_action", "") or "").strip()
    if config_action == "init" and output_file is None:
        output_file = Path(".mcp-skeleton.json")
    if bool(getattr(args, "validate", False)):
        config_file, config_values, context_defaults = _resolve_context_defaults(args)
        if config_file is None:
            raise FileNotFoundError(".mcp-skeleton.json")
        return (
            {
                "status": "ok",
                "entrypoint": "context-config",
                "mode": "validate",
                "config_file": str(config_file.resolve()),
                "config_values": config_values,
                "resolved_defaults": {
                    "preset_id": context_defaults["preset_id"] or "generic",
                    "focus_mode": context_defaults["focus_mode"] or "full",
                    "skeleton_density": context_defaults["skeleton_density"] or "adaptive",
                    "exclude_patterns": context_defaults["exclude_patterns"],
                },
                "supported": supported,
            },
            EXIT_OK,
        )

    if bool(getattr(args, "recommend", False)):
        config_file, config_values, context_defaults = _resolve_context_defaults(args)
        compression_payload = build_context_compress_payload(
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
            preset_id=context_defaults["preset_id"],
            tokenizer_backend=getattr(args, "tokenizer_backend", None),
            tokenizer_model=getattr(args, "tokenizer_model", None),
            focus_mode=context_defaults["focus_mode"],
            skeleton_density=context_defaults["skeleton_density"],
            exclude_patterns=context_defaults["exclude_patterns"],
            config_file=config_file,
            config_values=config_values,
        )
        recommended = dict(compression_payload.get("recommended_config") or {})
        metrics = dict(compression_payload.get("metrics") or {})
        suggested_excludes = list(
            context_defaults["exclude_patterns"]
            or recommended.get("exclude")
            or compression_payload.get("preset_suggested_excludes")
            or []
        )
        recommended_config = {
            "preset": recommended.get("preset_id") or compression_payload.get("preset_id") or "generic",
            "focus_mode": recommended.get("focus_mode") or compression_payload.get("focus_mode") or "full",
            "skeleton_density": recommended.get("skeleton_density") or compression_payload.get("skeleton_density") or "adaptive",
            "exclude": suggested_excludes,
        }
        comparison = _build_config_recommendation_comparison(
            args=args,
            current_payload=compression_payload,
            recommended_config=recommended_config,
        )
        recommended_command_args = _build_config_recommended_command_args(args, recommended_config)
        written_path, written = _write_context_config_file(output_file, recommended_config, force=force)
        payload = {
            "status": "ok",
            "entrypoint": "context-config",
            "mode": "recommend",
            "config_file": written_path,
            "written": written,
            "config": recommended_config,
            "analysis": {
                "source_kind": compression_payload.get("source_kind"),
                "source_label": compression_payload.get("source_label"),
                "preset_id": compression_payload.get("preset_id"),
                "focus_mode": compression_payload.get("focus_mode"),
                "skeleton_density": compression_payload.get("skeleton_density"),
                "estimated_token_reduction_ratio": metrics.get("estimated_token_reduction_ratio"),
                "estimated_tokens_saved": metrics.get("estimated_tokens_saved"),
                "estimated_token_direction": metrics.get("estimated_token_direction"),
                "source_scale_profile": compression_payload.get("source_scale_profile") or {},
                "compression_warnings": compression_payload.get("compression_warnings") or [],
                "compression_recommendations": compression_payload.get("compression_recommendations") or [],
                "recommended_config": compression_payload.get("recommended_config") or {},
            },
            "comparison": comparison,
            "recommended_command_args": recommended_command_args,
            "supported": supported,
        }
        report_text = _render_context_config_recommend_report(payload)
        report_path, report_written = _write_text_report_file(
            _opt_path(args, "output_report_file"),
            report_text,
            force=force,
        )
        payload["report_file"] = report_path
        payload["report_written"] = report_written
        return (
            payload,
            EXIT_OK,
        )

    payload = {
        "status": "ok",
        "entrypoint": "context-config",
        "mode": "template",
        "config_file": "",
        "config": dict(CONTEXT_CONFIG_TEMPLATE),
        "supported": supported,
    }
    written_path, written = _write_context_config_file(output_file, CONTEXT_CONFIG_TEMPLATE, force=force)
    payload["config_file"] = written_path
    payload["written"] = written
    return payload, EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_USAGE
    if args.command != "context":
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported top-level command: context")
    try:
        return cmd_context(args)
    except FileNotFoundError as exc:
        return _emit_command_error(args, EXIT_GENERAL_ERROR, "file_not_found", str(exc))
    except ValueError as exc:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
    except Exception as exc:  # pragma: no cover
        return _emit_command_error(args, EXIT_GENERAL_ERROR, "cli_error", str(exc))


def cmd_context(args: argparse.Namespace) -> int:
    command = getattr(args, "context_command", None)
    supported = {"compress", "restore", "inspect", "apply-check", "preset", "config", "init", "install-hook", "doctor", "bundle", "patch", "patch-apply"}
    if command not in supported:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported context subcommands: compress, restore, inspect, apply-check, preset, config, init, install-hook, doctor, bundle, patch, patch-apply")

    if command == "preset":
        payload = build_context_preset_payload(getattr(args, "preset_id", None))
        return _emit_simple_result(args, payload)

    if command == "install-hook":
        payload, exit_code = _build_context_install_hook_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("hook_preview", _render_simple_summary(payload, ["hook", "hook_path", "installed", "dry_run"]))), exit_code=exit_code)

    if command in {"config", "init"}:
        if command == "init":
            setattr(args, "config_action", "init")
        payload, exit_code = _build_context_config_payload(args)
        if _json_enabled(args):
            _print_json_payload(payload)
        else:
            print(json.dumps(payload.get("config", payload), indent=2, ensure_ascii=False))
        return exit_code

    if command == "doctor":
        payload, exit_code = _build_context_doctor_payload(args)
        return _emit_simple_result(args, payload, text=_render_simple_summary(payload, [
            "readiness_status", "compression_mode", "source_label", "skeleton_char_count"
        ]), exit_code=exit_code)

    if command == "compress":
        config_file, config_values, context_defaults = _resolve_context_defaults(args)
        payload = build_context_compress_payload(
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
            preset_id=context_defaults["preset_id"],
            output_dir=_opt_path(args, "output_dir"),
            tokenizer_backend=getattr(args, "tokenizer_backend", None),
            tokenizer_model=getattr(args, "tokenizer_model", None),
            incremental=bool(getattr(args, "incremental", False)),
            base_commit=getattr(args, "base_commit", None),
            focus_mode=context_defaults["focus_mode"],
            skeleton_density=context_defaults["skeleton_density"],
            exclude_patterns=context_defaults["exclude_patterns"],
            config_file=config_file,
            config_values=config_values,
        )
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_skeleton", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("skeleton_text", "")))
            sys.stdout.write(str(payload.get("skeleton_text", "")))
            return EXIT_OK
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")))

    if command == "bundle":
        config_file, config_values, context_defaults = _resolve_context_defaults(args)
        payload = build_context_bundle_payload(
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
            preset_id=context_defaults["preset_id"],
            output_dir=_opt_path(args, "output_dir"),
            make_zip=bool(getattr(args, "zip_bundle", False)),
            candidate_inline_text=_candidate_inline_text(args),
            candidate_text_file=_opt_path(args, "candidate_text_file"),
            candidate_input_file=_opt_path(args, "candidate_input_file"),
            candidate_input_dir=_opt_path(args, "candidate_input_dir"),
            tokenizer_backend=getattr(args, "tokenizer_backend", None),
            tokenizer_model=getattr(args, "tokenizer_model", None),
            incremental=bool(getattr(args, "incremental", False)),
            base_commit=getattr(args, "base_commit", None),
            focus_mode=context_defaults["focus_mode"],
            skeleton_density=context_defaults["skeleton_density"],
            exclude_patterns=context_defaults["exclude_patterns"],
            config_file=config_file,
            config_values=config_values,
        )
        exit_code = EXIT_OK if (payload.get("apply_check") is None or bool((payload.get("apply_check") or {}).get("apply_check_passed"))) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            return _emit_summary_text(args, payload, exit_code=exit_code)
        return _emit_simple_result(args, payload, exit_code=exit_code, text=_render_simple_summary(payload, [
            "focus_mode", "skeleton_density", "compression_mode", "source_kind", "source_label", "bundle_root", "zip_enabled", "file_count"
        ]))

    if command == "patch-apply":
        source_package_file = _opt_path(args, "source_package_file")
        output_file = _opt_path(args, "output_file")
        output_dir = _opt_path(args, "output_dir")
        policy_file = _opt_path(args, "policy_file")
        write_policy_template_path = _opt_path(args, "write_policy_template")
        write_merge_report_path = _opt_path(args, "write_merge_report")
        write_dry_run_report_path = _opt_path(args, "write_dry_run_report")
        report_path = _opt_path(args, "output_report_file")
        emit_policy_template = bool(getattr(args, "emit_policy_template", False) or write_policy_template_path is not None)
        if emit_policy_template:
            payload = build_context_patch_policy_template_payload(
                policy_mode=getattr(args, "policy_mode", None),
                sample_policy=getattr(args, "sample_policy", None),
                policy_file=policy_file,
                allow_roots=list(getattr(args, "allow_roots", None) or []),
                forbid_roots=list(getattr(args, "forbid_roots", None) or []),
                block_removals=bool(getattr(args, "block_removals", False)),
                block_additions=bool(getattr(args, "block_additions", False)),
                require_apply_check_passed=bool(getattr(args, "require_apply_check_passed", False)),
                max_changed_paths=getattr(args, "max_changed_paths", None),
            )
            if write_policy_template_path is not None:
                _write_cli_output_file(write_policy_template_path, payload.get("policy_template") or {}, as_json=True)
            if args.json:
                if report_path is not None:
                    _write_cli_output_file(report_path, payload, as_json=True)
                _print_json_payload(payload)
            else:
                if report_path is not None:
                    _write_cli_output_file(report_path, str(payload.get("summary_text", "")))
                sys.stdout.write(str(payload.get("summary_text", "")))
            return EXIT_OK

        patch_file = _required_path(args, "patch_file", "context patch-apply requires --patch-file")
        patch_payload = load_context_package(patch_file)
        if source_package_file is None:
            implicit = str(patch_payload.get("source_package_file") or "").strip()
            if implicit:
                source_package_file = Path(implicit).expanduser()
        source_package_payload = load_context_package(source_package_file) if source_package_file is not None else None
        payload = apply_context_patch_payload(
            patch_payload=patch_payload,
            source_package_payload=source_package_payload,
            output_dir=output_dir,
            output_file=output_file,
            dry_run=bool(getattr(args, "dry_run", False)),
            merge_mode=getattr(args, "merge_mode", "overwrite"),
            policy_mode=getattr(args, "policy_mode", None),
            sample_policy=getattr(args, "sample_policy", None),
            policy_file=policy_file,
            allow_roots=list(getattr(args, "allow_roots", None) or []),
            forbid_roots=list(getattr(args, "forbid_roots", None) or []),
            block_removals=bool(getattr(args, "block_removals", False)),
            block_additions=bool(getattr(args, "block_additions", False)),
            require_apply_check_passed=bool(getattr(args, "require_apply_check_passed", False)),
            max_changed_paths=getattr(args, "max_changed_paths", None),
        )
        if write_merge_report_path is not None:
            _write_cli_output_file(write_merge_report_path, build_context_patch_merge_report_payload(payload), as_json=True)
        if write_dry_run_report_path is not None:
            _write_cli_output_file(write_dry_run_report_path, build_context_patch_dry_run_report_payload(payload), as_json=True)
        exit_code = EXIT_OK if bool(payload.get("policy_passed", True)) and bool(payload.get("merge_check_passed", True)) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            return _emit_summary_text(args, payload, output_file=report_path, exit_code=exit_code)
        if args.json:
            if report_path is not None:
                _write_cli_output_file(report_path, payload, as_json=True)
            _print_json_payload(payload)
        else:
            if report_path is not None:
                _write_cli_output_file(report_path, str(payload.get("summary_text", "")))
            print(_render_simple_summary(payload, [
                "apply_mode", "dry_run", "merge_mode", "merge_check_passed", "policy_mode", "policy_passed"
            ]))
        return exit_code

    package_file = _required_path(args, "package_file", f"context {command} requires --package-file")
    package_payload = load_context_package(package_file)

    if command == "restore":
        payload, emitted_text = restore_context_from_package(
            package_payload,
            output_dir=_opt_path(args, "output_dir"),
            output_file=_opt_path(args, "output_file"),
        )
        if getattr(args, "emit_text", False):
            if emitted_text is None:
                return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "context restore --emit-text only supports text packages")
            sys.stdout.write(emitted_text)
            return EXIT_OK
        if args.json:
            _print_json_payload(payload)
        else:
            print(_render_simple_summary(payload, ["restore_mode"]))
        return EXIT_OK

    if command == "inspect":
        payload = inspect_context_package(
            package_payload,
            tokenizer_backend=getattr(args, "tokenizer_backend", None),
            tokenizer_model=getattr(args, "tokenizer_model", None),
        )
        if getattr(args, "emit_summary", False):
            return _emit_summary_text(args, payload)
        return _emit_simple_result(args, payload, text=_render_simple_summary(payload, [
            "compression_mode", "source_label", "restore_mode", "skeleton_char_count", "compression_ratio"
        ]))

    if command == "apply-check":
        payload = build_context_apply_check_payload(
            package_payload=package_payload,
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
        )
        exit_code = EXIT_OK if payload.get("apply_check_passed") else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            return _emit_summary_text(args, payload, exit_code=exit_code)
        summary_keys = ["apply_check_passed", "alignment_score", "alignment_band"]
        if payload.get("incremental_mode"):
            summary_keys.extend(["incremental_mode", "incremental_scope", "incremental_path_count"])
        return _emit_simple_result(args, payload, exit_code=exit_code, text=_render_simple_summary(payload, summary_keys))

    if command == "patch":
        payload = build_context_patch_payload(
            package_payload=package_payload,
            source_package_file=package_file,
            inline_text=_inline_text(args),
            text_file=_opt_path(args, "text_file"),
            input_file=_opt_path(args, "input_file"),
            input_dir=_opt_path(args, "input_dir"),
            output_dir=_opt_path(args, "output_dir"),
            make_zip=bool(getattr(args, "zip_bundle", False)),
        )
        exit_code = EXIT_OK if bool(payload.get("apply_check_passed")) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            return _emit_summary_text(args, payload, exit_code=exit_code)
        return _emit_simple_result(args, payload, exit_code=exit_code, text=_render_simple_summary(payload, [
            "patch_mode", "patch_root", "apply_check_passed"
        ]))

    return _emit_command_error(args, EXIT_USAGE, "invalid_usage", f"unsupported context subcommand: {command}")


def _inline_text(args: argparse.Namespace) -> str | None:
    value = str(getattr(args, "context_text", "") or "").strip()
    return value or None


def _candidate_inline_text(args: argparse.Namespace) -> str | None:
    value = str(getattr(args, "candidate_text", "") or "").strip()
    return value or None


def _opt_path(args: argparse.Namespace, attr: str) -> Path | None:
    value = getattr(args, attr, None)
    if not value:
        return None
    return Path(str(value)).expanduser()


def _required_path(args: argparse.Namespace, attr: str, message: str) -> Path:
    value = _opt_path(args, attr)
    if value is None:
        raise ValueError(message)
    return value


def _emit_summary_text(
    args: argparse.Namespace,
    payload: dict[str, Any],
    *,
    output_file: Path | None = None,
    exit_code: int = EXIT_OK,
) -> int:
    summary_text = str(payload.get("summary_text", ""))
    target = output_file or _opt_path(args, "output_file")
    if target is not None:
        _write_cli_output_file(target, summary_text)
    sys.stdout.write(summary_text)
    return exit_code


def _emit_simple_result(
    args: argparse.Namespace,
    payload: dict[str, Any],
    *,
    exit_code: int = EXIT_OK,
    text: str | None = None,
) -> int:
    output_file = _opt_path(args, "output_file")
    if _json_enabled(args):
        if output_file is not None:
            _write_cli_output_file(output_file, payload, as_json=True)
        _print_json_payload(payload)
    else:
        rendered = text or str(payload.get("summary_text", ""))
        if output_file is not None:
            _write_cli_output_file(output_file, rendered)
        print(rendered)
    return exit_code


def _render_simple_summary(payload: dict[str, Any], keys: list[str]) -> str:
    lines = [str(payload.get("entrypoint", "context"))]
    status = payload.get("status")
    if status is not None:
        lines.append(f"- status: {status}")
    for key in keys:
        if key in payload:
            lines.append(f"- {key}: {payload.get(key)}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp-skeleton", description="MCP-Skeleton: lossless context compression, exact restore, patch, and replay workflows")
    subparsers = parser.add_subparsers(dest="command")

    context_parser = subparsers.add_parser("context", help="Compress long code or text context into an MCP skeleton and restore it later")
    context_subparsers = context_parser.add_subparsers(dest="context_command")

    compress = context_subparsers.add_parser("compress", help="Compress text, one file, or one directory into an MCP skeleton bundle")
    compress.add_argument("--text", dest="context_text")
    compress.add_argument("--text-file", dest="text_file")
    compress.add_argument("--input-file", dest="input_file")
    compress.add_argument("--input-dir", dest="input_dir")
    compress.add_argument("--config", dest="config_file", help="Read context defaults from a .mcp-skeleton.json/yaml file")
    compress.add_argument("--preset", dest="preset_id")
    compress.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    compress.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    compress.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from directory compression; can be repeated")
    compress.add_argument("--incremental", action="store_true")
    compress.add_argument("--base-commit", dest="base_commit")
    compress.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    compress.add_argument("--tokenizer-model", dest="tokenizer_model")
    compress.add_argument("--emit-skeleton", action="store_true")
    compress.add_argument("--output-file", dest="output_file")
    compress.add_argument("--output-dir", dest="output_dir")
    compress.add_argument("--json", action="store_true")

    restore = context_subparsers.add_parser("restore", help="Restore the original text, file, or directory from a context bundle")
    restore.add_argument("--package-file", dest="package_file", required=True)
    restore.add_argument("--output-file", dest="output_file")
    restore.add_argument("--output-dir", dest="output_dir")
    restore.add_argument("--emit-text", action="store_true")
    restore.add_argument("--json", action="store_true")

    inspect = context_subparsers.add_parser("inspect", help="Inspect one context bundle without restoring the original content")
    inspect.add_argument("--package-file", dest="package_file", required=True)
    inspect.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    inspect.add_argument("--tokenizer-model", dest="tokenizer_model")
    inspect.add_argument("--emit-summary", action="store_true")
    inspect.add_argument("--output-file", dest="output_file")
    inspect.add_argument("--json", action="store_true")

    apply_check = context_subparsers.add_parser("apply-check", help="Validate that edited text, a file, or a directory still stays inside the original context skeleton boundary")
    apply_check.add_argument("--package-file", dest="package_file", required=True)
    apply_check.add_argument("--text", dest="context_text")
    apply_check.add_argument("--text-file", dest="text_file")
    apply_check.add_argument("--input-file", dest="input_file")
    apply_check.add_argument("--input-dir", dest="input_dir")
    apply_check.add_argument("--emit-summary", action="store_true")
    apply_check.add_argument("--output-file", dest="output_file")
    apply_check.add_argument("--json", action="store_true")

    preset = context_subparsers.add_parser("preset", help="List available compression presets or inspect one selected preset")
    preset.add_argument("preset_id", nargs="?", default="generic")
    preset.add_argument("--json", action="store_true")

    config = context_subparsers.add_parser("config", help="Emit, initialize, recommend, or validate a .mcp-skeleton.json/yaml project defaults file")
    config.add_argument("config_action", nargs="?", choices=["init"], help="Use `init` to write .mcp-skeleton.json by default")
    config.add_argument("--config", dest="config_file", help="Config file to validate; defaults to discovered .mcp-skeleton.json/yaml when --validate is used")
    config.add_argument("--validate", action="store_true", help="Validate an existing config file instead of emitting a template")
    config.add_argument("--recommend", action="store_true", help="Analyze an input and emit recommended project defaults")
    config.add_argument("--text", dest="context_text")
    config.add_argument("--input-file", dest="input_file", help="Discover .mcp-skeleton config next to this file when validating")
    config.add_argument("--input-dir", dest="input_dir", help="Discover .mcp-skeleton config inside this directory when validating")
    config.add_argument("--text-file", dest="text_file", help="Discover .mcp-skeleton config next to this text file when validating")
    config.add_argument("--preset", dest="preset_id")
    config.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    config.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    config.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from recommendation analysis; can be repeated")
    config.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    config.add_argument("--tokenizer-model", dest="tokenizer_model")
    config.add_argument("--output-file", dest="output_file", help="Write the default template to this path; .yaml/.yml writes YAML")
    config.add_argument("--output-report-file", dest="output_report_file", help="Write a Markdown recommendation report when using --recommend")
    config.add_argument("--force", action="store_true", help="Overwrite --output-file if it already exists")
    config.add_argument("--json", action="store_true")

    init = context_subparsers.add_parser("init", help="Initialize a .mcp-skeleton.json/yaml project config")
    init.add_argument("--output-file", dest="output_file", default=".mcp-skeleton.json", help="Config path to write; .yaml/.yml writes YAML")
    init.add_argument("--force", action="store_true", help="Overwrite --output-file if it already exists")
    init.add_argument("--json", action="store_true")

    install_hook = context_subparsers.add_parser("install-hook", help="Install a lightweight git pre-commit hook for config validation and CLI syntax checks")
    install_hook.add_argument("--hook", dest="hook_name", default="pre-commit", choices=["pre-commit"])
    install_hook.add_argument("--dry-run", action="store_true", help="Print the hook that would be installed without writing it")
    install_hook.add_argument("--force", action="store_true", help="Overwrite an existing hook")
    install_hook.add_argument("--json", action="store_true")

    doctor = context_subparsers.add_parser("doctor", help="Check config, compression advice, and exact restore readiness for one source")
    doctor.add_argument("--text", dest="context_text")
    doctor.add_argument("--text-file", dest="text_file")
    doctor.add_argument("--input-file", dest="input_file")
    doctor.add_argument("--input-dir", dest="input_dir")
    doctor.add_argument("--config", dest="config_file", help="Read context defaults from a .mcp-skeleton.json/yaml file")
    doctor.add_argument("--preset", dest="preset_id")
    doctor.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    doctor.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    doctor.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from directory compression; can be repeated")
    doctor.add_argument("--incremental", action="store_true")
    doctor.add_argument("--base-commit", dest="base_commit")
    doctor.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    doctor.add_argument("--tokenizer-model", dest="tokenizer_model")
    doctor.add_argument("--json", action="store_true")

    bundle = context_subparsers.add_parser("bundle", help="Export a full context bundle with compression, inspect, and optional apply-check artifacts")
    bundle.add_argument("--text", dest="context_text")
    bundle.add_argument("--text-file", dest="text_file")
    bundle.add_argument("--input-file", dest="input_file")
    bundle.add_argument("--input-dir", dest="input_dir")
    bundle.add_argument("--config", dest="config_file", help="Read context defaults from a .mcp-skeleton.json/yaml file")
    bundle.add_argument("--preset", dest="preset_id")
    bundle.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    bundle.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    bundle.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from directory compression; can be repeated")
    bundle.add_argument("--incremental", action="store_true")
    bundle.add_argument("--base-commit", dest="base_commit")
    bundle.add_argument("--candidate-text", dest="candidate_text")
    bundle.add_argument("--candidate-text-file", dest="candidate_text_file")
    bundle.add_argument("--candidate-input-file", dest="candidate_input_file")
    bundle.add_argument("--candidate-input-dir", dest="candidate_input_dir")
    bundle.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    bundle.add_argument("--tokenizer-model", dest="tokenizer_model")
    bundle.add_argument("--zip", dest="zip_bundle", action="store_true")
    bundle.add_argument("--emit-summary", action="store_true")
    bundle.add_argument("--output-file", dest="output_file")
    bundle.add_argument("--output-dir", dest="output_dir")
    bundle.add_argument("--json", action="store_true")

    patch = context_subparsers.add_parser("patch", help="Export a patch bundle that compares one edited candidate against the original context bundle")
    patch.add_argument("--package-file", dest="package_file", required=True)
    patch.add_argument("--text", dest="context_text")
    patch.add_argument("--text-file", dest="text_file")
    patch.add_argument("--input-file", dest="input_file")
    patch.add_argument("--input-dir", dest="input_dir")
    patch.add_argument("--zip", dest="zip_bundle", action="store_true")
    patch.add_argument("--emit-summary", action="store_true")
    patch.add_argument("--output-file", dest="output_file")
    patch.add_argument("--output-dir", dest="output_dir")
    patch.add_argument("--json", action="store_true")

    patch_apply = context_subparsers.add_parser("patch-apply", help="Replay one context patch bundle into a safe output target")
    patch_apply.add_argument("--patch-file", dest="patch_file")
    patch_apply.add_argument("--source-package-file", dest="source_package_file")
    patch_apply.add_argument("--output-file", dest="output_file")
    patch_apply.add_argument("--output-dir", dest="output_dir")
    patch_apply.add_argument("--dry-run", action="store_true")
    patch_apply.add_argument("--merge-mode", choices=["overwrite", "reject-conflicts"], default="overwrite")
    patch_apply.add_argument("--policy-mode", choices=["open", "safe", "strict"], default="open")
    patch_apply.add_argument("--sample-policy", choices=["safe", "strict"])
    patch_apply.add_argument("--policy-file", dest="policy_file")
    patch_apply.add_argument("--allow-root", dest="allow_roots", action="append")
    patch_apply.add_argument("--forbid-root", dest="forbid_roots", action="append")
    patch_apply.add_argument("--block-removals", action="store_true")
    patch_apply.add_argument("--block-additions", action="store_true")
    patch_apply.add_argument("--require-apply-check-pass", dest="require_apply_check_passed", action="store_true")
    patch_apply.add_argument("--max-changed-paths", dest="max_changed_paths", type=int)
    patch_apply.add_argument("--emit-policy-template", action="store_true")
    patch_apply.add_argument("--write-policy-template", dest="write_policy_template")
    patch_apply.add_argument("--write-merge-report", dest="write_merge_report")
    patch_apply.add_argument("--write-dry-run-report", dest="write_dry_run_report")
    patch_apply.add_argument("--emit-summary", action="store_true")
    patch_apply.add_argument("--output-report-file", dest="output_report_file")
    patch_apply.add_argument("--json", action="store_true")

    return parser


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
