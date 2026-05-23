from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
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
PACKAGE_NAME = "mcp-skeleton"
FALLBACK_VERSION = "0.1.0"

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
    "exclude": ["node_modules/", "dist/", "build/", ".workspace_ail/", "*.map"],
}
CONTEXT_CONFIG_FILENAMES = [".mcp-skeleton.json", ".mcp-skeleton.yaml", ".mcp-skeleton.yml"]
IGNORE_CWD_CONFIG_ENV = "MCP_SKELETON_IGNORE_CWD_CONFIG"
CONTEXT_SUBCOMMANDS = {
    "compress",
    "restore",
    "inspect",
    "explain",
    "apply-check",
    "preset",
    "config",
    "init",
    "install-hook",
    "doctor",
    "start",
    "quick",
    "recent",
    "demo",
    "bundle",
    "patch",
    "patch-apply",
}
CODELIKE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".html", ".vue", ".sql", ".sh", ".rb", ".php", ".swift", ".kt",
}
PROSE_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}


def _print_json_payload(payload: Any, *, file: Any = sys.stdout) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False), file=file)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_project_version() -> str:
    try:
        from importlib.metadata import version

        return version(PACKAGE_NAME)
    except Exception:
        pass
    pyproject = _project_root() / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("version"):
                _, value = stripped.split("=", 1)
                return value.strip().strip('"').strip("'")
    return FALLBACK_VERSION


def _build_version_payload() -> dict[str, Any]:
    command_path = shutil.which("mcp-skeleton") or ""
    executable = command_path or sys.executable
    payload = {
        "status": "ok",
        "entrypoint": "mcp-skeleton-version",
        "package_name": PACKAGE_NAME,
        "version": _read_project_version(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "executable": executable,
        "command_path": command_path,
        "project_root": str(_project_root()),
        "install_home": os.environ.get("MCP_SKELETON_HOME", str(Path.home() / ".mcp-skeleton")),
        "path_hint": "ok" if command_path else "mcp-skeleton command was not found on PATH; use python3 -m cli or run sh install.sh",
    }
    payload["summary_text"] = "\n".join(
        [
            "mcp-skeleton version",
            "",
            f"Version: {payload['version']}",
            f"Python: {payload['python_version']} ({payload['python_executable']})",
            f"Command: {payload['command_path'] or '(not found on PATH)'}",
            f"Install home: {payload['install_home']}",
            f"Project root: {payload['project_root']}",
            f"PATH status: {payload['path_hint']}",
        ]
    )
    return payload


def _emit_version_result(args: argparse.Namespace) -> int:
    payload = _build_version_payload()
    if bool(getattr(args, "json", False)):
        _print_json_payload(payload)
    else:
        print(payload["summary_text"])
    return EXIT_OK


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


def _current_command_text(extra_args: list[str] | None = None) -> str:
    args = [*sys.argv[1:], *(extra_args or [])]
    return _format_cli_command(args)


def _current_command_text_with_replaced_option(option: str, value: str) -> str:
    original = list(sys.argv[1:])
    updated: list[str] = []
    index = 0
    replaced = False
    while index < len(original):
        item = original[index]
        if item == option:
            updated.extend([option, value])
            replaced = True
            index += 2 if index + 1 < len(original) else 1
            continue
        if item.startswith(f"{option}="):
            updated.extend([option, value])
            replaced = True
            index += 1
            continue
        updated.append(item)
        index += 1
    if not replaced:
        updated.extend([option, value])
    return _format_cli_command(updated)


def _build_error_guidance(code: str, message: str) -> dict[str, Any]:
    lower = message.lower()
    recovery_steps: list[str] = []
    fix_command_text = ""
    if "already exists; use --force" in lower:
        recovery_steps = [
            "rerun the same command with --force if overwriting is intentional",
            "or choose a different output/config/report path to keep the existing file",
        ]
        if "--force" not in sys.argv[1:]:
            fix_command_text = _current_command_text(["--force"])
    elif "does not exist" in lower or "must be a file" in lower or "must be a directory" in lower:
        recovery_steps = [
            "check that the input path exists on this machine",
            "use --input-dir for directories, --input-file for one file, or --text-file for prose/text files",
        ]
    elif "requires exactly one input source" in lower or "did not receive a usable input source" in lower:
        recovery_steps = [
            "provide exactly one source: --input-dir, --input-file, --text-file, or --text",
            "for the current repository, try: mcp-skeleton quick --input-dir .",
        ]
        fix_command_text = "mcp-skeleton quick --input-dir ."
    elif "requires --output-dir" in lower:
        recovery_steps = [
            "add --output-dir with a safe empty directory for restored or replayed files",
            "avoid using the original source directory as the output target",
        ]
    else:
        recovery_steps = [
            "review the command arguments and paths, then rerun with --json for machine-readable diagnostics",
        ]
    return {
        "recovery_steps": recovery_steps,
        "fix_command_text": fix_command_text,
        "error_category": code,
    }


def _emit_command_error(args: argparse.Namespace, exit_code: int, code: str, message: str) -> int:
    guidance = _build_error_guidance(code, message)
    if _json_enabled(args):
        _print_json_error(code, message, exit_code=exit_code, details=guidance)
    else:
        print(f"error: {message}", file=sys.stderr)
        for step in guidance.get("recovery_steps", []):
            print(f"recovery: {step}", file=sys.stderr)
        if guidance.get("fix_command_text"):
            print(f"try: {guidance['fix_command_text']}", file=sys.stderr)
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
        if os.environ.get(IGNORE_CWD_CONFIG_ENV) not in {"1", "true", "TRUE", "yes", "YES"}:
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


def _infer_context_preset(args: argparse.Namespace) -> str:
    if _opt_path(args, "input_dir") is not None:
        return "codebase"
    if _inline_text(args) is not None:
        return "writing"
    source_file = _opt_path(args, "text_file") or _opt_path(args, "input_file")
    if source_file is not None:
        suffix = source_file.suffix.lower()
        if suffix in PROSE_EXTENSIONS:
            return "writing"
        if suffix in CODELIKE_EXTENSIONS:
            return "codebase"
    return "generic"


def _infer_context_focus_mode(args: argparse.Namespace, *, preset_id: str | None) -> str:
    if preset_id == "writing":
        return "writing-outline"
    if _opt_path(args, "input_dir") is not None:
        return "imports" if preset_id == "codebase" else "tree"
    return "full"


def _resolve_context_defaults(args: argparse.Namespace) -> tuple[Path | None, dict[str, Any], dict[str, Any]]:
    config_file, config = _load_context_config(args)
    cli_excludes = list(getattr(args, "exclude_patterns", None) or [])
    config_excludes = _config_list(config, "exclude", "excludes", "exclude_patterns")
    preset_id = getattr(args, "preset_id", None) or _config_string(config, "preset", "preset_id")
    if preset_id is None:
        preset_id = _infer_context_preset(args)
    if preset_id is not None:
        preset_id = resolve_context_preset(preset_id)["preset_id"]
    focus_mode = getattr(args, "focus_mode", None) or _config_string(config, "focus_mode")
    if focus_mode is None:
        focus_mode = _infer_context_focus_mode(args, preset_id=preset_id)
    focus_mode = _normalize_config_choice(focus_mode, field="focus_mode", supported=CONTEXT_FOCUS_MODES)
    skeleton_density = getattr(args, "skeleton_density", None) or _config_string(config, "skeleton_density", "density")
    if skeleton_density is None:
        skeleton_density = "adaptive"
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


def _format_cli_command(command_args: list[Any]) -> str:
    if not command_args:
        return ""
    normalized = list(command_args)
    if normalized and normalized[0] == "context" and len(normalized) > 1 and normalized[1] in CONTEXT_SUBCOMMANDS:
        normalized = normalized[1:]
    quoted = " ".join(shlex.quote(str(item)) for item in normalized)
    return f"mcp-skeleton {quoted}"


def _normalize_top_level_context_aliases(argv: list[str]) -> list[str]:
    if argv and argv[0] in CONTEXT_SUBCOMMANDS:
        return ["context", *argv]
    return argv


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 2)


def _build_readiness_action_plan(
    *,
    readiness_status: str,
    restore_check: dict[str, Any],
    warnings: list[dict[str, Any]],
    recommended_command_args: list[Any],
) -> list[dict[str, str]]:
    if readiness_status == "ready":
        return [
            {
                "step": "use_recommended_command",
                "status": "ready",
                "message": "copy the recommended command to create a compressed context bundle",
            },
            {
                "step": "keep_restore_package",
                "status": "ready",
                "message": "keep the generated manifest/package with the skeleton so exact restore remains available",
            },
        ]
    if readiness_status == "watch":
        warning_text = warnings[0].get("message", "review compression warnings") if warnings else "review watch-level checks"
        return [
            {
                "step": "review_warnings",
                "status": "watch",
                "message": warning_text,
            },
            {
                "step": "try_recommended_command",
                "status": "watch",
                "message": "run the recommended command after reviewing warnings and expected token savings",
            },
        ]
    missing = int(restore_check.get("missing_count") or 0)
    mismatched = int(restore_check.get("mismatched_count") or 0)
    return [
        {
            "step": "do_not_rely_on_bundle_yet",
            "status": "blocked",
            "message": "restore verification did not pass, so do not use this skeleton as a source of truth yet",
        },
        {
            "step": "inspect_restore_failures",
            "status": "blocked",
            "message": f"missing={missing}, mismatched={mismatched}; rerun doctor after fixing input/config issues",
        },
    ]


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


