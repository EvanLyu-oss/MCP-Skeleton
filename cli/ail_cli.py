from __future__ import annotations

import argparse
import json
import sys
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
            candidates.append((path if path.is_dir() else path.parent) / ".mcp-skeleton.json")
            break
        candidates.append(Path.cwd() / ".mcp-skeleton.json")

    for path in candidates:
        if not path.exists():
            if explicit is not None:
                raise FileNotFoundError(str(path))
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON config file {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"config file must contain a JSON object: {path}")
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
    target.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target), True


def _build_context_config_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    supported = {
        "presets": sorted(CONTEXT_PRESETS.keys()),
        "focus_modes": sorted(CONTEXT_FOCUS_MODES),
        "skeleton_densities": sorted(SKELETON_DENSITY_MODES),
        "config_keys": list(CONTEXT_CONFIG_KEYS),
    }
    output_file = _opt_path(args, "output_file")
    force = bool(getattr(args, "force", False))
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
        suggested_excludes = list(context_defaults["exclude_patterns"] or compression_payload.get("preset_suggested_excludes") or [])
        recommended_config = {
            "preset": recommended.get("preset_id") or compression_payload.get("preset_id") or "generic",
            "focus_mode": recommended.get("focus_mode") or compression_payload.get("focus_mode") or "full",
            "skeleton_density": recommended.get("skeleton_density") or compression_payload.get("skeleton_density") or "adaptive",
            "exclude": suggested_excludes,
        }
        written_path, written = _write_context_config_file(output_file, recommended_config, force=force)
        return (
            {
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
                    "compression_warnings": compression_payload.get("compression_warnings") or [],
                    "compression_recommendations": compression_payload.get("compression_recommendations") or [],
                    "recommended_config": compression_payload.get("recommended_config") or {},
                },
                "supported": supported,
            },
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
    supported = {"compress", "restore", "inspect", "apply-check", "preset", "config", "bundle", "patch", "patch-apply"}
    if command not in supported:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported context subcommands: compress, restore, inspect, apply-check, preset, config, bundle, patch, patch-apply")

    if command == "preset":
        payload = build_context_preset_payload(getattr(args, "preset_id", None))
        return _emit_simple_result(args, payload)

    if command == "config":
        payload, exit_code = _build_context_config_payload(args)
        if _json_enabled(args):
            _print_json_payload(payload)
        else:
            print(json.dumps(payload.get("config", payload), indent=2, ensure_ascii=False))
        return exit_code

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
    compress.add_argument("--config", dest="config_file", help="Read context defaults from a .mcp-skeleton.json file")
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

    config = context_subparsers.add_parser("config", help="Emit or validate a .mcp-skeleton.json project defaults file")
    config.add_argument("--config", dest="config_file", help="Config file to validate; defaults to discovered .mcp-skeleton.json when --validate is used")
    config.add_argument("--validate", action="store_true", help="Validate an existing config file instead of emitting a template")
    config.add_argument("--recommend", action="store_true", help="Analyze an input and emit recommended project defaults")
    config.add_argument("--text", dest="context_text")
    config.add_argument("--input-file", dest="input_file", help="Discover .mcp-skeleton.json next to this file when validating")
    config.add_argument("--input-dir", dest="input_dir", help="Discover .mcp-skeleton.json inside this directory when validating")
    config.add_argument("--text-file", dest="text_file", help="Discover .mcp-skeleton.json next to this text file when validating")
    config.add_argument("--preset", dest="preset_id")
    config.add_argument("--focus-mode", dest="focus_mode", choices=["full", "tree", "imports", "symbols", "writing-outline"])
    config.add_argument("--skeleton-density", dest="skeleton_density", choices=["adaptive", "standard", "compact"])
    config.add_argument("--exclude", dest="exclude_patterns", action="append", help="Exclude a relative path or glob from recommendation analysis; can be repeated")
    config.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"])
    config.add_argument("--tokenizer-model", dest="tokenizer_model")
    config.add_argument("--output-file", dest="output_file", help="Write the default template to this path")
    config.add_argument("--force", action="store_true", help="Overwrite --output-file if it already exists")
    config.add_argument("--json", action="store_true")

    bundle = context_subparsers.add_parser("bundle", help="Export a full context bundle with compression, inspect, and optional apply-check artifacts")
    bundle.add_argument("--text", dest="context_text")
    bundle.add_argument("--text-file", dest="text_file")
    bundle.add_argument("--input-file", dest="input_file")
    bundle.add_argument("--input-dir", dest="input_dir")
    bundle.add_argument("--config", dest="config_file", help="Read context defaults from a .mcp-skeleton.json file")
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