def _build_context_doctor_payload(
    args: argparse.Namespace,
    *,
    include_compression_payload: bool = False,
) -> tuple[dict[str, Any], int]:
    total_started = time.perf_counter()
    config_file, config_values, context_defaults = _resolve_context_defaults(args)
    compress_started = time.perf_counter()
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
    compress_ms = _elapsed_ms(compress_started)
    restore_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="mcp_skeleton_doctor.") as tmp:
        restore_check = _compare_doctor_restore(compression_payload, output_dir=Path(tmp))
    restore_check_ms = _elapsed_ms(restore_started)

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
    recommended_command_args = list(compression_payload.get("recommended_command_args") or [])
    action_plan = _build_readiness_action_plan(
        readiness_status=readiness,
        restore_check=restore_check,
        warnings=warnings,
        recommended_command_args=recommended_command_args,
    )
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
        "recommended_command_args": recommended_command_args,
        "recommended_command_text": _format_cli_command(recommended_command_args),
        "restore_check": restore_check,
        "install": _build_version_payload(),
        "timings_ms": {
            "compress": compress_ms,
            "restore_check": restore_check_ms,
            "total": 0.0,
        },
        "checks": blocking_checks + watch_checks,
        "action_plan": action_plan,
        "next_steps": [
            item["message"] for item in action_plan
        ],
    }
    report_path, report_written = _write_text_report_file(
        _opt_path(args, "output_report_file"),
        _render_context_doctor_report(payload),
        force=bool(getattr(args, "force", False)),
    )
    payload["report_file"] = report_path
    payload["report_written"] = report_written
    payload["timings_ms"]["total"] = _elapsed_ms(total_started)
    payload["summary_text"] = _render_context_doctor_summary(payload)
    if include_compression_payload:
        payload["_compression_payload"] = compression_payload
    return payload, EXIT_OK if not failed_blocks else EXIT_VALIDATION


def _render_context_doctor_report(payload: dict[str, Any]) -> str:
    metrics = payload.get("metrics") or {}
    restore_check = payload.get("restore_check") or {}
    scale_profile = payload.get("source_scale_profile") or {}
    recommended_config = payload.get("recommended_config") or {}
    warnings = list(payload.get("compression_warnings") or [])
    explanations = list(payload.get("compression_explanations") or [])
    command_args = list(payload.get("recommended_command_args") or [])
    action_plan = list(payload.get("action_plan") or [])
    lines = [
        "# MCP-Skeleton Doctor Report",
        "",
        "## Verdict",
        f"- status: {payload.get('status', '')}",
        f"- readiness_status: {payload.get('readiness_status', '')}",
        f"- restore_status: {restore_check.get('status', '')}",
        f"- missing_count: {restore_check.get('missing_count', 0)}",
        f"- mismatched_count: {restore_check.get('mismatched_count', 0)}",
        "",
        "## Source",
        f"- source_label: {payload.get('source_label', '')}",
        f"- source_kind: {payload.get('source_kind', '')}",
        f"- compression_mode: {payload.get('compression_mode', '')}",
        f"- scale_class: {scale_profile.get('scale_class', '')}",
        f"- total_files: {scale_profile.get('total_files', 0)}",
        f"- total_chars: {scale_profile.get('total_chars', 0)}",
        "",
        "## Recommended Config",
        f"- preset: {recommended_config.get('preset_id', '')}",
        f"- focus_mode: {recommended_config.get('focus_mode', '')}",
        f"- skeleton_density: {recommended_config.get('skeleton_density', '')}",
        f"- exclude_count: {len(recommended_config.get('exclude') or [])}",
        "",
        "## Token Estimate",
        f"- estimated_token_reduction_ratio: {metrics.get('estimated_token_reduction_ratio', '')}",
        f"- estimated_token_direction: {metrics.get('estimated_token_direction', '')}",
        f"- estimated_tokens_saved: {metrics.get('estimated_tokens_saved', '')}",
        "",
        "## Recommended Command Args",
        json.dumps(command_args, ensure_ascii=False),
        "",
        "## Recommended Command",
        payload.get("recommended_command_text", "") or "(not available)",
        "",
        "## Warnings",
    ]
    if warnings:
        lines.extend(f"- {item.get('code', '')}: {item.get('message', '')}" for item in warnings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Explanations")
    if explanations:
        lines.extend(f"- {item.get('code', '')}: {item.get('message', '')}" for item in explanations)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Steps",
        ]
    )
    if action_plan:
        lines.extend(f"- {item.get('status', '')}: {item.get('message', '')}" for item in action_plan)
    else:
        lines.append("- Use the recommended command args for the next compression run.")
    lines.append("")
    return "\n".join(lines)


def _render_context_doctor_summary(payload: dict[str, Any]) -> str:
    restore_check = payload.get("restore_check") or {}
    action_plan = list(payload.get("action_plan") or [])
    timings = payload.get("timings_ms") or {}
    metrics = payload.get("metrics") or {}
    install = payload.get("install") or {}
    lines = [
        "MCP-Skeleton Doctor",
        "",
        f"Readiness: {payload.get('readiness_status', '')}",
        f"Restore status: {restore_check.get('status', '')}",
        f"Missing files: {restore_check.get('missing_count', 0)}",
        f"Mismatched files: {restore_check.get('mismatched_count', 0)}",
        f"Estimated token savings: {metrics.get('estimated_tokens_saved', '')}",
        f"Total time: {timings.get('total', '')} ms",
        f"Command: {install.get('executable', '') or '(not found on PATH)'}",
        f"Recommended command: {payload.get('recommended_command_text', '') or '(not available)'}",
        "",
        "Next steps:",
    ]
    if action_plan:
        lines.extend(f"- {item.get('message', '')}" for item in action_plan)
    else:
        lines.append("- Use the recommended command args for the next compression run.")
    return "\n".join(lines)


def _render_context_start_summary(payload: dict[str, Any]) -> str:
    metrics = payload.get("metrics") or {}
    readiness = str(payload.get("doctor_readiness_status") or "")
    restore_safe = "OK" if payload.get("restore_safe") else "BLOCKED"
    status_label = "READY TO USE" if readiness == "ready" and payload.get("restore_safe") else "REVIEW FIRST" if readiness == "watch" else "BLOCKED"
    command = str(payload.get("next_command") or "")
    action_plan = list(payload.get("action_plan") or [])
    config_state = "written" if payload.get("config_written") else "already exists"
    report_state = "written" if payload.get("report_written") else "already exists"
    scale_profile = payload.get("source_scale_profile") or {}
    timings = payload.get("timings_ms") or {}
    lines = [
        "MCP-Skeleton Start",
        "",
        f"Status: {status_label}",
        "",
        "What happened:",
        f"- Restore safety: {restore_safe}",
        f"- Readiness: {readiness}",
        f"- Config file ({config_state}): {payload.get('config_file', '') or '(not written)'}",
        f"- Report file ({report_state}): {payload.get('report_file', '') or '(not written)'}",
        "",
        "Recommended setup:",
        f"- Mode: {payload.get('recommended_mode', '')}",
        f"- Files included: {scale_profile.get('total_files', 0)}",
        f"- Source tokens: {metrics.get('estimated_token_count_source', 0)}",
        f"- Skeleton tokens: {metrics.get('estimated_token_count_skeleton', 0)}",
        f"- Estimated tokens saved: {metrics.get('estimated_tokens_saved', 0)}",
        f"- Estimated token savings: {metrics.get('estimated_savings_percent', 0)}%",
        "",
        "Timing:",
        f"- Total: {timings.get('total', 0)} ms",
        f"- Recommend config: {timings.get('config_recommend', 0)} ms",
        f"- Restore safety check: {timings.get('doctor', 0)} ms",
        "",
        "Copy/paste this command:",
        command or "(not available)",
        "",
        "Next steps:",
    ]
    if action_plan:
        lines.extend(f"- {item.get('message', '')}" for item in action_plan)
    else:
        lines.extend(str(item) for item in payload.get("next_steps") or [])
    warnings = list(payload.get("warnings") or [])
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item.get('message', '')}" for item in warnings[:3])
    return "\n".join(lines)


def _quick_restore_command_args(bundle_payload: dict[str, Any]) -> list[str]:
    manifest_file = str(Path(str(bundle_payload.get("bundle_root") or "")) / "context_manifest.json")
    mode = str(bundle_payload.get("compression_mode") or "")
    args = ["context", "restore", "--package-file", manifest_file]
    if mode == "text":
        source_label = str(bundle_payload.get("source_label") or "restored.txt")
        args.extend(["--output-file", str(Path.cwd() / source_label)])
    else:
        args.extend(["--output-dir", str(Path.cwd() / "mcp-skeleton-restore")])
    return args


def _quick_fast_command_text(args: argparse.Namespace) -> str:
    command_args = ["context", "quick", "--fast"]
    if _inline_text(args) is not None:
        return ""
    if _opt_path(args, "input_dir") is not None:
        command_args.extend(["--input-dir", str(_opt_path(args, "input_dir").resolve())])  # type: ignore[union-attr]
    elif _opt_path(args, "input_file") is not None:
        command_args.extend(["--input-file", str(_opt_path(args, "input_file").resolve())])  # type: ignore[union-attr]
    elif _opt_path(args, "text_file") is not None:
        command_args.extend(["--text-file", str(_opt_path(args, "text_file").resolve())])  # type: ignore[union-attr]
    else:
        return ""
    output_dir = _opt_path(args, "output_dir")
    if output_dir is not None:
        command_args.extend(["--output-dir", str(output_dir.resolve() if output_dir.is_absolute() else (Path.cwd() / output_dir).resolve())])
    if getattr(args, "zip_bundle", False):
        command_args.append("--zip")
    return _format_cli_command(command_args)


def _build_quick_handoff_payload(bundle_payload: dict[str, Any], *, bundle_root: str, manifest_file: str) -> dict[str, Any]:
    files = bundle_payload.get("files") or {}
    skeleton_file = str(files.get("skeleton_file") or (str(Path(bundle_root) / "context_skeleton.mcp") if bundle_root else ""))
    inspect_summary = str(files.get("inspect_summary_txt") or (str(Path(bundle_root) / "inspect_summary.txt") if bundle_root else ""))
    return {
        "status": "ready" if skeleton_file and manifest_file else "unavailable",
        "message": "feed the skeleton file to your AI or IDE; keep the bundle folder and manifest for exact restore",
        "skeleton_file": skeleton_file,
        "bundle_root": bundle_root,
        "manifest_file": manifest_file,
        "inspect_summary": inspect_summary,
        "restore_package": str(files.get("restore_package") or ""),
    }


def _quick_open_command_text(bundle_root: str) -> str:
    if not bundle_root:
        return ""
    return " ".join(["open", shlex.quote(bundle_root)])


def _maybe_open_quick_bundle(args: argparse.Namespace, *, bundle_root: str) -> tuple[bool, str]:
    if not bool(getattr(args, "open_bundle", False)):
        return False, ""
    if not bundle_root:
        return False, "bundle folder is not available"
    if sys.platform != "darwin":
        return False, "--open currently opens Finder only on macOS"
    proc = subprocess.run(["open", bundle_root], text=True, capture_output=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "open command failed").strip()
        return False, detail
    return True, ""


def _quick_copy_command_text(skeleton_file: str) -> str:
    if not skeleton_file:
        return ""
    return f"cat {shlex.quote(skeleton_file)} | pbcopy"


def _maybe_copy_quick_skeleton(args: argparse.Namespace, *, skeleton_file: str) -> tuple[bool, str]:
    if not bool(getattr(args, "copy_command", False)):
        return False, ""
    if not skeleton_file:
        return False, "skeleton file is not available"
    if sys.platform != "darwin":
        return False, "--copy-command currently uses pbcopy only on macOS"
    try:
        content = Path(skeleton_file).read_text(encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    proc = subprocess.run(["pbcopy"], input=content, text=True, capture_output=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "pbcopy command failed").strip()
        return False, detail
    return True, ""


def _recent_root_from_args(args: argparse.Namespace) -> Path:
    input_dir = _opt_path(args, "input_dir")
    if input_dir is not None:
        return input_dir.resolve()
    input_file = _opt_path(args, "input_file") or _opt_path(args, "text_file")
    if input_file is not None:
        return input_file.resolve().parent
    return Path.cwd().resolve()


def _recent_file_from_args(args: argparse.Namespace) -> Path:
    return _recent_root_from_args(args) / ".workspace_ail" / "recent_quick.json"


def _build_recent_record(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    metrics = ((payload.get("start") or {}).get("metrics") or {})
    return {
        "status": "ok",
        "entrypoint": "context-recent-record",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "source_root": str(_recent_root_from_args(args)),
        "bundle_root": payload.get("bundle_root", ""),
        "manifest_file": payload.get("manifest_file", ""),
        "skeleton_file": (payload.get("handoff") or {}).get("skeleton_file", ""),
        "inspect_command_text": payload.get("inspect_command_text", ""),
        "restore_command_text": payload.get("restore_command_text", ""),
        "open_command_text": payload.get("open_command_text", ""),
        "copy_command_text": payload.get("copy_command_text", ""),
        "estimated_tokens_saved": metrics.get("estimated_tokens_saved", 0),
        "estimated_savings_percent": metrics.get("estimated_savings_percent", 0),
        "experience": payload.get("experience") or {},
    }


def _write_recent_record(args: argparse.Namespace, payload: dict[str, Any]) -> str:
    recent_file = _recent_file_from_args(args)
    recent_file.parent.mkdir(parents=True, exist_ok=True)
    recent_file.write_text(json.dumps(_build_recent_record(args, payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(recent_file)


def _render_context_recent_summary(payload: dict[str, Any]) -> str:
    lines = [
        "MCP-Skeleton Recent",
        "",
        f"Status: {payload.get('recent_status', '')}",
        f"Recent file: {payload.get('recent_file', '')}",
        "",
        "Last bundle:",
        f"- Bundle: {payload.get('bundle_root', '') or '(not available)'}",
        f"- Skeleton: {payload.get('skeleton_file', '') or '(not available)'}",
        f"- Manifest: {payload.get('manifest_file', '') or '(not available)'}",
        f"- Estimated tokens saved: {payload.get('estimated_tokens_saved', 0)}",
        f"- Estimated token savings: {payload.get('estimated_savings_percent', 0)}%",
        "",
        "Open bundle:",
        payload.get("open_command_text") or "(not available)",
        "",
        "Copy skeleton:",
        payload.get("copy_command_text") or "(not available)",
        "",
        "Next commands:",
        f"- Inspect: {payload.get('inspect_command_text', '') or '(not available)'}",
        f"- Restore: {payload.get('restore_command_text', '') or '(not available)'}",
    ]
    return "\n".join(lines)


def _build_context_recent_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    recent_file = _recent_file_from_args(args)
    if not recent_file.exists():
        payload = {
            "status": "error",
            "entrypoint": "context-recent",
            "recent_status": "missing",
            "recent_file": str(recent_file),
            "message": "no recent quick bundle was found for this project; run mcp-skeleton quick --input-dir . first",
        }
        payload["summary_text"] = _render_context_recent_summary(payload)
        return payload, EXIT_VALIDATION
    record = json.loads(recent_file.read_text(encoding="utf-8"))
    payload = {
        "status": "ok",
        "entrypoint": "context-recent",
        "recent_status": "ready",
        "recent_file": str(recent_file),
        **{key: record.get(key, "") for key in [
            "source_root",
            "bundle_root",
            "manifest_file",
            "skeleton_file",
            "inspect_command_text",
            "restore_command_text",
            "open_command_text",
            "copy_command_text",
        ]},
        "estimated_tokens_saved": record.get("estimated_tokens_saved", 0),
        "estimated_savings_percent": record.get("estimated_savings_percent", 0),
        "experience": record.get("experience") or {},
    }
    payload["summary_text"] = _render_context_recent_summary(payload)
    return payload, EXIT_OK


def _build_quick_speed_tip(args: argparse.Namespace, *, start_payload: dict[str, Any], timings_ms: dict[str, Any], fast_path: bool) -> dict[str, Any]:
    if fast_path:
        return {}
    scale_profile = start_payload.get("source_scale_profile") or {}
    scale_class = str(scale_profile.get("scale_class") or "")
    total_files = int(scale_profile.get("total_files") or 0)
    total_ms = float(timings_ms.get("total") or 0.0)
    if scale_class not in {"large", "huge"} and total_files < 100 and total_ms < 1500:
        return {}
    command_text = _quick_fast_command_text(args)
    if not command_text:
        return {}
    return {
        "status": "available",
        "reason": "large input or noticeable quick runtime",
        "scale_class": scale_class,
        "total_files": total_files,
        "observed_total_ms": total_ms,
        "suggested_command_text": command_text,
        "message": "Next time, use --fast to skip onboarding generation while keeping restore safety checks.",
    }


def _build_quick_experience_payload(*, start_payload: dict[str, Any], timings_ms: dict[str, Any], fast_path: bool) -> dict[str, Any]:
    scale_profile = start_payload.get("source_scale_profile") or {}
    metrics = start_payload.get("metrics") or {}
    total_ms = float(timings_ms.get("total") or 0.0)
    total_files = int(scale_profile.get("total_files") or 0)
    scale_class = str(scale_profile.get("scale_class") or "unknown")
    savings_percent = float(metrics.get("estimated_savings_percent") or 0.0)
    token_direction = str(metrics.get("estimated_token_direction") or "")

    if total_ms < 500:
        speed_status = "fast"
        speed_message = "quick completed in well under a second on this input"
    elif total_ms < 2500:
        speed_status = "ok"
        speed_message = "quick runtime is within the normal interactive range"
    else:
        speed_status = "slow"
        speed_message = "quick took long enough that --fast may feel better next time"

    if token_direction == "reduced" and savings_percent >= 30:
        token_status = "good"
        token_message = "token savings look meaningful for AI/IDE handoff"
    elif token_direction == "reduced":
        token_status = "watch"
        token_message = "token savings exist, but review whether the skeleton is compact enough"
    else:
        token_status = "expanded"
        token_message = "this input is very small; compression can expand tiny projects"

    recommendation = "use this bundle as the AI/IDE handoff"
    if speed_status == "slow" and not fast_path:
        recommendation = "next time, use --fast for a quicker safe bundle path"
    elif token_status == "expanded":
        recommendation = "use quick on a larger project or long document to see the token advantage"
    elif scale_class in {"large", "huge"} and token_status == "good":
        recommendation = "large input looks healthy; keep the bundle and share the skeleton"

    return {
        "speed_status": speed_status,
        "speed_message": speed_message,
        "token_status": token_status,
        "token_message": token_message,
        "recommendation": recommendation,
        "scale_class": scale_class,
        "total_files": total_files,
        "total_ms": total_ms,
        "estimated_savings_percent": savings_percent,
    }


def _render_context_quick_summary(payload: dict[str, Any]) -> str:
    start = payload.get("start") or {}
    bundle = payload.get("bundle") or {}
    restore_safe = "OK" if payload.get("restore_safe") else "BLOCKED"
    metrics = start.get("metrics") or {}
    timings = payload.get("timings_ms") or {}
    handoff = payload.get("handoff") or {}
    open_error = str(payload.get("open_error") or "")
    copy_error = str(payload.get("copy_error") or "")
    experience = payload.get("experience") or {}
    quick_mode = "fast" if payload.get("fast_path") else "standard"
    scale_profile = start.get("source_scale_profile") or {}
    token_direction = str(metrics.get("estimated_token_direction") or "")
    saved_tokens = int(metrics.get("estimated_tokens_saved") or 0)
    savings_percent = metrics.get("estimated_savings_percent", 0)
    token_result = "reduced" if token_direction == "reduced" else "expanded"
    primary_next = payload.get("inspect_command_text") or payload.get("restore_command_text") or ""
    lines = [
        "MCP-Skeleton Quick",
        "",
        "Result:",
        f"- Status: {payload.get('quick_status', '')}",
        f"- Mode: {quick_mode}",
        f"- Restore safety: {restore_safe}",
        f"- Readiness: {payload.get('doctor_readiness_status', '')}",
        f"- Bundle: {payload.get('bundle_root', '') or '(not created)'}",
        f"- Manifest: {payload.get('manifest_file', '') or '(not created)'}",
        "",
        "Created:",
        f"- Config: {payload.get('config_file', '') or '(not written)'}",
        f"- Onboarding report: {payload.get('report_file', '') or '(not written)'}",
        f"- Bundle: {payload.get('bundle_root', '') or '(not created)'}",
        f"- Manifest: {payload.get('manifest_file', '') or '(not created)'}",
        "",
        "Token impact:",
        f"- Files included: {scale_profile.get('total_files', 0)}",
        f"- Source tokens: {metrics.get('estimated_token_count_source', 0)}",
        f"- Skeleton tokens: {metrics.get('estimated_token_count_skeleton', 0)}",
        f"- Estimated tokens saved: {saved_tokens}",
        f"- Estimated token savings: {savings_percent}%",
        f"- Direction: {token_result}",
        "",
        "Give to AI/IDE:",
        f"- Skeleton file: {handoff.get('skeleton_file', '') or '(not available)'}",
        f"- Bundle folder to keep: {handoff.get('bundle_root', '') or '(not available)'}",
        f"- Manifest for restore: {handoff.get('manifest_file', '') or '(not available)'}",
        f"- Guidance: {handoff.get('message', '') or 'feed the skeleton file to your AI or IDE'}",
        "",
        "Open bundle folder:",
        payload.get("open_command_text") or "(not available)",
        f"- Auto-open requested: {payload.get('open_requested', False)}",
        f"- Auto-open performed: {payload.get('open_performed', False)}",
        *( [f"- Open error: {open_error}"] if open_error else [] ),
        "",
        "Copy skeleton to clipboard:",
        payload.get("copy_command_text") or "(not available)",
        f"- Auto-copy requested: {payload.get('copy_requested', False)}",
        f"- Auto-copy performed: {payload.get('copy_performed', False)}",
        *( [f"- Copy error: {copy_error}"] if copy_error else [] ),
        "",
        "Experience:",
        f"- Speed: {experience.get('speed_status', '')} - {experience.get('speed_message', '')}",
        f"- Token savings: {experience.get('token_status', '')} - {experience.get('token_message', '')}",
        f"- Recommendation: {experience.get('recommendation', '')}",
        "",
        "Recommended setup:",
        f"- Mode: {start.get('recommended_mode', '')}",
        f"- Files included: {scale_profile.get('total_files', 0)}",
        f"- Source tokens: {metrics.get('estimated_token_count_source', 0)}",
        f"- Skeleton tokens: {metrics.get('estimated_token_count_skeleton', 0)}",
        f"- Estimated tokens saved: {saved_tokens}",
        f"- Estimated token savings: {savings_percent}%",
        "",
        "Timing:",
        f"- Total: {timings.get('total', 0)} ms",
        f"- Start/doctor: {timings.get('start', 0)} ms",
        f"- Bundle write: {timings.get('bundle', 0)} ms",
        "",
        "Copy/paste next:",
        primary_next or "(not available)",
        "",
        "Next commands:",
        f"- Inspect bundle: {payload.get('inspect_command_text', '') or '(not available)'}",
        f"- Restore later: {payload.get('restore_command_text', '') or '(not available)'}",
        "",
        "Next steps:",
    ]
    lines.extend(f"- {item}" for item in payload.get("next_steps") or [])
    if payload.get("fast_path"):
        lines.extend(
            [
                "",
                "Fast path:",
                "- skipped config recommendation/onboarding generation",
                "- kept sandbox restore safety verification enabled",
            ]
        )
    speed_tip = payload.get("speed_tip") or {}
    if speed_tip:
        lines.extend(
            [
                "",
                "Speed tip:",
                f"- {speed_tip.get('message', '')}",
                f"- Try: {speed_tip.get('suggested_command_text', '')}",
            ]
        )
    warnings = list(start.get("warnings") or [])
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item.get('message', '')}" for item in warnings[:3])
    if bundle.get("archive_path"):
        lines.extend(["", f"Zip archive: {bundle.get('archive_path')}"])
    return "\n".join(lines)


def _quick_output_dir_conflict_payload(output_dir: Path) -> dict[str, Any] | None:
    target = output_dir.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if not target.exists() or not target.is_dir() or not any(target.iterdir()):
        return None
    fix_command = _current_command_text_with_replaced_option("--output-dir", str(target.parent / f"{target.name}-new"))
    payload = {
        "status": "error",
        "entrypoint": "context-quick",
        "quick_status": "blocked",
        "error": {
            "code": "output_dir_not_empty",
            "message": f"context quick output directory already exists and is not empty: {target}",
            "exit_code": EXIT_USAGE,
            "details": {
                "output_dir": str(target),
                "recovery_steps": [
                    "choose a new --output-dir for this quick bundle",
                    "or move/delete the existing directory after confirming it is no longer needed",
                ],
                "fix_command_text": fix_command,
                "error_category": "invalid_usage",
            },
        },
        "restore_safe": False,
        "doctor_readiness_status": "",
        "start": {},
        "bundle": {},
        "bundle_root": "",
        "manifest_file": "",
        "handoff": {},
        "inspect_command_args": [],
        "inspect_command_text": "",
        "restore_command_args": [],
        "restore_command_text": "",
        "next_steps": [
            "choose a new --output-dir for this quick bundle",
            "rerun context quick after the output path is empty or changed",
        ],
    }
    payload["summary_text"] = _render_context_quick_summary(payload)
    return payload


def _build_quick_fast_start_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], float, int]:
    doctor_args = _clone_args(
        args,
        context_command="doctor",
        output_report_file=None,
        force=False,
    )
    doctor_started = time.perf_counter()
    doctor_payload, doctor_exit = _build_context_doctor_payload(
        doctor_args,
        include_compression_payload=True,
    )
    doctor_ms = _elapsed_ms(doctor_started)
    reusable_compression_payload = doctor_payload.pop("_compression_payload", None)
    metrics = dict(doctor_payload.get("metrics") or {})
    source_tokens = int(metrics.get("estimated_token_count_source") or 0)
    saved_tokens = int(metrics.get("estimated_tokens_saved") or 0)
    metrics["estimated_savings_percent"] = round((saved_tokens / source_tokens) * 100, 2) if source_tokens else 0.0
    recommended_config = dict(doctor_payload.get("recommended_config") or {})
    recommended_mode = " / ".join(
        str(item) for item in [
            doctor_payload.get("preset_id") or recommended_config.get("preset_id"),
            doctor_payload.get("focus_mode") or recommended_config.get("focus_mode"),
            doctor_payload.get("skeleton_density") or recommended_config.get("skeleton_density"),
        ] if item
    )
    restore_check = doctor_payload.get("restore_check") or {}
    restore_safe = restore_check.get("status") == "ok"
    action_plan = _build_readiness_action_plan(
        readiness_status=str(doctor_payload.get("readiness_status") or ""),
        restore_check=restore_check,
        warnings=list(doctor_payload.get("compression_warnings") or []),
        recommended_command_args=list(doctor_payload.get("recommended_command_args") or []),
    )
    start_payload = {
        "status": "ok" if doctor_exit == EXIT_OK else "error",
        "entrypoint": "context-start",
        "mode": "fast",
        "fast_path": True,
        "config_file": doctor_payload.get("config_file", ""),
        "config_written": False,
        "config_already_exists": bool(doctor_payload.get("config_file")),
        "report_file": "",
        "report_written": False,
        "report_already_exists": False,
        "recommended_config": recommended_config,
        "recommended_mode": recommended_mode,
        "recommended_command_args": list(doctor_payload.get("recommended_command_args") or []),
        "recommended_command_text": doctor_payload.get("recommended_command_text", ""),
        "next_command": doctor_payload.get("recommended_command_text", ""),
        "doctor_readiness_status": doctor_payload.get("readiness_status", ""),
        "restore_safe": restore_safe,
        "restore_check": restore_check,
        "source_scale_profile": doctor_payload.get("source_scale_profile") or {},
        "metrics": metrics,
        "warnings": list(doctor_payload.get("compression_warnings") or []),
        "explanations": list(doctor_payload.get("compression_explanations") or []),
        "recommendation": {},
        "doctor": doctor_payload,
        "timings_ms": {
            "config_recommend": 0.0,
            "doctor": doctor_ms,
            "doctor_compress": (doctor_payload.get("timings_ms") or {}).get("compress", 0.0),
            "doctor_restore_check": (doctor_payload.get("timings_ms") or {}).get("restore_check", 0.0),
            "total": doctor_ms,
        },
        "action_plan": action_plan,
        "next_steps": [item["message"] for item in action_plan],
    }
    start_payload["summary_text"] = _render_context_start_summary(start_payload)
    return start_payload, reusable_compression_payload if isinstance(reusable_compression_payload, dict) else {}, doctor_ms, doctor_exit


def _build_context_quick_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    total_started = time.perf_counter()
    output_dir = _opt_path(args, "output_dir")
    if output_dir is not None:
        conflict_payload = _quick_output_dir_conflict_payload(output_dir)
        if conflict_payload is not None:
            return conflict_payload, EXIT_USAGE

    fast_path = bool(getattr(args, "fast", False))
    if fast_path:
        start_payload, reusable_compression_payload, start_ms, start_exit = _build_quick_fast_start_payload(args)
    else:
        start_args = _clone_args(args, context_command="start", output_file=None)
        start_started = time.perf_counter()
        start_payload, start_exit = _build_context_start_payload(
            start_args,
            include_doctor_compression_payload=True,
        )
        start_ms = _elapsed_ms(start_started)
        reusable_compression_payload = start_payload.pop("_compression_payload", None)
    restore_safe = bool(start_payload.get("restore_safe"))
    if start_exit != EXIT_OK or not restore_safe:
        payload = {
            "status": "error",
            "entrypoint": "context-quick",
            "quick_status": "blocked",
            "restore_safe": restore_safe,
            "doctor_readiness_status": start_payload.get("doctor_readiness_status", ""),
            "start": start_payload,
            "bundle": {},
            "bundle_root": "",
            "manifest_file": "",
            "handoff": {},
            "open_command_text": "",
            "open_requested": bool(getattr(args, "open_bundle", False)),
            "open_performed": False,
            "open_error": "quick stopped before creating a bundle",
            "copy_command_text": "",
            "copy_requested": bool(getattr(args, "copy_command", False)),
            "copy_performed": False,
            "copy_error": "quick stopped before creating a bundle",
            "inspect_command_args": [],
            "inspect_command_text": "",
            "restore_command_args": [],
            "restore_command_text": "",
            "timings_ms": {
                "start": start_ms,
                "bundle": 0.0,
                "total": _elapsed_ms(total_started),
            },
            "next_steps": [
                "quick stopped before creating a bundle because restore safety is not ok",
                "review start.doctor.restore_check and rerun context quick after fixing the input/config",
            ],
        }
        payload["summary_text"] = _render_context_quick_summary(payload)
        return payload, start_exit if start_exit != EXIT_OK else EXIT_VALIDATION

    bundle_args = _clone_args(
        args,
        context_command="bundle",
        config_file=Path(str(start_payload.get("config_file"))) if start_payload.get("config_file") else getattr(args, "config_file", None),
        preset_id=None,
        focus_mode=None,
        skeleton_density=None,
        exclude_patterns=None,
        output_file=None,
    )
    config_file, config_values, context_defaults = _resolve_context_defaults(bundle_args)
    bundle_started = time.perf_counter()
    bundle_payload = build_context_bundle_payload(
        inline_text=_inline_text(bundle_args),
        text_file=_opt_path(bundle_args, "text_file"),
        input_file=_opt_path(bundle_args, "input_file"),
        input_dir=_opt_path(bundle_args, "input_dir"),
        preset_id=context_defaults["preset_id"],
        output_dir=_opt_path(bundle_args, "output_dir"),
        make_zip=bool(getattr(bundle_args, "zip_bundle", False)),
        candidate_inline_text=_candidate_inline_text(bundle_args),
        candidate_text_file=_opt_path(bundle_args, "candidate_text_file"),
        candidate_input_file=_opt_path(bundle_args, "candidate_input_file"),
        candidate_input_dir=_opt_path(bundle_args, "candidate_input_dir"),
        tokenizer_backend=getattr(bundle_args, "tokenizer_backend", None),
        tokenizer_model=getattr(bundle_args, "tokenizer_model", None),
        incremental=bool(getattr(bundle_args, "incremental", False)),
        base_commit=getattr(bundle_args, "base_commit", None),
        focus_mode=context_defaults["focus_mode"],
        skeleton_density=context_defaults["skeleton_density"],
        exclude_patterns=context_defaults["exclude_patterns"],
        config_file=config_file,
        config_values=config_values,
        compression_payload=reusable_compression_payload if isinstance(reusable_compression_payload, dict) else None,
    )
    bundle_ms = _elapsed_ms(bundle_started)
    bundle_root = str(bundle_payload.get("bundle_root") or "")
    manifest_file = str(Path(bundle_root) / "context_manifest.json") if bundle_root else ""
    handoff = _build_quick_handoff_payload(bundle_payload, bundle_root=bundle_root, manifest_file=manifest_file)
    open_command_text = _quick_open_command_text(bundle_root)
    open_performed, open_error = _maybe_open_quick_bundle(args, bundle_root=bundle_root)
    copy_command_text = _quick_copy_command_text(str(handoff.get("skeleton_file") or ""))
    copy_performed, copy_error = _maybe_copy_quick_skeleton(args, skeleton_file=str(handoff.get("skeleton_file") or ""))
    inspect_args = ["context", "inspect", "--package-file", manifest_file, "--json"] if manifest_file else []
    restore_args = _quick_restore_command_args(bundle_payload) if manifest_file else []
    timings_ms = {
        "start": start_ms,
        "start_config_recommend": (start_payload.get("timings_ms") or {}).get("config_recommend", 0.0),
        "start_doctor": (start_payload.get("timings_ms") or {}).get("doctor", 0.0),
        "bundle": bundle_ms,
        "total": _elapsed_ms(total_started),
    }
    experience = _build_quick_experience_payload(start_payload=start_payload, timings_ms=timings_ms, fast_path=fast_path)
    payload = {
        "status": "ok",
        "entrypoint": "context-quick",
        "quick_status": "ready",
        "fast_path": fast_path,
        "restore_safe": restore_safe,
        "doctor_readiness_status": start_payload.get("doctor_readiness_status", ""),
        "config_file": start_payload.get("config_file", ""),
        "config_written": bool(start_payload.get("config_written")),
        "report_file": start_payload.get("report_file", ""),
        "report_written": bool(start_payload.get("report_written")),
        "bundle_root": bundle_root,
        "manifest_file": manifest_file,
        "handoff": handoff,
        "open_command_text": open_command_text,
        "open_requested": bool(getattr(args, "open_bundle", False)),
        "open_performed": open_performed,
        "open_error": open_error,
        "copy_command_text": copy_command_text,
        "copy_requested": bool(getattr(args, "copy_command", False)),
        "copy_performed": copy_performed,
        "copy_error": copy_error,
        "experience": experience,
        "archive_path": bundle_payload.get("archive_path", ""),
        "inspect_command_args": inspect_args,
        "inspect_command_text": _format_cli_command(inspect_args),
        "restore_command_args": restore_args,
        "restore_command_text": _format_cli_command(restore_args),
        "start": start_payload,
        "bundle": bundle_payload,
        "timings_ms": timings_ms,
        "next_steps": [
            "share the bundle directory or zip with the downstream AI/IDE",
            "keep the manifest file so exact restore remains available",
            "use the restore command if you need to reconstruct the original input later",
        ],
    }
    payload["speed_tip"] = _build_quick_speed_tip(
        args,
        start_payload=start_payload,
        timings_ms=payload["timings_ms"],
        fast_path=fast_path,
    )
    payload["recent_file"] = _write_recent_record(args, payload)
    payload["summary_text"] = _render_context_quick_summary(payload)
    return payload, EXIT_OK


def _build_explain_action_plan(*, package_file: Path | None, inspect_payload: dict[str, Any]) -> list[dict[str, str]]:
    restore_args = ["context", "restore"]
    if package_file is not None:
        restore_args.extend(["--package-file", str(package_file.resolve())])
    mode = str(inspect_payload.get("compression_mode") or inspect_payload.get("restore_mode") or "")
    if mode == "text":
        restore_args.extend(["--output-file", str(Path.cwd() / str(inspect_payload.get("source_label") or "restored.txt"))])
    else:
        restore_args.extend(["--output-dir", str(Path.cwd() / "mcp-skeleton-restore")])
    return [
        {
            "step": "use_skeleton_for_ai_context",
            "status": "ready",
            "message": "use context_skeleton.mcp or skeleton_text as the AI-facing compressed context",
        },
        {
            "step": "keep_manifest_for_restore",
            "status": "ready",
            "message": "keep context_manifest.json with the restore package for byte-exact recovery",
        },
        {
            "step": "restore_when_needed",
            "status": "ready",
            "message": f"restore later with: {_format_cli_command(restore_args)}",
        },
    ]


def _render_context_explain_summary(payload: dict[str, Any]) -> str:
    inspect_payload = payload.get("inspect") or {}
    metrics = inspect_payload.get("metrics") or {}
    source_summary = inspect_payload.get("source_summary") or {}
    lines = [
        "MCP-Skeleton Explain",
        "",
        f"Status: {payload.get('explain_status', '')}",
        f"Safe to restore: {'yes' if payload.get('restore_available') else 'no'}",
        "",
        "What this is:",
        f"- Source: {inspect_payload.get('source_label', '')}",
        f"- Kind: {inspect_payload.get('source_kind', '')}",
        f"- Compression mode: {inspect_payload.get('compression_mode', '')}",
        f"- Focus/density: {inspect_payload.get('focus_mode', '')} / {inspect_payload.get('skeleton_density', '')}",
        "",
        "Why it is useful:",
        f"- Skeleton chars: {inspect_payload.get('skeleton_char_count', 0)}",
        f"- Restore bytes: {inspect_payload.get('restore_raw_byte_count', 0)}",
        f"- Estimated token direction: {metrics.get('estimated_token_direction', '')}",
        f"- Estimated tokens saved: {metrics.get('estimated_tokens_saved', '')}",
        "",
        "Source shape:",
        f"- Files: {source_summary.get('total_files', 0)}",
        f"- Text/code/binary: {source_summary.get('text_files', 0)} / {source_summary.get('code_files', 0)} / {source_summary.get('binary_files', 0)}",
        f"- Total chars: {source_summary.get('total_chars', 0)}",
        "",
        "Next steps:",
    ]
    action_plan = list(payload.get("action_plan") or [])
    lines.extend(f"- {item.get('message', '')}" for item in action_plan)
    return "\n".join(lines)


def _build_context_explain_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    package_file = _required_path(args, "package_file", "context explain requires --package-file")
    package_payload = load_context_package(package_file)
    inspect_payload = inspect_context_package(
        package_payload,
        tokenizer_backend=getattr(args, "tokenizer_backend", None),
        tokenizer_model=getattr(args, "tokenizer_model", None),
    )
    action_plan = _build_explain_action_plan(package_file=package_file, inspect_payload=inspect_payload)
    payload = {
        "status": "ok",
        "entrypoint": "context-explain",
        "explain_status": "ready" if inspect_payload.get("has_restore_package") else "watch",
        "package_file": str(package_file.resolve()),
        "restore_available": bool(inspect_payload.get("has_restore_package")),
        "inspect": inspect_payload,
        "action_plan": action_plan,
        "next_steps": [item["message"] for item in action_plan],
    }
    payload["summary_text"] = _render_context_explain_summary(payload)
    return payload, EXIT_OK


def _write_demo_project(source_dir: Path) -> None:
    (source_dir / "src").mkdir(parents=True, exist_ok=True)
    (source_dir / "docs").mkdir(parents=True, exist_ok=True)
    (source_dir / "tests").mkdir(parents=True, exist_ok=True)
    architecture_notes = "\n\n".join(
        [
            (
                f"## Feature Slice {idx}\n\n"
                "The product keeps a small public interface while preserving exact project state for later restore. "
                "Each workflow records a manifest, an inspectable skeleton, and a restore package so an AI assistant can "
                "reason over the project without receiving every raw byte up front. The important guarantee is simple: "
                "the skeleton can be compact, but the restore path must remain lossless and auditable.\n\n"
                "- Compress the relevant source tree before a long AI session.\n"
                "- Share the generated skeleton with the assistant or IDE.\n"
                "- Keep the manifest beside the bundle for exact restore.\n"
                "- Use doctor or quick when the user wants safe defaults."
            )
            for idx in range(1, 9)
        ]
    )
    handoff_notes = "\n".join(
        [
            f"- Task {idx}: keep the UX direct, explain the token impact, and verify restore safety before recommending the bundle."
            for idx in range(1, 31)
        ]
    )
    (source_dir / "README.md").write_text(
        "# Demo Project\n\n"
        "This demo project lets MCP-Skeleton show compression, restore safety, token impact, and next-step guidance "
        "without needing your own files first.\n\n"
        "It is intentionally larger than a hello-world example so the first run demonstrates useful token savings "
        "instead of a misleading tiny-project expansion.\n",
        encoding="utf-8",
    )
    (source_dir / "src" / "app.py").write_text(
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class Task:\n"
        "    title: str\n"
        "    done: bool = False\n\n"
        "def summarize(tasks: list[Task]) -> str:\n"
        "    complete = sum(1 for task in tasks if task.done)\n"
        "    return f'{complete}/{len(tasks)} tasks complete'\n",
        encoding="utf-8",
    )
    (source_dir / "src" / "pipeline.py").write_text(
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n"
        "from pathlib import Path\n\n\n"
        "@dataclass\n"
        "class BundlePlan:\n"
        "    input_dir: Path\n"
        "    output_dir: Path\n"
        "    focus_mode: str = 'imports'\n"
        "    density: str = 'adaptive'\n\n\n"
        "def build_steps(plan: BundlePlan) -> list[str]:\n"
        "    return [\n"
        "        'scan source tree',\n"
        "        f'compress with {plan.focus_mode}/{plan.density}',\n"
        "        'write manifest and skeleton',\n"
        "        'verify restore in a sandbox',\n"
        "    ]\n\n\n"
        "def describe(plan: BundlePlan) -> str:\n"
        "    steps = ', '.join(build_steps(plan))\n"
        "    return f'Bundle {plan.input_dir} into {plan.output_dir}: {steps}'\n",
        encoding="utf-8",
    )
    (source_dir / "src" / "restore.py").write_text(
        "from __future__ import annotations\n\n"
        "import hashlib\n"
        "from pathlib import Path\n\n\n"
        "def sha256_file(path: Path) -> str:\n"
        "    digest = hashlib.sha256()\n"
        "    with path.open('rb') as handle:\n"
        "        for chunk in iter(lambda: handle.read(1024 * 1024), b''):\n"
        "            digest.update(chunk)\n"
        "    return digest.hexdigest()\n\n\n"
        "def compare_files(left: Path, right: Path) -> bool:\n"
        "    return sha256_file(left) == sha256_file(right)\n",
        encoding="utf-8",
    )
    (source_dir / "docs" / "handoff.md").write_text(
        "# Handoff Notes\n\n"
        f"{handoff_notes}\n",
        encoding="utf-8",
    )
    (source_dir / "docs" / "architecture.md").write_text(
        "# Architecture Notes\n\n"
        f"{architecture_notes}\n",
        encoding="utf-8",
    )
    (source_dir / "tests" / "test_pipeline.py").write_text(
        "from pathlib import Path\n\n"
        "from src.pipeline import BundlePlan, build_steps\n\n\n"
        "def test_build_steps_mentions_restore() -> None:\n"
        "    plan = BundlePlan(input_dir=Path('src'), output_dir=Path('bundle'))\n"
        "    assert any('restore' in step for step in build_steps(plan))\n",
        encoding="utf-8",
    )


def _default_demo_root(args: argparse.Namespace) -> Path:
    output_dir = _opt_path(args, "output_dir")
    if output_dir is not None:
        return output_dir.resolve() if output_dir.is_absolute() else (Path.cwd() / output_dir).resolve()
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    return Path.cwd().resolve() / ".workspace_ail" / "demo_runs" / f"mcp-skeleton-demo-{stamp}"


def _render_context_demo_summary(payload: dict[str, Any]) -> str:
    quick = payload.get("quick") or {}
    start = quick.get("start") or {}
    metrics = start.get("metrics") or {}
    lines = [
        "MCP-Skeleton Demo",
        "",
        f"Status: {payload.get('demo_status', '')}",
        f"Demo root: {payload.get('demo_root', '')}",
        f"Restore safety: {'OK' if quick.get('restore_safe') else 'BLOCKED'}",
        "",
        "What happened:",
        f"- Created demo source: {payload.get('source_dir', '')}",
        f"- Created bundle: {quick.get('bundle_root', '')}",
        f"- Manifest: {quick.get('manifest_file', '')}",
        "",
        "Token impact:",
        f"- Source tokens: {metrics.get('estimated_token_count_source', 0)}",
        f"- Skeleton tokens: {metrics.get('estimated_token_count_skeleton', 0)}",
        f"- Estimated tokens saved: {metrics.get('estimated_tokens_saved', 0)}",
        f"- Estimated token savings: {metrics.get('estimated_savings_percent', 0)}%",
        "",
        "Try next:",
        f"- Inspect: {quick.get('inspect_command_text', '')}",
        f"- Restore: {quick.get('restore_command_text', '')}",
        "",
        "Use on your project:",
        "mcp-skeleton quick --input-dir .",
        "mcp-skeleton quick --fast --input-dir .",
    ]
    return "\n".join(lines)


def _build_context_demo_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    demo_root = _default_demo_root(args)
    source_dir = demo_root / "source"
    bundle_dir = demo_root / "bundle"
    if demo_root.exists() and any(demo_root.iterdir()) and not bool(getattr(args, "force", False)):
        raise ValueError(f"demo output directory already exists; use --force to overwrite: {demo_root}")
    if demo_root.exists() and bool(getattr(args, "force", False)):
        import shutil

        shutil.rmtree(demo_root)
    _write_demo_project(source_dir)
    quick_args = _clone_args(
        args,
        context_command="quick",
        fast=True,
        input_dir=source_dir,
        input_file=None,
        text_file=None,
        context_text=None,
        output_dir=bundle_dir,
        output_file=None,
        output_config_file=None,
        output_report_file=None,
        force=False,
    )
    quick_payload, quick_exit = _build_context_quick_payload(quick_args)
    manifest_file = str(quick_payload.get("manifest_file") or "")
    if manifest_file:
        demo_restore_args = [
            "context",
            "restore",
            "--package-file",
            manifest_file,
            "--output-dir",
            str(demo_root / "restore"),
        ]
        quick_payload["restore_command_args"] = demo_restore_args
        quick_payload["restore_command_text"] = _format_cli_command(demo_restore_args)
        quick_payload["summary_text"] = _render_context_quick_summary(quick_payload)
    payload = {
        "status": "ok" if quick_exit == EXIT_OK else "error",
        "entrypoint": "context-demo",
        "demo_status": "ready" if quick_exit == EXIT_OK else "blocked",
        "demo_root": str(demo_root),
        "source_dir": str(source_dir),
        "bundle_dir": str(bundle_dir),
        "quick": quick_payload,
        "next_steps": [
            "inspect the demo bundle",
            "restore the demo bundle",
            "run mcp-skeleton quick --input-dir . in your own project",
        ],
    }
    payload["summary_text"] = _render_context_demo_summary(payload)
    return payload, quick_exit


def _clone_args(args: argparse.Namespace, **updates: Any) -> argparse.Namespace:
    values = dict(vars(args))
    values.update(updates)
    return argparse.Namespace(**values)


def _default_start_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if _opt_path(args, "output_config_file") is not None:
        config_path = _opt_path(args, "output_config_file")
        assert config_path is not None
        if config_path.is_absolute():
            resolved_config = config_path
        else:
            resolved_config = (Path.cwd() / config_path).resolve()
    elif _opt_path(args, "input_dir") is not None:
        resolved_config = _opt_path(args, "input_dir").resolve() / ".mcp-skeleton.json"  # type: ignore[union-attr]
    elif _opt_path(args, "input_file") is not None:
        resolved_config = _opt_path(args, "input_file").resolve().parent / ".mcp-skeleton.json"  # type: ignore[union-attr]
    elif _opt_path(args, "text_file") is not None:
        resolved_config = _opt_path(args, "text_file").resolve().parent / ".mcp-skeleton.json"  # type: ignore[union-attr]
    else:
        resolved_config = Path.cwd().resolve() / ".mcp-skeleton.json"

    if _opt_path(args, "output_report_file") is not None:
        report_path = _opt_path(args, "output_report_file")
        assert report_path is not None
        resolved_report = report_path if report_path.is_absolute() else (Path.cwd() / report_path).resolve()
    else:
        resolved_report = resolved_config.parent / "mcp-skeleton-onboarding.md"
    return resolved_config, resolved_report


def _start_source_root(args: argparse.Namespace) -> Path:
    if _opt_path(args, "input_dir") is not None:
        return _opt_path(args, "input_dir").resolve()  # type: ignore[union-attr]
    if _opt_path(args, "input_file") is not None:
        return _opt_path(args, "input_file").resolve().parent  # type: ignore[union-attr]
    if _opt_path(args, "text_file") is not None:
        return _opt_path(args, "text_file").resolve().parent  # type: ignore[union-attr]
    return Path.cwd().resolve()


def _relative_start_exclude(path: Path, *, source_root: Path) -> str:
    try:
        return path.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError:
        return ""


def _append_unique_excludes(config: dict[str, Any], patterns: list[str]) -> dict[str, Any]:
    updated = dict(config)
    existing = [str(item) for item in (updated.get("exclude") or []) if str(item).strip()]
    seen = set(existing)
    for pattern in patterns:
        clean = str(pattern).strip()
        if clean and clean not in seen:
            existing.append(clean)
            seen.add(clean)
    updated["exclude"] = existing
    return updated


def _build_start_next_command_args(args: argparse.Namespace, *, config_path: Path) -> list[str]:
    command_args = ["context", "compress"]
    if _inline_text(args) is not None:
        return []
    if _opt_path(args, "input_dir") is not None:
        command_args.extend(["--input-dir", str(_opt_path(args, "input_dir").resolve())])  # type: ignore[union-attr]
    elif _opt_path(args, "input_file") is not None:
        command_args.extend(["--input-file", str(_opt_path(args, "input_file").resolve())])  # type: ignore[union-attr]
    elif _opt_path(args, "text_file") is not None:
        command_args.extend(["--text-file", str(_opt_path(args, "text_file").resolve())])  # type: ignore[union-attr]
    else:
        return []
    command_args.extend(["--config", str(config_path), "--json"])
    return command_args


def _build_context_start_payload(
    args: argparse.Namespace,
    *,
    include_doctor_compression_payload: bool = False,
) -> tuple[dict[str, Any], int]:
    total_started = time.perf_counter()
    config_path, report_path = _default_start_output_paths(args)
    source_root = _start_source_root(args)
    force = bool(getattr(args, "force", False))
    write_config = force or not config_path.exists()
    write_report = force or not report_path.exists()
    recommend_args = _clone_args(
        args,
        context_command="config",
        recommend=True,
        validate=False,
        config_action="",
        output_file=config_path if write_config else None,
        output_report_file=report_path if write_report else None,
    )
    recommend_started = time.perf_counter()
    recommend_payload, _recommend_exit = _build_context_config_payload(recommend_args)
    recommend_ms = _elapsed_ms(recommend_started)
    recommended_config = dict(recommend_payload.get("config") or {})
    self_excludes = [
        _relative_start_exclude(config_path, source_root=source_root),
        _relative_start_exclude(report_path, source_root=source_root),
    ]
    recommended_config = _append_unique_excludes(recommended_config, self_excludes)
    if write_config:
        written_path, written = _write_context_config_file(config_path, recommended_config, force=True)
        recommend_payload["config_file"] = written_path
        recommend_payload["written"] = written
        recommend_payload["config"] = recommended_config

    doctor_args = _clone_args(
        args,
        context_command="doctor",
        config_file=config_path if config_path.exists() or write_config else None,
        preset_id=recommended_config.get("preset") or getattr(args, "preset_id", None),
        focus_mode=recommended_config.get("focus_mode") or getattr(args, "focus_mode", None),
        skeleton_density=recommended_config.get("skeleton_density") or getattr(args, "skeleton_density", None),
        exclude_patterns=list(recommended_config.get("exclude") or getattr(args, "exclude_patterns", None) or []),
    )
    doctor_started = time.perf_counter()
    doctor_payload, doctor_exit = _build_context_doctor_payload(
        doctor_args,
        include_compression_payload=include_doctor_compression_payload,
    )
    doctor_ms = _elapsed_ms(doctor_started)
    reusable_compression_payload = doctor_payload.pop("_compression_payload", None)
    metrics = dict(doctor_payload.get("metrics") or {})
    source_tokens = int(metrics.get("estimated_token_count_source") or 0)
    saved_tokens = int(metrics.get("estimated_tokens_saved") or 0)
    estimated_savings_percent = round((saved_tokens / source_tokens) * 100, 2) if source_tokens else 0.0
    metrics["estimated_savings_percent"] = estimated_savings_percent
    recommended_command_args = _build_start_next_command_args(args, config_path=config_path)
    if not recommended_command_args:
        recommended_command_args = list(recommend_payload.get("recommended_command_args") or doctor_payload.get("recommended_command_args") or [])
    next_command = _format_cli_command(recommended_command_args)
    restore_check = doctor_payload.get("restore_check") or {}
    restore_safe = restore_check.get("status") == "ok"
    action_plan = _build_readiness_action_plan(
        readiness_status=str(doctor_payload.get("readiness_status") or ""),
        restore_check=restore_check,
        warnings=list(doctor_payload.get("compression_warnings") or []),
        recommended_command_args=recommended_command_args,
    )
    payload = {
        "status": "ok" if doctor_exit == EXIT_OK else "error",
        "entrypoint": "context-start",
        "mode": "start",
        "config_file": str(config_path),
        "config_written": bool(recommend_payload.get("written")),
        "config_already_exists": config_path.exists() and not bool(recommend_payload.get("written")),
        "report_file": str(report_path),
        "report_written": bool(recommend_payload.get("report_written")),
        "report_already_exists": report_path.exists() and not bool(recommend_payload.get("report_written")),
        "recommended_config": recommended_config,
        "recommended_mode": " / ".join(
            str(item) for item in [
                recommended_config.get("preset"),
                recommended_config.get("focus_mode"),
                recommended_config.get("skeleton_density"),
            ] if item
        ),
        "recommended_command_args": recommended_command_args,
        "recommended_command_text": next_command,
        "next_command": next_command,
        "doctor_readiness_status": doctor_payload.get("readiness_status", ""),
        "restore_safe": restore_safe,
        "restore_check": restore_check,
        "source_scale_profile": doctor_payload.get("source_scale_profile") or {},
        "metrics": metrics,
        "warnings": list(doctor_payload.get("compression_warnings") or []),
        "explanations": list(doctor_payload.get("compression_explanations") or []),
        "recommendation": recommend_payload,
        "doctor": doctor_payload,
        "timings_ms": {
            "config_recommend": recommend_ms,
            "doctor": doctor_ms,
            "doctor_compress": (doctor_payload.get("timings_ms") or {}).get("compress", 0.0),
            "doctor_restore_check": (doctor_payload.get("timings_ms") or {}).get("restore_check", 0.0),
            "total": 0.0,
        },
        "action_plan": action_plan,
        "next_steps": [
            item["message"] for item in action_plan
        ],
    }
    if include_doctor_compression_payload and reusable_compression_payload is not None:
        payload["_compression_payload"] = reusable_compression_payload
    payload["timings_ms"]["total"] = _elapsed_ms(total_started)
    payload["summary_text"] = _render_context_start_summary(payload)
    return payload, doctor_exit


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
            "2. Run `mcp-skeleton config --validate --config .mcp-skeleton.json --json`.",
            "3. Reuse `recommended_command_args` for a direct trial compression, or run `mcp-skeleton compress --input-dir . --json` and confirm the reported config file is used.",
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
    normalized_argv = _normalize_top_level_context_aliases(list(sys.argv[1:] if argv is None else argv))
    args = parser.parse_args(normalized_argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_USAGE
    if args.command == "version":
        return _emit_version_result(args)
    if args.command != "context":
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported top-level commands: context, version")
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
    supported = CONTEXT_SUBCOMMANDS
    if command not in supported:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported context subcommands: compress, restore, inspect, explain, apply-check, preset, config, init, install-hook, doctor, start, quick, recent, demo, bundle, patch, patch-apply")

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
        return _emit_simple_result(args, payload, text=_render_context_doctor_summary(payload), exit_code=exit_code)

    if command == "start":
        payload, exit_code = _build_context_start_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")), exit_code=exit_code)

    if command == "quick":
        payload, exit_code = _build_context_quick_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")), exit_code=exit_code)

    if command == "recent":
        payload, exit_code = _build_context_recent_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")), exit_code=exit_code)

    if command == "demo":
        payload, exit_code = _build_context_demo_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")), exit_code=exit_code)

    if command == "explain":
        payload, exit_code = _build_context_explain_payload(args)
        return _emit_simple_result(args, payload, text=str(payload.get("summary_text", "")), exit_code=exit_code)

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
    parser = argparse.ArgumentParser(
        prog="mcp-skeleton",
        description="MCP-Skeleton: lossless context compression, exact restore, patch, and replay workflows",
        epilog=(
            "Common shortcuts: mcp-skeleton quick --input-dir . | "
            "mcp-skeleton start --input-dir . | "
            "mcp-skeleton doctor --input-dir . | "
            "mcp-skeleton explain --package-file context_manifest.json"
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser("version", help="Show MCP-Skeleton version, Python, and install path details")
    version_parser.add_argument("--json", action="store_true")

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

    explain = context_subparsers.add_parser("explain", help="Explain one context bundle in human terms with next-step guidance")
    explain.add_argument("--package-file", dest="package_file", required=True)
    explain.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    explain.add_argument("--tokenizer-model", dest="tokenizer_model")
    explain.add_argument("--output-file", dest="output_file")
    explain.add_argument("--json", action="store_true")

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
    doctor.add_argument("--write-report", dest="output_report_file", help="Write a Markdown readiness report")
    doctor.add_argument("--force", action="store_true", help="Overwrite --write-report if it already exists")
    doctor.add_argument("--json", action="store_true")

    start = context_subparsers.add_parser("start", help="Zero-friction onboarding: recommend config, run doctor, and print the next compression command")
    start.add_argument("--text", dest="context_text")
    start.add_argument("--text-file", dest="text_file")
    start.add_argument("--input-file", dest="input_file")
    start.add_argument("--input-dir", dest="input_dir")
    start.add_argument("--config", dest="config_file", help="Read existing context defaults before recommending")
    start.add_argument("--preset", dest="preset_id")
    start.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    start.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    start.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from directory compression; can be repeated")
    start.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    start.add_argument("--tokenizer-model", dest="tokenizer_model")
    start.add_argument("--output-config-file", dest="output_config_file", help="Config path to write; defaults to .mcp-skeleton.json near the input")
    start.add_argument("--output-report-file", dest="output_report_file", help="Markdown onboarding report path; defaults to mcp-skeleton-onboarding.md near the config")
    start.add_argument("--force", action="store_true", help="Overwrite generated config/report files if they already exist")
    start.add_argument("--json", action="store_true")

    quick = context_subparsers.add_parser("quick", help="One-command start + doctor + bundle workflow for zero-friction use")
    quick.add_argument("--text", dest="context_text")
    quick.add_argument("--text-file", dest="text_file")
    quick.add_argument("--input-file", dest="input_file")
    quick.add_argument("--input-dir", dest="input_dir")
    quick.add_argument("--config", dest="config_file", help="Read existing context defaults before recommending")
    quick.add_argument("--preset", dest="preset_id")
    quick.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    quick.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    quick.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from directory compression; can be repeated")
    quick.add_argument("--incremental", action="store_true")
    quick.add_argument("--base-commit", dest="base_commit")
    quick.add_argument("--candidate-text", dest="candidate_text")
    quick.add_argument("--candidate-text-file", dest="candidate_text_file")
    quick.add_argument("--candidate-input-file", dest="candidate_input_file")
    quick.add_argument("--candidate-input-dir", dest="candidate_input_dir")
    quick.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    quick.add_argument("--tokenizer-model", dest="tokenizer_model")
    quick.add_argument("--fast", action="store_true", help="Skip config recommendation/onboarding generation while keeping restore safety checks enabled")
    quick.add_argument("--open", dest="open_bundle", action="store_true", help="Open the created bundle folder in Finder on macOS")
    quick.add_argument("--copy-command", dest="copy_command", action="store_true", help="Copy the generated skeleton text to the macOS clipboard with pbcopy")
    quick.add_argument("--zip", dest="zip_bundle", action="store_true")
    quick.add_argument("--output-config-file", dest="output_config_file", help="Config path to write; defaults to .mcp-skeleton.json near the input")
    quick.add_argument("--output-report-file", dest="output_report_file", help="Markdown onboarding report path; defaults to mcp-skeleton-onboarding.md near the config")
    quick.add_argument("--output-dir", dest="output_dir", help="Bundle directory to create; defaults under .workspace_ail/context_bundles")
    quick.add_argument("--output-file", dest="output_file", help="Write JSON or human summary to a file")
    quick.add_argument("--force", action="store_true", help="Overwrite generated config/report files if they already exist")
    quick.add_argument("--json", action="store_true")

    recent = context_subparsers.add_parser("recent", help="Show the most recent quick bundle for this project")
    recent.add_argument("--input-dir", dest="input_dir", help="Project directory whose .workspace_ail/recent_quick.json should be read; defaults to current directory")
    recent.add_argument("--input-file", dest="input_file", help="Read recent state next to this file")
    recent.add_argument("--text-file", dest="text_file", help="Read recent state next to this text file")
    recent.add_argument("--json", action="store_true")

    demo = context_subparsers.add_parser("demo", help="Run a one-command demo that creates a sample project, safe bundle, and restore guidance")
    demo.add_argument("--output-dir", dest="output_dir", help="Demo root directory; defaults under .workspace_ail/demo_runs")
    demo.add_argument("--force", action="store_true", help="Overwrite --output-dir if it already exists")
    demo.add_argument("--json", action="store_true")

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
