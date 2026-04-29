from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import glob
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .cloud_client import AILCloudClient, CloudClientError
from .context_compression import (
    apply_context_patch_payload,
    build_context_apply_check_payload,
    build_context_bundle_payload,
    build_context_compress_payload,
    build_context_patch_payload,
    build_context_patch_policy_template_payload,
    build_context_preset_payload,
    inspect_context_package,
    load_context_package,
    restore_context_from_package,
)
from .context import MANAGED_ROOTS, ProjectContext, USER_ROOTS
from .manifest_service import ManifestService
from .skill_bridge import load_repair_module
from .source_normalizer import normalize_for_user_source
from .sync_engine import SyncEngine, SyncError

EXIT_OK = 0
EXIT_GENERAL_ERROR = 1
EXIT_USAGE = 2
EXIT_VALIDATION = 3
EXIT_CONFLICT = 4
EXIT_REMOTE = 5
REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_REPO_ROOT = "/Users/carwynmac/ai-cl"
REPO_ROOT_STR = str(REPO_ROOT)
BUILD_WEBSITE_DELIVERY_ASSETS_SH = str((REPO_ROOT / "testing" / "build_website_delivery_assets.sh").resolve())
RUN_READINESS_SNAPSHOT_SH = str((REPO_ROOT / "testing" / "run_readiness_snapshot.sh").resolve())
RUN_RC_CHECKS_SH = str((REPO_ROOT / "testing" / "run_rc_checks.sh").resolve())


def _portable_payload(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(LEGACY_REPO_ROOT, REPO_ROOT_STR)
    if isinstance(value, dict):
        return {key: _portable_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_portable_payload(item) for item in value)
    return value


def _print_json_payload(payload: Any, *, file: Any = sys.stdout) -> None:
    print(json.dumps(_portable_payload(payload), indent=2, ensure_ascii=False), file=file)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_USAGE

    handlers = {
        "init": cmd_init,
        "generate": cmd_generate,
        "context": cmd_context,
        "website": cmd_website,
        "writing": cmd_writing,
        "rc-check": cmd_rc_check,
        "rc-go": cmd_rc_go,
        "workspace": cmd_workspace,
        "cloud": cmd_cloud,
        "compile": cmd_compile,
        "build": cmd_build,
        "project": cmd_project,
        "sync": cmd_sync,
        "diagnose": cmd_diagnose,
        "repair": cmd_repair,
        "conflicts": cmd_conflicts,
        "trial-run": cmd_trial_run,
    }
    handler = handlers[args.command]
    try:
        return handler(args)
    except FileNotFoundError as exc:
        if _json_enabled(args):
            _print_json_error("file_not_found", str(exc), exit_code=EXIT_GENERAL_ERROR)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_GENERAL_ERROR
    except CloudClientError as exc:
        if _json_enabled(args):
            _print_json_error("cloud_api_error", str(exc), exit_code=EXIT_REMOTE)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_REMOTE
    except SyncError as exc:
        if _json_enabled(args):
            _print_json_error(
                "sync_conflict",
                str(exc),
                exit_code=EXIT_CONFLICT,
                details=getattr(exc, "details", None) or None,
            )
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    except Exception as exc:  # pragma: no cover - safety net for CLI users
        if _json_enabled(args):
            _print_json_error("cli_error", str(exc), exit_code=EXIT_GENERAL_ERROR)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_GENERAL_ERROR



def cmd_init(args: argparse.Namespace) -> int:
    ctx = ProjectContext.discover(Path(args.path).resolve(), allow_uninitialized=True)
    created, existing = _initialize_project(ctx)

    print(f"Initialized AIL project at {ctx.root}")
    if created:
        print("Created:")
        for item in created:
            print(f"- {item}")
    if existing:
        print("Already existed:")
        for item in existing:
            print(f"- {item}")
    return EXIT_OK


def cmd_generate(args: argparse.Namespace) -> int:
    ctx = ProjectContext.discover()
    requirement = _read_requirement(args)
    if not requirement:
        print("error: requirement is empty", file=sys.stderr)
        return EXIT_USAGE
    client = AILCloudClient(base_url=args.base_url)
    generated_ail = client.generate_ail(requirement)
    normalized = normalize_for_user_source(generated_ail)
    notices = _generate_notices(client, normalized)
    ctx.source_file.parent.mkdir(parents=True, exist_ok=True)
    ctx.source_file.write_text(normalized.text.rstrip() + "\n", encoding="utf-8")
    print(f"Generated AIL and wrote {ctx.to_relative(ctx.source_file)}")
    for notice in notices:
        print(f"note: {notice}")
    return EXIT_OK


def cmd_context(args: argparse.Namespace) -> int:
    if getattr(args, "context_command", None) not in {"compress", "restore", "inspect", "apply-check", "preset", "bundle", "patch", "patch-apply"}:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported context subcommands: compress, restore, inspect, apply-check, preset, bundle, patch, patch-apply")

    if getattr(args, "context_command", None) == "preset":
        try:
            payload = build_context_preset_payload(getattr(args, "preset_id", None))
        except ValueError as exc:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
        if args.json:
            _print_json_payload(payload)
        else:
            selected = payload.get("selected_preset") or {}
            print("Context preset")
            print(f"- status: {payload['status']}")
            print(f"- preset_count: {payload.get('preset_count', 0)}")
            print(f"- selected_preset: {selected.get('preset_id', '')}")
            print(f"- selected_label: {selected.get('label', '')}")
            if selected.get("focus"):
                print("Focus:")
                for item in selected.get("focus", []):
                    print(f"- {item}")
            print("Available presets:")
            for item in payload.get("presets", []):
                print(f"- {item.get('preset_id', '')}: {item.get('label', '')}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "context_command", None) == "compress":
        inline_text = str(getattr(args, "context_text", "") or "").strip()
        text_file = Path(args.text_file).expanduser() if getattr(args, "text_file", None) else None
        input_file = Path(args.input_file).expanduser() if getattr(args, "input_file", None) else None
        input_dir = Path(args.input_dir).expanduser() if getattr(args, "input_dir", None) else None
        output_dir = Path(args.output_dir).expanduser() if getattr(args, "output_dir", None) else None
        try:
            payload = build_context_compress_payload(
                inline_text=inline_text if inline_text else None,
                text_file=text_file,
                input_file=input_file,
                input_dir=input_dir,
                preset_id=getattr(args, "preset_id", None),
                output_dir=output_dir,
                tokenizer_backend=getattr(args, "tokenizer_backend", None),
                tokenizer_model=getattr(args, "tokenizer_model", None),
            )
        except ValueError as exc:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_skeleton", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("skeleton_text", "")))
            sys.stdout.write(str(payload.get("skeleton_text", "")))
            return EXIT_OK
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("skeleton_text", "")))
            print("Context compress")
            print(f"- status: {payload['status']}")
            print(f"- preset_id: {payload.get('preset_id', '')}")
            print(f"- compression_mode: {payload.get('compression_mode', '')}")
            print(f"- source_kind: {payload.get('source_kind', '')}")
            print(f"- source_label: {payload.get('source_label', '')}")
            print(f"- skeleton_language: {payload.get('skeleton_language', '')}")
            print(f"- skeleton_char_count: {payload.get('skeleton_char_count', 0)}")
            print(f"- compression_ratio: {payload.get('compression_ratio', 0)}")
            metrics = payload.get("metrics") or {}
            if metrics:
                print(f"- estimated_token_count_source: {metrics.get('estimated_token_count_source', 0)}")
                print(f"- estimated_token_count_skeleton: {metrics.get('estimated_token_count_skeleton', 0)}")
                print(f"- token_estimate_backend: {metrics.get('token_estimate_backend', '')}")
                print(f"- token_estimate_basis: {metrics.get('token_estimate_basis', '')}")
                if metrics.get("token_estimate_model"):
                    print(f"- token_estimate_model: {metrics.get('token_estimate_model', '')}")
                print(f"- estimated_token_direction: {metrics.get('estimated_token_direction', '')}")
                print(f"- estimated_token_reduction_ratio: {metrics.get('estimated_token_reduction_ratio', 0)}")
            if payload.get("output_dir"):
                print(f"- output_dir: {payload.get('output_dir', '')}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "context_command", None) == "bundle":
        inline_text = str(getattr(args, "context_text", "") or "").strip()
        text_file = Path(args.text_file).expanduser() if getattr(args, "text_file", None) else None
        input_file = Path(args.input_file).expanduser() if getattr(args, "input_file", None) else None
        input_dir = Path(args.input_dir).expanduser() if getattr(args, "input_dir", None) else None
        output_dir = Path(args.output_dir).expanduser() if getattr(args, "output_dir", None) else None
        candidate_inline_text = str(getattr(args, "candidate_text", "") or "").strip()
        candidate_text_file = Path(args.candidate_text_file).expanduser() if getattr(args, "candidate_text_file", None) else None
        candidate_input_file = Path(args.candidate_input_file).expanduser() if getattr(args, "candidate_input_file", None) else None
        candidate_input_dir = Path(args.candidate_input_dir).expanduser() if getattr(args, "candidate_input_dir", None) else None
        try:
            payload = build_context_bundle_payload(
                inline_text=inline_text if inline_text else None,
                text_file=text_file,
                input_file=input_file,
                input_dir=input_dir,
                preset_id=getattr(args, "preset_id", None),
                output_dir=output_dir,
                make_zip=bool(getattr(args, "zip_bundle", False)),
                candidate_inline_text=candidate_inline_text if candidate_inline_text else None,
                candidate_text_file=candidate_text_file,
                candidate_input_file=candidate_input_file,
                candidate_input_dir=candidate_input_dir,
                tokenizer_backend=getattr(args, "tokenizer_backend", None),
                tokenizer_model=getattr(args, "tokenizer_model", None),
            )
        except ValueError as exc:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
        output_file = getattr(args, "output_file", None)
        exit_code = EXIT_OK if (payload.get("apply_check") is None or bool((payload.get("apply_check") or {}).get("apply_check_passed"))) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            print("Context bundle")
            print(f"- status: {payload['status']}")
            print(f"- preset_id: {payload.get('preset_id', '')}")
            print(f"- compression_mode: {payload.get('compression_mode', '')}")
            print(f"- source_kind: {payload.get('source_kind', '')}")
            print(f"- source_label: {payload.get('source_label', '')}")
            print(f"- bundle_root: {payload.get('bundle_root', '')}")
            print(f"- zip_enabled: {payload.get('zip_enabled', False)}")
            print(f"- apply_check_included: {payload.get('apply_check_included', False)}")
            print(f"- file_count: {payload.get('file_count', 0)}")
            if payload.get("archive_path"):
                print(f"- archive_path: {payload.get('archive_path', '')}")
            print("Files:")
            for label, path in (payload.get("files") or {}).items():
                print(f"- {label}: {path}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return exit_code

    if getattr(args, "context_command", None) == "patch":
        package_file = Path(str(getattr(args, "package_file", "") or "")).expanduser()
        if not str(package_file).strip():
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "context patch requires --package-file")
        inline_text = str(getattr(args, "context_text", "") or "").strip()
        text_file = Path(args.text_file).expanduser() if getattr(args, "text_file", None) else None
        input_file = Path(args.input_file).expanduser() if getattr(args, "input_file", None) else None
        input_dir = Path(args.input_dir).expanduser() if getattr(args, "input_dir", None) else None
        output_dir = Path(args.output_dir).expanduser() if getattr(args, "output_dir", None) else None
        try:
            package_payload = load_context_package(package_file)
            payload = build_context_patch_payload(
                package_payload=package_payload,
                source_package_file=package_file,
                inline_text=inline_text if inline_text else None,
                text_file=text_file,
                input_file=input_file,
                input_dir=input_dir,
                output_dir=output_dir,
                make_zip=bool(getattr(args, "zip_bundle", False)),
            )
        except ValueError as exc:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
        output_file = getattr(args, "output_file", None)
        exit_code = EXIT_OK if bool(payload.get("apply_check_passed")) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            print("Context patch")
            print(f"- status: {payload['status']}")
            print(f"- patch_mode: {payload.get('patch_mode', '')}")
            print(f"- preset_id: {payload.get('preset_id', '')}")
            print(f"- compression_mode: {payload.get('compression_mode', '')}")
            print(f"- source_kind: {payload.get('source_kind', '')}")
            print(f"- source_label: {payload.get('source_label', '')}")
            print(f"- candidate_source_kind: {payload.get('candidate_source_kind', '')}")
            print(f"- candidate_source_label: {payload.get('candidate_source_label', '')}")
            print(f"- patch_root: {payload.get('patch_root', '')}")
            print(f"- zip_enabled: {payload.get('zip_enabled', False)}")
            print(f"- apply_check_passed: {payload.get('apply_check_passed', False)}")
            print(f"- file_count: {payload.get('file_count', 0)}")
            print("Change counts:")
            for label, value in (payload.get("change_counts") or {}).items():
                print(f"- {label}: {value}")
            print("Files:")
            for label, path in (payload.get("files") or {}).items():
                print(f"- {label}: {path}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return exit_code

    if getattr(args, "context_command", None) == "patch-apply":
        patch_file = Path(str(getattr(args, "patch_file", "") or "")).expanduser()
        source_package_file = Path(args.source_package_file).expanduser() if getattr(args, "source_package_file", None) else None
        output_file = Path(args.output_file).expanduser() if getattr(args, "output_file", None) else None
        output_dir = Path(args.output_dir).expanduser() if getattr(args, "output_dir", None) else None
        policy_file = Path(args.policy_file).expanduser() if getattr(args, "policy_file", None) else None
        report_path = None
        if getattr(args, "output_report_file", None):
            report_path = Path(args.output_report_file).expanduser()
        elif getattr(args, "emit_policy_template", False) and output_file is not None:
            report_path = output_file
        if getattr(args, "emit_policy_template", False):
            try:
                payload = build_context_patch_policy_template_payload(
                    policy_mode=getattr(args, "policy_mode", None),
                    policy_file=policy_file,
                    allow_roots=list(getattr(args, "allow_roots", None) or []),
                    forbid_roots=list(getattr(args, "forbid_roots", None) or []),
                    block_removals=bool(getattr(args, "block_removals", False)),
                    block_additions=bool(getattr(args, "block_additions", False)),
                    require_apply_check_passed=bool(getattr(args, "require_apply_check_passed", False)),
                    max_changed_paths=getattr(args, "max_changed_paths", None),
                )
            except ValueError as exc:
                return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
            if args.json:
                if report_path is not None:
                    _write_cli_output_file(report_path, payload, as_json=True)
                _print_json_payload(payload)
            else:
                if report_path is not None:
                    _write_cli_output_file(report_path, str(payload.get("summary_text", "")))
                sys.stdout.write(str(payload.get("summary_text", "")))
            return EXIT_OK
        if not str(patch_file).strip():
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "context patch-apply requires --patch-file")
        try:
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
                policy_mode=getattr(args, "policy_mode", None),
                policy_file=policy_file,
                allow_roots=list(getattr(args, "allow_roots", None) or []),
                forbid_roots=list(getattr(args, "forbid_roots", None) or []),
                block_removals=bool(getattr(args, "block_removals", False)),
                block_additions=bool(getattr(args, "block_additions", False)),
                require_apply_check_passed=bool(getattr(args, "require_apply_check_passed", False)),
                max_changed_paths=getattr(args, "max_changed_paths", None),
            )
        except ValueError as exc:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
        exit_code = EXIT_OK if bool(payload.get("policy_passed", True)) else EXIT_VALIDATION
        if getattr(args, "emit_summary", False):
            if report_path is not None:
                _write_cli_output_file(report_path, str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if report_path is not None:
                _write_cli_output_file(report_path, payload, as_json=True)
            _print_json_payload(payload)
        else:
            if report_path is not None:
                _write_cli_output_file(report_path, str(payload.get("summary_text", "")))
            print("Context patch-apply")
            print(f"- status: {payload['status']}")
            print(f"- apply_mode: {payload.get('apply_mode', '')}")
            print(f"- patch_mode: {payload.get('patch_mode', '')}")
            print(f"- source_label: {payload.get('source_label', '')}")
            print(f"- policy_mode: {payload.get('policy_mode', '')}")
            print(f"- policy_passed: {payload.get('policy_passed', True)}")
            print(f"- applied_path_count: {len(payload.get('applied_paths') or [])}")
            print(f"- removed_path_count: {len(payload.get('removed_paths_applied') or [])}")
            if payload.get("policy_findings"):
                print("Policy findings:")
                for item in payload.get("policy_findings", []):
                    print(f"- {item}")
            print("Applied paths:")
            for item in payload.get("applied_paths", []):
                print(f"- {item}")
            if payload.get("removed_paths_applied"):
                print("Removed paths:")
                for item in payload.get("removed_paths_applied", []):
                    print(f"- {item}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return exit_code

    package_file = Path(str(getattr(args, "package_file", "") or "")).expanduser()
    if not str(package_file).strip():
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", f"context {getattr(args, 'context_command', '')} requires --package-file")
    try:
        package_payload = load_context_package(package_file)
        if getattr(args, "context_command", None) == "inspect":
            inspect_payload = inspect_context_package(
                package_payload,
                tokenizer_backend=getattr(args, "tokenizer_backend", None),
                tokenizer_model=getattr(args, "tokenizer_model", None),
            )
            output_file = getattr(args, "output_file", None)
            if getattr(args, "emit_summary", False):
                if output_file:
                    _write_cli_output_file(Path(output_file), str(inspect_payload.get("summary_text", "")))
                sys.stdout.write(str(inspect_payload.get("summary_text", "")))
                return EXIT_OK
            if args.json:
                if output_file:
                    _write_cli_output_file(Path(output_file), inspect_payload, as_json=True)
                _print_json_payload(inspect_payload)
            else:
                if output_file:
                    _write_cli_output_file(Path(output_file), str(inspect_payload.get("summary_text", "")))
                print("Context inspect")
                print(f"- status: {inspect_payload['status']}")
                print(f"- preset_id: {inspect_payload.get('preset_id', '')}")
                print(f"- compression_mode: {inspect_payload.get('compression_mode', '')}")
                print(f"- source_kind: {inspect_payload.get('source_kind', '')}")
                print(f"- source_label: {inspect_payload.get('source_label', '')}")
                print(f"- restore_mode: {inspect_payload.get('restore_mode', '')}")
                print(f"- skeleton_char_count: {inspect_payload.get('skeleton_char_count', 0)}")
                print(f"- compression_ratio: {inspect_payload.get('compression_ratio', 0)}")
                metrics = inspect_payload.get("metrics") or {}
                if metrics:
                    print(f"- estimated_token_count_source: {metrics.get('estimated_token_count_source', 0)}")
                    print(f"- estimated_token_count_skeleton: {metrics.get('estimated_token_count_skeleton', 0)}")
                    print(f"- token_estimate_backend: {metrics.get('token_estimate_backend', '')}")
                    print(f"- token_estimate_basis: {metrics.get('token_estimate_basis', '')}")
                    if metrics.get("token_estimate_model"):
                        print(f"- token_estimate_model: {metrics.get('token_estimate_model', '')}")
                    print(f"- estimated_token_direction: {metrics.get('estimated_token_direction', '')}")
                    print(f"- estimated_token_reduction_ratio: {metrics.get('estimated_token_reduction_ratio', 0)}")
                source_summary = inspect_payload.get("source_summary") or {}
                if source_summary.get("total_files") is not None:
                    print(f"- total_files: {source_summary.get('total_files', 0)}")
                tree_preview = inspect_payload.get("tree_preview") or []
                if tree_preview:
                    print("Tree preview:")
                    for item in tree_preview:
                        print(f"- {item}")
                print("Next:")
                for step in inspect_payload.get("next_steps", []):
                    print(f"- {step}")
            return EXIT_OK
        if getattr(args, "context_command", None) == "apply-check":
            inline_text = str(getattr(args, "context_text", "") or "").strip()
            text_file = Path(args.text_file).expanduser() if getattr(args, "text_file", None) else None
            input_file = Path(args.input_file).expanduser() if getattr(args, "input_file", None) else None
            input_dir = Path(args.input_dir).expanduser() if getattr(args, "input_dir", None) else None
            apply_payload = build_context_apply_check_payload(
                package_payload=package_payload,
                inline_text=inline_text if inline_text else None,
                text_file=text_file,
                input_file=input_file,
                input_dir=input_dir,
            )
            output_file = getattr(args, "output_file", None)
            exit_code = EXIT_OK if apply_payload.get("apply_check_passed") else EXIT_VALIDATION
            if getattr(args, "emit_summary", False):
                if output_file:
                    _write_cli_output_file(Path(output_file), str(apply_payload.get("summary_text", "")))
                sys.stdout.write(str(apply_payload.get("summary_text", "")))
                return exit_code
            if args.json:
                if output_file:
                    _write_cli_output_file(Path(output_file), apply_payload, as_json=True)
                _print_json_payload(apply_payload)
            else:
                if output_file:
                    _write_cli_output_file(Path(output_file), str(apply_payload.get("summary_text", "")))
                print("Context apply-check")
                print(f"- status: {apply_payload['status']}")
                print(f"- apply_check_mode: {apply_payload.get('apply_check_mode', '')}")
                print(f"- apply_check_passed: {apply_payload.get('apply_check_passed', False)}")
                print(f"- preset_id: {apply_payload.get('preset_id', '')}")
                print(f"- source_kind: {apply_payload.get('source_kind', '')}")
                print(f"- candidate_source_kind: {apply_payload.get('candidate_source_kind', '')}")
                print(f"- alignment_score: {apply_payload.get('alignment_score', 0)}")
                print(f"- alignment_band: {apply_payload.get('alignment_band', '')}")
                if apply_payload.get("strengths"):
                    print("Strengths:")
                    for item in apply_payload.get("strengths", []):
                        print(f"- {item}")
                if apply_payload.get("drift_findings"):
                    print("Drift findings:")
                    for item in apply_payload.get("drift_findings", []):
                        print(f"- {item}")
                if apply_payload.get("revision_targets"):
                    print("Revision targets:")
                    for item in apply_payload.get("revision_targets", []):
                        print(f"- {item}")
                print("Next:")
                for step in apply_payload.get("next_steps", []):
                    print(f"- {step}")
            return exit_code
        output_dir = Path(args.output_dir).expanduser() if getattr(args, "output_dir", None) else None
        output_file = Path(args.output_file).expanduser() if getattr(args, "output_file", None) else None
        restore_payload, restored_text = restore_context_from_package(
            package_payload,
            output_dir=output_dir,
            output_file=output_file,
        )
    except ValueError as exc:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", str(exc))
    output_path = getattr(args, "output_file", None)
    if getattr(args, "emit_text", False) or (restored_text is not None and not args.json):
        if restored_text is None:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "context restore can emit raw text only for text-based packages")
        if output_path:
            _write_cli_output_file(Path(output_path), restored_text)
        sys.stdout.write(restored_text)
        return EXIT_OK
    if args.json:
        if output_path:
            _write_cli_output_file(Path(output_path), restore_payload, as_json=True)
        _print_json_payload(restore_payload)
    else:
        if output_path:
            _write_cli_output_file(Path(output_path), json.dumps(_portable_payload(restore_payload), indent=2, ensure_ascii=False))
        print("Context restore")
        print(f"- status: {restore_payload['status']}")
        print(f"- restore_mode: {restore_payload.get('restore_mode', '')}")
        print(f"- source_kind: {restore_payload.get('source_kind', '')}")
        print(f"- source_label: {restore_payload.get('source_label', '')}")
        if restore_payload.get("restored_paths"):
            print("Restored paths:")
            for item in restore_payload.get("restored_paths", []):
                print(f"- {item}")
        print("Next:")
        for step in restore_payload.get("next_steps", []):
            print(f"- {step}")
    return EXIT_OK


def cmd_website(args: argparse.Namespace) -> int:
    if getattr(args, "website_command", None) == "preview":
        payload, exit_code = _build_website_preview_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website preview")
            print(f"- status: {payload['status']}")
            print(f"- asset_scope: {payload['asset_scope']}")
            print(f"- primary_target_label: {payload.get('primary_target_label', '')}")
            print(f"- preview_hint: {payload.get('preview_hint', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "run-inspect-command":
        payload, exit_code = _build_website_run_inspect_command_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website run-inspect-command")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload.get('route_taken', '')}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            inspection = payload.get("inspection") or {}
            if inspection:
                print(f"- inspection_kind: {inspection.get('kind', '')}")
                print(f"- inspection_exists: {inspection.get('exists', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "export-handoff":
        payload, exit_code = _build_website_export_handoff_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website export-handoff")
            print(f"- status: {payload['status']}")
            print(f"- asset_scope: {payload['asset_scope']}")
            print(f"- primary_target_label: {payload.get('primary_target_label', '')}")
            print(f"- recommended_website_action: {payload.get('recommended_website_action', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "inspect-asset":
        payload, exit_code = _build_website_inspect_asset_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website inspect-asset")
            print(f"- status: {payload['status']}")
            print(f"- asset_scope: {payload['asset_scope']}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            inspection = payload.get("inspection") or {}
            if inspection:
                print(f"- inspection_kind: {inspection.get('kind', '')}")
                print(f"- inspection_exists: {inspection.get('exists', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "open-asset":
        payload, exit_code = _build_website_open_asset_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website open-asset")
            print(f"- status: {payload['status']}")
            print(f"- asset_scope: {payload['asset_scope']}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            target = payload.get("target") or {}
            if target:
                print(f"- target_path: {target.get('path', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "go":
        payload, exit_code = _run_website_go(
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False))
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website go")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_website_action: {payload['executed_website_action']}")
            print(f"- result_status: {payload['status']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "summary":
        payload, exit_code = _build_website_summary_payload(
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False))
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website summary")
            print(f"- status: {payload['status']}")
            print(f"- supported_pack_count: {payload['supported_pack_count']}")
            print(f"- partial_pack_count: {payload['partial_pack_count']}")
            print(f"- assets_status: {payload['assets'].get('status', '')}")
            if payload["assets"].get("public_surface_note"):
                print(f"- public_surface_note: {payload['assets']['public_surface_note']}")
            print(f"- delivery_validation_status: {payload['delivery_validation'].get('status', '')}")
            print(f"- demo_pack_status: {payload['demo_pack_run'].get('status', '')}")
            print(f"- recommended_website_action: {payload['recommended_website_action']}")
            print(f"- recommended_website_reason: {payload['recommended_website_reason']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) == "assets":
        payload, exit_code = _build_website_assets_payload(
            pack_id=getattr(args, "pack_id", None),
            include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Website assets")
            print(f"- status: {payload['status']}")
            print(f"- asset_scope: {payload['asset_scope']}")
            print(f"- available_pack_count: {len(payload.get('available_pack_ids', []))}")
            if payload.get("public_surface_note"):
                print(f"- public_surface_note: {payload['public_surface_note']}")
            if payload.get("selected_pack"):
                print(f"- selected_pack: {payload['selected_pack'].get('pack')}")
                print(f"- selected_support_level: {payload['selected_pack'].get('support_level')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "website_command", None) != "check":
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported website subcommands: check, assets, open-asset, inspect-asset, preview, run-inspect-command, export-handoff, summary, go")

    requirement = _read_requirement(args)
    if not requirement:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "website check requires a non-empty requirement")

    payload, exit_code = _build_website_check_payload(
        requirement=requirement,
        base_url=args.base_url,
        project_dir=getattr(args, "project_dir", None),
        keep_existing=bool(getattr(args, "keep_existing", False)),
        include_experimental_dynamic=bool(getattr(args, "experimental_dynamic", False)),
    )

    if args.json:
        _print_json_payload(payload)
    else:
        print("Website check")
        print(f"- support_level: {payload['support_level']}")
        print(f"- website_pack: {payload['website_pack']}")
        print(f"- expected_profile: {payload['expected_profile']}")
        print(f"- delivery_decision: {payload['delivery_decision']}")
        print(f"- website_reason: {payload['website_reason']}")
        delivery_contract = payload.get("delivery_contract") or {}
        if delivery_contract:
            print(f"- delivery_surface: {delivery_contract.get('surface', '')}")
            print(f"- operator_positioning: {delivery_contract.get('operator_positioning', '')}")
            print(f"- stability_note: {delivery_contract.get('stability_note', '')}")
        print(f"- page_realization_mode: {payload['page_realization_mode']}")
        print(f"- routing_expectation: {payload['routing_expectation']}")
        print(f"- route_expectation_detail: {payload['route_expectation_detail']}")
        if payload.get("matched_signals"):
            print(f"- matched_signals: {', '.join(payload['matched_signals'])}")
        if payload.get("boundary_findings"):
            print("Boundary findings:")
            for item in payload["boundary_findings"]:
                print(f"- {item}")
        if delivery_contract.get("supported_capabilities"):
            print("Supported capabilities:")
            for item in delivery_contract["supported_capabilities"]:
                print(f"- {item}")
        if delivery_contract.get("unsupported_capabilities"):
            print("Unsupported capabilities:")
            for item in delivery_contract["unsupported_capabilities"]:
                print(f"- {item}")
        trial = payload.get("trial_result") or {}
        if trial:
            print(f"- trial_status: {trial.get('status', '')}")
            print(f"- detected_profile: {trial.get('detected_profile', '')}")
            print(f"- trial_project_path: {payload.get('trial_project_path', '')}")
        print("Next:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return exit_code


def cmd_writing(args: argparse.Namespace) -> int:
    if getattr(args, "writing_command", None) == "packs":
        payload, exit_code = _build_writing_packs_payload()
        if args.json:
            _print_json_payload(payload)
        else:
            print("Writing packs")
            print(f"- status: {payload['status']}")
            print(f"- available_pack_count: {payload.get('available_pack_count', 0)}")
            print(f"- public_surface_note: {payload.get('public_surface_note', '')}")
            print("Available packs:")
            for item in payload.get("packs", []):
                print(f"- {item.get('pack_id', '')}: {item.get('pack', '')} ({item.get('support_level', '')})")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) not in {"check", "intent", "scaffold", "brief", "expand", "review", "apply-check", "bundle"}:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported writing subcommands: check, packs, scaffold, brief, expand, review, apply-check, bundle, intent")

    if getattr(args, "writing_command", None) == "check":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing check requires a non-empty requirement")
        payload, exit_code = _build_writing_check_payload(requirement=requirement)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Writing check")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- support_level: {payload['support_level']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- writing_reason: {payload.get('writing_reason', '')}")
            print(f"- operator_positioning: {payload.get('safe_positioning', '')}")
            if payload.get("matched_signals"):
                print(f"- matched_signals: {', '.join(payload['matched_signals'])}")
            if payload.get("boundary_findings"):
                print("Boundary findings:")
                for item in payload["boundary_findings"]:
                    print(f"- {item}")
            contract = payload.get("writing_contract") or {}
            if contract:
                print(f"- delivery_surface: {contract.get('surface', '')}")
                print(f"- stability_note: {contract.get('stability_note', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "scaffold":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing scaffold requires a non-empty requirement")
        payload, exit_code = _build_writing_scaffold_payload(requirement=requirement)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Writing scaffold")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- scaffold_surface: {payload.get('scaffold_surface', '')}")
            print(f"- audience: {(payload.get('writing_intent') or {}).get('audience', '')}")
            scaffold = payload.get("scaffold") or {}
            if scaffold.get("headline"):
                print(f"- headline: {scaffold.get('headline', '')}")
            if scaffold.get("working_title"):
                print(f"- working_title: {scaffold.get('working_title', '')}")
            if scaffold.get("book_title"):
                print(f"- book_title: {scaffold.get('book_title', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "brief":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing brief requires a non-empty requirement")
        payload, exit_code = _build_writing_brief_payload(requirement=requirement)
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_prompt", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("model_prompt", "")))
            sys.stdout.write(str(payload.get("model_prompt", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("model_prompt", "")))
            print("Writing brief")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- brief_mode: {payload.get('brief_mode', '')}")
            print(f"- operator_positioning: {payload.get('operator_positioning', '')}")
            print(f"- scaffold_surface: {(payload.get('scaffold_summary') or {}).get('scaffold_surface', '')}")
            print(f"- intent_scope_status: {payload.get('intent_scope_status', '')}")
            print("Recommended commands:")
            for item in payload.get("recommended_commands", []):
                print(f"- {item}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "expand":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing expand requires a non-empty requirement")
        payload, exit_code = _build_writing_expand_payload(
            requirement=requirement,
            deep=bool(getattr(args, "deep", False)),
        )
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_text", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("expanded_text", "")))
            sys.stdout.write(str(payload.get("expanded_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("expanded_text", "")))
            print("Writing expand")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- expand_mode: {payload.get('expand_mode', '')}")
            print(f"- expand_depth: {payload.get('expand_depth', '')}")
            print(f"- expanded_unit_count: {payload.get('expanded_unit_count', 0)}")
            print(f"- intent_scope_status: {payload.get('intent_scope_status', '')}")
            if payload.get("expanded_text"):
                print("Preview:")
                print(payload["expanded_text"][:1200].rstrip())
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "review":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing review requires a non-empty requirement")
        draft_text = _read_review_text(args)
        if not draft_text:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing review requires draft text via --text, --text-file, or stdin")
        payload, exit_code = _build_writing_review_payload(requirement=requirement, draft_text=draft_text)
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_summary", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            print("Writing review")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- review_mode: {payload.get('review_mode', '')}")
            print(f"- alignment_score: {payload.get('alignment_score', 0)}")
            print(f"- alignment_band: {payload.get('alignment_band', '')}")
            print(f"- draft_char_count: {payload.get('draft_char_count', 0)}")
            print(f"- draft_paragraph_count: {payload.get('draft_paragraph_count', 0)}")
            if payload.get("strengths"):
                print("Strengths:")
                for item in payload.get("strengths", []):
                    print(f"- {item}")
            if payload.get("weak_spots"):
                print("Weak spots:")
                for item in payload.get("weak_spots", []):
                    print(f"- {item}")
            if payload.get("drift_findings"):
                print("Drift findings:")
                for item in payload.get("drift_findings", []):
                    print(f"- {item}")
            if payload.get("revision_targets"):
                print("Revision targets:")
                for item in payload.get("revision_targets", []):
                    print(f"- {item}")
            if payload.get("next_pass_prompt"):
                print("Next pass prompt:")
                print(payload["next_pass_prompt"][:1200].rstrip())
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "apply-check":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing apply-check requires a non-empty requirement")
        draft_text = _read_review_text(args)
        if not draft_text:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing apply-check requires draft text via --text, --text-file, or stdin")
        payload, exit_code = _build_writing_apply_check_payload(requirement=requirement, draft_text=draft_text)
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_summary", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            print("Writing apply-check")
            print(f"- status: {payload['status']}")
            print(f"- writing_pack: {payload['writing_pack']}")
            print(f"- expected_profile: {payload.get('expected_profile', '')}")
            print(f"- apply_check_mode: {payload.get('apply_check_mode', '')}")
            print(f"- apply_check_passed: {payload.get('apply_check_passed', False)}")
            print(f"- alignment_score: {payload.get('alignment_score', 0)}")
            print(f"- alignment_band: {payload.get('alignment_band', '')}")
            if payload.get("drift_findings"):
                print("Drift findings:")
                for item in payload.get("drift_findings", []):
                    print(f"- {item}")
            if payload.get("revision_targets"):
                print("Revision targets:")
                for item in payload.get("revision_targets", []):
                    print(f"- {item}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "writing_command", None) == "bundle":
        requirement = _read_requirement(args)
        if not requirement:
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "writing bundle requires a non-empty requirement")
        payload, exit_code = _build_writing_bundle_payload(
            requirement=requirement,
            draft_text=_read_review_text(args, allow_stdin=False),
            deep=bool(getattr(args, "deep", False)),
            output_dir=getattr(args, "output_dir", None),
            make_zip=bool(getattr(args, "zip_bundle", False)),
            copy_archive_path=bool(getattr(args, "copy_archive_path", False)),
            copy_summary=bool(getattr(args, "copy_summary", False)),
        )
        output_file = getattr(args, "output_file", None)
        if getattr(args, "emit_summary", False):
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            if output_file:
                _write_cli_output_file(Path(output_file), payload, as_json=True)
            _print_json_payload(payload)
        else:
            if output_file:
                _write_cli_output_file(Path(output_file), str(payload.get("summary_text", "")))
            print("Writing bundle")
            print(f"- status: {payload['status']}")
            print(f"- bundle_root: {payload.get('bundle_root', '')}")
            print(f"- writing_pack: {payload.get('writing_pack', '')}")
            print(f"- deep_enabled: {payload.get('deep_enabled', False)}")
            print(f"- review_source: {payload.get('review_source', '')}")
            print(f"- file_count: {payload.get('file_count', 0)}")
            if payload.get("archive_path"):
                print(f"- archive_path: {payload.get('archive_path', '')}")
            if "copied_archive_path_to_clipboard" in payload:
                print(f"- copied_archive_path_to_clipboard: {payload.get('copied_archive_path_to_clipboard', False)}")
            if payload.get("copy_archive_path_error"):
                print(f"- copy_archive_path_error: {payload.get('copy_archive_path_error', '')}")
            if "copied_summary_to_clipboard" in payload:
                print(f"- copied_summary_to_clipboard: {payload.get('copied_summary_to_clipboard', False)}")
            if payload.get("copy_summary_error"):
                print(f"- copy_summary_error: {payload.get('copy_summary_error', '')}")
            print("Files:")
            for label, path in (payload.get("files") or {}).items():
                print(f"- {label}: {path}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return exit_code

    payload, exit_code = _build_writing_intent_payload(
        audience=getattr(args, "audience", None),
        format_mode=getattr(args, "format_mode", None),
        genre=getattr(args, "genre", None),
        style_direction=getattr(args, "style_direction", None),
        localization_mode=getattr(args, "localization_mode", None),
        target_length=getattr(args, "target_length", None),
        notes=getattr(args, "notes", None),
        style_keywords=getattr(args, "style_keyword", None),
        tone_keywords=getattr(args, "tone_keyword", None),
        narrative_constraints=getattr(args, "narrative_constraint", None),
        reset=bool(getattr(args, "reset", False)),
    )
    if args.json:
        _print_json_payload(payload)
    else:
        print("Writing intent")
        print(f"- status: {payload['status']}")
        print(f"- writing_intent_path: {payload.get('writing_intent_path', '')}")
        print(f"- action: {payload.get('action', '')}")
        intent = payload.get("writing_intent") or {}
        print(f"- audience: {intent.get('audience', '')}")
        print(f"- format_mode: {intent.get('format_mode', '')}")
        print(f"- genre: {intent.get('genre', '')}")
        print(f"- style_direction: {intent.get('style_direction', '')}")
        print(f"- localization_mode: {intent.get('localization_mode', '')}")
        print(f"- target_length: {intent.get('target_length', '')}")
        print(f"- style_keywords: {', '.join(intent.get('style_keywords') or [])}")
        print(f"- tone_keywords: {', '.join(intent.get('tone_keywords') or [])}")
        print(f"- narrative_constraints: {', '.join(intent.get('narrative_constraints') or [])}")
        print(f"- notes: {intent.get('notes', '')}")
        print("Next:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return exit_code


def cmd_rc_check(args: argparse.Namespace) -> int:
    refresh_result = _refresh_rc_check_sources() if getattr(args, "refresh", False) else None
    payload = _build_rc_check_payload(base_url=args.base_url)
    if refresh_result is not None:
        payload["refresh"] = refresh_result
    if args.json:
        _print_json_payload(payload)
    else:
        print("RC check")
        print(f"- rc_status: {payload['rc']['status']}")
        print(f"- readiness_status: {payload['readiness']['status']}")
        print(f"- benchmark_release_baseline_ok: {payload['benchmark']['release_baseline_ok']}")
        print(f"- benchmark_release_decision: {payload['benchmark']['release_decision']}")
        if refresh_result is not None:
            print(f"- refresh_status: {refresh_result['status']}")
            print(f"- refresh_reason: {refresh_result['reason']}")
        print(f"- recommended_release_action: {payload['recommended_release_action']}")
        print(f"- recommended_release_reason: {payload['recommended_release_reason']}")
        print("Next:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return EXIT_OK if payload["status"] == "ok" else EXIT_VALIDATION


def cmd_rc_go(args: argparse.Namespace) -> int:
    refresh_result = _refresh_rc_check_sources() if getattr(args, "refresh", False) else None
    payload, exit_code = _run_rc_go(base_url=args.base_url)
    if refresh_result is not None:
        payload["refresh"] = refresh_result
    if args.json:
        _print_json_payload(payload)
    else:
        print("RC go")
        print(f"- route_taken: {payload['route_taken']}")
        print(f"- route_reason: {payload['route_reason']}")
        print(f"- executed_release_action: {payload['executed_release_action']}")
        if refresh_result is not None:
            print(f"- refresh_status: {refresh_result['status']}")
            print(f"- refresh_reason: {refresh_result['reason']}")
        print(f"- result_status: {payload['status']}")
        result_payload = payload.get("result") or {}
        if result_payload.get("project_path"):
            print(f"- project_path: {result_payload.get('project_path')}")
        if result_payload.get("build_id"):
            print(f"- build_id: {result_payload.get('build_id')}")
        if result_payload.get("managed_files_written") is not None:
            print(f"- managed_files_written: {result_payload.get('managed_files_written')}")
        print("Next:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return exit_code


def cmd_workspace(args: argparse.Namespace) -> int:
    if getattr(args, "workspace_command", None) == "hooks":
        payload = _build_workspace_hooks_payload()
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace hooks")
            print(f"- repo_root: {payload['repo_root']}")
            print(f"- output_projects_root: {payload['output_projects_root']}")
            print(f"- scanned_project_count: {payload['scanned_project_count']}")
            print(f"- catalog_project_count: {payload['catalog_project_count']}")
            print(f"- page_count: {payload['page_count']}")
            print(f"- section_hook_count: {payload['section_hook_count']}")
            print(f"- slot_hook_count: {payload['slot_hook_count']}")
            if payload.get("current_project_included"):
                print(f"- current_project_root: {payload.get('current_project_root', '')}")
            if payload.get("recent_hook_project"):
                print(f"- recent_hook_project: {payload['recent_hook_project']}")
            if payload.get("preferred_workspace_hook_command"):
                print(f"- preferred_workspace_hook_command: {payload['preferred_workspace_hook_command']}")
            if payload.get("preferred_workspace_hook_reason"):
                print(f"- preferred_workspace_hook_reason: {payload['preferred_workspace_hook_reason']}")
            if payload["projects"]:
                print("Projects:")
                for item in payload["projects"][:10]:
                    print(
                        "- "
                        f"{item['project_name']} "
                        f"(pages={item['hook_catalog']['page_count']} "
                        f"sections={item['hook_catalog']['section_hook_count']} "
                        f"slots={item['hook_catalog']['slot_hook_count']})"
                    )
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "workspace_command", None) == "hook-guide":
        payload, exit_code = _build_workspace_hook_guide_payload()
        preferred_command = str(payload.get("preferred_workspace_hook_command") or "").strip()
        preferred_run_command = str(payload.get("preferred_workspace_hook_run_command") or preferred_command or "").strip()
        if getattr(args, "run_command", False):
            payload["run_command"] = preferred_run_command or None
            payload["run_command_requires_confirmation"] = True
            payload["run_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_command_confirm_command"] = f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace hook-guide --run-command --yes --json"
            if getattr(args, "yes", False):
                if preferred_run_command:
                    ran_ok, run_stdout, run_stderr, run_exit_code, run_result = _run_shell_command(preferred_run_command)
                    payload["ran_command"] = ran_ok
                    payload["run_command_exit_code"] = run_exit_code
                    payload["run_command_stdout"] = run_stdout
                    payload["run_command_stderr"] = run_stderr
                    payload["run_result"] = run_result
                else:
                    payload["ran_command"] = False
                    payload["run_command_exit_code"] = EXIT_USAGE
                    payload["run_command_stdout"] = ""
                    payload["run_command_stderr"] = ""
                    payload["run_result"] = None
                    payload["run_command_warning"] = "No preferred workspace hook-guide command was available to execute."
            else:
                payload["ran_command"] = False
                payload["run_command_exit_code"] = EXIT_OK
                payload["run_command_stdout"] = ""
                payload["run_command_stderr"] = ""
                payload["run_result"] = None
                payload["run_command_warning"] = "Confirmation required. Re-run with --yes to execute the preferred workspace hook-guide command."
        if getattr(args, "run_command", False) and args.json:
            _print_json_payload(payload)
            return int(payload.get("run_command_exit_code", exit_code)) if payload.get("run_command_confirmed") else exit_code
        if getattr(args, "run_command", False):
            if payload.get("run_command_confirmed"):
                if payload.get("ran_command"):
                    print("Workspace hook-guide command executed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_result") and isinstance(payload["run_result"], dict):
                        result = payload["run_result"]
                        print(f"- run_result_entrypoint: {result.get('entrypoint', '')}")
                else:
                    print("Workspace hook-guide command execution failed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_command_stderr"):
                        print(f"- run_command_stderr: {payload['run_command_stderr']}")
                return int(payload.get("run_command_exit_code", exit_code))
            print("Workspace hook-guide command ready")
            print(f"- run_command: {payload.get('run_command', '')}")
            if payload.get("run_command_warning"):
                print(f"- run_command_warning: {payload['run_command_warning']}")
            if payload.get("run_command_confirm_command"):
                print(f"- run_command_confirm_command: {payload['run_command_confirm_command']}")
            return exit_code
        if getattr(args, "emit_shell", False):
            if preferred_command:
                print(preferred_command)
                return EXIT_OK
            print("No preferred workspace hook-guide command was available.")
            return EXIT_USAGE
        if getattr(args, "copy_command", False):
            copied_ok, copied_error = _copy_text_to_clipboard(preferred_command) if preferred_command else (False, "No preferred workspace hook-guide command was available to copy.")
            if copied_ok:
                print("Workspace hook-guide command copied")
                print(f"- copied_command: {preferred_command}")
                return EXIT_OK
            print("Workspace hook-guide command copy failed")
            if copied_error:
                print(f"- copy_command_error: {copied_error}")
            if preferred_command:
                print(f"- fallback_command: {preferred_command}")
            return EXIT_USAGE
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace hook-guide")
            print(f"- repo_root: {payload['repo_root']}")
            if payload.get("recommended_project_name"):
                print(f"- recommended_project_name: {payload['recommended_project_name']}")
            if payload.get("preferred_workspace_hook_command"):
                print(f"- human_next_command: {payload['preferred_workspace_hook_command']}")
            if payload.get("preferred_workspace_hook_run_command"):
                print(f"- runnable_next_command: {payload['preferred_workspace_hook_run_command']}")
            if payload.get("preferred_workspace_hook_reason"):
                print(f"- human_next_reason: {payload['preferred_workspace_hook_reason']}")
            if payload.get("preferred_workspace_hook_run_command") and payload.get("preferred_workspace_hook_command") and payload.get("preferred_workspace_hook_run_command") != payload.get("preferred_workspace_hook_command"):
                print("- runnable_next_reason: The runnable path stays on a JSON-safe suggestion route so it can be executed and parsed reliably.")
            print(f"- cheat_sheet_path: {payload['cheat_sheet_path']}")
            print("Guide paths:")
            for section in payload.get("guide_sections") or []:
                print(f"- {section.get('label', '')}: {section.get('summary', '')}")
                if section.get("command"):
                    print(f"  {section['command']}")
            print("Next:")
            if payload.get("preferred_workspace_hook_command"):
                print(f"- run {payload['preferred_workspace_hook_command']}")
            if payload.get("preferred_workspace_hook_run_command"):
                print(f"- run {payload['preferred_workspace_hook_run_command']}")
            print(f"- inspect {payload['cheat_sheet_path']}")
        return exit_code

    if getattr(args, "workspace_command", None) == "export-handoff":
        payload, exit_code = _build_workspace_export_handoff_payload(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace export-handoff")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- primary_target_label: {payload.get('primary_target_label', '')}")
            print(f"- preview_hint: {payload.get('preview_hint', '')}")
            print(f"- recommended_workspace_action: {payload.get('recommended_workspace_action', '')}")
            primary_inspection = payload.get("primary_inspection") or {}
            if primary_inspection.get("kind") == "directory":
                print(f"- primary_entry_count: {primary_inspection.get('entry_count', 0)}")
            elif primary_inspection.get("kind") == "file":
                print(f"- primary_line_count: {primary_inspection.get('line_count', 0)}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "open-target":
        payload, exit_code = _build_workspace_open_target_payload(
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace open-target")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            if payload["status"] == "ok":
                print(f"- resolved_label: {payload['resolved_label']}")
                print(f"- target_path: {payload['target']['path']}")
                print(f"- target_kind: {payload['target']['kind']}")
                print(f"- target_exists: {str(payload['target']['exists']).lower()}")
                print(f"- inspect_command: {payload['inspect_command']}")
            else:
                print(f"- message: {payload['message']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "inspect-target":
        payload, exit_code = _build_workspace_inspect_target_payload(
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace inspect-target")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload.get('route_taken', '')}")
            print(f"- route_reason: {payload.get('route_reason', '')}")
            if payload["status"] == "ok":
                print(f"- resolved_label: {payload.get('resolved_label', '')}")
                print(f"- target_path: {payload.get('target', {}).get('path', '')}")
                print(f"- target_kind: {payload.get('target', {}).get('kind', '')}")
                inspection = payload.get("inspection") or {}
                if inspection.get("kind") == "file":
                    print(f"- line_count: {inspection.get('line_count', 0)}")
                    print(f"- size_bytes: {inspection.get('size_bytes', 0)}")
                    preview = inspection.get("content_preview") or ""
                    if preview:
                        print("Preview:")
                        print(preview)
                elif inspection.get("kind") == "directory":
                    print(f"- entry_count: {inspection.get('entry_count', 0)}")
                    print("Entries:")
                    for item in inspection.get("entries", []):
                        print(f"- {item['name']} [{item['kind']}]")
                else:
                    print(f"- exists: {str(inspection.get('exists', False)).lower()}")
            else:
                print(f"- message: {payload.get('message', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "run-inspect-command":
        payload, exit_code = _build_workspace_run_inspect_command_payload(
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace run-inspect-command")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_inspect_command: {payload.get('executed_inspect_command', '')}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            inspection = payload.get("inspection") or {}
            if inspection.get("kind") == "file":
                print(f"- line_count: {inspection.get('line_count', 0)}")
            elif inspection.get("kind") == "directory":
                print(f"- entry_count: {inspection.get('entry_count', 0)}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "preview":
        payload, exit_code = _build_workspace_preview_payload(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace preview")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- preview_hint: {payload['preview_hint']}")
            primary = payload["preview_handoff"]["primary_target"]
            print(f"- primary_preview_target: {primary['label']} -> {primary['path']}")
            print(f"- recommended_workspace_action: {payload['recommended_workspace_action']}")
            print("Open targets:")
            for item in payload["open_targets"]:
                print(f"- {item['label']}: {item['path']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "doctor":
        payload, exit_code = _build_workspace_doctor_payload(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace doctor")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- recommended_workspace_action: {payload['recommended_workspace_action']}")
            print(f"- recommended_workspace_reason: {payload['recommended_workspace_reason']}")
            for finding in payload.get("findings", []):
                print(f"- finding: {finding}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "continue":
        payload, exit_code = _run_workspace_continue(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace continue")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_workspace_action: {payload['executed_workspace_action']}")
            print(f"- recommended_workspace_reason: {payload['recommended_workspace_reason']}")
            print(f"- result_status: {payload['status']}")
            result_payload = payload.get("result") or {}
            if result_payload.get("project_path"):
                print(f"- project_path: {result_payload.get('project_path')}")
            if result_payload.get("project_root"):
                print(f"- project_root: {result_payload.get('project_root')}")
            if result_payload.get("build_id"):
                print(f"- build_id: {result_payload.get('build_id')}")
            if result_payload.get("managed_files_written") is not None:
                print(f"- managed_files_written: {result_payload.get('managed_files_written')}")
            if payload.get("preview_hint"):
                print(f"- preview_hint: {payload['preview_hint']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "summary":
        payload = _build_workspace_summary_payload(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace summary")
            print(f"- repo_root: {payload['repo_root']}")
            print(f"- cwd: {payload['cwd']}")
            print(f"- inside_ail_project: {str(payload['inside_ail_project']).lower()}")
            print(f"- readiness_status: {payload['readiness']['status']}")
            print(f"- rc_status: {payload['rc']['status']}")
            print(f"- trial_batch_status: {payload['latest_trial_batch']['status']}")
            hook_catalogs = payload.get("hook_catalogs") or {}
            print(
                "- hook_catalogs: "
                f"projects={hook_catalogs.get('catalog_project_count', 0)} "
                f"pages={hook_catalogs.get('page_count', 0)} "
                f"sections={hook_catalogs.get('section_hook_count', 0)} "
                f"slots={hook_catalogs.get('slot_hook_count', 0)}"
            )
            if hook_catalogs.get("recommended_hook_suggest_command"):
                print(f"- recommended_hook_suggest_command: {hook_catalogs['recommended_hook_suggest_command']}")
            if hook_catalogs.get("recommended_workspace_hook_suggest_command"):
                print(f"- recommended_workspace_hook_suggest_command: {hook_catalogs['recommended_workspace_hook_suggest_command']}")
            if hook_catalogs.get("recommended_workspace_hook_pick_command"):
                print(f"- recommended_workspace_hook_pick_command: {hook_catalogs['recommended_workspace_hook_pick_command']}")
            if hook_catalogs.get("recent_hook_project"):
                print(f"- recent_hook_project: {hook_catalogs['recent_hook_project']}")
            if hook_catalogs.get("recent_workspace_hook_suggest_command"):
                print(f"- recent_workspace_hook_suggest_command: {hook_catalogs['recent_workspace_hook_suggest_command']}")
            if hook_catalogs.get("recent_workspace_hook_pick_command"):
                print(f"- recent_workspace_hook_pick_command: {hook_catalogs['recent_workspace_hook_pick_command']}")
            print(f"- recommended_workspace_action: {payload['recommended_workspace_action']}")
            print(f"- recommended_workspace_reason: {payload['recommended_workspace_reason']}")
            if payload.get("current_project"):
                project = payload["current_project"]
                print(f"- current_project_id: {project.get('project_id', '')}")
                print(f"- current_project_primary_action: {project.get('recommended_primary_action', '')}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "workspace_command", None) == "hook-init":
        if getattr(args, "run_command", False) and getattr(args, "run_open_command", False):
            return _emit_command_error(
                args,
                EXIT_USAGE,
                "invalid_usage",
                "choose only one of --run-command or --run-open-command",
            )
        payload, exit_code = _run_workspace_hook_init(
            hook_name=getattr(args, "hook_name", ""),
            project_name=getattr(args, "project_name", None),
            use_recommended_project=getattr(args, "use_recommended_project", False),
            use_last_project=getattr(args, "use_last_project", False),
            follow_recommended=getattr(args, "follow_recommended", False),
            template_kind=getattr(args, "template", "auto"),
            suggest=getattr(args, "suggest", False),
            last_suggest=getattr(args, "last_suggest", False),
            open_catalog=getattr(args, "open_catalog", False),
            page_key_filter=getattr(args, "page_key", None),
            section_key_filter=getattr(args, "section_key", None),
            slot_key_filter=getattr(args, "slot_key", None),
            reuse_last_suggest=getattr(args, "reuse_last_suggest", False),
            pick=getattr(args, "pick", False),
            pick_recommended=getattr(args, "pick_recommended", False),
            pick_index=getattr(args, "pick_index", None),
            dry_run=getattr(args, "dry_run", False),
            force=getattr(args, "force", False),
        )
        workspace_result_payload = payload.get("result") or {}
        workspace_emit_confirm_command = (
            payload.get("rerun_without_dry_run_command")
            or workspace_result_payload.get("rerun_without_dry_run_command")
            or (
                _build_workspace_hook_init_command(
                    str(
                        workspace_result_payload.get("hook_name")
                        or payload.get("hook_name")
                        or payload.get("requested_hook_name")
                        or getattr(args, "hook_name", "")
                        or ""
                    ),
                    project_name=getattr(args, "project_name", None),
                    use_recommended_project=bool(getattr(args, "use_recommended_project", False)),
                    use_last_project=bool(getattr(args, "use_last_project", False)),
                    follow_recommended=bool(getattr(args, "follow_recommended", False)),
                    force=bool(getattr(args, "force", False)),
                )
                if getattr(args, "dry_run", False)
                and str(
                    workspace_result_payload.get("hook_name")
                    or payload.get("hook_name")
                    or payload.get("requested_hook_name")
                    or getattr(args, "hook_name", "")
                    or ""
                ).strip()
                else ""
            )
            or ""
        )
        workspace_emit_target_path = (
            payload.get("target_path")
            or ((payload.get("result") or {}).get("target_path"))
            or ""
        )
        workspace_emit_target_dir = str(Path(workspace_emit_target_path).parent) if workspace_emit_target_path else ""
        workspace_emit_target_project_root = str(payload.get("selected_project_root") or payload.get("project_root") or "").strip()
        workspace_emit_target_project_name = Path(workspace_emit_target_project_root).name if workspace_emit_target_project_root else ""
        workspace_emit_target_relative_path = (
            payload.get("target_relative_path")
            or ((payload.get("result") or {}).get("target_relative_path"))
            or ""
        )
        workspace_emit_open_command = f"inspect {workspace_emit_target_path}" if workspace_emit_target_path else ""
        if getattr(args, "inspect_target", False):
            if workspace_emit_target_path:
                target = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": workspace_emit_target_path,
                    "exists": Path(workspace_emit_target_path).exists(),
                }
                parent = {
                    "label": "hook_target_parent",
                    "kind": "directory",
                    "path": str(Path(workspace_emit_target_path).parent),
                    "exists": Path(workspace_emit_target_path).parent.exists(),
                }
                payload["target_inspection"] = _inspect_resolved_target(target)
                payload["target_parent_inspection"] = _inspect_resolved_target(parent)
                payload["inspect_target_summary"] = f"Inspected the resolved hook-init target {Path(workspace_emit_target_path).name} and its parent directory."
                payload["inspect_target_parent_summary"] = f"Parent directory: {Path(workspace_emit_target_path).parent}"
            else:
                payload["target_inspection"] = None
                payload["target_parent_inspection"] = None
                payload["inspect_target_summary"] = "No hook-init target path was available to inspect."
                payload["inspect_target_parent_summary"] = ""
        if getattr(args, "open_target", False):
            if workspace_emit_target_path:
                target_path_obj = Path(workspace_emit_target_path)
                payload["open_target"] = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": str(target_path_obj),
                    "exists": target_path_obj.exists(),
                }
                payload["open_target_command"] = f"inspect {target_path_obj}"
                payload["open_target_summary"] = f"Open the resolved hook-init target {target_path_obj.name}."
                payload["open_target_reason"] = "The hook-init flow already resolved one concrete durable hook file path, so opening that file is the shortest next inspection step."
            else:
                payload["open_target"] = None
                payload["open_target_command"] = ""
                payload["open_target_summary"] = "No hook-init target path was available to open."
                payload["open_target_reason"] = "The hook-init flow did not resolve a concrete hook file path."
        if getattr(args, "open_now", False):
            if workspace_emit_target_path:
                target = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": workspace_emit_target_path,
                    "exists": Path(workspace_emit_target_path).exists(),
                }
                payload["open_now"] = True
                payload["open_now_result"] = _inspect_resolved_target(target)
                preview_lines = [
                    line.strip()
                    for line in str((payload["open_now_result"] or {}).get("content_preview") or "").splitlines()
                    if line.strip()
                ]
                payload["open_now_preview"] = (preview_lines[0][:160] if preview_lines else "")
                payload["open_now_summary"] = f"Inspected the resolved hook-init target {Path(workspace_emit_target_path).name} inline."
                payload["open_now_reason"] = "The hook-init flow already resolved one concrete hook file path, so the CLI can inspect that file directly without an extra command."
            else:
                payload["open_now"] = True
                payload["open_now_result"] = None
                payload["open_now_preview"] = ""
                payload["open_now_summary"] = "No hook-init target path was available to inspect inline."
                payload["open_now_reason"] = "The hook-init flow did not resolve a concrete hook file path."
        workspace_emit_command = workspace_emit_confirm_command or None
        payload["emit_command"] = workspace_emit_command
        payload["emit_confirm_command"] = workspace_emit_confirm_command or None
        payload["emit_target_path"] = workspace_emit_target_path or None
        payload["emit_target_dir"] = workspace_emit_target_dir or None
        payload["emit_target_project_root"] = workspace_emit_target_project_root or None
        payload["emit_target_project_name"] = workspace_emit_target_project_name or None
        payload["emit_target_relative_path"] = workspace_emit_target_relative_path or None
        payload["emit_target_bundle"] = {
            "target_path": workspace_emit_target_path or None,
            "target_dir": workspace_emit_target_dir or None,
            "target_project_root": workspace_emit_target_project_root or None,
            "target_project_name": workspace_emit_target_project_name or None,
            "target_relative_path": workspace_emit_target_relative_path or None,
            "open_command": workspace_emit_open_command or None,
            "confirm_command": workspace_emit_confirm_command or None,
        }
        payload["emit_target_bundle_json"] = json.dumps(payload["emit_target_bundle"], ensure_ascii=False)
        if getattr(args, "copy_command", False):
            copied_command_ok, copied_command_error = _copy_text_to_clipboard(workspace_emit_command) if workspace_emit_command else (False, "No hook-init next command was available to copy.")
            payload["copied_command"] = workspace_emit_command
            payload["copied_command_to_clipboard"] = copied_command_ok
            payload["copy_command_error"] = copied_command_error or None
        if getattr(args, "copy_confirm_command", False):
            copied_confirm_ok, copied_confirm_error = _copy_text_to_clipboard(workspace_emit_confirm_command) if workspace_emit_confirm_command else (False, "No hook-init confirm command was available to copy.")
            payload["copied_confirm_command"] = workspace_emit_confirm_command or None
            payload["copied_confirm_to_clipboard"] = copied_confirm_ok
            payload["copy_confirm_command_error"] = copied_confirm_error or None
        if getattr(args, "copy_target_path", False):
            copied_target_ok, copied_target_error = _copy_text_to_clipboard(workspace_emit_target_path) if workspace_emit_target_path else (False, "No hook-init target path was available to copy.")
            payload["copied_target_path"] = workspace_emit_target_path or None
            payload["copied_target_path_to_clipboard"] = copied_target_ok
            payload["copy_target_path_error"] = copied_target_error or None
        if getattr(args, "copy_target_dir", False):
            copied_target_dir_ok, copied_target_dir_error = _copy_text_to_clipboard(workspace_emit_target_dir) if workspace_emit_target_dir else (False, "No hook-init target directory was available to copy.")
            payload["copied_target_dir"] = workspace_emit_target_dir or None
            payload["copied_target_dir_to_clipboard"] = copied_target_dir_ok
            payload["copy_target_dir_error"] = copied_target_dir_error or None
        if getattr(args, "copy_target_project_root", False):
            copied_target_project_root_ok, copied_target_project_root_error = _copy_text_to_clipboard(workspace_emit_target_project_root) if workspace_emit_target_project_root else (False, "No hook-init target project root was available to copy.")
            payload["copied_target_project_root"] = workspace_emit_target_project_root or None
            payload["copied_target_project_root_to_clipboard"] = copied_target_project_root_ok
            payload["copy_target_project_root_error"] = copied_target_project_root_error or None
        if getattr(args, "copy_target_project_name", False):
            copied_target_project_name_ok, copied_target_project_name_error = _copy_text_to_clipboard(workspace_emit_target_project_name) if workspace_emit_target_project_name else (False, "No hook-init target project name was available to copy.")
            payload["copied_target_project_name"] = workspace_emit_target_project_name or None
            payload["copied_target_project_name_to_clipboard"] = copied_target_project_name_ok
            payload["copy_target_project_name_error"] = copied_target_project_name_error or None
        if getattr(args, "copy_target_relative_path", False):
            copied_target_relative_ok, copied_target_relative_error = _copy_text_to_clipboard(workspace_emit_target_relative_path) if workspace_emit_target_relative_path else (False, "No hook-init target relative path was available to copy.")
            payload["copied_target_relative_path"] = workspace_emit_target_relative_path or None
            payload["copied_target_relative_path_to_clipboard"] = copied_target_relative_ok
            payload["copy_target_relative_path_error"] = copied_target_relative_error or None
        if getattr(args, "copy_target_bundle", False):
            copied_target_bundle_ok, copied_target_bundle_error = _copy_text_to_clipboard(payload["emit_target_bundle_json"]) if payload.get("emit_target_bundle_json") else (False, "No hook-init target bundle was available to copy.")
            payload["copied_target_bundle"] = payload.get("emit_target_bundle")
            payload["copied_target_bundle_json"] = payload.get("emit_target_bundle_json")
            payload["copied_target_bundle_to_clipboard"] = copied_target_bundle_ok
            payload["copy_target_bundle_error"] = copied_target_bundle_error or None
        if getattr(args, "copy_open_command", False):
            copied_open_ok, copied_open_error = _copy_text_to_clipboard(workspace_emit_open_command) if workspace_emit_open_command else (False, "No hook-init open command was available to copy.")
            payload["copied_open_command"] = workspace_emit_open_command or None
            payload["copied_open_to_clipboard"] = copied_open_ok
            payload["copy_open_command_error"] = copied_open_error or None
        if getattr(args, "run_open_command", False):
            payload["run_open_command"] = workspace_emit_open_command or None
            payload["run_open_command_requires_confirmation"] = True
            payload["run_open_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_open_command_confirm_command"] = _build_workspace_hook_init_run_open_command(
                payload.get("requested_hook_name") or "",
                project_name=payload.get("selected_project_name"),
                use_recommended_project=bool(getattr(args, "use_recommended_project", False)),
                use_last_project=bool(getattr(args, "use_last_project", False)),
                follow_recommended=bool(getattr(args, "follow_recommended", False)),
                dry_run=bool(getattr(args, "dry_run", False)),
                force=bool(getattr(args, "force", False)),
                yes=True,
            )
            if getattr(args, "yes", False):
                if workspace_emit_target_path:
                    target = {
                        "label": "hook_target",
                        "kind": "file",
                        "path": workspace_emit_target_path,
                        "exists": Path(workspace_emit_target_path).exists(),
                    }
                    payload["ran_open_command"] = True
                    payload["run_open_command_exit_code"] = EXIT_OK
                    payload["run_open_result"] = _inspect_resolved_target(target)
                    payload["run_open_command_warning"] = None
                else:
                    payload["ran_open_command"] = False
                    payload["run_open_command_exit_code"] = EXIT_USAGE
                    payload["run_open_result"] = None
                    payload["run_open_command_warning"] = "No hook-init target path was available to inspect."
            else:
                payload["ran_open_command"] = False
                payload["run_open_command_exit_code"] = EXIT_OK
                payload["run_open_result"] = None
                payload["run_open_command_warning"] = "Confirmation required. Re-run with --yes to execute the resolved hook-init open step."
        if getattr(args, "run_command", False):
            payload["run_command"] = workspace_emit_command or None
            payload["run_command_requires_confirmation"] = True
            payload["run_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_command_confirm_command"] = _build_workspace_hook_init_run_command(
                payload.get("requested_hook_name") or "",
                project_name=payload.get("selected_project_name"),
                use_recommended_project=bool(getattr(args, "use_recommended_project", False)),
                use_last_project=bool(getattr(args, "use_last_project", False)),
                follow_recommended=bool(getattr(args, "follow_recommended", False)),
                dry_run=bool(getattr(args, "dry_run", False)),
                force=bool(getattr(args, "force", False)),
                yes=True,
            )
            if getattr(args, "yes", False):
                ran_ok, run_stdout, run_stderr, run_exit_code, run_result = _run_shell_command(workspace_emit_command or "")
                payload["ran_command"] = ran_ok
                payload["run_command_exit_code"] = run_exit_code
                payload["run_command_stdout"] = run_stdout
                payload["run_command_stderr"] = run_stderr
                payload["run_result"] = run_result
            else:
                payload["ran_command"] = False
                payload["run_command_exit_code"] = EXIT_OK
                payload["run_command_stdout"] = ""
                payload["run_command_stderr"] = ""
                payload["run_result"] = None
                payload["run_command_warning"] = "Confirmation required. Re-run with --yes to execute the selected hook-init next command."
        if args.json:
            _print_json_payload(payload)
        elif getattr(args, "run_command", False):
            if payload.get("run_command_confirmed"):
                if payload.get("ran_command"):
                    print("Workspace hook-init command executed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_result") and isinstance(payload["run_result"], dict):
                        result = payload["run_result"]
                        print(f"- run_result_entrypoint: {result.get('entrypoint', '')}")
                        if result.get("target_path"):
                            print(f"- run_result_target_path: {result['target_path']}")
                        if result.get("hook_name"):
                            print(f"- run_result_hook_name: {result['hook_name']}")
                else:
                    print("Workspace hook-init command execution failed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_command_stderr"):
                        print(f"- run_command_stderr: {payload['run_command_stderr'].strip()}")
                    elif payload.get("run_command_stdout"):
                        print(f"- run_command_stdout: {payload['run_command_stdout'].strip()}")
                return int(payload.get("run_command_exit_code", exit_code))
            print("Workspace hook-init command ready")
            print(f"- run_command: {payload.get('run_command', '')}")
            if payload.get("run_command_warning"):
                print(f"- run_command_warning: {payload['run_command_warning']}")
            if payload.get("run_command_confirm_command"):
                print(f"- run_command_confirm_command: {payload['run_command_confirm_command']}")
            return exit_code
        elif getattr(args, "run_open_command", False):
            if payload.get("run_open_command_confirmed"):
                if payload.get("ran_open_command"):
                    print("Workspace hook-init open command executed")
                    print(f"- run_open_command: {payload.get('run_open_command', '')}")
                    print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                    run_open_result = payload.get("run_open_result") or {}
                    if run_open_result.get("path"):
                        print(f"- run_open_path: {run_open_result['path']}")
                    if run_open_result.get("exists") is not None:
                        print(f"- run_open_exists: {bool(run_open_result.get('exists'))}")
                    if run_open_result.get("line_count") is not None:
                        print(f"- run_open_line_count: {run_open_result['line_count']}")
                else:
                    print("Workspace hook-init open command execution failed")
                    print(f"- run_open_command: {payload.get('run_open_command', '')}")
                    print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                    if payload.get("run_open_command_warning"):
                        print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
                return int(payload.get("run_open_command_exit_code", exit_code))
            print("Workspace hook-init open command ready")
            print(f"- run_open_command: {payload.get('run_open_command', '')}")
            if payload.get("run_open_command_warning"):
                print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
            if payload.get("run_open_command_confirm_command"):
                print(f"- run_open_command_confirm_command: {payload['run_open_command_confirm_command']}")
            return exit_code
        elif getattr(args, "explain", False) and (payload.get("result") or {}).get("entrypoint") == "project-hook-init":
            print("Workspace hook-init explain")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            if payload.get("selected_project_name"):
                print(f"- selected_project_name: {payload['selected_project_name']}")
            if workspace_emit_confirm_command:
                print(f"- runnable_next_command: {workspace_emit_confirm_command}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            blocks = payload.get("explanation_blocks") or []
            for item in blocks:
                print(f"- {item.get('label', '')}: {item.get('summary', '')}")
                if item.get("detail"):
                    print(f"  {item['detail']}")
            return exit_code
        elif getattr(args, "text_compact", False) and (payload.get("result") or {}).get("entrypoint") == "project-hook-init":
            result_payload = payload.get("result") or {}
            print("Workspace hook-init compact")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            if payload.get("selected_project_name"):
                print(f"- selected_project_name: {payload['selected_project_name']}")
            if result_payload.get("hook_name"):
                print(f"- hook_name: {result_payload['hook_name']}")
            if result_payload.get("template"):
                print(f"- template: {result_payload['template']}")
            if result_payload.get("target_path"):
                print(f"- target_path: {result_payload['target_path']}")
            if result_payload.get("target_relative_path"):
                print(f"- target_relative_path: {result_payload['target_relative_path']}")
            if payload.get("inspect_target_summary"):
                print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
            if payload.get("inspect_target_parent_summary"):
                print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
            if (payload.get("target_inspection") or {}).get("path"):
                print(f"- inspected_target_path: {(payload.get('target_inspection') or {}).get('path')}")
            if (payload.get("target_inspection") or {}).get("exists") is not None:
                print(f"- inspected_target_exists: {bool((payload.get('target_inspection') or {}).get('exists'))}")
            parent_entries = [
                entry.get("name", "")
                for entry in ((payload.get("target_parent_inspection") or {}).get("entries") or [])
                if entry.get("name")
            ]
            if parent_entries:
                print(f"- nearby_entries: {', '.join(parent_entries[:6])}")
            if payload.get("open_now_summary"):
                print(f"- open_now_summary: {payload['open_now_summary']}")
            if (payload.get("open_now_result") or {}).get("path"):
                print(f"- open_now_path: {(payload.get('open_now_result') or {}).get('path')}")
            if (payload.get("open_now_result") or {}).get("exists") is not None:
                print(f"- open_now_exists: {bool((payload.get('open_now_result') or {}).get('exists'))}")
            if (payload.get("open_now_result") or {}).get("line_count") is not None:
                print(f"- open_now_line_count: {(payload.get('open_now_result') or {}).get('line_count')}")
            if payload.get("open_now_preview"):
                print(f"- open_now_preview: {payload['open_now_preview']}")
            if result_payload.get("dry_run_summary"):
                print(f"- target_summary: {result_payload['dry_run_summary']}")
            if result_payload.get("target_reason"):
                print(f"- target_reason: {result_payload['target_reason']}")
            if result_payload.get("would_overwrite") is not None:
                print(f"- would_overwrite: {str(result_payload.get('would_overwrite', False)).lower()}")
            if workspace_emit_confirm_command:
                print(f"- runnable_next_command: {workspace_emit_confirm_command}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            return exit_code
        elif getattr(args, "inspect_target", False):
            print("Workspace hook-init inspect target")
            if payload.get("inspect_target_summary"):
                print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
            if payload.get("inspect_target_parent_summary"):
                print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
            target_inspection = payload.get("target_inspection") or {}
            parent_inspection = payload.get("target_parent_inspection") or {}
            if target_inspection.get("path"):
                print(f"- inspected_target_path: {target_inspection['path']}")
            if target_inspection.get("exists") is not None:
                print(f"- inspected_target_exists: {bool(target_inspection.get('exists'))}")
            if parent_inspection.get("path"):
                print(f"- inspected_target_parent_path: {parent_inspection['path']}")
            if parent_inspection.get("entry_count") is not None:
                print(f"- inspected_target_parent_entry_count: {parent_inspection['entry_count']}")
            return exit_code
        elif getattr(args, "open_target", False):
            print("Workspace hook-init open target")
            if payload.get("open_target_summary"):
                print(f"- open_target_summary: {payload['open_target_summary']}")
            if payload.get("open_target_reason"):
                print(f"- open_target_reason: {payload['open_target_reason']}")
            if payload.get("open_target_command"):
                print(f"- open_target_command: {payload['open_target_command']}")
            open_target = payload.get("open_target") or {}
            if open_target.get("path"):
                print(f"- open_target_path: {open_target['path']}")
            if open_target.get("exists") is not None:
                print(f"- open_target_exists: {bool(open_target.get('exists'))}")
            return exit_code
        elif getattr(args, "open_now", False):
            print("Workspace hook-init open now")
            if payload.get("open_now_summary"):
                print(f"- open_now_summary: {payload['open_now_summary']}")
            if payload.get("open_now_reason"):
                print(f"- open_now_reason: {payload['open_now_reason']}")
            open_now_result = payload.get("open_now_result") or {}
            if open_now_result.get("path"):
                print(f"- open_now_path: {open_now_result['path']}")
            if open_now_result.get("exists") is not None:
                print(f"- open_now_exists: {bool(open_now_result.get('exists'))}")
            if open_now_result.get("line_count") is not None:
                print(f"- open_now_line_count: {open_now_result['line_count']}")
            if payload.get("open_now_preview"):
                print(f"- open_now_preview: {payload['open_now_preview']}")
            return exit_code
        elif getattr(args, "emit_shell", False):
            if workspace_emit_command:
                print(workspace_emit_command)
            else:
                print("No hook-init next command was available.")
            return exit_code if workspace_emit_command else EXIT_USAGE
        elif getattr(args, "emit_confirm_shell", False):
            if workspace_emit_confirm_command:
                print(workspace_emit_confirm_command)
            else:
                print("No hook-init confirm command was available.")
            return exit_code if workspace_emit_confirm_command else EXIT_USAGE
        elif getattr(args, "emit_target_path", False):
            if workspace_emit_target_path:
                print(workspace_emit_target_path)
            else:
                print("No hook-init target path was available.")
            return exit_code if workspace_emit_target_path else EXIT_USAGE
        elif getattr(args, "emit_target_dir", False):
            if workspace_emit_target_dir:
                print(workspace_emit_target_dir)
            else:
                print("No hook-init target directory was available.")
            return exit_code if workspace_emit_target_dir else EXIT_USAGE
        elif getattr(args, "emit_target_project_root", False):
            if workspace_emit_target_project_root:
                print(workspace_emit_target_project_root)
            else:
                print("No hook-init target project root was available.")
            return exit_code if workspace_emit_target_project_root else EXIT_USAGE
        elif getattr(args, "emit_target_project_name", False):
            if workspace_emit_target_project_name:
                print(workspace_emit_target_project_name)
            else:
                print("No hook-init target project name was available.")
            return exit_code if workspace_emit_target_project_name else EXIT_USAGE
        elif getattr(args, "emit_target_relative_path", False):
            if workspace_emit_target_relative_path:
                print(workspace_emit_target_relative_path)
            else:
                print("No hook-init target relative path was available.")
            return exit_code if workspace_emit_target_relative_path else EXIT_USAGE
        elif getattr(args, "emit_target_bundle", False):
            if payload.get("emit_target_bundle_json"):
                print(payload["emit_target_bundle_json"])
            else:
                print("No hook-init target bundle was available.")
            return exit_code if payload.get("emit_target_bundle_json") else EXIT_USAGE
        elif getattr(args, "emit_open_shell", False):
            if workspace_emit_open_command:
                print(workspace_emit_open_command)
            else:
                print("No hook-init open command was available.")
            return exit_code if workspace_emit_open_command else EXIT_USAGE
        elif getattr(args, "copy_command", False):
            if payload.get("copied_command_to_clipboard"):
                print("Workspace hook-init next command copied")
                print(f"- copied_command: {payload.get('copied_command', '')}")
            else:
                print("Workspace hook-init next command copy failed")
                if payload.get("copy_command_error"):
                    print(f"- copy_command_error: {payload['copy_command_error']}")
            return exit_code if payload.get("copied_command_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_confirm_command", False):
            if payload.get("copied_confirm_to_clipboard"):
                print("Workspace hook-init confirm command copied")
                print(f"- copied_confirm_command: {payload.get('copied_confirm_command', '')}")
            else:
                print("Workspace hook-init confirm command copy failed")
                if payload.get("copy_confirm_command_error"):
                    print(f"- copy_confirm_command_error: {payload['copy_confirm_command_error']}")
            return exit_code if payload.get("copied_confirm_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_path", False):
            if payload.get("copied_target_path_to_clipboard"):
                print("Workspace hook-init target path copied")
                print(f"- copied_target_path: {payload.get('copied_target_path', '')}")
            else:
                print("Workspace hook-init target path copy failed")
                if payload.get("copy_target_path_error"):
                    print(f"- copy_target_path_error: {payload['copy_target_path_error']}")
            return exit_code if payload.get("copied_target_path_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_dir", False):
            if payload.get("copied_target_dir_to_clipboard"):
                print("Workspace hook-init target directory copied")
                print(f"- copied_target_dir: {payload.get('copied_target_dir', '')}")
            else:
                print("Workspace hook-init target directory copy failed")
                if payload.get("copy_target_dir_error"):
                    print(f"- copy_target_dir_error: {payload['copy_target_dir_error']}")
            return exit_code if payload.get("copied_target_dir_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_project_root", False):
            if payload.get("copied_target_project_root_to_clipboard"):
                print("Workspace hook-init target project root copied")
                print(f"- copied_target_project_root: {payload.get('copied_target_project_root', '')}")
            else:
                print("Workspace hook-init target project root copy failed")
                if payload.get("copy_target_project_root_error"):
                    print(f"- copy_target_project_root_error: {payload['copy_target_project_root_error']}")
            return exit_code if payload.get("copied_target_project_root_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_project_name", False):
            if payload.get("copied_target_project_name_to_clipboard"):
                print("Workspace hook-init target project name copied")
                print(f"- copied_target_project_name: {payload.get('copied_target_project_name', '')}")
            else:
                print("Workspace hook-init target project name copy failed")
                if payload.get("copy_target_project_name_error"):
                    print(f"- copy_target_project_name_error: {payload['copy_target_project_name_error']}")
            return exit_code if payload.get("copied_target_project_name_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_relative_path", False):
            if payload.get("copied_target_relative_path_to_clipboard"):
                print("Workspace hook-init target relative path copied")
                print(f"- copied_target_relative_path: {payload.get('copied_target_relative_path', '')}")
            else:
                print("Workspace hook-init target relative path copy failed")
                if payload.get("copy_target_relative_path_error"):
                    print(f"- copy_target_relative_path_error: {payload['copy_target_relative_path_error']}")
            return exit_code if payload.get("copied_target_relative_path_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_bundle", False):
            if payload.get("copied_target_bundle_to_clipboard"):
                print("Workspace hook-init target bundle copied")
                print(f"- copied_target_bundle: {payload.get('copied_target_bundle_json', '')}")
            else:
                print("Workspace hook-init target bundle copy failed")
                if payload.get("copy_target_bundle_error"):
                    print(f"- copy_target_bundle_error: {payload['copy_target_bundle_error']}")
            return exit_code if payload.get("copied_target_bundle_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_open_command", False):
            if payload.get("copied_open_to_clipboard"):
                print("Workspace hook-init open command copied")
                print(f"- copied_open_command: {payload.get('copied_open_command', '')}")
            else:
                print("Workspace hook-init open command copy failed")
                if payload.get("copy_open_command_error"):
                    print(f"- copy_open_command_error: {payload['copy_open_command_error']}")
            return exit_code if payload.get("copied_open_to_clipboard") else EXIT_USAGE
        else:
            print("Workspace hook-init")
            print(f"- route: {payload['route_taken']}")
            if payload.get("selected_project_name"):
                print(f"- project: {payload['selected_project_name']}")
            if payload.get("dry_run"):
                print("- dry_run: true")
            result_payload = payload.get("result") or {}
            if result_payload.get("hook_name"):
                print(f"- hook_name: {result_payload['hook_name']}")
            if result_payload.get("template"):
                print(f"- template: {result_payload['template']}")
            if result_payload.get("target_relative_path"):
                print(f"- target_relative_path: {result_payload['target_relative_path']}")
            if result_payload.get("dry_run_summary"):
                print(f"- target_summary: {result_payload['dry_run_summary']}")
            if result_payload.get("target_reason"):
                print(f"- target_reason: {result_payload['target_reason']}")
            if payload.get("rerun_without_dry_run_command"):
                print(f"- runnable_next_command: {payload['rerun_without_dry_run_command']}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) == "hook-continue":
        if getattr(args, "run_command", False) and getattr(args, "run_open_command", False):
            return _emit_command_error(
                args,
                EXIT_USAGE,
                "invalid_usage",
                "choose only one of --run-command or --run-open-command",
            )
        payload, exit_code = _run_workspace_hook_continue(
            force=getattr(args, "force", False),
            broaden_to=getattr(args, "broaden_to", None),
            dry_run=getattr(args, "dry_run", False),
        )
        if getattr(args, "inspect_target", False):
            target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
            if target_path:
                inspection_bundle = _inspect_hook_target_path(target_path)
                payload["target_inspection"] = inspection_bundle["inspection"]
                payload["target_parent_inspection"] = inspection_bundle["parent_inspection"]
                parent_entries = list((inspection_bundle["parent_inspection"] or {}).get("entries") or [])
                payload["inspect_target_neighbor_names"] = [str(item.get("name") or "") for item in parent_entries[:5] if str(item.get("name") or "").strip()]
                parent_entry_count = int((inspection_bundle["parent_inspection"] or {}).get("entry_count") or 0)
                payload["inspect_target_parent_summary"] = (
                    f"Parent directory currently has {parent_entry_count} entries."
                )
                payload["inspect_target_summary"] = (
                    f"Resolved hook target {Path(target_path).name} under {inspection_bundle['parent_target']['path']}."
                )
            else:
                payload["target_inspection"] = None
                payload["target_parent_inspection"] = None
                payload["inspect_target_neighbor_names"] = []
                payload["inspect_target_parent_summary"] = "No parent directory summary was available."
                payload["inspect_target_summary"] = "No hook target path was available to inspect."
        if getattr(args, "open_target", False):
            target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
            if target_path:
                target_path_obj = Path(target_path)
                payload["open_target"] = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": str(target_path_obj),
                    "exists": target_path_obj.exists(),
                }
                payload["open_target_command"] = f"inspect {target_path_obj}"
                payload["open_target_summary"] = f"Open the resolved hook target {target_path_obj.name}."
                payload["open_target_reason"] = "The continue flow already resolved one concrete durable hook file path, so opening that file is the shortest next inspection step."
            else:
                payload["open_target"] = None
                payload["open_target_command"] = ""
                payload["open_target_summary"] = "No hook target path was available to open."
                payload["open_target_reason"] = "The continue flow did not resolve a concrete hook file path."
        if getattr(args, "open_now", False):
            target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
            if target_path:
                open_target = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": target_path,
                    "exists": Path(target_path).exists(),
                }
                payload["open_now"] = True
                payload["open_now_result"] = _inspect_resolved_target(open_target)
                preview_lines = [
                    line.strip()
                    for line in str((payload["open_now_result"] or {}).get("content_preview") or "").splitlines()
                    if line.strip()
                ]
                payload["open_now_preview"] = (preview_lines[0][:160] if preview_lines else "")
                payload["open_now_summary"] = f"Inspected the resolved hook target {Path(target_path).name} inline."
                payload["open_now_reason"] = "The continue flow already resolved one concrete hook file path, so the CLI can inspect that file directly without an extra command."
            else:
                payload["open_now"] = True
                payload["open_now_result"] = None
                payload["open_now_preview"] = ""
                payload["open_now_summary"] = "No hook target path was available to inspect inline."
                payload["open_now_reason"] = "The continue flow did not resolve a concrete hook file path."
        emit_command = (
            payload.get("dry_run_confirm_command")
            or payload.get("preferred_followup_command")
            or payload.get("recommended_next_command")
            or payload.get("selected_strategy_command")
            or ""
        )
        resolved_target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
        resolved_target_dir = str(Path(resolved_target_path).parent) if resolved_target_path else ""
        resolved_target_project_root = str(payload.get("selected_project_root") or payload.get("project_root") or "").strip()
        resolved_target_project_name = Path(resolved_target_project_root).name if resolved_target_project_root else ""
        resolved_target_relative_path = ""
        if resolved_target_path and resolved_target_project_root:
            try:
                resolved_target_relative_path = str(Path(resolved_target_path).relative_to(Path(resolved_target_project_root)))
            except ValueError:
                resolved_target_relative_path = ""
        payload["emit_target_path"] = resolved_target_path or None
        payload["emit_target_dir"] = resolved_target_dir or None
        payload["emit_target_project_root"] = resolved_target_project_root or None
        payload["emit_target_project_name"] = resolved_target_project_name or None
        payload["emit_target_relative_path"] = resolved_target_relative_path or None
        emit_open_command = payload.get("open_target_command") or (f"inspect {resolved_target_path}" if resolved_target_path else "")
        payload["emit_open_shell_command"] = emit_open_command or None
        emit_target_bundle = {
            "target_path": resolved_target_path or None,
            "target_dir": resolved_target_dir or None,
            "target_project_root": resolved_target_project_root or None,
            "target_project_name": resolved_target_project_name or None,
            "target_relative_path": resolved_target_relative_path or None,
            "open_command": emit_open_command or None,
            "confirm_command": None,
        }
        emit_confirm_command = (
            payload.get("run_open_command_confirm_command")
            or payload.get("run_command_confirm_command")
            or payload.get("dry_run_confirm_command")
            or payload.get("rerun_without_dry_run_command")
            or payload.get("recommended_next_command")
            or ""
        )
        payload["emit_confirm_command"] = emit_confirm_command or None
        emit_target_bundle["confirm_command"] = emit_confirm_command or None
        payload["emit_target_bundle"] = emit_target_bundle
        payload["emit_target_bundle_json"] = json.dumps(emit_target_bundle, ensure_ascii=False)
        if getattr(args, "copy_open_command", False):
            copied_open_ok, copied_open_error = _copy_text_to_clipboard(emit_open_command) if emit_open_command else (False, "No open-target command was available to copy.")
            payload["copied_open_command"] = emit_open_command or None
            payload["copied_open_to_clipboard"] = copied_open_ok
            payload["copy_open_command_error"] = copied_open_error or None
        if getattr(args, "copy_confirm_command", False):
            copied_confirm_ok, copied_confirm_error = _copy_text_to_clipboard(emit_confirm_command) if emit_confirm_command else (False, "No confirm command was available to copy.")
            payload["copied_confirm_command"] = emit_confirm_command or None
            payload["copied_confirm_to_clipboard"] = copied_confirm_ok
            payload["copy_confirm_command_error"] = copied_confirm_error or None
        if getattr(args, "copy_target_path", False):
            copied_target_ok, copied_target_error = _copy_text_to_clipboard(resolved_target_path) if resolved_target_path else (False, "No resolved hook target path was available to copy.")
            payload["copied_target_path"] = resolved_target_path or None
            payload["copied_target_path_to_clipboard"] = copied_target_ok
            payload["copy_target_path_error"] = copied_target_error or None
        if getattr(args, "copy_target_dir", False):
            copied_target_dir_ok, copied_target_dir_error = _copy_text_to_clipboard(resolved_target_dir) if resolved_target_dir else (False, "No resolved hook target directory was available to copy.")
            payload["copied_target_dir"] = resolved_target_dir or None
            payload["copied_target_dir_to_clipboard"] = copied_target_dir_ok
            payload["copy_target_dir_error"] = copied_target_dir_error or None
        if getattr(args, "copy_target_project_root", False):
            copied_target_project_root_ok, copied_target_project_root_error = _copy_text_to_clipboard(resolved_target_project_root) if resolved_target_project_root else (False, "No resolved hook target project root was available to copy.")
            payload["copied_target_project_root"] = resolved_target_project_root or None
            payload["copied_target_project_root_to_clipboard"] = copied_target_project_root_ok
            payload["copy_target_project_root_error"] = copied_target_project_root_error or None
        if getattr(args, "copy_target_project_name", False):
            copied_target_project_name_ok, copied_target_project_name_error = _copy_text_to_clipboard(resolved_target_project_name) if resolved_target_project_name else (False, "No resolved hook target project name was available to copy.")
            payload["copied_target_project_name"] = resolved_target_project_name or None
            payload["copied_target_project_name_to_clipboard"] = copied_target_project_name_ok
            payload["copy_target_project_name_error"] = copied_target_project_name_error or None
        if getattr(args, "copy_target_relative_path", False):
            copied_target_relative_path_ok, copied_target_relative_path_error = _copy_text_to_clipboard(resolved_target_relative_path) if resolved_target_relative_path else (False, "No resolved hook target path relative to the generated project root was available to copy.")
            payload["copied_target_relative_path"] = resolved_target_relative_path or None
            payload["copied_target_relative_path_to_clipboard"] = copied_target_relative_path_ok
            payload["copy_target_relative_path_error"] = copied_target_relative_path_error or None
        if getattr(args, "copy_target_bundle", False):
            copied_target_bundle_ok, copied_target_bundle_error = _copy_text_to_clipboard(payload["emit_target_bundle_json"]) if payload.get("emit_target_bundle_json") else (False, "No resolved hook target bundle was available to copy.")
            payload["copied_target_bundle"] = payload.get("emit_target_bundle")
            payload["copied_target_bundle_json"] = payload.get("emit_target_bundle_json")
            payload["copied_target_bundle_to_clipboard"] = copied_target_bundle_ok
            payload["copy_target_bundle_error"] = copied_target_bundle_error or None
        if getattr(args, "copy_command", False):
            copied_ok, copied_error = _copy_text_to_clipboard(emit_command) if emit_command else (False, "No next command was available to copy.")
            payload["copied_command"] = emit_command or None
            payload["copied_to_clipboard"] = copied_ok
            payload["copy_command_error"] = copied_error or None
        if getattr(args, "run_open_command", False):
            payload["run_open_command"] = emit_open_command or None
            payload["run_open_command_requires_confirmation"] = True
            payload["run_open_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_open_command_confirm_command"] = _build_workspace_hook_continue_run_open_command(
                force=getattr(args, "force", False),
                broaden_to=getattr(args, "broaden_to", None),
                dry_run=getattr(args, "dry_run", False),
                yes=True,
            )
            if getattr(args, "yes", False):
                if resolved_target_path:
                    target = {
                        "label": "hook_target",
                        "kind": "file",
                        "path": resolved_target_path,
                        "exists": Path(resolved_target_path).exists(),
                    }
                    payload["ran_open_command"] = True
                    payload["run_open_command_exit_code"] = EXIT_OK
                    payload["run_open_result"] = _inspect_resolved_target(target)
                    payload["run_open_command_warning"] = None
                else:
                    payload["ran_open_command"] = False
                    payload["run_open_command_exit_code"] = EXIT_USAGE
                    payload["run_open_result"] = None
                    payload["run_open_command_warning"] = "No resolved hook target path was available to inspect."
            else:
                payload["ran_open_command"] = False
                payload["run_open_command_exit_code"] = EXIT_OK
                payload["run_open_result"] = None
                payload["run_open_command_warning"] = "Confirmation required. Re-run with --yes to execute the resolved open-target inspection step."
        if getattr(args, "run_command", False):
            payload["run_command"] = emit_command or None
            payload["run_command_requires_confirmation"] = True
            payload["run_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_command_confirm_command"] = _build_workspace_hook_continue_run_command(
                force=getattr(args, "force", False),
                broaden_to=getattr(args, "broaden_to", None),
                dry_run=getattr(args, "dry_run", False),
                yes=True,
            )
            if getattr(args, "yes", False):
                ran_ok, run_stdout, run_stderr, run_exit_code, run_result = _run_shell_command(emit_command)
                payload["ran_command"] = ran_ok
                payload["run_command_exit_code"] = run_exit_code
                payload["run_command_stdout"] = run_stdout
                payload["run_command_stderr"] = run_stderr
                payload["run_result"] = run_result
            else:
                payload["ran_command"] = False
                payload["run_command_exit_code"] = EXIT_OK
                payload["run_command_stdout"] = ""
                payload["run_command_stderr"] = ""
                payload["run_result"] = None
                payload["run_command_warning"] = "Confirmation required. Re-run with --yes to execute the selected next command."
        if args.json:
            _print_json_payload(payload)
        else:
            if getattr(args, "run_open_command", False):
                if payload.get("run_open_command_confirmed"):
                    if payload.get("ran_open_command"):
                        print("Workspace hook-continue open command executed")
                        print(f"- run_open_command: {payload.get('run_open_command', '')}")
                        print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                        run_open_result = payload.get("run_open_result") or {}
                        if run_open_result.get("path"):
                            print(f"- run_open_path: {run_open_result['path']}")
                        if run_open_result.get("exists") is not None:
                            print(f"- run_open_exists: {bool(run_open_result.get('exists'))}")
                        if run_open_result.get("line_count") is not None:
                            print(f"- run_open_line_count: {run_open_result['line_count']}")
                    else:
                        print("Workspace hook-continue open command execution failed")
                        print(f"- run_open_command: {payload.get('run_open_command', '')}")
                        print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                        if payload.get("run_open_command_warning"):
                            print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
                    return int(payload.get("run_open_command_exit_code", exit_code))
                print("Workspace hook-continue open command ready")
                print(f"- run_open_command: {payload.get('run_open_command', '')}")
                if payload.get("run_open_command_warning"):
                    print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
                if payload.get("run_open_command_confirm_command"):
                    print(f"- run_open_command_confirm_command: {payload['run_open_command_confirm_command']}")
                return exit_code
            if getattr(args, "run_command", False):
                if payload.get("run_command_confirmed"):
                    if payload.get("ran_command"):
                        print("Workspace hook-continue command executed")
                        print(f"- run_command: {payload.get('run_command', '')}")
                        print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                        if payload.get("run_result") and isinstance(payload["run_result"], dict):
                            result = payload["run_result"]
                            print(f"- run_result_entrypoint: {result.get('entrypoint', '')}")
                            if result.get("target_path"):
                                print(f"- run_result_target_path: {result['target_path']}")
                            if result.get("hook_name"):
                                print(f"- run_result_hook_name: {result['hook_name']}")
                    else:
                        print("Workspace hook-continue command execution failed")
                        print(f"- run_command: {payload.get('run_command', '')}")
                        print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                        if payload.get("run_command_stderr"):
                            print(f"- run_command_stderr: {payload['run_command_stderr'].strip()}")
                        elif payload.get("run_command_stdout"):
                            print(f"- run_command_stdout: {payload['run_command_stdout'].strip()}")
                    return int(payload.get("run_command_exit_code", exit_code))
                print("Workspace hook-continue command ready")
                print(f"- run_command: {payload.get('run_command', '')}")
                if payload.get("run_command_warning"):
                    print(f"- run_command_warning: {payload['run_command_warning']}")
                if payload.get("run_command_confirm_command"):
                    print(f"- run_command_confirm_command: {payload['run_command_confirm_command']}")
                return exit_code
            if getattr(args, "copy_command", False):
                if payload.get("copied_to_clipboard"):
                    print("Workspace hook-continue command copied")
                    print(f"- copied_command: {payload.get('copied_command', '')}")
                else:
                    print("Workspace hook-continue command copy failed")
                    if payload.get("copy_command_error"):
                        print(f"- copy_command_error: {payload['copy_command_error']}")
                    if emit_command:
                        print(f"- fallback_command: {emit_command}")
                return exit_code
            if getattr(args, "copy_confirm_command", False):
                if payload.get("copied_confirm_to_clipboard"):
                    print("Workspace hook-continue confirm command copied")
                    print(f"- copied_confirm_command: {payload.get('copied_confirm_command', '')}")
                else:
                    print("Workspace hook-continue confirm command copy failed")
                    if payload.get("copy_confirm_command_error"):
                        print(f"- copy_confirm_command_error: {payload['copy_confirm_command_error']}")
                    if emit_confirm_command:
                        print(f"- fallback_confirm_command: {emit_confirm_command}")
                return exit_code
            if getattr(args, "copy_target_path", False):
                if payload.get("copied_target_path_to_clipboard"):
                    print("Workspace hook-continue target path copied")
                    print(f"- copied_target_path: {payload.get('copied_target_path', '')}")
                else:
                    print("Workspace hook-continue target path copy failed")
                    if payload.get("copy_target_path_error"):
                        print(f"- copy_target_path_error: {payload['copy_target_path_error']}")
                    if resolved_target_path:
                        print(f"- fallback_target_path: {resolved_target_path}")
                return EXIT_OK
            if getattr(args, "copy_target_dir", False):
                if payload.get("copied_target_dir_to_clipboard"):
                    print("Workspace hook-continue target directory copied")
                    print(f"- copied_target_dir: {payload.get('copied_target_dir', '')}")
                else:
                    print("Workspace hook-continue target directory copy failed")
                    if payload.get("copy_target_dir_error"):
                        print(f"- copy_target_dir_error: {payload['copy_target_dir_error']}")
                    if resolved_target_dir:
                        print(f"- fallback_target_dir: {resolved_target_dir}")
                return EXIT_OK
            if getattr(args, "copy_target_project_root", False):
                if payload.get("copied_target_project_root_to_clipboard"):
                    print("Workspace hook-continue target project root copied")
                    print(f"- copied_target_project_root: {payload.get('copied_target_project_root', '')}")
                else:
                    print("Workspace hook-continue target project root copy failed")
                    if payload.get("copy_target_project_root_error"):
                        print(f"- copy_target_project_root_error: {payload['copy_target_project_root_error']}")
                    if resolved_target_project_root:
                        print(f"- fallback_target_project_root: {resolved_target_project_root}")
                return EXIT_OK
            if getattr(args, "copy_target_project_name", False):
                if payload.get("copied_target_project_name_to_clipboard"):
                    print("Workspace hook-continue target project name copied")
                    print(f"- copied_target_project_name: {payload.get('copied_target_project_name', '')}")
                else:
                    print("Workspace hook-continue target project name copy failed")
                    if payload.get("copy_target_project_name_error"):
                        print(f"- copy_target_project_name_error: {payload['copy_target_project_name_error']}")
                    if resolved_target_project_name:
                        print(f"- fallback_target_project_name: {resolved_target_project_name}")
                return EXIT_OK
            if getattr(args, "copy_target_relative_path", False):
                if payload.get("copied_target_relative_path_to_clipboard"):
                    print("Workspace hook-continue target relative path copied")
                    print(f"- copied_target_relative_path: {payload.get('copied_target_relative_path', '')}")
                else:
                    print("Workspace hook-continue target relative path copy failed")
                    if payload.get("copy_target_relative_path_error"):
                        print(f"- copy_target_relative_path_error: {payload['copy_target_relative_path_error']}")
                    if resolved_target_relative_path:
                        print(f"- fallback_target_relative_path: {resolved_target_relative_path}")
                return EXIT_OK
            if getattr(args, "copy_target_bundle", False):
                if payload.get("copied_target_bundle_to_clipboard"):
                    print("Workspace hook-continue target bundle copied")
                    print(f"- copied_target_bundle: {payload.get('copied_target_bundle_json', '')}")
                else:
                    print("Workspace hook-continue target bundle copy failed")
                    if payload.get("copy_target_bundle_error"):
                        print(f"- copy_target_bundle_error: {payload['copy_target_bundle_error']}")
                    if payload.get("emit_target_bundle_json"):
                        print(f"- fallback_target_bundle: {payload['emit_target_bundle_json']}")
                return EXIT_OK
            if getattr(args, "emit_shell", False):
                if emit_command:
                    print(emit_command)
                return exit_code
            if getattr(args, "emit_confirm_shell", False):
                if emit_confirm_command:
                    print(emit_confirm_command)
                return exit_code
            if getattr(args, "emit_target_path", False):
                if resolved_target_path:
                    print(resolved_target_path)
                return EXIT_OK
            if getattr(args, "emit_target_dir", False):
                if resolved_target_dir:
                    print(resolved_target_dir)
                return EXIT_OK
            if getattr(args, "emit_target_project_root", False):
                if resolved_target_project_root:
                    print(resolved_target_project_root)
                return EXIT_OK
            if getattr(args, "emit_target_project_name", False):
                if resolved_target_project_name:
                    print(resolved_target_project_name)
                return EXIT_OK
            if getattr(args, "emit_target_relative_path", False):
                if resolved_target_relative_path:
                    print(resolved_target_relative_path)
                return EXIT_OK
            if getattr(args, "emit_target_bundle", False):
                if payload.get("emit_target_bundle_json"):
                    print(payload["emit_target_bundle_json"])
                return EXIT_OK
            if getattr(args, "emit_open_shell", False):
                if emit_open_command:
                    print(emit_open_command)
                return exit_code
            if getattr(args, "copy_open_command", False):
                if payload.get("copied_open_to_clipboard"):
                    print("Workspace hook-continue open command copied")
                    print(f"- copied_open_command: {payload.get('copied_open_command', '')}")
                else:
                    print("Workspace hook-continue open command copy failed")
                    if payload.get("copy_open_command_error"):
                        print(f"- copy_open_command_error: {payload['copy_open_command_error']}")
                    if emit_open_command:
                        print(f"- fallback_open_command: {emit_open_command}")
                return exit_code
            if getattr(args, "text_compact", False):
                print("Workspace hook-continue (compact)")
                print(f"- continue_strategy: {payload.get('continue_strategy', '')}")
                if payload.get("selected_project_name"):
                    print(f"- project: {payload['selected_project_name']}")
                if payload.get("dry_run"):
                    print("- dry_run: true")
                if payload.get("dry_run_summary"):
                    print(f"- target_summary: {payload['dry_run_summary']}")
                elif payload.get("continue_summary"):
                    print(f"- target_summary: {payload['continue_summary']}")
                if payload.get("dry_run_target_reason"):
                    print(f"- target_reason: {payload['dry_run_target_reason']}")
                elif payload.get("continue_reason"):
                    print(f"- target_reason: {payload['continue_reason']}")
                result_payload = payload.get("result") or {}
                if result_payload.get("hook_name"):
                    print(f"- hook_name: {result_payload['hook_name']}")
                if result_payload.get("target_path"):
                    print(f"- target_path: {result_payload['target_path']}")
                if payload.get("preferred_followup_command"):
                    print(f"- human_next_command: {payload['preferred_followup_command']}")
                if payload.get("dry_run_confirm_command"):
                    print(f"- runnable_next_command: {payload['dry_run_confirm_command']}")
                elif payload.get("recommended_next_command"):
                    print(f"- runnable_next_command: {payload['recommended_next_command']}")
                if payload.get("rerun_with_force_command"):
                    print(f"- force_next_command: {payload['rerun_with_force_command']}")
                if getattr(args, "inspect_target", False):
                    if payload.get("inspect_target_summary"):
                        print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
                    if payload.get("inspect_target_parent_summary"):
                        print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
                    target_inspection = payload.get("target_inspection") or {}
                    neighbor_names = list(payload.get("inspect_target_neighbor_names") or [])
                    if target_inspection.get("path"):
                        print(f"- inspected_target_path: {target_inspection['path']}")
                    print(f"- inspected_target_exists: {bool(target_inspection.get('exists'))}")
                    if neighbor_names:
                        print(f"- nearby_entries: {', '.join(neighbor_names)}")
                if getattr(args, "open_target", False):
                    if payload.get("open_target_summary"):
                        print(f"- open_target_summary: {payload['open_target_summary']}")
                    if payload.get("open_target_command"):
                        print(f"- open_target_command: {payload['open_target_command']}")
                if getattr(args, "open_now", False):
                    if payload.get("open_now_summary"):
                        print(f"- open_now_summary: {payload['open_now_summary']}")
                    open_now_result = payload.get("open_now_result") or {}
                    if open_now_result.get("path"):
                        print(f"- open_now_path: {open_now_result['path']}")
                    if open_now_result.get("exists") is not None:
                        print(f"- open_now_exists: {bool(open_now_result.get('exists'))}")
                    if open_now_result.get("line_count") is not None:
                        print(f"- open_now_line_count: {open_now_result['line_count']}")
                    if payload.get("open_now_preview"):
                        print(f"- open_now_preview: {payload['open_now_preview']}")
                return exit_code
            if getattr(args, "explain", False):
                print("Workspace hook-continue explain")
                if payload.get("continue_strategy"):
                    print(f"- continue_strategy: {payload['continue_strategy']}")
                if payload.get("selected_project_name"):
                    print(f"- project: {payload['selected_project_name']}")
                if payload.get("preferred_followup_command"):
                    print(f"- human_next_command: {payload['preferred_followup_command']}")
                if payload.get("dry_run_confirm_command"):
                    print(f"- runnable_next_command: {payload['dry_run_confirm_command']}")
                elif payload.get("recommended_next_command"):
                    print(f"- runnable_next_command: {payload['recommended_next_command']}")
                if payload.get("rerun_with_force_command"):
                    print(f"- force_next_command: {payload['rerun_with_force_command']}")
                blocks = payload.get("explanation_blocks") or []
                if blocks:
                    print("Explain:")
                    for item in blocks:
                        print(f"- {item.get('label', '')}: {item.get('summary', '')}")
                        if item.get("detail"):
                            print(f"  {item['detail']}")
                print("Next:")
                if payload.get("preferred_followup_command"):
                    print(f"- run {payload['preferred_followup_command']}")
                if payload.get("dry_run_confirm_command"):
                    print(f"- run {payload['dry_run_confirm_command']}")
                elif payload.get("recommended_next_command"):
                    print(f"- run {payload['recommended_next_command']}")
                if payload.get("rerun_with_force_command"):
                    print(f"- run {payload['rerun_with_force_command']}")
                return exit_code
            print("Workspace hook-continue")
            print(f"- continue_strategy: {payload.get('continue_strategy', '')}")
            if payload.get("selected_project_name"):
                print(f"- project: {payload['selected_project_name']}")
            if payload.get("dry_run"):
                print("- dry_run: true")
                if payload.get("dry_run_summary"):
                    print(f"- target_summary: {payload['dry_run_summary']}")
                if payload.get("dry_run_target_reason"):
                    print(f"- target_reason: {payload['dry_run_target_reason']}")
            elif payload.get("continue_summary"):
                print(f"- target_summary: {payload['continue_summary']}")
            elif payload.get("continue_reason"):
                print(f"- target_reason: {payload['continue_reason']}")
            if payload.get("preferred_followup_command"):
                print(f"- human_next_command: {payload['preferred_followup_command']}")
            result_payload = payload.get("result") or {}
            if result_payload.get("target_path"):
                print(f"- target_path: {result_payload['target_path']}")
            if result_payload.get("message"):
                print(f"- message: {result_payload['message']}")
            if payload.get("dry_run_confirm_command"):
                print(f"- runnable_next_command: {payload['dry_run_confirm_command']}")
            elif payload.get("recommended_next_command"):
                print(f"- runnable_next_command: {payload['recommended_next_command']}")
            if payload.get("rerun_with_force_command"):
                print(f"- force_next_command: {payload['rerun_with_force_command']}")
            if getattr(args, "inspect_target", False):
                if payload.get("inspect_target_summary"):
                    print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
                if payload.get("inspect_target_parent_summary"):
                    print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
                target_inspection = payload.get("target_inspection") or {}
                parent_inspection = payload.get("target_parent_inspection") or {}
                neighbor_names = list(payload.get("inspect_target_neighbor_names") or [])
                if target_inspection.get("path"):
                    print(f"- inspected_target_path: {target_inspection['path']}")
                if target_inspection.get("kind"):
                    print(f"- inspected_target_kind: {target_inspection['kind']}")
                if target_inspection.get("path") or target_inspection.get("kind"):
                    print(f"- inspected_target_exists: {bool(target_inspection.get('exists'))}")
                if parent_inspection.get("path"):
                    print(f"- inspected_target_parent_path: {parent_inspection['path']}")
                    print(f"- inspected_target_parent_exists: {bool(parent_inspection.get('exists'))}")
                    if parent_inspection.get("entry_count") is not None:
                        print(f"- inspected_target_parent_entry_count: {parent_inspection['entry_count']}")
                if neighbor_names:
                    print(f"- inspect_target_neighbor_names: {', '.join(neighbor_names)}")
            if getattr(args, "open_target", False):
                if payload.get("open_target_summary"):
                    print(f"- open_target_summary: {payload['open_target_summary']}")
                if payload.get("open_target_reason"):
                    print(f"- open_target_reason: {payload['open_target_reason']}")
                open_target = payload.get("open_target") or {}
                if open_target.get("path"):
                    print(f"- open_target_path: {open_target['path']}")
                    print(f"- open_target_exists: {bool(open_target.get('exists'))}")
                if payload.get("open_target_command"):
                    print(f"- open_target_command: {payload['open_target_command']}")
            if getattr(args, "open_now", False):
                if payload.get("open_now_summary"):
                    print(f"- open_now_summary: {payload['open_now_summary']}")
                if payload.get("open_now_reason"):
                    print(f"- open_now_reason: {payload['open_now_reason']}")
                open_now_result = payload.get("open_now_result") or {}
                if open_now_result.get("path"):
                    print(f"- open_now_path: {open_now_result['path']}")
                if open_now_result.get("kind"):
                    print(f"- open_now_kind: {open_now_result['kind']}")
                if open_now_result.get("exists") is not None:
                    print(f"- open_now_exists: {bool(open_now_result.get('exists'))}")
                if open_now_result.get("line_count") is not None:
                    print(f"- open_now_line_count: {open_now_result['line_count']}")
                if payload.get("open_now_preview"):
                    print(f"- open_now_preview: {payload['open_now_preview']}")
            if getattr(args, "explain", False):
                blocks = payload.get("explanation_blocks") or []
                if blocks:
                    print("Explain:")
                    for item in blocks:
                        print(f"- {item.get('label', '')}: {item.get('summary', '')}")
                        if item.get("detail"):
                            print(f"  {item['detail']}")
            print("Next:")
            if payload.get("recommended_next_command"):
                recommended = str(payload["recommended_next_command"]).strip()
                human = str(payload.get("preferred_followup_command") or "").strip()
                runnable = str(payload.get("dry_run_confirm_command") or "").strip()
                force_cmd = str(payload.get("rerun_with_force_command") or "").strip()
                if recommended and recommended not in {human, runnable, force_cmd}:
                    print(f"- {recommended}")
        return exit_code

    if getattr(args, "workspace_command", None) == "go":
        payload, exit_code = _run_workspace_go(base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print("Workspace go")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_workspace_action: {payload['executed_workspace_action']}")
            print(f"- recommended_workspace_reason: {payload['recommended_workspace_reason']}")
            print(f"- result_status: {payload['status']}")
            result_payload = payload.get("result") or {}
            if result_payload.get("project_path"):
                print(f"- project_path: {result_payload.get('project_path')}")
            if result_payload.get("build_id"):
                print(f"- build_id: {result_payload.get('build_id')}")
            if result_payload.get("managed_files_written") is not None:
                print(f"- managed_files_written: {result_payload.get('managed_files_written')}")
            if payload.get("preview_hint"):
                print(f"- preview_hint: {payload['preview_hint']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "workspace_command", None) != "status":
        return _emit_command_error(
            args,
            EXIT_USAGE,
            "invalid_usage",
            "supported workspace subcommands: status, summary, hooks, hook-init, hook-continue, preview, open-target, inspect-target, run-inspect-command, export-handoff, go, doctor, continue",
        )

    payload = _build_workspace_status_payload(base_url=args.base_url)
    if args.json:
        _print_json_payload(payload)
    else:
        print("Workspace status")
        print(f"- repo_root: {payload['repo_root']}")
        print(f"- cwd: {payload['cwd']}")
        print(f"- inside_ail_project: {str(payload['inside_ail_project']).lower()}")
        if payload.get("current_project"):
            project = payload["current_project"]
            print(f"- current_project_id: {project.get('project_id', '')}")
            print(f"- current_project_doctor_status: {project.get('doctor_status', '')}")
            print(f"- current_project_primary_action: {project.get('recommended_primary_action', '')}")
        if payload.get("readiness_snapshot"):
            readiness = payload["readiness_snapshot"]
            print(f"- readiness_status: {readiness.get('status', '')}")
            print(f"- readiness_stage: {readiness.get('stage', '')}")
        if payload.get("rc_checks"):
            rc = payload["rc_checks"]
            print(f"- rc_status: {rc.get('status', '')}")
            print(f"- rc_primary_action_converged: {rc.get('checks', {}).get('project_workbench_primary_action_converged')}")
        if payload.get("latest_trial_batch"):
            batch = payload["latest_trial_batch"]
            print(f"- latest_trial_batch_status: {batch.get('status', '')}")
            print(f"- latest_trial_batch_record_count: {batch.get('record_count', 0)}")
            print(f"- latest_trial_route_distribution: {batch.get('route_taken_distribution', {})}")
        print(f"- recommended_workspace_action: {payload['recommended_workspace_action']}")
        print(f"- recommended_workspace_reason: {payload['recommended_workspace_reason']}")
        print("Next:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return EXIT_OK


def cmd_compile(args: argparse.Namespace) -> int:
    ctx = ProjectContext.discover()
    if not args.cloud:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "only '--cloud' mode is supported in CLI v1")
    manifest_service = ManifestService()
    current_manifest = manifest_service.load_manifest(ctx.manifest_file)
    ail_source = ctx.source_file.read_text(encoding="utf-8")
    client = AILCloudClient(base_url=args.base_url)
    build_payload = client.compile_ail(ctx.project_id, ail_source, current_manifest)
    manifest_service.save_last_build(ctx.last_build_file, build_payload)
    diff = build_payload.get("diff_summary") or {}
    notices = _compile_notices(client)
    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "project_id": ctx.project_id,
                    "build_id": build_payload.get("build_id", ""),
                    "file_count": len(build_payload.get("files", [])),
                    "deleted_file_count": len(build_payload.get("deleted_files", [])),
                    "diff_summary": diff,
                    "cached_build_path": ctx.to_relative(ctx.last_build_file),
                    "cloud": _cloud_summary(client),
                    "notices": notices,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Cloud compile succeeded: build_id={build_payload.get('build_id', '')}")
        print(
            "Diff summary: "
            f"added={diff.get('added', 0)} "
            f"updated={diff.get('updated', 0)} "
            f"deleted={diff.get('deleted', 0)}"
        )
        print(f"Cached build payload to {ctx.to_relative(ctx.last_build_file)}")
        cloud = _cloud_summary(client)
        print(
            "Cloud mode: "
            f"base_url={cloud['base_url']} "
            f"api_variant={cloud['api_variant']} "
            f"endpoint={cloud['endpoint']}"
        )
        for notice in notices:
            print(f"note: {notice}")
    return EXIT_OK


def cmd_cloud(args: argparse.Namespace) -> int:
    if getattr(args, "cloud_command", None) != "status":
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported cloud subcommands: status")

    project_id = _resolve_project_id_arg(getattr(args, "project_id", None))
    payload = _build_cloud_status_payload(AILCloudClient(base_url=args.base_url), project_id=project_id)
    preview_handoff = _build_cloud_preview_handoff(payload, project_id=project_id, base_url=args.base_url)
    payload["preview_handoff"] = preview_handoff
    payload["website_preview_summary"] = preview_handoff.get("website_summary")
    payload["preview_hint"] = preview_handoff["preview_hint"]
    payload["open_targets"] = preview_handoff["open_targets"]
    payload["next_steps"] = preview_handoff["next_steps"]

    if args.json:
        _print_json_payload(payload)
    else:
        project_data = payload.get("project") or {}
        latest_build = payload.get("latest_build") or {}
        artifact = payload.get("latest_artifact") or {}
        cloud = payload.get("cloud") or {}
        project_cloud = cloud.get("project") or {}
        builds_cloud = cloud.get("builds") or {}
        build_cloud = cloud.get("build") or {}
        artifact_cloud = cloud.get("artifact") or {}
        print(f"Cloud status: {project_id}")
        print(f"- latest_build_id: {project_data.get('latest_build_id', '')}")
        print(f"- latest_manifest_version: {project_data.get('latest_manifest_version', '')}")
        print(f"- recent_build_count: {payload['recent_build_count']}")
        if latest_build:
            diff = latest_build.get("diff_summary") or {}
            print(
                "- latest_build: "
                f"status={latest_build.get('status', '')} "
                f"mode={latest_build.get('mode', '')} "
                f"created_at={latest_build.get('created_at', '')} "
                f"added={diff.get('added', 0)} "
                f"updated={diff.get('updated', 0)} "
                f"deleted={diff.get('deleted', 0)}"
            )
        if artifact:
            print(
                "- latest_artifact: "
                f"id={artifact.get('artifact_id', '')} "
                f"format={artifact.get('format', '')} "
                f"local_path={artifact.get('local_path', '')}"
            )
        print(
            "- cloud.project: "
            f"base_url={project_cloud['base_url']} "
            f"api_variant={project_cloud['api_variant']} "
            f"endpoint={project_cloud['endpoint']}"
        )
        print(
            "- cloud.builds: "
            f"base_url={builds_cloud['base_url']} "
            f"api_variant={builds_cloud['api_variant']} "
            f"endpoint={builds_cloud['endpoint']}"
        )
        if build_cloud:
            print(
                "- cloud.build: "
                f"base_url={build_cloud['base_url']} "
                f"api_variant={build_cloud['api_variant']} "
                f"endpoint={build_cloud['endpoint']}"
            )
        if artifact_cloud:
            print(
                "- cloud.artifact: "
                f"base_url={artifact_cloud['base_url']} "
                f"api_variant={artifact_cloud['api_variant']} "
                f"endpoint={artifact_cloud['endpoint']}"
            )
        print(f"- preview_hint: {preview_handoff['preview_hint']}")
        for item in preview_handoff["open_targets"][:3]:
            print(f"- open_target[{item['label']}]: {item['path']}")
    return EXIT_OK


def cmd_sync(args: argparse.Namespace) -> int:
    ctx = ProjectContext.discover()
    manifest_service = ManifestService()
    current_manifest = manifest_service.load_manifest(ctx.manifest_file)
    last_build = manifest_service.load_last_build(ctx.last_build_file)
    if not last_build or not last_build.get("files"):
        return _emit_command_error(args, EXIT_GENERAL_ERROR, "build_not_found", "No cached cloud build found. Run 'ail compile --cloud' first.")

    engine = SyncEngine(manifest_service)
    result = engine.sync(
        ctx,
        last_build,
        current_manifest,
        backup_and_overwrite=bool(args.backup_and_overwrite),
    )
    manifest_service.save_manifest(ctx.manifest_file, last_build["manifest"])
    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "build_id": last_build.get("build_id", ""),
                    "written": result.written,
                    "deleted": result.deleted,
                    "backups_created": result.backups_created,
                    "conflict_summary": result.conflict_summary,
                    "manifest_path": ctx.to_relative(ctx.manifest_file),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Sync applied successfully: written={result.written} deleted={result.deleted}")
        if result.backups_created:
            print("Backups created:")
            for item in result.backups_created:
                print(f"- {item}")
        if result.conflict_summary:
            print(f"Conflict summary: {result.conflict_summary}")
        print(f"Updated manifest: {ctx.to_relative(ctx.manifest_file)}")
    return EXIT_OK


def cmd_build(args: argparse.Namespace) -> int:
    if getattr(args, "build_command", None) != "show":
        if getattr(args, "build_command", None) != "artifact":
            return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported build subcommands: show, artifact")
        client = AILCloudClient(base_url=args.base_url)
        data = client.get_build_artifact(args.build_id)
        cloud = _query_cloud_summary(client)
        preview_handoff = _build_preview_handoff(
            artifact_path=str(data.get("local_path") or ""),
            build_id=args.build_id,
            base_url=args.base_url,
            include_build_artifact_step=False,
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "data": data,
                        "cloud": cloud,
                        "website_preview_summary": preview_handoff.get("website_summary"),
                        "preview_handoff": preview_handoff,
                        "preview_hint": preview_handoff["preview_hint"],
                        "open_targets": preview_handoff["open_targets"],
                        "next_steps": preview_handoff["next_steps"],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Build artifact: {data.get('artifact_id', '')}")
            print(f"- build_id: {data.get('build_id', '')}")
            print(f"- format: {data.get('format', '')}")
            print(f"- sha256: {data.get('sha256', '')}")
            print(f"- local_path: {data.get('local_path', '')}")
            print(f"- download_url: {data.get('download_url', '')}")
            print(f"- expires_at: {data.get('expires_at', '')}")
            print(
                "- cloud: "
                f"base_url={cloud['base_url']} "
                f"api_variant={cloud['api_variant']} "
                f"endpoint={cloud['endpoint']}"
            )
            print(f"- preview_hint: {preview_handoff['preview_hint']}")
            for item in preview_handoff["open_targets"][:2]:
                print(f"- open_target[{item['label']}]: {item['path']}")
        return EXIT_OK
    client = AILCloudClient(base_url=args.base_url)
    data = client.get_build(args.build_id)
    cloud = _query_cloud_summary(client)
    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "data": data,
                    "cloud": cloud,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Build: {data.get('build_id', '')}")
        print(f"- project_id: {data.get('project_id', '')}")
        print(f"- mode: {data.get('mode', '')}")
        print(f"- status: {data.get('status', '')}")
        print(f"- created_at: {data.get('created_at', '')}")
        diff = data.get("diff_summary") or {}
        print(
            "- diff_summary: "
            f"added={diff.get('added', 0)} "
            f"updated={diff.get('updated', 0)} "
            f"deleted={diff.get('deleted', 0)}"
        )
        print(f"- artifact_available: {data.get('artifact_available', False)}")
        print(f"- manifest_version: {data.get('manifest_version', '')}")
        print(
            "- cloud: "
            f"base_url={cloud['base_url']} "
            f"api_variant={cloud['api_variant']} "
            f"endpoint={cloud['endpoint']}"
        )
    return EXIT_OK


def cmd_project(args: argparse.Namespace) -> int:
    if getattr(args, "project_command", None) == "go":
        ctx = ProjectContext.discover()
        payload, exit_code = _run_project_go(ctx, base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project go: {ctx.project_id}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_primary_action: {payload['executed_primary_action']}")
            print(f"- recommended_primary_reason: {payload['recommended_primary_reason']}")
            print(f"- result_status: {payload['status']}")
            result_payload = payload.get("result") or {}
            if result_payload.get("build_id"):
                print(f"- build_id: {result_payload.get('build_id')}")
            if result_payload.get("managed_files_written") is not None:
                print(f"- managed_files_written: {result_payload.get('managed_files_written')}")
            if payload.get("preview_hint"):
                print(f"- preview_hint: {payload['preview_hint']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "continue":
        action_count = (
            int(bool(getattr(args, "compile_sync", False)))
            + int(bool(getattr(args, "diagnose_compile_sync", False)))
            + int(bool(getattr(args, "auto_repair_compile_sync", False)))
        )
        if action_count != 1:
            return _emit_command_error(
                args,
                EXIT_USAGE,
                "invalid_usage",
                "use exactly one continue action: --compile-sync, --diagnose-compile-sync, or --auto-repair-compile-sync",
            )

        ctx = ProjectContext.discover()
        if getattr(args, "diagnose_compile_sync", False):
            repair_mod = load_repair_module()
            ail_source = ctx.source_file.read_text(encoding="utf-8")
            requirement = _default_requirement_for_ail(repair_mod, ail_source)
            diagnosis = repair_mod.diagnose(requirement, ail_source)
            if diagnosis["compile_recommended"] != "yes":
                payload = {
                    "status": "validation_failed",
                    "project_id": ctx.project_id,
                    "project_root": str(ctx.root),
                    "action": "diagnose_compile_sync",
                    "requirement": requirement,
                    "diagnosis": {
                        key: value
                        for key, value in diagnosis.items()
                        if key != "parsed"
                    },
                    "next_steps": [
                        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli diagnose {ctx.source_file} --json",
                        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli repair {ctx.source_file} --write --json",
                        "rerun project continue --diagnose-compile-sync after the source becomes a compile candidate",
                    ],
                }
                if args.json:
                    _print_json_payload(payload)
                else:
                    print(f"Project continue halted: {ctx.project_id}")
                    print("- action: diagnose_compile_sync")
                    print("- result: validation_failed")
                    print(f"- detected_profile: {diagnosis['detected_profile']}")
                    print(f"- compile_recommended: {diagnosis['compile_recommended']}")
                    print("Next:")
                    for step in payload["next_steps"]:
                        print(f"- {step}")
                return EXIT_VALIDATION
        elif getattr(args, "auto_repair_compile_sync", False):
            repair_mod = load_repair_module()
            ail_source = ctx.source_file.read_text(encoding="utf-8")
            requirement = _default_requirement_for_ail(repair_mod, ail_source)
            diagnosis_before = repair_mod.diagnose(requirement, ail_source)
            auto_repair_used = False
            if diagnosis_before["compile_recommended"] != "yes":
                repaired = repair_mod.repair(requirement, ail_source)
                ctx.source_file.write_text(repaired.rstrip() + "\n", encoding="utf-8")
                auto_repair_used = True
                diagnosis_after_raw = repair_mod.diagnose(requirement, repaired)
                if diagnosis_after_raw["compile_recommended"] != "yes":
                    payload = {
                        "status": "validation_failed",
                        "project_id": ctx.project_id,
                        "project_root": str(ctx.root),
                        "action": "auto_repair_compile_sync",
                        "auto_repair_used": auto_repair_used,
                        "requirement": requirement,
                        "diagnosis_before": {
                            key: value
                            for key, value in diagnosis_before.items()
                            if key != "parsed"
                        },
                        "diagnosis_after": {
                            key: value
                            for key, value in diagnosis_after_raw.items()
                            if key != "parsed"
                        },
                        "next_steps": [
                            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli diagnose {ctx.source_file} --json",
                            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project doctor --fix-plan --base-url {args.base_url or 'embedded://local'} --json",
                            "inspect the repaired source before attempting another compile-and-sync pass",
                        ],
                    }
                    if args.json:
                        _print_json_payload(payload)
                    else:
                        print(f"Project continue halted: {ctx.project_id}")
                        print("- action: auto_repair_compile_sync")
                        print("- result: validation_failed")
                        print("- auto_repair_used: yes")
                        print(f"- detected_profile_after: {diagnosis_after_raw['detected_profile']}")
                        print(f"- compile_recommended_after: {diagnosis_after_raw['compile_recommended']}")
                        print("Next:")
                        for step in payload["next_steps"]:
                            print(f"- {step}")
                    return EXIT_VALIDATION
                diagnosis_after = {
                    key: value
                    for key, value in diagnosis_after_raw.items()
                    if key != "parsed"
                }
            else:
                diagnosis_after = {
                    key: value
                    for key, value in diagnosis_before.items()
                    if key != "parsed"
                }

        payload = _run_project_compile_sync(ctx, base_url=args.base_url)
        if getattr(args, "diagnose_compile_sync", False):
            payload["action"] = "diagnose_compile_sync"
            payload["diagnosed_first"] = True
        elif getattr(args, "auto_repair_compile_sync", False):
            payload["action"] = "auto_repair_compile_sync"
            payload["auto_repair_used"] = auto_repair_used
            payload["requirement"] = requirement
            payload["diagnosis_before"] = {
                key: value
                for key, value in diagnosis_before.items()
                if key != "parsed"
            }
            payload["diagnosis_after"] = diagnosis_after
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project continue completed: {ctx.project_id}")
            print(f"- action: {payload['action']}")
            if getattr(args, "auto_repair_compile_sync", False):
                print(f"- auto_repair_used: {'yes' if payload['auto_repair_used'] else 'no'}")
            print(f"- build_id: {payload['build_id']}")
            print(f"- managed_files_written: {payload['managed_files_written']}")
            print(f"- deleted: {payload['deleted']}")
            print(
                "- cloud: "
                f"base_url={payload['cloud']['base_url']} "
                f"api_variant={payload['cloud']['api_variant']} "
                f"endpoint={payload['cloud']['endpoint']}"
            )
            print(f"- preview_hint: {payload['preview_hint']}")
            for notice in payload["compile_notices"]:
                print(f"note: {notice}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "project_command", None) == "check":
        ctx = ProjectContext.discover()
        payload = _build_project_check_payload(ctx, base_url=args.base_url)

        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project check: {ctx.project_id}")
            print(f"- status: {payload['status']}")
            print(f"- project_root: {ctx.root}")
            checks = payload["checks"]
            manifest_summary = payload["manifest_summary"]
            last_build_summary = payload["last_build_summary"]
            cloud_status_error = payload["cloud_status_error"]
            sync_conflict_error = payload["sync_conflict_error"]
            sync_conflict_summary = payload["sync_conflict_summary"]
            sync_conflicts = payload["sync_conflicts"]
            print(
                "- checks: "
                f"source_exists={checks['source_exists']} "
                f"manifest_exists={checks['manifest_exists']} "
                f"last_build_exists={checks['last_build_exists']} "
                f"cached_build_files_present={checks['cached_build_files_present']} "
                f"cloud_status_available={checks['cloud_status_available']} "
                f"sync_conflicts_detected={checks['sync_conflicts_detected']}"
            )
            print(
                "- manifest: "
                f"version={manifest_summary['manifest_version']} "
                f"current_build_id={manifest_summary['current_build_id']} "
                f"managed_file_count={manifest_summary['managed_file_count']}"
            )
            print(
                "- last_build: "
                f"build_id={last_build_summary['build_id']} "
                f"status={last_build_summary['status']} "
                f"created_at={last_build_summary['created_at']} "
                f"file_count={last_build_summary['file_count']} "
                f"deleted_file_count={last_build_summary['deleted_file_count']}"
            )
            if cloud_status_error:
                print(f"- cloud_status_error: {cloud_status_error}")
            if sync_conflict_error:
                print(f"- sync_conflict_error: {sync_conflict_error}")
            if sync_conflicts:
                if sync_conflict_summary:
                    print(f"- sync_conflict_message: {sync_conflict_summary['message']}")
                    print(f"- blocks_existing_output_review: {str(sync_conflict_summary['blocks_existing_output_review']).lower()}")
                print("Managed-file drift:")
                for item in sync_conflicts:
                    print(f"- {item['path']} | Level {item['level']} | {item.get('summary') or item['reason']}")
            print(f"- preview_hint: {payload['preview_hint']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")

        if payload["status"] == "error":
            return EXIT_VALIDATION
        if payload["status"] == "conflict":
            return EXIT_CONFLICT
        return EXIT_OK

    if getattr(args, "project_command", None) == "doctor":
        ctx = ProjectContext.discover()
        payload, fix_plan, exit_code = _build_project_doctor_payload(
            ctx,
            base_url=args.base_url,
            include_fix_plan=getattr(args, "fix_plan", False),
            apply_safe_fixes=getattr(args, "apply_safe_fixes", False),
            and_continue=getattr(args, "and_continue", False),
        )

        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project doctor: {ctx.project_id}")
            print(f"- status: {payload['status']}")
            print(f"- recommended_action: {payload['recommended_action']}")
            for finding in payload["findings"]:
                print(f"- finding: {finding}")
            if payload["source_diagnosis"]:
                diagnosis = payload["source_diagnosis"]["diagnosis"]
                print(
                    "- source_diagnosis: "
                    f"detected_profile={diagnosis.get('detected_profile', '')} "
                    f"compile_recommended={diagnosis.get('compile_recommended', '')}"
                )
            if getattr(args, "fix_plan", False):
                print("Fix plan:")
                for item in fix_plan:
                    print(f"- {item['step']}: {item['title']}")
                    print(f"  command: {item['command']}")
            if getattr(args, "apply_safe_fixes", False):
                safe_fix_result = payload.get("safe_fix_result") or {}
                print(f"- safe_fix_status: {safe_fix_result.get('status', 'unknown')}")
                for item in safe_fix_result.get("applied_fixes", []):
                    print(f"- applied_fix: {item}")
            if getattr(args, "and_continue", False):
                continue_result = payload.get("continue_result") or {}
                print(f"- continue_status: {continue_result.get('status', 'unknown')}")
                if continue_result.get("status") == "ok":
                    print(f"- build_id: {continue_result.get('build_id', '')}")
                    print(f"- managed_files_written: {continue_result.get('managed_files_written', 0)}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")

        return exit_code

    if getattr(args, "project_command", None) == "summary":
        ctx = ProjectContext.discover()
        summary = _build_project_summary_payload(
            ctx,
            base_url=args.base_url,
            project_id=getattr(args, "project_id", None),
        )
        if args.json:
            _print_json_payload(summary)
        else:
            print(f"Project summary: {summary['project_id']}")
            print(f"- project_root: {summary['project_root']}")
            print(f"- source_of_truth: {summary['source_of_truth']}")
            print(f"- manifest: {summary['manifest']}")
            print(f"- last_build: {summary['last_build']}")
            print(f"- recommended_primary_action: {summary['recommended_primary_action']}")
            print(f"- recommended_primary_reason: {summary['recommended_primary_reason']}")
            print(f"- preview_hint: {summary['preview_hint']}")
            hook_catalog = summary.get("hook_catalog") or {}
            print(
                "- hook_catalog: "
                f"exists={hook_catalog.get('exists', False)} "
                f"pages={hook_catalog.get('page_count', 0)} "
                f"sections={hook_catalog.get('section_hook_count', 0)} "
                f"slots={hook_catalog.get('slot_hook_count', 0)}"
            )
            print("Open targets:")
            for item in summary["open_targets"]:
                print(f"- {item['label']}: {item['path']}")
            print("Next:")
            for step in summary["next_steps"]:
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "project_command", None) == "hooks":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_hooks_payload(
            ctx,
            page_key=getattr(args, "page_key", None),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project hooks: {payload['project_id']}")
            print(f"- project_root: {payload['project_root']}")
            print(f"- hook_catalog_json: {payload['hook_catalog']['json_path']}")
            print(f"- hook_catalog_markdown: {payload['hook_catalog']['markdown_path']}")
            print(f"- page_count: {payload['hook_catalog']['page_count']}")
            print(f"- section_hook_count: {payload['hook_catalog']['section_hook_count']}")
            print(f"- slot_hook_count: {payload['hook_catalog']['slot_hook_count']}")
            if payload['status'] != 'ok':
                print(f"- status: {payload['status']}")
                print(f"- message: {payload.get('message', '')}")
            if payload.get('selected_page'):
                selected = payload['selected_page']
                print(
                    "- selected_page: "
                    f"{selected.get('page_key', '')} "
                    f"({selected.get('page_name', '')} @ {selected.get('page_path', '')})"
                )
                runtime_context = (selected.get('context') or {})
                page_runtime = ((runtime_context.get('page') or {}).get('runtime') or [])
                print(f"- selected_page_runtime_keys: {', '.join(page_runtime) if page_runtime else '(none)'}")
            else:
                print(f"- available_page_keys: {', '.join(payload.get('available_page_keys') or [])}")
            if payload.get("recommended_hook_suggest_command"):
                print(f"- recommended_hook_suggest_command: {payload['recommended_hook_suggest_command']}")
            if payload.get("recommended_workspace_hook_suggest_command"):
                print(f"- recommended_workspace_hook_suggest_command: {payload['recommended_workspace_hook_suggest_command']}")
            if payload.get("recommended_workspace_hook_pick_command"):
                print(f"- recommended_workspace_hook_pick_command: {payload['recommended_workspace_hook_pick_command']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "hook-guide":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_hook_guide_payload(ctx)
        preferred_command = str(payload.get("preferred_project_hook_command") or "").strip()
        preferred_run_command = str(payload.get("preferred_project_hook_run_command") or preferred_command or "").strip()
        if getattr(args, "run_command", False):
            payload["run_command"] = preferred_run_command or None
            payload["run_command_requires_confirmation"] = True
            payload["run_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_command_confirm_command"] = f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-guide --run-command --yes --json"
            if getattr(args, "yes", False):
                if preferred_run_command:
                    ran_ok, run_stdout, run_stderr, run_exit_code, run_result = _run_shell_command(preferred_run_command)
                    payload["ran_command"] = ran_ok
                    payload["run_command_exit_code"] = run_exit_code
                    payload["run_command_stdout"] = run_stdout
                    payload["run_command_stderr"] = run_stderr
                    payload["run_result"] = run_result
                else:
                    payload["ran_command"] = False
                    payload["run_command_exit_code"] = EXIT_USAGE
                    payload["run_command_stdout"] = ""
                    payload["run_command_stderr"] = ""
                    payload["run_result"] = None
                    payload["run_command_warning"] = "No preferred project hook-guide command was available to execute."
            else:
                payload["ran_command"] = False
                payload["run_command_exit_code"] = EXIT_OK
                payload["run_command_stdout"] = ""
                payload["run_command_stderr"] = ""
                payload["run_result"] = None
                payload["run_command_warning"] = "Confirmation required. Re-run with --yes to execute the preferred project hook-guide command."
        if getattr(args, "run_command", False) and args.json:
            _print_json_payload(payload)
            return int(payload.get("run_command_exit_code", exit_code)) if payload.get("run_command_confirmed") else exit_code
        if getattr(args, "run_command", False):
            if payload.get("run_command_confirmed"):
                if payload.get("ran_command"):
                    print("Project hook-guide command executed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_result") and isinstance(payload["run_result"], dict):
                        result = payload["run_result"]
                        print(f"- run_result_entrypoint: {result.get('entrypoint', '')}")
                else:
                    print("Project hook-guide command execution failed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_command_stderr"):
                        print(f"- run_command_stderr: {payload['run_command_stderr']}")
                return int(payload.get("run_command_exit_code", exit_code))
            print("Project hook-guide command ready")
            print(f"- run_command: {payload.get('run_command', '')}")
            if payload.get("run_command_warning"):
                print(f"- run_command_warning: {payload['run_command_warning']}")
            if payload.get("run_command_confirm_command"):
                print(f"- run_command_confirm_command: {payload['run_command_confirm_command']}")
            return exit_code
        if getattr(args, "emit_shell", False):
            if preferred_command:
                print(preferred_command)
                return EXIT_OK
            print("No preferred project hook-guide command was available.")
            return EXIT_USAGE
        if getattr(args, "copy_command", False):
            copied_ok, copied_error = _copy_text_to_clipboard(preferred_command) if preferred_command else (False, "No preferred project hook-guide command was available to copy.")
            if copied_ok:
                print("Project hook-guide command copied")
                print(f"- copied_command: {preferred_command}")
                return EXIT_OK
            print("Project hook-guide command copy failed")
            if copied_error:
                print(f"- copy_command_error: {copied_error}")
            if preferred_command:
                print(f"- fallback_command: {preferred_command}")
            return EXIT_USAGE
        if args.json:
            _print_json_payload(payload)
        else:
            print("Project hook-guide")
            print(f"- project_root: {payload['project_root']}")
            if payload.get("recommended_page_key"):
                print(f"- recommended_page_key: {payload['recommended_page_key']}")
            if payload.get("preferred_project_hook_command"):
                print(f"- human_next_command: {payload['preferred_project_hook_command']}")
            if payload.get("preferred_project_hook_run_command"):
                print(f"- runnable_next_command: {payload['preferred_project_hook_run_command']}")
            if payload.get("preferred_project_hook_reason"):
                print(f"- human_next_reason: {payload['preferred_project_hook_reason']}")
            if payload.get("preferred_project_hook_run_command") and payload.get("preferred_project_hook_command") and payload.get("preferred_project_hook_run_command") != payload.get("preferred_project_hook_command"):
                print("- runnable_next_reason: The runnable path stays on a JSON-safe suggestion route so it can be executed and parsed reliably.")
            print(f"- cheat_sheet_path: {payload['cheat_sheet_path']}")
            print("Guide paths:")
            for section in payload.get("guide_sections") or []:
                print(f"- {section.get('label', '')}: {section.get('summary', '')}")
                if section.get("command"):
                    print(f"  {section['command']}")
            print("Next:")
            if payload.get("preferred_project_hook_command"):
                print(f"- run {payload['preferred_project_hook_command']}")
            if payload.get("preferred_project_hook_run_command"):
                print(f"- run {payload['preferred_project_hook_run_command']}")
            print(f"- inspect {payload['cheat_sheet_path']}")
        return exit_code

    if getattr(args, "project_command", None) == "hook-init":
        if getattr(args, "run_command", False) and getattr(args, "run_open_command", False):
            return _emit_command_error(
                args,
                EXIT_USAGE,
                "invalid_usage",
                "choose only one of --run-command or --run-open-command",
            )
        ctx = ProjectContext.discover()
        payload, exit_code = _run_project_hook_init(
            ctx,
            hook_name=getattr(args, "hook_name", ""),
            template_kind=getattr(args, "template", "vue"),
            suggest=getattr(args, "suggest", False),
            last_suggest=getattr(args, "last_suggest", False),
            open_catalog=getattr(args, "open_catalog", False),
            page_key_filter=getattr(args, "page_key", None),
            section_key_filter=getattr(args, "section_key", None),
            slot_key_filter=getattr(args, "slot_key", None),
            reuse_last_suggest=getattr(args, "reuse_last_suggest", False),
            pick=getattr(args, "pick", False),
            pick_recommended=getattr(args, "pick_recommended", False),
            pick_index=getattr(args, "pick_index", None),
            dry_run=getattr(args, "dry_run", False),
            force=getattr(args, "force", False),
        )
        project_emit_confirm_command = (
            payload.get("rerun_without_dry_run_command")
            or (
                _build_project_hook_init_command(
                    str(
                        payload.get("hook_name")
                        or payload.get("requested_hook_name")
                        or getattr(args, "hook_name", "")
                        or ""
                    ),
                    template_kind=str(payload.get("requested_template") or "auto"),
                    force=bool(getattr(args, "force", False)),
                )
                if getattr(args, "dry_run", False)
                and str(
                    payload.get("hook_name")
                    or payload.get("requested_hook_name")
                    or getattr(args, "hook_name", "")
                    or ""
                ).strip()
                else ""
            )
            or ""
        )
        project_emit_target_path = payload.get("target_path") or ""
        project_emit_target_dir = str(Path(project_emit_target_path).parent) if project_emit_target_path else ""
        project_emit_target_project_root = str(payload.get("project_root") or "").strip()
        project_emit_target_project_name = Path(project_emit_target_project_root).name if project_emit_target_project_root else ""
        project_emit_target_relative_path = payload.get("target_relative_path") or ""
        project_emit_open_command = f"inspect {project_emit_target_path}" if project_emit_target_path else ""
        if getattr(args, "inspect_target", False):
            if project_emit_target_path:
                target = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": project_emit_target_path,
                    "exists": Path(project_emit_target_path).exists(),
                }
                parent = {
                    "label": "hook_target_parent",
                    "kind": "directory",
                    "path": str(Path(project_emit_target_path).parent),
                    "exists": Path(project_emit_target_path).parent.exists(),
                }
                payload["target_inspection"] = _inspect_resolved_target(target)
                payload["target_parent_inspection"] = _inspect_resolved_target(parent)
                payload["inspect_target_summary"] = f"Inspected the resolved hook-init target {Path(project_emit_target_path).name} and its parent directory."
                payload["inspect_target_parent_summary"] = f"Parent directory: {Path(project_emit_target_path).parent}"
            else:
                payload["target_inspection"] = None
                payload["target_parent_inspection"] = None
                payload["inspect_target_summary"] = "No hook-init target path was available to inspect."
                payload["inspect_target_parent_summary"] = ""
        if getattr(args, "open_target", False):
            if project_emit_target_path:
                target_path_obj = Path(project_emit_target_path)
                payload["open_target"] = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": str(target_path_obj),
                    "exists": target_path_obj.exists(),
                }
                payload["open_target_command"] = f"inspect {target_path_obj}"
                payload["open_target_summary"] = f"Open the resolved hook-init target {target_path_obj.name}."
                payload["open_target_reason"] = "The hook-init flow already resolved one concrete durable hook file path, so opening that file is the shortest next inspection step."
            else:
                payload["open_target"] = None
                payload["open_target_command"] = ""
                payload["open_target_summary"] = "No hook-init target path was available to open."
                payload["open_target_reason"] = "The hook-init flow did not resolve a concrete hook file path."
        if getattr(args, "open_now", False):
            if project_emit_target_path:
                target = {
                    "label": "hook_target",
                    "kind": "file",
                    "path": project_emit_target_path,
                    "exists": Path(project_emit_target_path).exists(),
                }
                payload["open_now"] = True
                payload["open_now_result"] = _inspect_resolved_target(target)
                preview_lines = [
                    line.strip()
                    for line in str((payload["open_now_result"] or {}).get("content_preview") or "").splitlines()
                    if line.strip()
                ]
                payload["open_now_preview"] = (preview_lines[0][:160] if preview_lines else "")
                payload["open_now_summary"] = f"Inspected the resolved hook-init target {Path(project_emit_target_path).name} inline."
                payload["open_now_reason"] = "The hook-init flow already resolved one concrete hook file path, so the CLI can inspect that file directly without an extra command."
            else:
                payload["open_now"] = True
                payload["open_now_result"] = None
                payload["open_now_preview"] = ""
                payload["open_now_summary"] = "No hook-init target path was available to inspect inline."
                payload["open_now_reason"] = "The hook-init flow did not resolve a concrete hook file path."
        project_emit_command = project_emit_confirm_command or None
        payload["emit_command"] = project_emit_command
        payload["emit_confirm_command"] = project_emit_confirm_command or None
        payload["emit_target_path"] = project_emit_target_path or None
        payload["emit_target_dir"] = project_emit_target_dir or None
        payload["emit_target_project_root"] = project_emit_target_project_root or None
        payload["emit_target_project_name"] = project_emit_target_project_name or None
        payload["emit_target_relative_path"] = project_emit_target_relative_path or None
        payload["emit_target_bundle"] = {
            "target_path": project_emit_target_path or None,
            "target_dir": project_emit_target_dir or None,
            "target_project_root": project_emit_target_project_root or None,
            "target_project_name": project_emit_target_project_name or None,
            "target_relative_path": project_emit_target_relative_path or None,
            "open_command": project_emit_open_command or None,
            "confirm_command": project_emit_confirm_command or None,
        }
        payload["emit_target_bundle_json"] = json.dumps(payload["emit_target_bundle"], ensure_ascii=False)
        if getattr(args, "copy_command", False):
            copied_command_ok, copied_command_error = _copy_text_to_clipboard(project_emit_command) if project_emit_command else (False, "No hook-init next command was available to copy.")
            payload["copied_command"] = project_emit_command
            payload["copied_command_to_clipboard"] = copied_command_ok
            payload["copy_command_error"] = copied_command_error or None
        if getattr(args, "copy_confirm_command", False):
            copied_confirm_ok, copied_confirm_error = _copy_text_to_clipboard(project_emit_confirm_command) if project_emit_confirm_command else (False, "No hook-init confirm command was available to copy.")
            payload["copied_confirm_command"] = project_emit_confirm_command or None
            payload["copied_confirm_to_clipboard"] = copied_confirm_ok
            payload["copy_confirm_command_error"] = copied_confirm_error or None
        if getattr(args, "copy_target_path", False):
            copied_target_ok, copied_target_error = _copy_text_to_clipboard(project_emit_target_path) if project_emit_target_path else (False, "No hook-init target path was available to copy.")
            payload["copied_target_path"] = project_emit_target_path or None
            payload["copied_target_path_to_clipboard"] = copied_target_ok
            payload["copy_target_path_error"] = copied_target_error or None
        if getattr(args, "copy_target_dir", False):
            copied_target_dir_ok, copied_target_dir_error = _copy_text_to_clipboard(project_emit_target_dir) if project_emit_target_dir else (False, "No hook-init target directory was available to copy.")
            payload["copied_target_dir"] = project_emit_target_dir or None
            payload["copied_target_dir_to_clipboard"] = copied_target_dir_ok
            payload["copy_target_dir_error"] = copied_target_dir_error or None
        if getattr(args, "copy_target_project_root", False):
            copied_target_project_root_ok, copied_target_project_root_error = _copy_text_to_clipboard(project_emit_target_project_root) if project_emit_target_project_root else (False, "No hook-init target project root was available to copy.")
            payload["copied_target_project_root"] = project_emit_target_project_root or None
            payload["copied_target_project_root_to_clipboard"] = copied_target_project_root_ok
            payload["copy_target_project_root_error"] = copied_target_project_root_error or None
        if getattr(args, "copy_target_project_name", False):
            copied_target_project_name_ok, copied_target_project_name_error = _copy_text_to_clipboard(project_emit_target_project_name) if project_emit_target_project_name else (False, "No hook-init target project name was available to copy.")
            payload["copied_target_project_name"] = project_emit_target_project_name or None
            payload["copied_target_project_name_to_clipboard"] = copied_target_project_name_ok
            payload["copy_target_project_name_error"] = copied_target_project_name_error or None
        if getattr(args, "copy_target_relative_path", False):
            copied_target_relative_ok, copied_target_relative_error = _copy_text_to_clipboard(project_emit_target_relative_path) if project_emit_target_relative_path else (False, "No hook-init target relative path was available to copy.")
            payload["copied_target_relative_path"] = project_emit_target_relative_path or None
            payload["copied_target_relative_path_to_clipboard"] = copied_target_relative_ok
            payload["copy_target_relative_path_error"] = copied_target_relative_error or None
        if getattr(args, "copy_target_bundle", False):
            copied_target_bundle_ok, copied_target_bundle_error = _copy_text_to_clipboard(payload["emit_target_bundle_json"]) if payload.get("emit_target_bundle_json") else (False, "No hook-init target bundle was available to copy.")
            payload["copied_target_bundle"] = payload.get("emit_target_bundle")
            payload["copied_target_bundle_json"] = payload.get("emit_target_bundle_json")
            payload["copied_target_bundle_to_clipboard"] = copied_target_bundle_ok
            payload["copy_target_bundle_error"] = copied_target_bundle_error or None
        if getattr(args, "copy_open_command", False):
            copied_open_ok, copied_open_error = _copy_text_to_clipboard(project_emit_open_command) if project_emit_open_command else (False, "No hook-init open command was available to copy.")
            payload["copied_open_command"] = project_emit_open_command or None
            payload["copied_open_to_clipboard"] = copied_open_ok
            payload["copy_open_command_error"] = copied_open_error or None
        if getattr(args, "run_open_command", False):
            payload["run_open_command"] = project_emit_open_command or None
            payload["run_open_command_requires_confirmation"] = True
            payload["run_open_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_open_command_confirm_command"] = _build_project_hook_init_run_open_command(
                payload.get("requested_hook_name") or "",
                template_kind=str(payload.get("requested_template") or "auto"),
                dry_run=bool(getattr(args, "dry_run", False)),
                force=bool(getattr(args, "force", False)),
                yes=True,
            )
            if getattr(args, "yes", False):
                if project_emit_target_path:
                    target = {
                        "label": "hook_target",
                        "kind": "file",
                        "path": project_emit_target_path,
                        "exists": Path(project_emit_target_path).exists(),
                    }
                    payload["ran_open_command"] = True
                    payload["run_open_command_exit_code"] = EXIT_OK
                    payload["run_open_result"] = _inspect_resolved_target(target)
                    payload["run_open_command_warning"] = None
                else:
                    payload["ran_open_command"] = False
                    payload["run_open_command_exit_code"] = EXIT_USAGE
                    payload["run_open_result"] = None
                    payload["run_open_command_warning"] = "No hook-init target path was available to inspect."
            else:
                payload["ran_open_command"] = False
                payload["run_open_command_exit_code"] = EXIT_OK
                payload["run_open_result"] = None
                payload["run_open_command_warning"] = "Confirmation required. Re-run with --yes to execute the resolved hook-init open step."
        if getattr(args, "run_command", False):
            payload["run_command"] = project_emit_command or None
            payload["run_command_requires_confirmation"] = True
            payload["run_command_confirmed"] = bool(getattr(args, "yes", False))
            payload["run_command_confirm_command"] = _build_project_hook_init_run_command(
                payload.get("requested_hook_name") or "",
                template_kind=str(payload.get("requested_template") or "auto"),
                dry_run=bool(getattr(args, "dry_run", False)),
                force=bool(getattr(args, "force", False)),
                yes=True,
            )
            if getattr(args, "yes", False):
                ran_ok, run_stdout, run_stderr, run_exit_code, run_result = _run_shell_command(project_emit_command or "")
                payload["ran_command"] = ran_ok
                payload["run_command_exit_code"] = run_exit_code
                payload["run_command_stdout"] = run_stdout
                payload["run_command_stderr"] = run_stderr
                payload["run_result"] = run_result
            else:
                payload["ran_command"] = False
                payload["run_command_exit_code"] = EXIT_OK
                payload["run_command_stdout"] = ""
                payload["run_command_stderr"] = ""
                payload["run_result"] = None
                payload["run_command_warning"] = "Confirmation required. Re-run with --yes to execute the selected hook-init next command."
        if args.json:
            _print_json_payload(payload)
        elif getattr(args, "run_command", False):
            if payload.get("run_command_confirmed"):
                if payload.get("ran_command"):
                    print("Project hook-init command executed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_result") and isinstance(payload["run_result"], dict):
                        result = payload["run_result"]
                        print(f"- run_result_entrypoint: {result.get('entrypoint', '')}")
                        if result.get("target_path"):
                            print(f"- run_result_target_path: {result['target_path']}")
                        if result.get("hook_name"):
                            print(f"- run_result_hook_name: {result['hook_name']}")
                else:
                    print("Project hook-init command execution failed")
                    print(f"- run_command: {payload.get('run_command', '')}")
                    print(f"- run_command_exit_code: {payload.get('run_command_exit_code', 0)}")
                    if payload.get("run_command_stderr"):
                        print(f"- run_command_stderr: {payload['run_command_stderr'].strip()}")
                    elif payload.get("run_command_stdout"):
                        print(f"- run_command_stdout: {payload['run_command_stdout'].strip()}")
                return int(payload.get("run_command_exit_code", exit_code))
            print("Project hook-init command ready")
            print(f"- run_command: {payload.get('run_command', '')}")
            if payload.get("run_command_warning"):
                print(f"- run_command_warning: {payload['run_command_warning']}")
            if payload.get("run_command_confirm_command"):
                print(f"- run_command_confirm_command: {payload['run_command_confirm_command']}")
            return exit_code
        elif getattr(args, "run_open_command", False):
            if payload.get("run_open_command_confirmed"):
                if payload.get("ran_open_command"):
                    print("Project hook-init open command executed")
                    print(f"- run_open_command: {payload.get('run_open_command', '')}")
                    print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                    run_open_result = payload.get("run_open_result") or {}
                    if run_open_result.get("path"):
                        print(f"- run_open_path: {run_open_result['path']}")
                    if run_open_result.get("exists") is not None:
                        print(f"- run_open_exists: {bool(run_open_result.get('exists'))}")
                    if run_open_result.get("line_count") is not None:
                        print(f"- run_open_line_count: {run_open_result['line_count']}")
                else:
                    print("Project hook-init open command execution failed")
                    print(f"- run_open_command: {payload.get('run_open_command', '')}")
                    print(f"- run_open_command_exit_code: {payload.get('run_open_command_exit_code', 0)}")
                    if payload.get("run_open_command_warning"):
                        print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
                return int(payload.get("run_open_command_exit_code", exit_code))
            print("Project hook-init open command ready")
            print(f"- run_open_command: {payload.get('run_open_command', '')}")
            if payload.get("run_open_command_warning"):
                print(f"- run_open_command_warning: {payload['run_open_command_warning']}")
            if payload.get("run_open_command_confirm_command"):
                print(f"- run_open_command_confirm_command: {payload['run_open_command_confirm_command']}")
            return exit_code
        elif getattr(args, "explain", False) and payload.get("entrypoint") == "project-hook-init":
            print("Project hook-init explain")
            if project_emit_confirm_command:
                print(f"- runnable_next_command: {project_emit_confirm_command}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            blocks = payload.get("explanation_blocks") or []
            for item in blocks:
                print(f"- {item.get('label', '')}: {item.get('summary', '')}")
                if item.get("detail"):
                    print(f"  {item['detail']}")
            return exit_code
        elif getattr(args, "text_compact", False) and payload.get("entrypoint") == "project-hook-init":
            print("Project hook-init compact")
            if payload.get("hook_name"):
                print(f"- hook_name: {payload['hook_name']}")
            if payload.get("template"):
                print(f"- template: {payload['template']}")
            if payload.get("target_path"):
                print(f"- target_path: {payload['target_path']}")
            if payload.get("target_relative_path"):
                print(f"- target_relative_path: {payload['target_relative_path']}")
            if payload.get("inspect_target_summary"):
                print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
            if payload.get("inspect_target_parent_summary"):
                print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
            if (payload.get("target_inspection") or {}).get("path"):
                print(f"- inspected_target_path: {(payload.get('target_inspection') or {}).get('path')}")
            if (payload.get("target_inspection") or {}).get("exists") is not None:
                print(f"- inspected_target_exists: {bool((payload.get('target_inspection') or {}).get('exists'))}")
            parent_entries = [
                entry.get("name", "")
                for entry in ((payload.get("target_parent_inspection") or {}).get("entries") or [])
                if entry.get("name")
            ]
            if parent_entries:
                print(f"- nearby_entries: {', '.join(parent_entries[:6])}")
            if payload.get("open_now_summary"):
                print(f"- open_now_summary: {payload['open_now_summary']}")
            if (payload.get("open_now_result") or {}).get("path"):
                print(f"- open_now_path: {(payload.get('open_now_result') or {}).get('path')}")
            if (payload.get("open_now_result") or {}).get("exists") is not None:
                print(f"- open_now_exists: {bool((payload.get('open_now_result') or {}).get('exists'))}")
            if (payload.get("open_now_result") or {}).get("line_count") is not None:
                print(f"- open_now_line_count: {(payload.get('open_now_result') or {}).get('line_count')}")
            if payload.get("open_now_preview"):
                print(f"- open_now_preview: {payload['open_now_preview']}")
            if payload.get("dry_run_summary"):
                print(f"- target_summary: {payload['dry_run_summary']}")
            if payload.get("target_reason"):
                print(f"- target_reason: {payload['target_reason']}")
            if payload.get("would_overwrite") is not None:
                print(f"- would_overwrite: {str(payload.get('would_overwrite', False)).lower()}")
            if project_emit_confirm_command:
                print(f"- runnable_next_command: {project_emit_confirm_command}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            return exit_code
        elif getattr(args, "inspect_target", False):
            print("Project hook-init inspect target")
            if payload.get("inspect_target_summary"):
                print(f"- inspect_target_summary: {payload['inspect_target_summary']}")
            if payload.get("inspect_target_parent_summary"):
                print(f"- inspect_target_parent_summary: {payload['inspect_target_parent_summary']}")
            target_inspection = payload.get("target_inspection") or {}
            parent_inspection = payload.get("target_parent_inspection") or {}
            if target_inspection.get("path"):
                print(f"- inspected_target_path: {target_inspection['path']}")
            if target_inspection.get("exists") is not None:
                print(f"- inspected_target_exists: {bool(target_inspection.get('exists'))}")
            if parent_inspection.get("path"):
                print(f"- inspected_target_parent_path: {parent_inspection['path']}")
            if parent_inspection.get("entry_count") is not None:
                print(f"- inspected_target_parent_entry_count: {parent_inspection['entry_count']}")
            return exit_code
        elif getattr(args, "open_target", False):
            print("Project hook-init open target")
            if payload.get("open_target_summary"):
                print(f"- open_target_summary: {payload['open_target_summary']}")
            if payload.get("open_target_reason"):
                print(f"- open_target_reason: {payload['open_target_reason']}")
            if payload.get("open_target_command"):
                print(f"- open_target_command: {payload['open_target_command']}")
            open_target = payload.get("open_target") or {}
            if open_target.get("path"):
                print(f"- open_target_path: {open_target['path']}")
            if open_target.get("exists") is not None:
                print(f"- open_target_exists: {bool(open_target.get('exists'))}")
            return exit_code
        elif getattr(args, "open_now", False):
            print("Project hook-init open now")
            if payload.get("open_now_summary"):
                print(f"- open_now_summary: {payload['open_now_summary']}")
            if payload.get("open_now_reason"):
                print(f"- open_now_reason: {payload['open_now_reason']}")
            open_now_result = payload.get("open_now_result") or {}
            if open_now_result.get("path"):
                print(f"- open_now_path: {open_now_result['path']}")
            if open_now_result.get("exists") is not None:
                print(f"- open_now_exists: {bool(open_now_result.get('exists'))}")
            if open_now_result.get("line_count") is not None:
                print(f"- open_now_line_count: {open_now_result['line_count']}")
            if payload.get("open_now_preview"):
                print(f"- open_now_preview: {payload['open_now_preview']}")
            return exit_code
        elif getattr(args, "emit_shell", False):
            if project_emit_command:
                print(project_emit_command)
            else:
                print("No hook-init next command was available.")
            return exit_code if project_emit_command else EXIT_USAGE
        elif getattr(args, "emit_confirm_shell", False):
            if project_emit_confirm_command:
                print(project_emit_confirm_command)
            else:
                print("No hook-init confirm command was available.")
            return exit_code if project_emit_confirm_command else EXIT_USAGE
        elif getattr(args, "emit_target_path", False):
            if project_emit_target_path:
                print(project_emit_target_path)
            else:
                print("No hook-init target path was available.")
            return exit_code if project_emit_target_path else EXIT_USAGE
        elif getattr(args, "emit_target_dir", False):
            if project_emit_target_dir:
                print(project_emit_target_dir)
            else:
                print("No hook-init target directory was available.")
            return exit_code if project_emit_target_dir else EXIT_USAGE
        elif getattr(args, "emit_target_project_root", False):
            if project_emit_target_project_root:
                print(project_emit_target_project_root)
            else:
                print("No hook-init target project root was available.")
            return exit_code if project_emit_target_project_root else EXIT_USAGE
        elif getattr(args, "emit_target_project_name", False):
            if project_emit_target_project_name:
                print(project_emit_target_project_name)
            else:
                print("No hook-init target project name was available.")
            return exit_code if project_emit_target_project_name else EXIT_USAGE
        elif getattr(args, "emit_target_relative_path", False):
            if project_emit_target_relative_path:
                print(project_emit_target_relative_path)
            else:
                print("No hook-init target relative path was available.")
            return exit_code if project_emit_target_relative_path else EXIT_USAGE
        elif getattr(args, "emit_target_bundle", False):
            if payload.get("emit_target_bundle_json"):
                print(payload["emit_target_bundle_json"])
            else:
                print("No hook-init target bundle was available.")
            return exit_code if payload.get("emit_target_bundle_json") else EXIT_USAGE
        elif getattr(args, "emit_open_shell", False):
            if project_emit_open_command:
                print(project_emit_open_command)
            else:
                print("No hook-init open command was available.")
            return exit_code if project_emit_open_command else EXIT_USAGE
        elif getattr(args, "copy_command", False):
            if payload.get("copied_command_to_clipboard"):
                print("Project hook-init next command copied")
                print(f"- copied_command: {payload.get('copied_command', '')}")
            else:
                print("Project hook-init next command copy failed")
                if payload.get("copy_command_error"):
                    print(f"- copy_command_error: {payload['copy_command_error']}")
            return exit_code if payload.get("copied_command_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_confirm_command", False):
            if payload.get("copied_confirm_to_clipboard"):
                print("Project hook-init confirm command copied")
                print(f"- copied_confirm_command: {payload.get('copied_confirm_command', '')}")
            else:
                print("Project hook-init confirm command copy failed")
                if payload.get("copy_confirm_command_error"):
                    print(f"- copy_confirm_command_error: {payload['copy_confirm_command_error']}")
            return exit_code if payload.get("copied_confirm_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_path", False):
            if payload.get("copied_target_path_to_clipboard"):
                print("Project hook-init target path copied")
                print(f"- copied_target_path: {payload.get('copied_target_path', '')}")
            else:
                print("Project hook-init target path copy failed")
                if payload.get("copy_target_path_error"):
                    print(f"- copy_target_path_error: {payload['copy_target_path_error']}")
            return exit_code if payload.get("copied_target_path_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_dir", False):
            if payload.get("copied_target_dir_to_clipboard"):
                print("Project hook-init target directory copied")
                print(f"- copied_target_dir: {payload.get('copied_target_dir', '')}")
            else:
                print("Project hook-init target directory copy failed")
                if payload.get("copy_target_dir_error"):
                    print(f"- copy_target_dir_error: {payload['copy_target_dir_error']}")
            return exit_code if payload.get("copied_target_dir_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_project_root", False):
            if payload.get("copied_target_project_root_to_clipboard"):
                print("Project hook-init target project root copied")
                print(f"- copied_target_project_root: {payload.get('copied_target_project_root', '')}")
            else:
                print("Project hook-init target project root copy failed")
                if payload.get("copy_target_project_root_error"):
                    print(f"- copy_target_project_root_error: {payload['copy_target_project_root_error']}")
            return exit_code if payload.get("copied_target_project_root_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_project_name", False):
            if payload.get("copied_target_project_name_to_clipboard"):
                print("Project hook-init target project name copied")
                print(f"- copied_target_project_name: {payload.get('copied_target_project_name', '')}")
            else:
                print("Project hook-init target project name copy failed")
                if payload.get("copy_target_project_name_error"):
                    print(f"- copy_target_project_name_error: {payload['copy_target_project_name_error']}")
            return exit_code if payload.get("copied_target_project_name_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_relative_path", False):
            if payload.get("copied_target_relative_path_to_clipboard"):
                print("Project hook-init target relative path copied")
                print(f"- copied_target_relative_path: {payload.get('copied_target_relative_path', '')}")
            else:
                print("Project hook-init target relative path copy failed")
                if payload.get("copy_target_relative_path_error"):
                    print(f"- copy_target_relative_path_error: {payload['copy_target_relative_path_error']}")
            return exit_code if payload.get("copied_target_relative_path_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_target_bundle", False):
            if payload.get("copied_target_bundle_to_clipboard"):
                print("Project hook-init target bundle copied")
                print(f"- copied_target_bundle: {payload.get('copied_target_bundle_json', '')}")
            else:
                print("Project hook-init target bundle copy failed")
                if payload.get("copy_target_bundle_error"):
                    print(f"- copy_target_bundle_error: {payload['copy_target_bundle_error']}")
            return exit_code if payload.get("copied_target_bundle_to_clipboard") else EXIT_USAGE
        elif getattr(args, "copy_open_command", False):
            if payload.get("copied_open_to_clipboard"):
                print("Project hook-init open command copied")
                print(f"- copied_open_command: {payload.get('copied_open_command', '')}")
            else:
                print("Project hook-init open command copy failed")
                if payload.get("copy_open_command_error"):
                    print(f"- copy_open_command_error: {payload['copy_open_command_error']}")
            return exit_code if payload.get("copied_open_to_clipboard") else EXIT_USAGE
        else:
            title = {
                "project-hook-init": "Project hook-init",
                "project-hook-suggest": "Project hook suggestions",
                "project-hook-last-suggest": "Project last hook suggestion",
                "project-hook-open-catalog": "Project hook catalog",
            }.get(payload.get("entrypoint", ""), "Project hook-init")
            print(f"{title}: {payload['project_id']}")
            print(f"- project_root: {payload['project_root']}")
            if payload.get("hook_name"):
                print(f"- hook_name: {payload['hook_name']}")
            if payload.get("template"):
                print(f"- template: {payload['template']}")
            if payload.get("entrypoint") == "project-hook-init" and payload.get("target_relative_path"):
                print(f"- target_relative_path: {payload['target_relative_path']}")
            if payload.get("entrypoint") == "project-hook-init" and payload.get("dry_run_summary"):
                print(f"- target_summary: {payload['dry_run_summary']}")
            if payload.get("entrypoint") == "project-hook-init" and payload.get("target_reason"):
                print(f"- target_reason: {payload['target_reason']}")
            if payload.get("dry_run"):
                print("- dry_run: true")
            if payload.get("entrypoint") != "project-hook-init" and payload.get("source_example_path"):
                print(f"- source_example_path: {payload['source_example_path']}")
            if payload.get("entrypoint") == "project-hook-init" and project_emit_confirm_command:
                print(f"- runnable_next_command: {project_emit_confirm_command}")
            if payload.get("hook_catalog"):
                print(f"- hook_catalog_json: {payload['hook_catalog'].get('json_path', '')}")
                print(f"- hook_catalog_markdown: {payload['hook_catalog'].get('markdown_path', '')}")
            if payload.get("page_key_filter"):
                print(f"- page_key_filter: {payload['page_key_filter']}")
            if payload.get("section_key_filter"):
                print(f"- section_key_filter: {payload['section_key_filter']}")
            if payload.get("slot_key_filter"):
                print(f"- slot_key_filter: {payload['slot_key_filter']}")
            if payload.get("reuse_last_suggest"):
                print("- reuse_last_suggest: true")
            if payload.get("entrypoint") == "project-hook-last-suggest" and payload.get("recent_suggestion_memory_path"):
                print(f"- recent_suggestion_memory_path: {payload['recent_suggestion_memory_path']}")
            if payload.get("used_recent_suggestion_memory"):
                print("- used_recent_suggestion_memory: true")
            elif payload.get("entrypoint") == "project-hook-suggest" and payload.get("recent_suggestion_memory_path"):
                print(f"- recent_suggestion_memory_path: {payload['recent_suggestion_memory_path']}")
            if payload.get("pick"):
                print(f"- pick: {str(payload['pick']).lower()}")
            if payload.get("pick_recommended"):
                print(f"- pick_recommended: {str(payload['pick_recommended']).lower()}")
            if payload.get("pick_index") is not None:
                print(f"- pick_index: {payload['pick_index']}")
            if payload.get("status") != "ok":
                if payload.get("message"):
                    print(f"- message: {payload['message']}")
            elif payload.get("entrypoint") == "project-hook-suggest":
                suggestions = payload.get("suggestions") or []
                print(f"- suggestion_count: {len(suggestions)}")
                for item in suggestions[:12]:
                    scope = item.get("scope", "")
                    page_key = item.get("page_key", "") or "-"
                    section_key = item.get("section_key", "") or "-"
                    slot_key = item.get("slot_key", "") or "-"
                    print(
                        "- suggestion: "
                        f"#{item.get('suggestion_index', '')} "
                        f"{item.get('hook_name', '')} "
                        f"[scope={scope} page={page_key} section={section_key} slot={slot_key} template={item.get('default_template', '')}]"
                    )
                    if item.get("pick_index_command"):
                        print(f"  pick: {item['pick_index_command']}")
                if payload.get("recommended_next_command"):
                    print(f"- recommended_next_command: {payload['recommended_next_command']}")
            elif payload.get("entrypoint") == "project-hook-last-suggest":
                last_suggest = payload.get("last_suggest") or {}
                print(f"- last_requested_hook_name: {last_suggest.get('requested_hook_name', '')}")
                print(f"- last_page_key_filter: {last_suggest.get('page_key_filter', '') or '-'}")
                print(f"- last_section_key_filter: {last_suggest.get('section_key_filter', '') or '-'}")
                print(f"- last_slot_key_filter: {last_suggest.get('slot_key_filter', '') or '-'}")
                print(f"- last_suggestion_count: {last_suggest.get('suggestion_count', 0)}")
                if payload.get("recommended_next_command"):
                    print(f"- recommended_next_command: {payload['recommended_next_command']}")
            else:
                print(f"- hook_catalog_verified: {str(payload.get('hook_catalog_verified', False)).lower()}")
                if payload.get("hook_catalog_warning"):
                    print(f"- hook_catalog_warning: {payload['hook_catalog_warning']}")
                print(f"- selected_from_suggestions: {str(payload.get('selected_from_suggestions', False)).lower()}")
                print(f"- wrote: {str(payload.get('wrote', False)).lower()}")
                if payload.get("would_write") is not None:
                    print(f"- would_write: {str(payload.get('would_write', False)).lower()}")
                print(f"- overwritten: {str(payload.get('overwritten', False)).lower()}")
                if payload.get("would_overwrite") is not None:
                    print(f"- would_overwrite: {str(payload.get('would_overwrite', False)).lower()}")
                if payload.get("message"):
                    print(f"- message: {payload['message']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "preview":
        ctx = ProjectContext.discover()
        preview = _build_project_preview_payload(
            ctx,
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(preview)
        else:
            print(f"Project preview: {preview['project_id']}")
            print(f"- project_root: {preview['project_root']}")
            print(f"- doctor_status: {preview['doctor_status']}")
            print(f"- preview_hint: {preview['preview_hint']}")
            primary = preview["preview_handoff"]["primary_target"]
            print(f"- primary_preview_target: {primary['label']} -> {primary['path']}")
            if preview.get("latest_build_id"):
                print(f"- latest_build_id: {preview['latest_build_id']}")
            if preview.get("latest_artifact_id"):
                print(f"- latest_artifact_id: {preview['latest_artifact_id']}")
            print(f"- recommended_primary_action: {preview['recommended_primary_action']}")
            print("Open targets:")
            for item in preview["open_targets"]:
                print(f"- {item['label']}: {item['path']}")
            print("Next:")
            for step in preview["next_steps"]:
                print(f"- {step}")
        return EXIT_OK

    if getattr(args, "project_command", None) == "serve":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_serve_payload(
            ctx,
            host=args.host,
            port=args.port,
            install_if_needed=args.install_if_needed,
            dry_run=args.dry_run,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project serve: {payload.get('project_id', ctx.project_id)}")
            print(f"- status: {payload.get('status', '')}")
            print(f"- project_root: {payload.get('project_root', '')}")
            print(f"- frontend_root: {payload.get('frontend_root', '')}")
            print(f"- local_url: {payload.get('local_url', '')}")
            if payload.get("dry_run"):
                print("- dry_run: true")
            if payload.get("npm_found") is not None:
                print(f"- npm_found: {str(bool(payload.get('npm_found'))).lower()}")
            if payload.get("dependencies_installed") is not None:
                print(f"- dependencies_installed: {str(bool(payload.get('dependencies_installed'))).lower()}")
            if payload.get("started"):
                print(f"- pid: {payload.get('pid', '')}")
                print(f"- log_path: {payload.get('log_path', '')}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            print("Next:")
            for step in payload.get("next_steps", []):
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "open-target":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_open_target_payload(
            ctx,
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project open-target: {payload['project_id']}")
            print(f"- resolved_label: {payload['resolved_label']}")
            print(f"- target_path: {payload['target']['path']}")
            print(f"- target_kind: {payload['target']['kind']}")
            print(f"- target_exists: {str(payload['target']['exists']).lower()}")
            print(f"- inspect_command: {payload['inspect_command']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "inspect-target":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_inspect_target_payload(
            ctx,
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project inspect-target: {payload['project_id']}")
            print(f"- status: {payload['status']}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            print(f"- target_path: {payload.get('target', {}).get('path', '')}")
            print(f"- target_kind: {payload.get('target', {}).get('kind', '')}")
            inspection = payload.get("inspection") or {}
            if inspection.get("kind") == "file":
                print(f"- line_count: {inspection.get('line_count', 0)}")
                print(f"- size_bytes: {inspection.get('size_bytes', 0)}")
                preview = inspection.get("content_preview") or ""
                if preview:
                    print("Preview:")
                    print(preview)
            elif inspection.get("kind") == "directory":
                print(f"- entry_count: {inspection.get('entry_count', 0)}")
                print("Entries:")
                for item in inspection.get("entries", []):
                    print(f"- {item['name']} [{item['kind']}]")
            else:
                print(f"- exists: {str(inspection.get('exists', False)).lower()}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "run-inspect-command":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_run_inspect_command_payload(
            ctx,
            label=getattr(args, "label", None),
            base_url=args.base_url,
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project run-inspect-command: {payload['project_id']}")
            print(f"- status: {payload['status']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- executed_inspect_command: {payload.get('executed_inspect_command', '')}")
            print(f"- resolved_label: {payload.get('resolved_label', '')}")
            inspection = payload.get("inspection") or {}
            if inspection.get("kind") == "file":
                print(f"- line_count: {inspection.get('line_count', 0)}")
            elif inspection.get("kind") == "directory":
                print(f"- entry_count: {inspection.get('entry_count', 0)}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "export-handoff":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_export_handoff_payload(ctx, base_url=args.base_url)
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project export-handoff: {payload['project_id']}")
            print(f"- status: {payload['status']}")
            print(f"- primary_target_label: {payload.get('primary_target_label', '')}")
            print(f"- preview_hint: {payload.get('preview_hint', '')}")
            print(f"- recommended_primary_action: {payload.get('recommended_primary_action', '')}")
            primary_inspection = payload.get("primary_inspection") or {}
            if primary_inspection.get("kind") == "directory":
                print(f"- primary_entry_count: {primary_inspection.get('entry_count', 0)}")
            elif primary_inspection.get("kind") == "file":
                print(f"- primary_line_count: {primary_inspection.get('line_count', 0)}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "style-brief":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_style_brief_payload(ctx, base_url=args.base_url)
        if getattr(args, "emit_prompt", False):
            sys.stdout.write(str(payload.get("model_prompt", "")))
            return exit_code
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project style-brief: {payload['project_id']}")
            print(f"- project_root: {payload['project_root']}")
            print(f"- style_mode: {payload.get('style_mode', '')}")
            print(f"- operator_positioning: {payload.get('operator_positioning', '')}")
            print(f"- primary_preview_target: {payload.get('primary_target_label', '')}")
            print(f"- current_profile: {payload.get('current_profile', '')}")
            override_surface = payload.get("override_surface") or {}
            print(f"- theme_tokens_path: {override_surface.get('theme_tokens_path', '')}")
            print(f"- custom_css_path: {override_surface.get('custom_css_path', '')}")
            print(f"- component_overrides_dir: {override_surface.get('component_overrides_dir', '')}")
            print(f"- asset_overrides_dir: {override_surface.get('asset_overrides_dir', '')}")
            print(f"- managed_boundary_rule: {payload.get('managed_boundary_rule', '')}")
            print("Recommended commands:")
            for item in payload.get("recommended_commands", []):
                print(f"- {item}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "style-apply-check":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_style_apply_check_payload(ctx, base_url=args.base_url)
        if getattr(args, "emit_summary", False):
            sys.stdout.write(str(payload.get("summary_text", "")))
            return exit_code
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project style-apply-check: {payload['project_id']}")
            print(f"- project_root: {payload['project_root']}")
            print(f"- status: {payload.get('status', '')}")
            print(f"- verification_mode: {payload.get('verification_mode', '')}")
            print(f"- managed_mirror_verified_count: {payload.get('managed_boundary', {}).get('verified_count', 0)}")
            print(f"- managed_mirror_violation_count: {payload.get('managed_boundary', {}).get('violation_count', 0)}")
            print(f"- route_contract_ok: {str(bool((payload.get('route_contract') or {}).get('route_contract_ok'))).lower()}")
            print(f"- serve_dry_run_status: {(payload.get('serve_dry_run') or {}).get('status', '')}")
            if payload.get("message"):
                print(f"- message: {payload['message']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "style-intent":
        ctx = ProjectContext.discover()
        payload, exit_code = _build_project_style_intent_payload(
            ctx,
            audience=getattr(args, "audience", None),
            style_direction=getattr(args, "style_direction", None),
            localization_mode=getattr(args, "localization_mode", None),
            notes=getattr(args, "notes", None),
            brand_keywords=getattr(args, "brand_keyword", None),
            tone_keywords=getattr(args, "tone_keyword", None),
            visual_constraints=getattr(args, "visual_constraint", None),
            reset=bool(getattr(args, "reset", False)),
        )
        if args.json:
            _print_json_payload(payload)
        else:
            print(f"Project style-intent: {payload['project_id']}")
            print(f"- project_root: {payload['project_root']}")
            print(f"- style_intent_path: {payload.get('style_intent_path', '')}")
            print(f"- action: {payload.get('action', '')}")
            intent = payload.get("style_intent") or {}
            print(f"- audience: {intent.get('audience', '')}")
            print(f"- style_direction: {intent.get('style_direction', '')}")
            print(f"- localization_mode: {intent.get('localization_mode', '')}")
            print(f"- brand_keywords: {', '.join(intent.get('brand_keywords') or [])}")
            print(f"- tone_keywords: {', '.join(intent.get('tone_keywords') or [])}")
            print(f"- visual_constraints: {', '.join(intent.get('visual_constraints') or [])}")
            if intent.get("notes"):
                print(f"- notes: {intent['notes']}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
        return exit_code

    if getattr(args, "project_command", None) == "show":
        project_id = _resolve_project_id_arg(getattr(args, "project_id", None))
        client = AILCloudClient(base_url=args.base_url)
        data = client.get_project(project_id)
        cloud = _query_cloud_summary(client)
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "data": data,
                        "cloud": cloud,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Project: {data.get('project_id', '')}")
            print(f"- latest_build_id: {data.get('latest_build_id', '')}")
            print(f"- latest_manifest_version: {data.get('latest_manifest_version', '')}")
            print(f"- created_at: {data.get('created_at', '')}")
            print(f"- updated_at: {data.get('updated_at', '')}")
            print(
                "- cloud: "
                f"base_url={cloud['base_url']} "
                f"api_variant={cloud['api_variant']} "
                f"endpoint={cloud['endpoint']}"
            )
        return EXIT_OK

    if getattr(args, "project_command", None) == "builds":
        project_id = _resolve_project_id_arg(getattr(args, "project_id", None))
        client = AILCloudClient(base_url=args.base_url)
        data = client.get_project_builds(
            project_id,
            limit=getattr(args, "limit", None),
            cursor=getattr(args, "cursor", None),
            mode=getattr(args, "mode", None),
        )
        cloud = _query_cloud_summary(client)
        items = data.get("items") or []
        next_cursor = data.get("next_cursor")
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "project_id": project_id,
                        "data": data,
                        "cloud": cloud,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Project builds: {project_id}")
            print(f"- total_returned: {len(items)}")
            print(f"- next_cursor: {next_cursor}")
            for item in items:
                diff = item.get("diff_summary") or {}
                print(
                    f"- {item.get('build_id', '')} | "
                    f"mode={item.get('mode', '')} | "
                    f"status={item.get('status', '')} | "
                    f"created_at={item.get('created_at', '')} | "
                    f"added={diff.get('added', 0)} "
                    f"updated={diff.get('updated', 0)} "
                    f"deleted={diff.get('deleted', 0)}"
                )
            print(
                "- cloud: "
                f"base_url={cloud['base_url']} "
                f"api_variant={cloud['api_variant']} "
                f"endpoint={cloud['endpoint']}"
            )
        return EXIT_OK

    return _emit_command_error(args, EXIT_USAGE, "invalid_usage", "supported project subcommands: go, continue, check, doctor, summary, hooks, hook-guide, hook-init, preview, serve, open-target, inspect-target, run-inspect-command, export-handoff, style-brief, style-apply-check, style-intent, show, builds")


def cmd_conflicts(args: argparse.Namespace) -> int:
    ctx = ProjectContext.discover()
    manifest_service = ManifestService()
    current_manifest = manifest_service.load_manifest(ctx.manifest_file)
    last_build = manifest_service.load_last_build(ctx.last_build_file)
    if not last_build or not last_build.get("files"):
        raise FileNotFoundError("No cached cloud build found. Run 'ail compile --cloud' first.")

    engine = SyncEngine(manifest_service)
    conflicts = engine.detect_conflicts(ctx, last_build, current_manifest)
    if not conflicts:
        if args.json:
            _print_json_payload({"status": "ok", "conflicts": []})
        else:
            print("No sync conflicts detected.")
        return EXIT_OK

    if args.json:
        conflict_help = SyncEngine.explain_conflicts(conflicts)
        print(
            json.dumps(
                {
                    "status": "conflict",
                    "build_id": last_build.get("build_id", ""),
                    **conflict_help,
                    "conflicts": conflicts,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        conflict_help = SyncEngine.explain_conflicts(conflicts)
        print("Managed-file drift detected:")
        print(f"- meaning: {conflict_help['message']}")
        print(f"- blocks_safe_sync: {str(conflict_help['blocks_safe_sync']).lower()}")
        print(f"- blocks_existing_output_review: {str(conflict_help['blocks_existing_output_review']).lower()}")
        print("Conflicts:")
        for item in conflicts:
            print(f"- {item['path']} | Level {item['level']} | {item.get('summary') or item['reason']}")
    return EXIT_CONFLICT


def cmd_trial_run(args: argparse.Namespace) -> int:
    if args.list_scenarios:
        for name in _available_trial_scenarios():
            print(name)
        return EXIT_OK

    if bool(args.requirement) == bool(args.scenario):
        return _emit_command_error(
            args,
            EXIT_USAGE,
            "invalid_usage",
            "use exactly one of --requirement or --scenario",
        )

    requirement = args.requirement.strip() if args.requirement else _scenario_requirement(args.scenario)
    if not requirement:
        return _emit_command_error(args, EXIT_USAGE, "invalid_usage", f"unsupported scenario: {args.scenario}")

    root = Path(args.project_dir).resolve() if args.project_dir else Path(tempfile.mkdtemp(prefix="ail_trial_run."))
    root.mkdir(parents=True, exist_ok=True)
    ctx = ProjectContext.discover(root, allow_uninitialized=True)
    if not args.keep_existing and ctx.ail_dir.exists():
        return _emit_command_error(
            args,
            EXIT_USAGE,
            "invalid_usage",
            f"target project already looks initialized: {ctx.root}. Use --keep-existing to reuse it.",
        )

    payload, exit_code = _run_trial_flow(
        ctx,
        requirement=requirement,
        scenario=args.scenario or "custom",
        base_url=args.base_url,
    )

    if args.json:
        _print_json_payload(payload)
    else:
        if payload["status"] != "ok":
            print("Trial run failed: diagnose did not pass after repair", file=sys.stderr)
            _print_json_payload(payload, file=sys.stderr)
        else:
            print(f"Trial run completed successfully at {ctx.root}")
            print(f"- scenario: {payload['scenario']}")
            print(f"- route_taken: {payload['route_taken']}")
            print(f"- route_reason: {payload['route_reason']}")
            print(f"- detected_profile: {payload['detected_profile']}")
            print(f"- repair_used: {'yes' if payload['repair_used'] else 'no'}")
            print(f"- build_id: {payload['build_id']}")
            print(f"- managed_files_written: {payload['managed_files_written']}")
            print(
                "- cloud: "
                f"base_url={payload['cloud']['base_url']} "
                f"api_variant={payload['cloud']['api_variant']} "
                f"endpoint={payload['cloud']['endpoint']}"
            )
            print(f"- recommended_primary_action: {payload['recommended_primary_action']}")
            print(f"- recommended_primary_reason: {payload['recommended_primary_reason']}")
            print(f"- preview_hint: {payload['preview_hint']}")
            for notice in payload["notices"]:
                print(f"note: {notice}")
            print("Next:")
            for step in payload["next_steps"]:
                print(f"- {step}")
    return exit_code


def cmd_diagnose(args: argparse.Namespace) -> int:
    repair_mod = load_repair_module()
    ail_path = _resolve_ail_input(args.input)
    ail_text = ail_path.read_text(encoding="utf-8")
    requirement = _read_requirement_optional(args) or _default_requirement_for_ail(repair_mod, ail_text)
    diagnosis = repair_mod.diagnose(requirement, ail_text)

    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok" if diagnosis["compile_recommended"] == "yes" else "validation_failed",
                    "input_path": str(ail_path),
                    "requirement": requirement,
                    "diagnosis": {
                        key: value
                        for key, value in diagnosis.items()
                        if key != "parsed"
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print("Diagnosis Summary")
        print(f"- valid: {diagnosis['valid']}")
        print(f"- compile_recommended: {diagnosis['compile_recommended']}")
        print(f"- confidence: {diagnosis['confidence']}")
        print("Profile Check")
        print(f"- detected_profile: {diagnosis['detected_profile']}")
        print(f"- profile_match: {diagnosis['profile_match']}")
        print(f"- multiple_profiles: {diagnosis['multiple_profiles']}")
        print("Structure Check")
        print(f"- structure_valid: {diagnosis['structure_valid']}")
        print(f"- notes: {diagnosis['structure_notes']}")
        print("Token Check")
        print(f"- alias_components: {diagnosis.get('alias_components', [])}")
        print(f"- alias_flows: {diagnosis.get('alias_flows', [])}")
        print(f"- unknown_components: {diagnosis['unknown_components']}")
        print(f"- unknown_flows: {diagnosis['unknown_flows']}")
        print(f"- unsupported_constructs: {diagnosis['unsupported_constructs']}")
        print("Boundary Check")
        print(f"- boundary_exceeded: {diagnosis['boundary_exceeded']}")
        print(f"- boundary_reason: {diagnosis['boundary_reason']}")

    return EXIT_OK if diagnosis["compile_recommended"] == "yes" else EXIT_VALIDATION


def cmd_repair(args: argparse.Namespace) -> int:
    repair_mod = load_repair_module()
    ail_path = _resolve_ail_input(args.input)
    ail_text = ail_path.read_text(encoding="utf-8")
    requirement = _read_requirement_optional(args) or _default_requirement_for_ail(repair_mod, ail_text)
    repaired = repair_mod.repair(requirement, ail_text)

    if args.json:
        payload = {
            "status": "ok",
            "input_path": str(ail_path),
            "requirement": requirement,
            "write": bool(args.write),
            "repaired_ail": repaired.rstrip(),
        }
        if args.write:
            ail_path.write_text(repaired.rstrip() + "\n", encoding="utf-8")
            payload["output_path"] = str(ail_path)
            payload["wrote"] = True
        else:
            payload["wrote"] = False
        _print_json_payload(payload)
    elif args.write:
        ail_path.write_text(repaired.rstrip() + "\n", encoding="utf-8")
        print(f"Repaired AIL and wrote {ail_path}")
    else:
        print(repaired.rstrip())
    return EXIT_OK


def cmd_placeholder(args: argparse.Namespace) -> int:
    print(f"'{args.command}' is reserved but not implemented in this CLI skeleton yet.", file=sys.stderr)
    return EXIT_USAGE


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ail", description="AIL CLI v1 skeleton")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize an AIL project")
    init_parser.add_argument("path", nargs="?", default=".", help="Project root to initialize")

    generate_parser = subparsers.add_parser("generate", help="Generate .ail/source.ail from a requirement")
    generate_parser.add_argument("requirement", nargs="?", help="Requirement text")
    generate_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    generate_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")

    context_parser = subparsers.add_parser("context", help="Compress long code or text context into an MCP-oriented skeleton and restore it later")
    context_subparsers = context_parser.add_subparsers(dest="context_command")
    context_compress_parser = context_subparsers.add_parser("compress", help="Compress text, one file, or one directory into an MCP skeleton bundle")
    context_compress_parser.add_argument("--text", dest="context_text", help="Inline text to compress")
    context_compress_parser.add_argument("--text-file", dest="text_file", help="Read long-form text from a file")
    context_compress_parser.add_argument("--input-file", dest="input_file", help="Compress one source file or project file")
    context_compress_parser.add_argument("--input-dir", dest="input_dir", help="Compress one project directory tree")
    context_compress_parser.add_argument("--preset", dest="preset_id", default="generic", help="Compression preset such as generic, codebase, writing, website, or ecommerce")
    context_compress_parser.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"], help="Token metrics backend: auto prefers tiktoken when available, heuristic uses chars/4, tiktoken requests tokenizer-backed counts")
    context_compress_parser.add_argument("--tokenizer-model", dest="tokenizer_model", help="Optional tokenizer model or encoding name such as cl100k_base when using tokenizer-backed metrics")
    context_compress_parser.add_argument("--emit-skeleton", action="store_true", help="Print only the MCP skeleton text")
    context_compress_parser.add_argument("--output-file", dest="output_file", help="Write the output to a file")
    context_compress_parser.add_argument("--output-dir", dest="output_dir", help="Write a full context bundle directory")
    context_compress_parser.add_argument("--json", action="store_true", help="Print context compression as JSON")
    context_restore_parser = context_subparsers.add_parser("restore", help="Restore the original text, file, or directory from a context bundle")
    context_restore_parser.add_argument("--package-file", dest="package_file", required=True, help="Path to a context manifest JSON file produced by context compress")
    context_restore_parser.add_argument("--output-file", dest="output_file", help="Write restored text or one restored file here")
    context_restore_parser.add_argument("--output-dir", dest="output_dir", help="Directory where restored files or directories should be written")
    context_restore_parser.add_argument("--emit-text", action="store_true", help="Print the restored text directly for text-based packages")
    context_restore_parser.add_argument("--json", action="store_true", help="Print context restore as JSON")
    context_inspect_parser = context_subparsers.add_parser("inspect", help="Inspect one context bundle without restoring the original content")
    context_inspect_parser.add_argument("--package-file", dest="package_file", required=True, help="Path to a context manifest JSON file produced by context compress")
    context_inspect_parser.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"], help="Token metrics backend for inspect; auto reuses stored metrics unless an override is requested")
    context_inspect_parser.add_argument("--tokenizer-model", dest="tokenizer_model", help="Optional tokenizer model or encoding name when recomputing inspect metrics")
    context_inspect_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact context bundle summary")
    context_inspect_parser.add_argument("--output-file", dest="output_file", help="Write the inspect output to a file")
    context_inspect_parser.add_argument("--json", action="store_true", help="Print context inspect as JSON")
    context_apply_check_parser = context_subparsers.add_parser("apply-check", help="Validate that edited text, a file, or a directory still stays inside the original context skeleton boundary")
    context_apply_check_parser.add_argument("--package-file", dest="package_file", required=True, help="Path to a context manifest JSON file produced by context compress")
    context_apply_check_parser.add_argument("--text", dest="context_text", help="Inline candidate text to validate")
    context_apply_check_parser.add_argument("--text-file", dest="text_file", help="Read candidate text from a file")
    context_apply_check_parser.add_argument("--input-file", dest="input_file", help="Validate one edited file against the original context bundle")
    context_apply_check_parser.add_argument("--input-dir", dest="input_dir", help="Validate one edited directory tree against the original context bundle")
    context_apply_check_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact context apply-check summary")
    context_apply_check_parser.add_argument("--output-file", dest="output_file", help="Write the apply-check output to a file")
    context_apply_check_parser.add_argument("--json", action="store_true", help="Print context apply-check as JSON")
    context_preset_parser = context_subparsers.add_parser("preset", help="List the available context compression presets or inspect one selected preset")
    context_preset_parser.add_argument("preset_id", nargs="?", default="generic", help="Optional preset id such as generic, codebase, writing, website, or ecommerce")
    context_preset_parser.add_argument("--json", action="store_true", help="Print context preset metadata as JSON")
    context_bundle_parser = context_subparsers.add_parser("bundle", help="Export a full context bundle with compression, inspect, and optional apply-check artifacts")
    context_bundle_parser.add_argument("--text", dest="context_text", help="Inline text to compress")
    context_bundle_parser.add_argument("--text-file", dest="text_file", help="Read long-form text from a file")
    context_bundle_parser.add_argument("--input-file", dest="input_file", help="Compress one source file or project file")
    context_bundle_parser.add_argument("--input-dir", dest="input_dir", help="Compress one project directory tree")
    context_bundle_parser.add_argument("--preset", dest="preset_id", default="generic", help="Compression preset such as generic, codebase, writing, website, or ecommerce")
    context_bundle_parser.add_argument("--candidate-text", dest="candidate_text", help="Optional inline edited text for apply-check")
    context_bundle_parser.add_argument("--candidate-text-file", dest="candidate_text_file", help="Read optional edited text for apply-check from a file")
    context_bundle_parser.add_argument("--candidate-input-file", dest="candidate_input_file", help="Optional edited file for apply-check")
    context_bundle_parser.add_argument("--candidate-input-dir", dest="candidate_input_dir", help="Optional edited directory tree for apply-check")
    context_bundle_parser.add_argument("--tokenizer-backend", dest="tokenizer_backend", default="auto", choices=["auto", "heuristic", "tiktoken"], help="Token metrics backend used for the bundle compression and inspect artifacts")
    context_bundle_parser.add_argument("--tokenizer-model", dest="tokenizer_model", help="Optional tokenizer model or encoding name for bundled metrics")
    context_bundle_parser.add_argument("--zip", dest="zip_bundle", action="store_true", help="Also create a zip archive next to the bundle directory")
    context_bundle_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact context bundle summary")
    context_bundle_parser.add_argument("--output-file", dest="output_file", help="Write the bundle output to a file")
    context_bundle_parser.add_argument("--output-dir", dest="output_dir", help="Directory where the context bundle should be written")
    context_bundle_parser.add_argument("--json", action="store_true", help="Print context bundle as JSON")
    context_patch_parser = context_subparsers.add_parser("patch", help="Export a patch bundle that compares one edited candidate against the original context bundle")
    context_patch_parser.add_argument("--package-file", dest="package_file", required=True, help="Path to a context manifest JSON file produced by context compress")
    context_patch_parser.add_argument("--text", dest="context_text", help="Inline edited text to diff against the original bundle")
    context_patch_parser.add_argument("--text-file", dest="text_file", help="Read edited text from a file")
    context_patch_parser.add_argument("--input-file", dest="input_file", help="Diff one edited file against the original context bundle")
    context_patch_parser.add_argument("--input-dir", dest="input_dir", help="Diff one edited directory tree against the original context bundle")
    context_patch_parser.add_argument("--zip", dest="zip_bundle", action="store_true", help="Also create a zip archive next to the patch directory")
    context_patch_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact context patch summary")
    context_patch_parser.add_argument("--output-file", dest="output_file", help="Write the patch output to a file")
    context_patch_parser.add_argument("--output-dir", dest="output_dir", help="Directory where the context patch bundle should be written")
    context_patch_parser.add_argument("--json", action="store_true", help="Print context patch as JSON")
    context_patch_apply_parser = context_subparsers.add_parser("patch-apply", help="Replay one context patch bundle into a safe output target")
    context_patch_apply_parser.add_argument("--patch-file", dest="patch_file", help="Path to a context patch manifest JSON file produced by context patch")
    context_patch_apply_parser.add_argument("--source-package-file", dest="source_package_file", help="Optional original context manifest JSON file; required for directory patch replay unless already recorded in the patch manifest")
    context_patch_apply_parser.add_argument("--output-file", dest="output_file", help="Target file path for text or single-file patch replay")
    context_patch_apply_parser.add_argument("--output-dir", dest="output_dir", help="Target directory root for directory patch replay or inferred file output")
    context_patch_apply_parser.add_argument("--policy-mode", choices=["open", "safe", "strict"], default="open", help="Patch replay policy preset")
    context_patch_apply_parser.add_argument("--policy-file", dest="policy_file", help="Optional JSON policy file to refine patch replay restrictions")
    context_patch_apply_parser.add_argument("--allow-root", dest="allow_roots", action="append", help="Allow replay only under one relative path prefix; repeatable")
    context_patch_apply_parser.add_argument("--forbid-root", dest="forbid_roots", action="append", help="Forbid replay under one relative path prefix; repeatable")
    context_patch_apply_parser.add_argument("--block-removals", action="store_true", help="Block replay when the patch removes any path")
    context_patch_apply_parser.add_argument("--block-additions", action="store_true", help="Block replay when the patch adds any path")
    context_patch_apply_parser.add_argument("--require-apply-check-pass", dest="require_apply_check_passed", action="store_true", help="Block replay unless the patch bundle recorded a passing apply-check result")
    context_patch_apply_parser.add_argument("--max-changed-paths", dest="max_changed_paths", type=int, help="Block replay when the patch touches more than this many changed, added, or removed paths")
    context_patch_apply_parser.add_argument("--emit-policy-template", action="store_true", help="Print the resolved patch replay policy as reusable JSON and exit")
    context_patch_apply_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact context patch-apply summary")
    context_patch_apply_parser.add_argument("--output-report-file", dest="output_report_file", help="Write the patch-apply report to a file")
    context_patch_apply_parser.add_argument("--json", action="store_true", help="Print context patch-apply as JSON")

    website_parser = subparsers.add_parser("website", help="Evaluate and validate static presentation-style website requests")
    website_subparsers = website_parser.add_subparsers(dest="website_command")
    website_check_parser = website_subparsers.add_parser("check", help="Classify a static presentation-style website requirement against the current supported public website surface and validate it through the canonical flow when in scope")
    website_check_parser.add_argument("requirement", nargs="?", help="Website requirement text")
    website_check_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    website_check_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or embedded://local")
    website_check_parser.add_argument("--project-dir", help="Optional target project directory for the validation run; default is a temp directory")
    website_check_parser.add_argument("--keep-existing", action="store_true", help="Reuse an already initialized validation project directory")
    website_check_parser.add_argument("--experimental-dynamic", action="store_true", help="Opt into experimental dynamic packs such as ecommerce or after-sales")
    website_check_parser.add_argument("--json", action="store_true", help="Print website check result as JSON")
    website_assets_parser = website_subparsers.add_parser("assets", help="Read the reusable website delivery asset bundles")
    website_assets_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_assets_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_assets_parser.add_argument("--json", action="store_true", help="Print website asset summary or one selected pack asset as JSON")
    website_open_asset_parser = website_subparsers.add_parser("open-asset", help="Resolve one concrete website delivery asset target")
    website_open_asset_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_open_asset_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_open_asset_parser.add_argument("--json", action="store_true", help="Print website open-asset result as JSON")
    website_inspect_asset_parser = website_subparsers.add_parser("inspect-asset", help="Inspect one resolved website delivery asset target")
    website_inspect_asset_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_inspect_asset_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_inspect_asset_parser.add_argument("--json", action="store_true", help="Print website inspect-asset result as JSON")
    website_preview_parser = website_subparsers.add_parser("preview", help="Show the current website-level preview and handoff targets")
    website_preview_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_preview_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_preview_parser.add_argument("--json", action="store_true", help="Print website preview as JSON")
    website_run_inspect_command_parser = website_subparsers.add_parser("run-inspect-command", help="Execute the inspect command implied by the current website delivery asset handoff")
    website_run_inspect_command_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_run_inspect_command_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_run_inspect_command_parser.add_argument("--json", action="store_true", help="Print website run-inspect-command result as JSON")
    website_export_handoff_parser = website_subparsers.add_parser("export-handoff", help="Export one consolidated website-oriented handoff bundle for operators, IDEs, and agents")
    website_export_handoff_parser.add_argument("pack_id", nargs="?", help="Optional website pack id such as company_product or ecom_storefront")
    website_export_handoff_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_export_handoff_parser.add_argument("--json", action="store_true", help="Print website export-handoff result as JSON")
    website_summary_parser = website_subparsers.add_parser("summary", help="Show the current website-oriented frontier, assets, validation, and demo state")
    website_summary_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_summary_parser.add_argument("--json", action="store_true", help="Print website summary as JSON")
    website_go_parser = website_subparsers.add_parser("go", help="Execute the current recommended website-oriented action")
    website_go_parser.add_argument("--experimental-dynamic", action="store_true", help="Include experimental dynamic packs such as ecommerce or after-sales")
    website_go_parser.add_argument("--json", action="store_true", help="Print website go as JSON")

    writing_parser = subparsers.add_parser("writing", help="Evaluate and scaffold low-token writing creation surfaces")
    writing_subparsers = writing_parser.add_subparsers(dest="writing_command")
    writing_check_parser = writing_subparsers.add_parser("check", help="Classify a writing requirement against the current structured low-token writing surface")
    writing_check_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_check_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_check_parser.add_argument("--json", action="store_true", help="Print writing check result as JSON")
    writing_packs_parser = writing_subparsers.add_parser("packs", help="List the current structured writing packs")
    writing_packs_parser.add_argument("--json", action="store_true", help="Print writing packs as JSON")
    writing_scaffold_parser = writing_subparsers.add_parser("scaffold", help="Generate one low-token writing scaffold for the current requirement")
    writing_scaffold_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_scaffold_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_scaffold_parser.add_argument("--json", action="store_true", help="Print writing scaffold as JSON")
    writing_brief_parser = writing_subparsers.add_parser("brief", help="Export one prompt-ready writing handoff for external models or editors")
    writing_brief_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_brief_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_brief_parser.add_argument("--emit-prompt", action="store_true", help="Print only the prompt-ready writing handoff text for an external model")
    writing_brief_parser.add_argument("--output-file", dest="output_file", help="Write the brief output to a file")
    writing_brief_parser.add_argument("--json", action="store_true", help="Print writing brief as JSON")
    writing_expand_parser = writing_subparsers.add_parser("expand", help="Expand one writing scaffold into a first drafting pass")
    writing_expand_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_expand_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_expand_parser.add_argument("--deep", action="store_true", help="Expand the first draft one layer deeper into a second-pass draft")
    writing_expand_parser.add_argument("--emit-text", action="store_true", help="Print only the expanded first-draft text")
    writing_expand_parser.add_argument("--output-file", dest="output_file", help="Write the expand output to a file")
    writing_expand_parser.add_argument("--json", action="store_true", help="Print writing expansion as JSON")
    writing_review_parser = writing_subparsers.add_parser("review", help="Review one draft against the current low-token writing scaffold")
    writing_review_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_review_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_review_parser.add_argument("--text", dest="review_text", help="Draft text to review")
    writing_review_parser.add_argument("--text-file", dest="review_text_file", help="Read draft text from a file")
    writing_review_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact review summary")
    writing_review_parser.add_argument("--output-file", dest="output_file", help="Write the review output to a file")
    writing_review_parser.add_argument("--json", action="store_true", help="Print writing review as JSON")
    writing_apply_check_parser = writing_subparsers.add_parser("apply-check", help="Validate that an external writing pass still stays inside the current scaffold boundary")
    writing_apply_check_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_apply_check_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_apply_check_parser.add_argument("--text", dest="review_text", help="Draft text to validate against the current scaffold")
    writing_apply_check_parser.add_argument("--text-file", dest="review_text_file", help="Read draft text from a file")
    writing_apply_check_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact apply-check summary")
    writing_apply_check_parser.add_argument("--output-file", dest="output_file", help="Write the apply-check output to a file")
    writing_apply_check_parser.add_argument("--json", action="store_true", help="Print writing apply-check as JSON")
    writing_bundle_parser = writing_subparsers.add_parser("bundle", help="Export one writing bundle with check, scaffold, brief, expand, and review outputs")
    writing_bundle_parser.add_argument("requirement", nargs="?", help="Writing requirement text")
    writing_bundle_parser.add_argument("--from-file", dest="from_file", help="Read requirement text from a file")
    writing_bundle_parser.add_argument("--text", dest="review_text", help="Optional draft text to review instead of reviewing the generated expand text")
    writing_bundle_parser.add_argument("--text-file", dest="review_text_file", help="Read optional draft text from a file")
    writing_bundle_parser.add_argument("--deep", action="store_true", help="Run the bundle with deep expansion enabled")
    writing_bundle_parser.add_argument("--zip", dest="zip_bundle", action="store_true", help="Also create a zip archive next to the bundle directory")
    writing_bundle_parser.add_argument("--copy-archive-path", action="store_true", help="Copy the generated bundle archive path to the macOS clipboard (requires --zip)")
    writing_bundle_parser.add_argument("--copy-summary", action="store_true", help="Copy the compact bundle summary text to the macOS clipboard")
    writing_bundle_parser.add_argument("--emit-summary", action="store_true", help="Print only a compact bundle summary")
    writing_bundle_parser.add_argument("--output-file", dest="output_file", help="Write the bundle output to a file")
    writing_bundle_parser.add_argument("--output-dir", dest="output_dir", help="Directory where the writing bundle should be written")
    writing_bundle_parser.add_argument("--json", action="store_true", help="Print writing bundle as JSON")
    writing_intent_parser = writing_subparsers.add_parser("intent", help="Show or save the current repo-level writing intent for later scaffolding and handoff")
    writing_intent_parser.add_argument("--audience", default=None, help="Primary audience summary for the current writing line")
    writing_intent_parser.add_argument("--format-mode", default=None, help="Writing mode, for example: copy, story, book")
    writing_intent_parser.add_argument("--genre", default=None, help="Genre or content lane, for example: fantasy, business, editorial")
    writing_intent_parser.add_argument("--style-direction", default=None, help="Short writing direction summary, for example: concise persuasive, calm literary, practical structured")
    writing_intent_parser.add_argument("--localization-mode", default=None, help="Localization mode, for example: english_only, bilingual, zh_cn_first")
    writing_intent_parser.add_argument("--target-length", default=None, help="Target output size, for example: short, chapter_outline, long_form")
    writing_intent_parser.add_argument("--notes", default=None, help="Freeform operator notes for the writing handoff")
    writing_intent_parser.add_argument("--style-keyword", action="append", default=None, help="Repeatable style keyword")
    writing_intent_parser.add_argument("--tone-keyword", action="append", default=None, help="Repeatable tone keyword")
    writing_intent_parser.add_argument("--narrative-constraint", action="append", default=None, help="Repeatable structural or narrative constraint")
    writing_intent_parser.add_argument("--reset", action="store_true", help="Reset the saved writing intent back to an empty default record")
    writing_intent_parser.add_argument("--json", action="store_true", help="Print writing intent as JSON")

    rc_check_parser = subparsers.add_parser("rc-check", help="Show the current RC and readiness state")
    rc_check_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    rc_check_parser.add_argument("--refresh", action="store_true", help="Refresh readiness snapshot before reading the latest RC state")
    rc_check_parser.add_argument("--json", action="store_true", help="Print rc-check as JSON")

    rc_go_parser = subparsers.add_parser("rc-go", help="Execute the current recommended RC-level action")
    rc_go_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    rc_go_parser.add_argument("--refresh", action="store_true", help="Refresh readiness snapshot before deciding the RC-level execution path")
    rc_go_parser.add_argument("--json", action="store_true", help="Print rc-go as JSON")

    workspace_parser = subparsers.add_parser("workspace", help="Show repo-level and current-project workspace status")
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")
    workspace_status_parser = workspace_subparsers.add_parser("status", help="Show current workspace, project, and readiness status")
    workspace_status_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_status_parser.add_argument("--json", action="store_true", help="Print workspace status as JSON")
    workspace_summary_parser = workspace_subparsers.add_parser("summary", help="Show a higher-level workspace summary")
    workspace_summary_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_summary_parser.add_argument("--json", action="store_true", help="Print workspace summary as JSON")
    workspace_hooks_parser = workspace_subparsers.add_parser("hooks", help="Inspect aggregated hook catalogs across generated workspace projects")
    workspace_hooks_parser.add_argument("--json", action="store_true", help="Print workspace hooks as JSON")
    workspace_hook_guide_parser = workspace_subparsers.add_parser(
        "hook-guide",
        help="Show the shortest repo-root hook workflow paths and their current recommended commands",
        description=(
            "Summarize the shortest repo-root hook workflow from the current workspace.\n"
            "Use this guide to decide whether to start from the preferred human path,\n"
            "or hand the machine-safe runnable path straight to another command."
        ),
        epilog=(
            "Common paths:\n"
            "  overview: ail workspace hook-guide --json\n"
            "  handoff:  ail workspace hook-guide --emit-shell\n"
            "  execute:  ail workspace hook-guide --run-command --json\n"
            "  preview:  ail workspace hook-continue --dry-run --text-compact\n"
            "  inspect:  ail workspace hook-continue --dry-run --inspect-target --text-compact"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    workspace_hook_guide_output_group = workspace_hook_guide_parser.add_argument_group("handoff helpers")
    workspace_hook_guide_output_group.add_argument("--emit-shell", action="store_true", help="Print only the preferred next workspace hook command from the current guide")
    workspace_hook_guide_output_group.add_argument("--copy-command", action="store_true", help="Copy only the preferred next workspace hook command from the current guide to the macOS clipboard")
    workspace_hook_guide_execution_group = workspace_hook_guide_parser.add_argument_group("execution")
    workspace_hook_guide_execution_group.add_argument("--run-command", action="store_true", help="Prepare or execute the machine-safe runnable workspace hook command from the current guide")
    workspace_hook_guide_execution_group.add_argument("--yes", action="store_true", help="Confirm that --run-command should actually execute the preferred runnable guide command")
    workspace_hook_guide_execution_group.add_argument("--json", action="store_true", help="Print workspace hook-guide as JSON")
    workspace_hook_init_parser = workspace_subparsers.add_parser(
        "hook-init",
        help="Scaffold one live hook file from the current project or one selected workspace project",
        description=(
            "Scaffold one durable hook file from the workspace root.\n"
            "Choose which generated project to target first, then narrow matching hook names,\n"
            "and finally pick or preview the live hook scaffold path."
        ),
        epilog=(
            "Common paths:\n"
            "  discover: ail workspace hook-init home --project-name MyProject --suggest --page-key home\n"
            "  preview:  ail workspace hook-init home.before --project-name MyProject --dry-run --json\n"
            "  explain:  ail workspace hook-init home.before --project-name MyProject --dry-run --explain\n"
            "  handoff:  ail workspace hook-init home.before --project-name MyProject --dry-run --emit-shell\n"
            "  execute:  ail workspace hook-init --follow-recommended --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    workspace_hook_init_parser.add_argument("hook_name", nargs="?", help="Real hook name, for example: page.home.before or shorthand like home.before")
    workspace_hook_init_project_group = workspace_hook_init_parser.add_argument_group("workspace project selection")
    workspace_hook_init_project_group.add_argument("--project-name", default=None, help="Optional generated project name under /output_projects to target from the workspace root")
    workspace_hook_init_project_group.add_argument("--use-recommended-project", action="store_true", help="Explicitly target the current recommended generated project from workspace hook coverage")
    workspace_hook_init_project_group.add_argument("--use-last-project", action="store_true", help="Reuse the most recently targeted workspace project from /.ail/last_workspace_hook_init.json")
    workspace_hook_init_project_group.add_argument("--follow-recommended", action="store_true", help="Use the current recommended workspace project and scaffold its first recommended live hook in one step")

    workspace_hook_init_scaffold_group = workspace_hook_init_parser.add_argument_group("scaffold setup")
    workspace_hook_init_scaffold_group.add_argument("--template", choices=["auto", "vue", "html"], default="auto", help="Starter example type to copy; auto picks a sensible default from the hook shape")
    workspace_hook_init_scaffold_group.add_argument("--dry-run", action="store_true", help="Preview the delegated hook scaffold target without writing a live hook file")
    workspace_hook_init_scaffold_group.add_argument("--force", action="store_true", help="Overwrite the target hook file if it already exists")

    workspace_hook_init_discovery_group = workspace_hook_init_parser.add_argument_group("hook discovery")
    workspace_hook_init_discovery_group.add_argument("--suggest", action="store_true", help="Suggest matching hook names instead of copying a file")
    workspace_hook_init_discovery_group.add_argument("--last-suggest", action="store_true", help="Show the most recent saved suggestion query from /.ail/last_hook_suggestions.json")
    workspace_hook_init_discovery_group.add_argument("--open-catalog", action="store_true", help="Return the project hook catalog paths and guidance without copying a file")
    workspace_hook_init_discovery_group.add_argument("--page-key", default=None, help="Optional page key filter for suggestions, for example: home, product, checkout")
    workspace_hook_init_discovery_group.add_argument("--section-key", default=None, help="Optional section key filter for suggestions, for example: hero, purchase, faq")
    workspace_hook_init_discovery_group.add_argument("--slot-key", default=None, help="Optional slot key filter for suggestions, for example: hero-actions, decision-grid, followup-actions")
    workspace_hook_init_discovery_group.add_argument("--reuse-last-suggest", action="store_true", help="Reuse the most recent saved suggestion query from /.ail/last_hook_suggestions.json")

    workspace_hook_init_selection_group = workspace_hook_init_parser.add_argument_group("selection, handoff, and execution")
    workspace_hook_init_selection_group.add_argument("--pick", action="store_true", help="When suggestion mode narrows to exactly one hook, scaffold it immediately instead of returning suggestions only")
    workspace_hook_init_selection_group.add_argument("--pick-recommended", action="store_true", help="When suggestion mode returns one or more hooks, scaffold the first recommended suggestion immediately")
    workspace_hook_init_selection_group.add_argument("--pick-index", type=int, default=None, help="Pick one numbered suggestion from suggestion mode and scaffold it immediately")
    workspace_hook_init_selection_group.add_argument("--emit-shell", action="store_true", help="Print only the single best next command for the current hook-init dry-run path")
    workspace_hook_init_selection_group.add_argument("--copy-command", action="store_true", help="Copy the single best next command for the current hook-init dry-run path to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-confirm-shell", action="store_true", help="Print only the most relevant confirm command for the current hook-init dry-run path")
    workspace_hook_init_selection_group.add_argument("--copy-confirm-command", action="store_true", help="Copy the most relevant confirm command for the current hook-init dry-run path to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-path", action="store_true", help="Print only the resolved target hook file path for the current hook-init flow")
    workspace_hook_init_selection_group.add_argument("--copy-target-path", action="store_true", help="Copy the resolved target hook file path for the current hook-init flow to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-dir", action="store_true", help="Print only the parent directory of the resolved target hook file path")
    workspace_hook_init_selection_group.add_argument("--copy-target-dir", action="store_true", help="Copy the parent directory of the resolved target hook file path to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-project-root", action="store_true", help="Print only the selected generated project root that owns the resolved target hook file path")
    workspace_hook_init_selection_group.add_argument("--copy-target-project-root", action="store_true", help="Copy the selected generated project root that owns the resolved target hook file path to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-project-name", action="store_true", help="Print only the selected generated project folder name that owns the resolved target hook file path")
    workspace_hook_init_selection_group.add_argument("--copy-target-project-name", action="store_true", help="Copy the selected generated project folder name that owns the resolved target hook file path to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-relative-path", action="store_true", help="Print only the resolved target hook file path relative to the selected project root")
    workspace_hook_init_selection_group.add_argument("--copy-target-relative-path", action="store_true", help="Copy the resolved target hook file path relative to the selected project root to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--emit-target-bundle", action="store_true", help="Print one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command")
    workspace_hook_init_selection_group.add_argument("--copy-target-bundle", action="store_true", help="Copy one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--inspect-target", action="store_true", help="Inspect the resolved hook-init target path and its parent directory as part of the current payload")
    workspace_hook_init_selection_group.add_argument("--open-target", action="store_true", help="Attach a direct open-target payload for the resolved hook-init file path")
    workspace_hook_init_selection_group.add_argument("--open-now", action="store_true", help="Resolve and immediately inspect the resolved hook-init target inside the current payload")
    workspace_hook_init_selection_group.add_argument("--emit-open-shell", action="store_true", help="Print only the direct inspect command for the resolved target hook file")
    workspace_hook_init_selection_group.add_argument("--copy-open-command", action="store_true", help="Copy the direct inspect command for the resolved target hook file to the macOS clipboard")
    workspace_hook_init_selection_group.add_argument("--run-command", action="store_true", help="Prepare or execute the single best next command for the current hook-init flow")
    workspace_hook_init_selection_group.add_argument("--run-open-command", action="store_true", help="Prepare or execute the direct inspect step for the resolved target hook file")
    workspace_hook_init_selection_group.add_argument("--yes", action="store_true", help="Confirm that --run-command or --run-open-command should actually execute the selected hook-init step")
    workspace_hook_init_selection_group.add_argument("--text-compact", action="store_true", help="Print a shorter operator-style text view for delegated scaffold and dry-run output")
    workspace_hook_init_selection_group.add_argument("--explain", action="store_true", help="Print a structured explanation of why this delegated scaffold path, target, and follow-up were chosen")
    workspace_hook_init_selection_group.add_argument("--json", action="store_true", help="Print workspace hook-init result as JSON")
    workspace_hook_continue_parser = workspace_subparsers.add_parser(
        "hook-continue",
        help="Continue the repo-root durable hook flow using the recent project when available, otherwise fall back to the recommended one-step path",
        description=(
            "Continue the repo-root durable hook workflow.\n"
            "Use preview flags to inspect the chosen surface first, target helpers to extract concrete paths,\n"
            "shell/clipboard helpers to hand commands off, and execution flags only when you're ready to act."
        ),
        epilog=(
            "Common paths:\n"
            "  preview: ail workspace hook-continue --dry-run --text-compact\n"
            "  inspect: ail workspace hook-continue --dry-run --inspect-target --text-compact\n"
            "  open:    ail workspace hook-continue --dry-run --open-target --json\n"
            "  execute: ail workspace hook-continue --dry-run --run-command --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    workspace_hook_continue_preview_group = workspace_hook_continue_parser.add_argument_group("preview and path selection")
    workspace_hook_continue_preview_group.add_argument("--broaden-to", choices=["auto", "section", "page"], default=None, help="When recent hook memory exists, optionally broaden the resumed surface automatically or from slot to section or from section/slot to page before continuing")
    workspace_hook_continue_preview_group.add_argument("--dry-run", action="store_true", help="Preview which continue path and hook target would be used without writing a live hook file")
    workspace_hook_continue_preview_group.add_argument("--text-compact", action="store_true", help="Print a shorter operator-oriented text summary instead of the full field-by-field view")
    workspace_hook_continue_preview_group.add_argument("--explain", action="store_true", help="Print a structured explanation of why this continue path, target, and follow-up were chosen")

    workspace_hook_continue_inspect_group = workspace_hook_continue_parser.add_argument_group("inspection and open helpers")
    workspace_hook_continue_inspect_group.add_argument("--inspect-target", action="store_true", help="Inspect the resolved hook target path and parent directory as part of the continue payload")
    workspace_hook_continue_inspect_group.add_argument("--open-target", action="store_true", help="Attach a direct open-target payload for the resolved hook file path")
    workspace_hook_continue_inspect_group.add_argument("--open-now", action="store_true", help="Resolve and immediately inspect the resolved hook target inside the current payload")

    workspace_hook_continue_shell_group = workspace_hook_continue_parser.add_argument_group("shell and clipboard helpers")
    workspace_hook_continue_shell_group.add_argument("--emit-shell", action="store_true", help="Print only the single best shell command to run next")
    workspace_hook_continue_shell_group.add_argument("--emit-open-shell", action="store_true", help="Print only the direct open-target shell command for the resolved hook file")
    workspace_hook_continue_shell_group.add_argument("--emit-confirm-shell", action="store_true", help="Print only the most relevant confirm command for the current continue mode")
    workspace_hook_continue_shell_group.add_argument("--copy-command", action="store_true", help="Copy the single best next command to the macOS clipboard")
    workspace_hook_continue_shell_group.add_argument("--copy-open-command", action="store_true", help="Copy the direct open-target shell command for the resolved hook file to the macOS clipboard")
    workspace_hook_continue_shell_group.add_argument("--copy-confirm-command", action="store_true", help="Copy the most relevant confirm command for the current continue mode to the macOS clipboard")

    workspace_hook_continue_target_group = workspace_hook_continue_parser.add_argument_group("target helpers")
    workspace_hook_continue_target_group.add_argument("--emit-target-path", action="store_true", help="Print only the resolved hook target path")
    workspace_hook_continue_target_group.add_argument("--emit-target-dir", action="store_true", help="Print only the parent directory of the resolved hook target path")
    workspace_hook_continue_target_group.add_argument("--emit-target-project-root", action="store_true", help="Print only the generated project root that owns the resolved hook target path")
    workspace_hook_continue_target_group.add_argument("--emit-target-project-name", action="store_true", help="Print only the generated project name that owns the resolved hook target path")
    workspace_hook_continue_target_group.add_argument("--emit-target-relative-path", action="store_true", help="Print the resolved hook target path relative to the generated project root")
    workspace_hook_continue_target_group.add_argument("--emit-target-bundle", action="store_true", help="Print one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command")
    workspace_hook_continue_target_group.add_argument("--copy-target-path", action="store_true", help="Copy the resolved hook target path to the macOS clipboard")
    workspace_hook_continue_target_group.add_argument("--copy-target-dir", action="store_true", help="Copy the parent directory of the resolved hook target path to the macOS clipboard")
    workspace_hook_continue_target_group.add_argument("--copy-target-project-root", action="store_true", help="Copy the generated project root that owns the resolved hook target path to the macOS clipboard")
    workspace_hook_continue_target_group.add_argument("--copy-target-project-name", action="store_true", help="Copy the generated project name that owns the resolved hook target path to the macOS clipboard")
    workspace_hook_continue_target_group.add_argument("--copy-target-relative-path", action="store_true", help="Copy the resolved hook target path relative to the generated project root to the macOS clipboard")
    workspace_hook_continue_target_group.add_argument("--copy-target-bundle", action="store_true", help="Copy one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command to the macOS clipboard")

    workspace_hook_continue_execution_group = workspace_hook_continue_parser.add_argument_group("execution")
    workspace_hook_continue_execution_group.add_argument("--run-open-command", action="store_true", help="Execute the direct open-target inspection step and return its result")
    workspace_hook_continue_execution_group.add_argument("--run-command", action="store_true", help="Execute the single best next command immediately and return its result")
    workspace_hook_continue_execution_group.add_argument("--yes", action="store_true", help="Confirm that --run-command or --run-open-command should actually execute the selected next command")
    workspace_hook_continue_execution_group.add_argument("--force", action="store_true", help="Overwrite the target hook file if it already exists")
    workspace_hook_continue_execution_group.add_argument("--json", action="store_true", help="Print workspace hook-continue result as JSON")
    workspace_preview_parser = workspace_subparsers.add_parser("preview", help="Show the current workspace-level preview and handoff targets")
    workspace_preview_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_preview_parser.add_argument("--json", action="store_true", help="Print workspace preview as JSON")
    workspace_open_target_parser = workspace_subparsers.add_parser("open-target", help="Resolve one preview target from the current workspace handoff")
    workspace_open_target_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    workspace_open_target_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_open_target_parser.add_argument("--json", action="store_true", help="Print resolved workspace preview target as JSON")
    workspace_inspect_target_parser = workspace_subparsers.add_parser("inspect-target", help="Inspect one resolved preview target from the current workspace handoff")
    workspace_inspect_target_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    workspace_inspect_target_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_inspect_target_parser.add_argument("--json", action="store_true", help="Print inspected workspace preview target as JSON")
    workspace_run_inspect_command_parser = workspace_subparsers.add_parser("run-inspect-command", help="Execute the inspect command implied by the current workspace preview handoff")
    workspace_run_inspect_command_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    workspace_run_inspect_command_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_run_inspect_command_parser.add_argument("--json", action="store_true", help="Print executed workspace inspect command result as JSON")
    workspace_export_handoff_parser = workspace_subparsers.add_parser("export-handoff", help="Export one consolidated workspace handoff bundle for IDEs, agents, and operators")
    workspace_export_handoff_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_export_handoff_parser.add_argument("--json", action="store_true", help="Print workspace export handoff as JSON")
    workspace_go_parser = workspace_subparsers.add_parser("go", help="Execute the current recommended workspace action")
    workspace_go_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_go_parser.add_argument("--json", action="store_true", help="Print workspace go result as JSON")
    workspace_doctor_parser = workspace_subparsers.add_parser("doctor", help="Run workspace-level recovery-oriented diagnosis and recommendations")
    workspace_doctor_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_doctor_parser.add_argument("--json", action="store_true", help="Print workspace doctor result as JSON")
    workspace_continue_parser = workspace_subparsers.add_parser("continue", help="Run the default high-frequency workspace follow-up action")
    workspace_continue_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    workspace_continue_parser.add_argument("--json", action="store_true", help="Print workspace continue result as JSON")

    cloud_parser = subparsers.add_parser("cloud", help="Show cloud-facing project and build status")
    cloud_subparsers = cloud_parser.add_subparsers(dest="cloud_command")
    cloud_status_parser = cloud_subparsers.add_parser("status", help="Show project, latest build, and artifact summary")
    cloud_status_parser.add_argument("project_id", nargs="?", help="Project identifier; defaults to the current project")
    cloud_status_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    cloud_status_parser.add_argument("--json", action="store_true", help="Print cloud status as JSON")

    compile_parser = subparsers.add_parser("compile", help="Compile AIL through cloud API")
    compile_parser.add_argument("--cloud", action="store_true", help="Use cloud compile mode")
    compile_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    compile_parser.add_argument("--json", action="store_true", help="Print compile result as JSON")

    build_parser = subparsers.add_parser("build", help="Query cloud build metadata")
    build_subparsers = build_parser.add_subparsers(dest="build_command")
    build_show_parser = build_subparsers.add_parser("show", help="Show one build by build id")
    build_show_parser.add_argument("build_id", help="Build identifier")
    build_show_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    build_show_parser.add_argument("--json", action="store_true", help="Print build result as JSON")
    build_artifact_parser = build_subparsers.add_parser("artifact", help="Show artifact descriptor for one build")
    build_artifact_parser.add_argument("build_id", help="Build identifier")
    build_artifact_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    build_artifact_parser.add_argument("--json", action="store_true", help="Print build artifact result as JSON")

    project_parser = subparsers.add_parser("project", help="Query cloud project metadata and build history")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    project_go_parser = project_subparsers.add_parser("go", help="Execute the current recommended project workbench action")
    project_go_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_go_parser.add_argument("--json", action="store_true", help="Print project go result as JSON")
    project_continue_parser = project_subparsers.add_parser("continue", help="Run the next high-frequency project action")
    continue_group = project_continue_parser.add_mutually_exclusive_group()
    continue_group.add_argument("--compile-sync", action="store_true", help="Compile current source and sync the latest managed output")
    continue_group.add_argument("--diagnose-compile-sync", action="store_true", help="Diagnose the current source first, then compile and sync only if it is already a compile candidate")
    continue_group.add_argument("--auto-repair-compile-sync", action="store_true", help="Diagnose the current source, auto-repair if needed, then compile and sync")
    project_continue_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_continue_parser.add_argument("--json", action="store_true", help="Print project continue result as JSON")
    project_check_parser = project_subparsers.add_parser("check", help="Run non-destructive local and cloud project health checks")
    project_check_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_check_parser.add_argument("--json", action="store_true", help="Print project check result as JSON")
    project_doctor_parser = project_subparsers.add_parser("doctor", help="Run project recovery-oriented diagnosis and action recommendations")
    project_doctor_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_doctor_parser.add_argument("--fix-plan", action="store_true", help="Include a structured fix plan for the recommended recovery path")
    project_doctor_parser.add_argument("--apply-safe-fixes", action="store_true", help="Apply low-risk local fixes or safe refresh actions for the current recovery path")
    project_doctor_parser.add_argument("--and-continue", action="store_true", help="After safe fixes, continue into compile and sync when the resulting state is safe to proceed")
    project_doctor_parser.add_argument("--json", action="store_true", help="Print project doctor result as JSON")
    project_summary_parser = project_subparsers.add_parser("summary", help="Show project-oriented local and cloud summary")
    project_summary_parser.add_argument("project_id", nargs="?", help="Project identifier; defaults to the current project")
    project_summary_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_summary_parser.add_argument("--json", action="store_true", help="Print project summary as JSON")
    project_hooks_parser = project_subparsers.add_parser("hooks", help="Inspect the current project hook catalog")
    project_hooks_parser.add_argument("page_key", nargs="?", help="Optional page key filter, for example: home, product, checkout")
    project_hooks_parser.add_argument("--json", action="store_true", help="Print project hooks as JSON")
    project_hook_guide_parser = project_subparsers.add_parser(
        "hook-guide",
        help="Show the shortest current-project hook workflow paths and their recommended commands",
        description=(
            "Summarize the shortest current-project hook workflow.\n"
            "Use this guide when you want one place that explains the preferred human path,\n"
            "the machine-safe runnable path, and the next safest handoff."
        ),
        epilog=(
            "Common paths:\n"
            "  overview: ail project hook-guide --json\n"
            "  handoff:  ail project hook-guide --emit-shell\n"
            "  execute:  ail project hook-guide --run-command --json\n"
            "  preview:  ail project hook-init home.before --dry-run --text-compact\n"
            "  explain:  ail project hook-init home.before --dry-run --explain"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    project_hook_guide_output_group = project_hook_guide_parser.add_argument_group("handoff helpers")
    project_hook_guide_output_group.add_argument("--emit-shell", action="store_true", help="Print only the preferred next project hook command from the current guide")
    project_hook_guide_output_group.add_argument("--copy-command", action="store_true", help="Copy only the preferred next project hook command from the current guide to the macOS clipboard")
    project_hook_guide_execution_group = project_hook_guide_parser.add_argument_group("execution")
    project_hook_guide_execution_group.add_argument("--run-command", action="store_true", help="Prepare or execute the machine-safe runnable project hook command from the current guide")
    project_hook_guide_execution_group.add_argument("--yes", action="store_true", help="Confirm that --run-command should actually execute the preferred runnable guide command")
    project_hook_guide_execution_group.add_argument("--json", action="store_true", help="Print project hook-guide as JSON")
    project_hook_init_parser = project_subparsers.add_parser(
        "hook-init",
        help="Copy one starter override example into a live hook file",
        description=(
            "Scaffold one durable hook file from the current project.\n"
            "Use discovery flags to inspect available hook names first, then choose one scaffold path,\n"
            "and only enable write-oriented flags when you're ready to materialize the live hook file."
        ),
        epilog=(
            "Common paths:\n"
            "  discover: ail project hook-init home --suggest --page-key home --section-key hero\n"
            "  preview:  ail project hook-init home.before --dry-run --json\n"
            "  explain: ail project hook-init home.before --dry-run --explain\n"
            "  handoff: ail project hook-init home.before --dry-run --emit-shell\n"
            "  execute: ail project hook-init home.before --suggest --pick --json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    project_hook_init_parser.add_argument("hook_name", nargs="?", help="Real hook name, for example: page.home.before or shorthand like home.before")
    project_hook_init_scaffold_group = project_hook_init_parser.add_argument_group("scaffold setup")
    project_hook_init_scaffold_group.add_argument("--template", choices=["auto", "vue", "html"], default="auto", help="Starter example type to copy; auto picks a sensible default from the hook shape")
    project_hook_init_scaffold_group.add_argument("--dry-run", action="store_true", help="Preview the hook scaffold target without writing a live hook file")
    project_hook_init_scaffold_group.add_argument("--force", action="store_true", help="Overwrite the target hook file if it already exists")

    project_hook_init_discovery_group = project_hook_init_parser.add_argument_group("hook discovery")
    project_hook_init_discovery_group.add_argument("--suggest", action="store_true", help="Suggest matching hook names instead of copying a file")
    project_hook_init_discovery_group.add_argument("--last-suggest", action="store_true", help="Show the most recent saved suggestion query from /.ail/last_hook_suggestions.json")
    project_hook_init_discovery_group.add_argument("--open-catalog", action="store_true", help="Return the project hook catalog paths and guidance without copying a file")
    project_hook_init_discovery_group.add_argument("--page-key", default=None, help="Optional page key filter for suggestions, for example: home, product, checkout")
    project_hook_init_discovery_group.add_argument("--section-key", default=None, help="Optional section key filter for suggestions, for example: hero, purchase, faq")
    project_hook_init_discovery_group.add_argument("--slot-key", default=None, help="Optional slot key filter for suggestions, for example: hero-actions, decision-grid, followup-actions")
    project_hook_init_discovery_group.add_argument("--reuse-last-suggest", action="store_true", help="Reuse the most recent saved suggestion query from /.ail/last_hook_suggestions.json")

    project_hook_init_selection_group = project_hook_init_parser.add_argument_group("selection, handoff, and execution")
    project_hook_init_selection_group.add_argument("--pick", action="store_true", help="When suggestion mode narrows to exactly one hook, scaffold it immediately instead of returning suggestions only")
    project_hook_init_selection_group.add_argument("--pick-recommended", action="store_true", help="When suggestion mode returns one or more hooks, scaffold the first recommended suggestion immediately")
    project_hook_init_selection_group.add_argument("--pick-index", type=int, default=None, help="Pick one numbered suggestion from suggestion mode and scaffold it immediately")
    project_hook_init_selection_group.add_argument("--emit-shell", action="store_true", help="Print only the single best next command for the current hook-init dry-run path")
    project_hook_init_selection_group.add_argument("--copy-command", action="store_true", help="Copy the single best next command for the current hook-init dry-run path to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-confirm-shell", action="store_true", help="Print only the most relevant confirm command for the current hook-init dry-run path")
    project_hook_init_selection_group.add_argument("--copy-confirm-command", action="store_true", help="Copy the most relevant confirm command for the current hook-init dry-run path to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-path", action="store_true", help="Print only the resolved target hook file path for the current hook-init flow")
    project_hook_init_selection_group.add_argument("--copy-target-path", action="store_true", help="Copy the resolved target hook file path for the current hook-init flow to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-dir", action="store_true", help="Print only the parent directory of the resolved target hook file path")
    project_hook_init_selection_group.add_argument("--copy-target-dir", action="store_true", help="Copy the parent directory of the resolved target hook file path to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-project-root", action="store_true", help="Print only the current generated project root that owns the resolved target hook file path")
    project_hook_init_selection_group.add_argument("--copy-target-project-root", action="store_true", help="Copy the current generated project root that owns the resolved target hook file path to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-project-name", action="store_true", help="Print only the current generated project folder name that owns the resolved target hook file path")
    project_hook_init_selection_group.add_argument("--copy-target-project-name", action="store_true", help="Copy the current generated project folder name that owns the resolved target hook file path to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-relative-path", action="store_true", help="Print only the resolved target hook file path relative to the current project root")
    project_hook_init_selection_group.add_argument("--copy-target-relative-path", action="store_true", help="Copy the resolved target hook file path relative to the current project root to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--emit-target-bundle", action="store_true", help="Print one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command")
    project_hook_init_selection_group.add_argument("--copy-target-bundle", action="store_true", help="Copy one compact JSON bundle containing the resolved target path, target dir, target project root, target project name, target relative path, open command, and confirm command to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--inspect-target", action="store_true", help="Inspect the resolved hook-init target path and its parent directory as part of the current payload")
    project_hook_init_selection_group.add_argument("--open-target", action="store_true", help="Attach a direct open-target payload for the resolved hook-init file path")
    project_hook_init_selection_group.add_argument("--open-now", action="store_true", help="Resolve and immediately inspect the resolved hook-init target inside the current payload")
    project_hook_init_selection_group.add_argument("--emit-open-shell", action="store_true", help="Print only the direct inspect command for the resolved target hook file")
    project_hook_init_selection_group.add_argument("--copy-open-command", action="store_true", help="Copy the direct inspect command for the resolved target hook file to the macOS clipboard")
    project_hook_init_selection_group.add_argument("--run-command", action="store_true", help="Prepare or execute the single best next command for the current hook-init flow")
    project_hook_init_selection_group.add_argument("--run-open-command", action="store_true", help="Prepare or execute the direct inspect step for the resolved target hook file")
    project_hook_init_selection_group.add_argument("--yes", action="store_true", help="Confirm that --run-command or --run-open-command should actually execute the selected hook-init step")
    project_hook_init_selection_group.add_argument("--text-compact", action="store_true", help="Print a shorter operator-style text view for direct scaffold and dry-run output")
    project_hook_init_selection_group.add_argument("--explain", action="store_true", help="Print a structured explanation of why this scaffold path, target, and follow-up were chosen")
    project_hook_init_selection_group.add_argument("--json", action="store_true", help="Print project hook-init result as JSON")
    project_preview_parser = project_subparsers.add_parser("preview", help="Show the current preview and artifact handoff for the project")
    project_preview_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_preview_parser.add_argument("--json", action="store_true", help="Print project preview as JSON")
    project_serve_parser = project_subparsers.add_parser("serve", help="Start or describe the local frontend dev server for the current generated project")
    project_serve_parser.add_argument("--host", default="127.0.0.1", help="Frontend dev server host, defaults to 127.0.0.1")
    project_serve_parser.add_argument("--port", type=int, default=5173, help="Frontend dev server port, defaults to 5173")
    project_serve_parser.add_argument("--install-if-needed", action="store_true", help="Run npm install if frontend dependencies are missing before starting the dev server")
    project_serve_parser.add_argument("--dry-run", action="store_true", help="Only show the serve command and local URL without starting the dev server")
    project_serve_parser.add_argument("--json", action="store_true", help="Print project serve result as JSON")
    project_open_target_parser = project_subparsers.add_parser("open-target", help="Resolve one preview target from the current project handoff")
    project_open_target_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    project_open_target_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_open_target_parser.add_argument("--json", action="store_true", help="Print resolved preview target as JSON")
    project_inspect_target_parser = project_subparsers.add_parser("inspect-target", help="Inspect one resolved preview target from the current project handoff")
    project_inspect_target_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    project_inspect_target_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_inspect_target_parser.add_argument("--json", action="store_true", help="Print inspected preview target as JSON")
    project_run_inspect_command_parser = project_subparsers.add_parser("run-inspect-command", help="Execute the inspect command implied by the current project preview handoff")
    project_run_inspect_command_parser.add_argument("label", nargs="?", help="Preview target label; defaults to the primary preview target")
    project_run_inspect_command_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_run_inspect_command_parser.add_argument("--json", action="store_true", help="Print executed project inspect command result as JSON")
    project_export_handoff_parser = project_subparsers.add_parser("export-handoff", help="Export one consolidated project handoff bundle for IDEs, agents, and operators")
    project_export_handoff_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_export_handoff_parser.add_argument("--json", action="store_true", help="Print project export handoff as JSON")
    project_style_brief_parser = project_subparsers.add_parser("style-brief", help="Export one architecture-first styling brief for external design models or operators")
    project_style_brief_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_style_brief_parser.add_argument("--emit-prompt", action="store_true", help="Print only the prompt-ready styling handoff text for an external model")
    project_style_brief_parser.add_argument("--json", action="store_true", help="Print project style brief as JSON")
    project_style_apply_check_parser = project_subparsers.add_parser("style-apply-check", help="Validate that styling changes stayed inside safe surfaces and preserved project runtime continuity")
    project_style_apply_check_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_style_apply_check_parser.add_argument("--emit-summary", action="store_true", help="Print only the compact style-apply-check summary text")
    project_style_apply_check_parser.add_argument("--json", action="store_true", help="Print project style apply check as JSON")
    project_style_intent_parser = project_subparsers.add_parser("style-intent", help="Show or save the current project styling intent for later handoff and validation")
    project_style_intent_parser.add_argument("--audience", default=None, help="Primary audience summary for the current project")
    project_style_intent_parser.add_argument("--style-direction", default=None, help="Short visual direction summary, for example: editorial, premium, bold, warm")
    project_style_intent_parser.add_argument("--localization-mode", default=None, help="Localization mode, for example: english_only, bilingual, zh_cn_first")
    project_style_intent_parser.add_argument("--notes", default=None, help="Freeform operator notes for the styling handoff")
    project_style_intent_parser.add_argument("--brand-keyword", action="append", default=None, help="Repeatable brand keyword")
    project_style_intent_parser.add_argument("--tone-keyword", action="append", default=None, help="Repeatable tone keyword")
    project_style_intent_parser.add_argument("--visual-constraint", action="append", default=None, help="Repeatable visual constraint or non-negotiable rule")
    project_style_intent_parser.add_argument("--reset", action="store_true", help="Reset the saved style intent back to an empty default record")
    project_style_intent_parser.add_argument("--json", action="store_true", help="Print project style intent as JSON")
    project_show_parser = project_subparsers.add_parser("show", help="Show project metadata")
    project_show_parser.add_argument("project_id", nargs="?", help="Project identifier; defaults to the current project")
    project_show_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_show_parser.add_argument("--json", action="store_true", help="Print project result as JSON")
    project_builds_parser = project_subparsers.add_parser("builds", help="List project build history")
    project_builds_parser.add_argument("project_id", nargs="?", help="Project identifier; defaults to the current project")
    project_builds_parser.add_argument("--limit", type=int, default=None, help="Maximum number of build records to return")
    project_builds_parser.add_argument("--cursor", default=None, help="Pagination cursor returned by a previous call")
    project_builds_parser.add_argument("--mode", default=None, help="Optional mode filter, for example: full")
    project_builds_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or http://127.0.0.1:5002")
    project_builds_parser.add_argument("--json", action="store_true", help="Print project builds as JSON")

    sync_parser = subparsers.add_parser("sync", help="Apply cached cloud build into managed zones")
    sync_group = sync_parser.add_mutually_exclusive_group()
    sync_group.add_argument("--backup-and-overwrite", action="store_true", help="Back up conflicting managed files under .ail/conflicts/<build_id>/ before overwrite")
    sync_group.add_argument("--abort-on-conflict", action="store_true", help="Abort if local drift is detected (default)")
    sync_parser.add_argument("--json", action="store_true", help="Print sync result as JSON")

    conflicts_parser = subparsers.add_parser("conflicts", help="Inspect current managed-file conflicts for the cached build")
    conflicts_parser.add_argument("--json", action="store_true", help="Print conflicts as JSON")

    diagnose_parser = subparsers.add_parser("diagnose", help="Diagnose AIL against current supported system boundaries")
    diagnose_parser.add_argument("input", nargs="?", default=".ail/source.ail", help="Path to AIL file, defaults to .ail/source.ail")
    diagnose_parser.add_argument("--requirement", help="Original requirement text")
    diagnose_parser.add_argument("--requirement-file", dest="requirement_file", help="Read requirement text from a file")
    diagnose_parser.add_argument("--json", action="store_true", help="Print diagnosis result as JSON")

    repair_parser = subparsers.add_parser("repair", help="Repair near-valid AIL into a compile candidate")
    repair_parser.add_argument("input", nargs="?", default=".ail/source.ail", help="Path to AIL file, defaults to .ail/source.ail")
    repair_parser.add_argument("--requirement", help="Original requirement text")
    repair_parser.add_argument("--requirement-file", dest="requirement_file", help="Read requirement text from a file")
    repair_parser.add_argument("--write", action="store_true", help="Write repaired output back to the input AIL file")
    repair_parser.add_argument("--json", action="store_true", help="Print repaired output as JSON")

    trial_parser = subparsers.add_parser("trial-run", help="Run the full frozen-profile trial path in one command")
    trial_parser.add_argument("--requirement", help="Requirement text for a custom trial run")
    trial_parser.add_argument("--scenario", help="Built-in scenario: landing, ecom_min, after_sales")
    trial_parser.add_argument("--list-scenarios", action="store_true", help="List built-in trial scenarios")
    trial_parser.add_argument("--project-dir", help="Target project directory; default is a temp directory")
    trial_parser.add_argument("--base-url", default=None, help="Cloud API base URL, defaults to AIL_CLOUD_BASE_URL or embedded://local")
    trial_parser.add_argument("--keep-existing", action="store_true", help="Reuse an already initialized project directory")
    trial_parser.add_argument("--json", action="store_true", help="Print trial result as JSON")

    return parser


def _available_trial_scenarios() -> list[str]:
    return ["landing", "ecom_min", "after_sales"]


def _scenario_requirement(name: str | None) -> str:
    scenarios = {
        "landing": "做一个 AI SaaS 官网，包含首页、功能介绍、FAQ、联系我们。",
        "ecom_min": "做一个数码商城，包含首页商品列表、商品详情、购物车、结算。",
        "after_sales": "做一个售后页面，包含退款申请、换货申请、投诉提交、联系客服。",
    }
    if not name:
        return ""
    return scenarios.get(name, "")


def _writing_pack_metadata() -> dict[str, dict[str, str]]:
    return {
        "copy_min": {
            "pack": "Copy / Messaging Pack",
            "support_level": "Supported",
            "expected_profile": "copy_min",
            "safe_positioning": "Position this as structured copywriting support for campaigns, product messaging, brand text, and page-level sales copy.",
        },
        "story_min": {
            "pack": "Story / Fiction Outline Pack",
            "support_level": "Supported",
            "expected_profile": "story_min",
            "safe_positioning": "Position this as a story-outline and scene-planning surface, not as a fully auto-finished long-form novel generator.",
        },
        "book_min": {
            "pack": "Book / Nonfiction Blueprint Pack",
            "support_level": "Supported",
            "expected_profile": "book_min",
            "safe_positioning": "Position this as a book-outline and chapter-planning surface for structured long-form writing.",
        },
        "out_of_scope": {
            "pack": "Out Of Scope",
            "support_level": "Out of Scope",
            "expected_profile": "out_of_scope",
            "safe_positioning": "Narrow the request back to structured copy, story, or book-planning work before treating it as current writing delivery scope.",
        },
    }


def _writing_intent_root() -> Path:
    return REPO_ROOT / ".workspace_ail"


def _writing_intent_path() -> Path:
    return _writing_intent_root() / "writing_intent.json"


def _default_writing_intent() -> dict[str, Any]:
    return {
        "audience": "",
        "format_mode": "",
        "genre": "",
        "style_direction": "",
        "localization_mode": "",
        "target_length": "",
        "style_keywords": [],
        "tone_keywords": [],
        "narrative_constraints": [],
        "notes": "",
    }


def _load_writing_intent() -> dict[str, Any]:
    payload = _default_writing_intent()
    path = _writing_intent_path()
    if not path.exists():
        return payload
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return payload
    if not isinstance(raw, dict):
        return payload
    payload["audience"] = str(raw.get("audience") or "").strip()
    payload["format_mode"] = str(raw.get("format_mode") or "").strip()
    payload["genre"] = str(raw.get("genre") or "").strip()
    payload["style_direction"] = str(raw.get("style_direction") or "").strip()
    payload["localization_mode"] = str(raw.get("localization_mode") or "").strip()
    payload["target_length"] = str(raw.get("target_length") or "").strip()
    payload["style_keywords"] = _normalize_string_list(list(raw.get("style_keywords") or []))
    payload["tone_keywords"] = _normalize_string_list(list(raw.get("tone_keywords") or []))
    payload["narrative_constraints"] = _normalize_string_list(list(raw.get("narrative_constraints") or []))
    payload["notes"] = str(raw.get("notes") or "").strip()
    return payload


def _save_writing_intent(payload: dict[str, Any]) -> Path:
    _writing_intent_root().mkdir(parents=True, exist_ok=True)
    path = _writing_intent_path()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _contains_any_term(req_lower: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in req_lower]


def _analyze_writing_requirement(requirement: str) -> dict[str, Any]:
    req = requirement.strip()
    req_lower = req.lower()
    matched_signals: list[str] = []
    boundary_findings: list[str] = []
    meta = _writing_pack_metadata()

    out_of_scope_terms = {
        "多人协作平台": "request includes collaborative platform behavior",
        "publishing platform": "request includes publishing-platform behavior",
        "出版平台": "request includes publishing-platform behavior",
        "cms": "request includes CMS behavior rather than writing scaffolding",
        "工作流系统": "request includes workflow-system behavior",
        "database": "request includes database-backed application behavior",
        "数据库": "request includes database-backed application behavior",
        "游戏引擎": "request includes game-engine behavior",
        "interactive game": "request includes interactive game behavior",
        "editor app": "request includes editor-application behavior",
        "写作软件": "request includes writing-software product behavior",
        "知识库": "request includes knowledge-base product behavior",
        "审稿后台": "request includes editorial back-office behavior",
        "投稿平台": "request includes submission-platform behavior",
    }
    for needle, finding in out_of_scope_terms.items():
        if needle in req_lower:
            boundary_findings.append(finding)
            matched_signals.append(needle)

    if boundary_findings:
        return {
            **meta["out_of_scope"],
            "classification_key": "out_of_scope",
            "writing_reason": "Requirement crosses the current writing boundary into software, platform, workflow, or database-backed product behavior.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    copy_terms = [
        "文案", "广告", "宣传", "营销", "产品介绍", "品牌介绍", "slogan", "tagline",
        "landing copy", "sales copy", "email copy", "campaign copy", "产品文案", "品牌文案",
        "官网文案", "转化文案", "邮件文案", "press release", "新闻稿",
        "公告", "announcement", "launch announcement", "产品发布", "发布公告",
        "发布说明", "发布稿", "上新", "新品发布", "媒体稿", "公关稿",
    ]
    story_terms = [
        "小说", "故事", "短篇", "长篇", "角色", "人物设定", "世界观", "章节", "情节", "plot",
        "scene", "chapter outline", "protagonist", "fantasy", "sci-fi", "romance", "悬疑", "奇幻",
    ]
    book_terms = [
        "书", "书籍", "目录", "章节目标", "非虚构", "商业书", "guidebook", "handbook", "memoir",
        "table of contents", "book outline", "chapter plan", "manual", "playbook", "教程书",
    ]

    story_matches = _contains_any_term(req_lower, story_terms)
    book_matches = _contains_any_term(req_lower, book_terms)
    copy_matches = _contains_any_term(req_lower, copy_terms)
    longform_completion_terms = [
        "20万字", "20 万字", "直接写完", "完整生成", "完整全文", "直接出版",
        "出版级", "publication-ready", "publish-ready", "full manuscript",
        "完整小说", "完整商业书", "完整书稿",
    ]
    longform_completion_matches = _contains_any_term(req_lower, longform_completion_terms)

    if longform_completion_matches and (story_matches or book_matches):
        matched_signals.extend(longform_completion_matches)
        matched_signals.extend(book_matches)
        matched_signals.extend(story_matches)
        return {
            **meta["out_of_scope"],
            "classification_key": "out_of_scope",
            "writing_reason": "Requirement asks for a fully finished long-form manuscript rather than the current scaffold-first writing surface.",
            "matched_signals": list(dict.fromkeys(matched_signals)),
            "boundary_findings": [
                "request asks for one-shot finished long-form delivery",
                "supported writing lanes currently stop at scaffold, brief, draft, and review passes",
            ],
        }

    if book_matches:
        matched_signals.extend(book_matches)
        return {
            **meta["book_min"],
            "classification_key": "book_min",
            "writing_reason": "Requirement maps to structured long-form book planning, such as table of contents, chapter goals, or nonfiction framing.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }
    if story_matches:
        matched_signals.extend(story_matches)
        return {
            **meta["story_min"],
            "classification_key": "story_min",
            "writing_reason": "Requirement maps to structured fiction planning, such as outline, character, chapter, or scene design.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }
    if copy_matches:
        matched_signals.extend(copy_matches)
        return {
            **meta["copy_min"],
            "classification_key": "copy_min",
            "writing_reason": "Requirement maps to structured copy and messaging work, such as campaign, product, landing, or brand text.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    return {
        **meta["out_of_scope"],
        "classification_key": "out_of_scope",
        "writing_reason": "Requirement does not map clearly to the current structured copy, story, or book-planning packs.",
        "matched_signals": matched_signals,
        "boundary_findings": ["request does not clearly fit one supported writing pack"],
    }


def _writing_delivery_contract(classification_key: str, *, expected_profile: str) -> dict[str, Any]:
    if classification_key == "copy_min":
        return {
            "surface": "structured_copy_scaffold",
            "supported_capabilities": [
                "campaign message hierarchy",
                "landing-page copy blocks",
                "product or brand messaging frameworks",
                "headline, CTA, and section-level copy planning",
            ],
            "unsupported_capabilities": [
                "fully auto-finalized brand system",
                "live content management workflows",
                "database-backed approval pipelines",
            ],
            "operator_positioning": "Position this as low-token structured copy generation, not as a finished content operations platform.",
            "stability_note": "This lane is best at structure, framing, and reusable copy blocks. Final polish can still be delegated to an external model or editor.",
            "validation_focus": [
                "check whether the output needs stronger audience positioning",
                "confirm the CTA and offer structure before treating it as final copy",
            ],
            "expected_profile": expected_profile,
        }
    if classification_key == "story_min":
        return {
            "surface": "story_outline_scaffold",
            "supported_capabilities": [
                "story premise and character cards",
                "chapter or scene skeletons",
                "conflict, arc, and pacing breakdowns",
                "worldbuilding and cast planning",
            ],
            "unsupported_capabilities": [
                "one-shot finished long-form novel generation",
                "book-length continuity guarantees without iteration",
                "publishing workflow management",
            ],
            "operator_positioning": "Position this as a low-token story architecture tool, not as an instant finished novel generator.",
            "stability_note": "This lane is strongest at scaffold-level fiction planning. Final prose quality still depends on later drafting passes.",
            "validation_focus": [
                "check if the character and arc structure is coherent before drafting",
                "confirm chapter granularity and point-of-view decisions early",
            ],
            "expected_profile": expected_profile,
        }
    if classification_key == "book_min":
        return {
            "surface": "book_blueprint_scaffold",
            "supported_capabilities": [
                "table of contents design",
                "chapter goal planning",
                "argument or lesson sequencing",
                "book framing, audience fit, and writing roadmap",
            ],
            "unsupported_capabilities": [
                "fully finished publication-ready manuscript generation",
                "editorial workflow management",
                "automated publishing-system behavior",
            ],
            "operator_positioning": "Position this as a low-token book blueprint and chapter-planning surface for long-form writing.",
            "stability_note": "This lane is strongest at structure and chapter planning, not at final publication-ready prose.",
            "validation_focus": [
                "check if the table of contents matches the target reader transformation",
                "confirm chapter goals before large drafting passes",
            ],
            "expected_profile": expected_profile,
        }
    return {
        "surface": "out_of_scope",
        "supported_capabilities": [],
        "unsupported_capabilities": [],
        "operator_positioning": "Narrow the requirement back to copy, story, or book scaffolding before positioning it as deliverable.",
        "stability_note": "No writing delivery contract is available because the request is currently out of scope.",
        "validation_focus": [
            "remove workflow, platform, editor-app, or publishing-system behavior from the request",
        ],
        "expected_profile": expected_profile,
    }


def _build_writing_check_next_steps(*, support_level: str, expected_profile: str) -> list[str]:
    if support_level == "Out of Scope":
        return [
            "narrow the requirement back to copy, story, or book scaffolding work",
            "remove platform, workflow-system, editor-app, or database-backed behavior from the request",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check \"<narrowed writing requirement>\" --json",
        ]
    return [
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing intent --format-mode {expected_profile} --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing packs --json",
        "use the resulting pack as a low-token scaffold, then let an external model or editor expand final prose if needed",
    ]


def _build_writing_check_payload(*, requirement: str) -> tuple[dict[str, Any], int]:
    analysis = _analyze_writing_requirement(requirement)
    support_level = analysis["support_level"]
    status = "ok" if support_level == "Supported" else "out_of_scope"
    exit_code = EXIT_OK if support_level == "Supported" else EXIT_VALIDATION
    payload = {
        "status": status,
        "entrypoint": "writing-check",
        "requirement": requirement,
        "writing_pack": analysis["pack"],
        "support_level": support_level,
        "expected_profile": analysis["expected_profile"],
        "writing_reason": analysis["writing_reason"],
        "safe_positioning": analysis["safe_positioning"],
        "matched_signals": analysis.get("matched_signals", []),
        "boundary_findings": analysis.get("boundary_findings", []),
        "writing_contract": _writing_delivery_contract(
            analysis["classification_key"],
            expected_profile=analysis["expected_profile"],
        ),
    }
    payload["next_steps"] = _build_writing_check_next_steps(
        support_level=support_level,
        expected_profile=analysis["expected_profile"] or "copy_min",
    )
    return payload, exit_code


def _writing_requirement_focus(requirement: str) -> str:
    cleaned = re.sub(r"\s+", " ", requirement.strip())
    return cleaned[:160] if cleaned else "the current writing requirement"


def _writing_effective_intent(*, classification_key: str) -> tuple[dict[str, Any], str]:
    intent = _load_writing_intent()
    stored_mode = str(intent.get("format_mode") or "").strip().lower()
    desired_mode = {
        "copy_min": "copy",
        "story_min": "story",
        "book_min": "book",
    }.get(classification_key, "")
    scope_status = "direct"
    if stored_mode and desired_mode and stored_mode not in {desired_mode, f"{desired_mode}_min"}:
        intent["genre"] = ""
        scope_status = "cross_mode_softened"
    if not intent.get("format_mode"):
        intent["format_mode"] = "adaptive"
    if not intent.get("localization_mode"):
        intent["localization_mode"] = "unspecified"
    if not intent.get("target_length"):
        intent["target_length"] = "structured_scaffold"
    return intent, scope_status


def _copy_scaffold(requirement: str, intent: dict[str, Any]) -> dict[str, Any]:
    audience = intent.get("audience") or "the target buyer"
    focus = _writing_requirement_focus(requirement)
    tone = ", ".join(intent.get("tone_keywords") or []) or "clear and persuasive"
    style = ", ".join(intent.get("style_keywords") or []) or "structured"
    return {
        "headline": f"Help {audience} understand why this offer deserves the next click.",
        "one_line_promise": f"Turn {focus} into a short, conversion-aware message hierarchy.",
        "message_architecture": {
            "problem": f"{audience} still needs a faster way to understand the offer, the fit, and the next action.",
            "promise": f"Present the offer in a {tone} way so the reader reaches a decision with less friction.",
            "proof": [
                "clarify the audience fit first",
                "translate the value into concrete outcomes",
                "close with one visible next action",
            ],
            "cta_direction": [
                "Book a demo",
                "Request pricing",
                "Start the conversation",
            ],
        },
        "sections": [
            {"section": "hero", "goal": "state the promise fast", "notes": f"use a {style} headline and one direct CTA"},
            {"section": "pain", "goal": "name the current friction", "notes": "show what is slow, expensive, or confusing today"},
            {"section": "solution", "goal": "introduce the offer", "notes": "connect the product or service to one immediate operational benefit"},
            {"section": "proof", "goal": "lower doubt", "notes": "use proof points, examples, or credibility signals"},
            {"section": "offer", "goal": "make the action obvious", "notes": "restate fit, value, and CTA in one compact block"},
        ],
        "draft_tasks": [
            "write three headline options with different intensity levels",
            "draft one short proof block and one longer proof block",
            "draft two CTA variants for high-intent and mid-intent readers",
        ],
    }


def _story_scaffold(requirement: str, intent: dict[str, Any]) -> dict[str, Any]:
    audience = intent.get("audience") or "story readers"
    genre = intent.get("genre") or "speculative fiction"
    focus = _writing_requirement_focus(requirement)
    constraints = intent.get("narrative_constraints") or ["keep the conflict visible in every chapter"]
    return {
        "working_title": f"{genre.title()} Blueprint for {audience}",
        "story_core": {
            "premise": f"Build a story around {focus}, with a conflict that escalates before the protagonist fully understands the cost.",
            "protagonist_goal": "want something concrete enough to pursue chapter by chapter",
            "opposition": "introduce one human force and one systemic force working against that goal",
            "stakes": "if the protagonist fails, they lose more than status or convenience",
            "tone": ", ".join(intent.get("tone_keywords") or []) or "clear, tense, and forward-moving",
        },
        "character_cards": [
            {"role": "protagonist", "need": "external victory", "hidden_need": "internal correction", "risk": "chooses speed over understanding"},
            {"role": "ally", "need": "keep the mission alive", "hidden_need": "prove loyalty without disappearing into support work", "risk": "knows too much and says too little"},
            {"role": "opposition", "need": "preserve control", "hidden_need": "avoid exposure", "risk": "underestimates what pressure reveals"},
        ],
        "chapter_tree": [
            {"chapter": 1, "label": "disruption", "goal": "break the old equilibrium and show the cost of inaction"},
            {"chapter": 2, "label": "commitment", "goal": "force the protagonist to choose a path they cannot easily reverse"},
            {"chapter": 3, "label": "pressure", "goal": "tighten the conflict and reveal the first deeper consequence"},
            {"chapter": 4, "label": "reversal", "goal": "strip away a false assumption and force a harder strategy"},
            {"chapter": 5, "label": "decision", "goal": "land the major confrontation and set up the next draft pass"},
        ],
        "scene_tasks": [
            "draft the opening disturbance scene in one page",
            "write one confrontation scene that reveals the protagonist's flaw",
            "draft the midpoint reversal before expanding secondary threads",
        ],
        "narrative_constraints": constraints,
    }


def _book_scaffold(requirement: str, intent: dict[str, Any]) -> dict[str, Any]:
    audience = intent.get("audience") or "the target reader"
    genre = intent.get("genre") or "practical nonfiction"
    focus = _writing_requirement_focus(requirement)
    return {
        "book_title": f"{genre.title()} Blueprint for {audience}",
        "reader_transformation": f"Help {audience} move from confusion to a repeatable approach around {focus}.",
        "positioning": {
            "reader": audience,
            "promise": "deliver a structured transformation rather than a loose set of ideas",
            "scope_boundary": "keep the book focused on one clear progression the reader can follow chapter by chapter",
        },
        "table_of_contents": [
            {"chapter": 1, "title": "Why the current approach breaks", "goal": "name the reader's current friction and reset expectations"},
            {"chapter": 2, "title": "What the new model changes", "goal": "introduce the core framework in plain language"},
            {"chapter": 3, "title": "How to apply it step by step", "goal": "turn the framework into an operating sequence"},
            {"chapter": 4, "title": "Where execution usually fails", "goal": "surface edge cases, mistakes, and recovery patterns"},
            {"chapter": 5, "title": "How to sustain the result", "goal": "show how the reader keeps the new system working over time"},
        ],
        "chapter_cards": [
            {"chapter": 1, "reader_question": "why does this keep feeling harder than it should?", "evidence_needed": "one strong example or contrast"},
            {"chapter": 2, "reader_question": "what is the new mental model?", "evidence_needed": "one diagram, metaphor, or named framework"},
            {"chapter": 3, "reader_question": "what do I do first?", "evidence_needed": "a sequence the reader can test immediately"},
            {"chapter": 4, "reader_question": "what could go wrong?", "evidence_needed": "mistakes, objections, and correction paths"},
            {"chapter": 5, "reader_question": "how do I keep this working?", "evidence_needed": "a maintenance loop or review cadence"},
        ],
        "research_gaps": [
            "collect one concrete case study or operational example for each major chapter",
            "decide which chapter deserves a framework diagram",
            "identify where definitions need to be simplified for first-time readers",
        ],
    }


def _build_writing_scaffold_payload(*, requirement: str) -> tuple[dict[str, Any], int]:
    analysis = _analyze_writing_requirement(requirement)
    support_level = analysis["support_level"]
    if support_level != "Supported":
        payload, exit_code = _build_writing_check_payload(requirement=requirement)
        payload = {
            **payload,
            "entrypoint": "writing-scaffold",
            "scaffold_surface": "unavailable",
            "scaffold": {},
        }
        return payload, exit_code

    classification_key = analysis["classification_key"]
    intent, intent_scope_status = _writing_effective_intent(classification_key=classification_key)
    if classification_key == "copy_min":
        scaffold = _copy_scaffold(requirement, intent)
        scaffold_surface = "copy_message_hierarchy"
    elif classification_key == "story_min":
        scaffold = _story_scaffold(requirement, intent)
        scaffold_surface = "story_outline_architecture"
    else:
        scaffold = _book_scaffold(requirement, intent)
        scaffold_surface = "book_blueprint_architecture"

    next_steps = [
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing intent --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check {shlex.quote(requirement)} --json",
        "use this scaffold as the low-token source of truth before asking an external model to expand prose",
    ]
    payload = {
        "status": "ok",
        "entrypoint": "writing-scaffold",
        "requirement": requirement,
        "writing_pack": analysis["pack"],
        "support_level": support_level,
        "expected_profile": analysis["expected_profile"],
        "writing_reason": analysis["writing_reason"],
        "safe_positioning": analysis["safe_positioning"],
        "matched_signals": analysis.get("matched_signals", []),
        "boundary_findings": analysis.get("boundary_findings", []),
        "writing_contract": _writing_delivery_contract(
            classification_key,
            expected_profile=analysis["expected_profile"],
        ),
        "scaffold_surface": scaffold_surface,
        "writing_intent_path": str(_writing_intent_path()),
        "intent_scope_status": intent_scope_status,
        "writing_intent": intent,
        "scaffold": scaffold,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_writing_brief_prompt_text(payload: dict[str, Any]) -> str:
    intent = payload.get("writing_intent") or {}
    contract = payload.get("writing_contract") or {}
    scaffold = payload.get("scaffold") or {}
    style_keywords = ", ".join(intent.get("style_keywords") or []) or "(not specified)"
    tone_keywords = ", ".join(intent.get("tone_keywords") or []) or "(not specified)"
    narrative_constraints = "\n".join(f"- {item}" for item in (intent.get("narrative_constraints") or [])) or "- (not specified)"
    supported_capabilities = "\n".join(f"- {item}" for item in (contract.get("supported_capabilities") or [])) or "- (none)"
    unsupported_capabilities = "\n".join(f"- {item}" for item in (contract.get("unsupported_capabilities") or [])) or "- (none)"

    return (
        "You are continuing a writing task from an AIL Builder low-token scaffold.\n\n"
        "Keep the structure, scope, and pack boundary intact.\n"
        "Do not reposition this as a software product, CMS, editor platform, or database-backed workflow.\n\n"
        f"Requirement:\n- {payload.get('requirement', '')}\n\n"
        "Current writing intent:\n"
        f"- audience: {intent.get('audience') or '(not specified)'}\n"
        f"- format_mode: {intent.get('format_mode') or '(not specified)'}\n"
        f"- genre: {intent.get('genre') or '(not specified)'}\n"
        f"- style_direction: {intent.get('style_direction') or '(not specified)'}\n"
        f"- localization_mode: {intent.get('localization_mode') or '(not specified)'}\n"
        f"- target_length: {intent.get('target_length') or '(not specified)'}\n"
        f"- style_keywords: {style_keywords}\n"
        f"- tone_keywords: {tone_keywords}\n"
        f"- notes: {intent.get('notes') or '(none)'}\n\n"
        "Narrative or structural constraints:\n"
        f"{narrative_constraints}\n\n"
        "Supported capabilities in this lane:\n"
        f"{supported_capabilities}\n\n"
        "Do not claim these capabilities:\n"
        f"{unsupported_capabilities}\n\n"
        "Scaffold summary:\n"
        f"{json.dumps(scaffold, ensure_ascii=False, indent=2)}\n\n"
        "Working rules:\n"
        "- preserve the scaffold's hierarchy before expanding language\n"
        "- expand one section, scene, or chapter unit at a time\n"
        "- keep continuity with the intended audience and tone\n"
        "- do not overpromise production-ready completeness if the scaffold is still exploratory\n\n"
        "Preferred next move:\n"
        "- expand this scaffold into a first drafting pass while keeping the structure recognizable\n"
    )


def _build_writing_brief_payload(*, requirement: str) -> tuple[dict[str, Any], int]:
    scaffold_payload, exit_code = _build_writing_scaffold_payload(requirement=requirement)
    recommended_commands = [
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing intent --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check {shlex.quote(requirement)} --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing scaffold {shlex.quote(requirement)} --json",
    ]
    next_steps = [
        f"run {recommended_commands[0]}",
        f"run {recommended_commands[2]}",
        "paste the model_prompt into your external writing model and expand one unit at a time",
    ]
    payload = {
        **scaffold_payload,
        "entrypoint": "writing-brief",
        "brief_mode": "architecture_first_writing_handoff",
        "operator_positioning": "AIL owns the low-token writing structure; external models should expand prose without breaking the scaffold boundary.",
        "scaffold_summary": {
            "scaffold_surface": scaffold_payload.get("scaffold_surface", ""),
            "intent_scope_status": scaffold_payload.get("intent_scope_status", ""),
            "headline": ((scaffold_payload.get("scaffold") or {}).get("headline") or ""),
            "working_title": ((scaffold_payload.get("scaffold") or {}).get("working_title") or ""),
            "book_title": ((scaffold_payload.get("scaffold") or {}).get("book_title") or ""),
        },
        "recommended_commands": recommended_commands,
        "source_commands": {
            "writing_intent": recommended_commands[0],
            "writing_check": recommended_commands[1],
            "writing_scaffold": recommended_commands[2],
        },
        "next_steps": next_steps,
    }
    payload["model_prompt"] = _build_writing_brief_prompt_text(payload)
    return payload, exit_code


def _writing_expand_variant_seed(requirement: str, profile: str) -> int:
    key = f"{profile}|{requirement.strip()}".strip()
    if not key:
        return 0
    return sum(ord(ch) for ch in key) % 3


def _copy_expand(scaffold: dict[str, Any], intent: dict[str, Any], *, variant_seed: int) -> tuple[str, list[dict[str, str]], str]:
    headline = str(scaffold.get("headline") or "A clearer offer starts here.")
    promise = str(scaffold.get("one_line_promise") or "Turn the current offer into a message the reader can act on.")
    message_architecture = scaffold.get("message_architecture") or {}
    proof_points = list(message_architecture.get("proof") or [])
    ctas = list(message_architecture.get("cta_direction") or ["Book a demo"])
    tone = ", ".join(intent.get("tone_keywords") or []) or "clear and direct"
    variant_id = ["copy_direct", "copy_editorial", "copy_operator"][variant_seed]
    if variant_seed == 0:
        sections = [
            {
                "label": "hero_draft",
                "text": (
                    f"{headline}\n\n"
                    f"{promise} We frame the problem in a {tone} voice, then move quickly into why this offer is easier to trust, easier to understand, and easier to act on."
                ),
            },
            {
                "label": "proof_draft",
                "text": (
                    "Why this lands:\n"
                    + "\n".join(f"- {point.capitalize()}." for point in proof_points)
                    + "\n\nInstead of forcing the reader to decode the value, the page carries them from fit to proof to next step."
                ),
            },
            {
                "label": "cta_draft",
                "text": (
                    f"Next step: {ctas[0]}\n\n"
                    f"If the reader already feels the pain and can see the fit, the call to action should feel like the natural continuation rather than a hard sell."
                ),
            },
        ]
    elif variant_seed == 1:
        sections = [
            {
                "label": "hero_draft",
                "text": (
                    f"{headline}\n\n"
                    f"{promise} The copy should open with confidence, then slow just enough to help the reader feel oriented instead of rushed."
                ),
            },
            {
                "label": "proof_draft",
                "text": (
                    "What makes the message believable:\n"
                    + "\n".join(f"- {point.capitalize()}." for point in proof_points)
                    + "\n\nThe reader should feel that each line reduces uncertainty rather than piling on more claims."
                ),
            },
            {
                "label": "cta_draft",
                "text": (
                    f"Suggested close: {ctas[0]}\n\n"
                    f"End with one clear action and one short reason to take it now, so the page finishes with momentum instead of hesitation."
                ),
            },
        ]
    else:
        sections = [
            {
                "label": "hero_draft",
                "text": (
                    f"{headline}\n\n"
                    f"{promise} The opening should work like an operator summary: what changed, why it matters, and what the reader should do next."
                ),
            },
            {
                "label": "proof_draft",
                "text": (
                    "Operational proof:\n"
                    + "\n".join(f"- {point.capitalize()}." for point in proof_points)
                    + "\n\nEach point should help the reader move from vague interest to a more concrete buying decision."
                ),
            },
            {
                "label": "cta_draft",
                "text": (
                    f"Recommended action: {ctas[0]}\n\n"
                    f"Treat the CTA like the next operational step, not a decorative footer button."
                ),
            },
        ]
    expanded_text = "\n\n".join(item["text"] for item in sections)
    return variant_id, sections, expanded_text


def _story_expand(scaffold: dict[str, Any], intent: dict[str, Any], *, variant_seed: int) -> tuple[str, list[dict[str, str]], str]:
    story_core = scaffold.get("story_core") or {}
    chapter_tree = list(scaffold.get("chapter_tree") or [])
    character_cards = list(scaffold.get("character_cards") or [])
    protagonist = (character_cards[0] if character_cards else {})
    tone = str(story_core.get("tone") or ", ".join(intent.get("tone_keywords") or []) or "tense")
    chapter_one = chapter_tree[0] if chapter_tree else {"label": "opening", "goal": "disturb the current equilibrium"}
    chapter_two = chapter_tree[1] if len(chapter_tree) > 1 else {"label": "choice", "goal": "force a commitment"}
    variant_id = ["story_cinematic", "story_close_psychology", "story_forward_pressure"][variant_seed]
    if variant_seed == 0:
        sections = [
            {
                "label": "opening_scene_draft",
                "text": (
                    f"Opening scene, {chapter_one['label']}:\n\n"
                    f"The story begins in a {tone} register. The protagonist moves through a familiar routine until the cost of staying passive becomes impossible to ignore. "
                    f"What seemed manageable suddenly carries a sharper consequence, and the first real fracture in the old equilibrium appears."
                ),
            },
            {
                "label": "character_motion_draft",
                "text": (
                    f"Character motion:\n\n"
                    f"The protagonist wants {protagonist.get('need', 'a concrete win')}, but the hidden pressure comes from {protagonist.get('hidden_need', 'an internal correction')}. "
                    f"That tension shapes every decision, especially once the ally and the opposition begin pulling the same conflict in different directions."
                ),
            },
            {
                "label": "chapter_progression_draft",
                "text": (
                    f"From chapter one into chapter two:\n\n"
                    f"After the initial disruption, the story pivots into {chapter_two['label']}. "
                    f"The protagonist is forced to choose a path that costs them safety, clarity, or reputation, which gives the next chapter its forward pressure."
                ),
            },
        ]
    elif variant_seed == 1:
        sections = [
            {
                "label": "opening_scene_draft",
                "text": (
                    f"Opening scene, {chapter_one['label']}:\n\n"
                    f"The opening should feel intimate before it feels large. We stay close to the protagonist's perception, letting the first disturbance arrive through one detail that refuses to stay ignorable."
                ),
            },
            {
                "label": "character_motion_draft",
                "text": (
                    "Inner pressure:\n\n"
                    f"Under the visible goal of {protagonist.get('need', 'a concrete win')}, the protagonist is really wrestling with {protagonist.get('hidden_need', 'an internal correction')}. "
                    f"That inner contradiction is what gives later scenes their emotional recoil."
                ),
            },
            {
                "label": "chapter_progression_draft",
                "text": (
                    f"Toward chapter two:\n\n"
                    f"The consequence of the first disturbance should narrow the protagonist's options until {chapter_two['label']} is no longer a free choice but the least survivable refusal."
                ),
            },
        ]
    else:
        sections = [
            {
                "label": "opening_scene_draft",
                "text": (
                    f"Opening scene, {chapter_one['label']}:\n\n"
                    f"Begin with motion. The world is already leaning toward rupture, and the protagonist notices it a breath too late. The first scene should feel like pressure arriving before explanation."
                ),
            },
            {
                "label": "character_motion_draft",
                "text": (
                    "Conflict engine:\n\n"
                    f"The protagonist reaches for {protagonist.get('need', 'a concrete win')}, but every fast decision drags them closer to the weakness hidden inside {protagonist.get('hidden_need', 'an internal correction')}."
                ),
            },
            {
                "label": "chapter_progression_draft",
                "text": (
                    f"Forward pressure:\n\n"
                    f"Chapter one should end with momentum already pointing at {chapter_two['label']}, so the next move feels unavoidable and costly at the same time."
                ),
            },
        ]
    expanded_text = "\n\n".join(item["text"] for item in sections)
    return variant_id, sections, expanded_text


def _book_expand(scaffold: dict[str, Any], intent: dict[str, Any], *, variant_seed: int) -> tuple[str, list[dict[str, str]], str]:
    transformation = str(scaffold.get("reader_transformation") or "Help the reader move toward a more repeatable approach.")
    toc = list(scaffold.get("table_of_contents") or [])
    first = toc[0] if toc else {"title": "Why the current approach breaks", "goal": "reset expectations"}
    second = toc[1] if len(toc) > 1 else {"title": "What the new model changes", "goal": "introduce the framework"}
    audience = str((scaffold.get("positioning") or {}).get("reader") or intent.get("audience") or "the target reader")
    variant_id = ["book_coach", "book_editorial", "book_operator"][variant_seed]
    if variant_seed == 0:
        sections = [
            {
                "label": "intro_draft",
                "text": (
                    f"Book introduction:\n\n"
                    f"This book is for {audience}. {transformation} The opening pages should make the reader feel seen, then quickly show that the current way of operating breaks for predictable reasons."
                ),
            },
            {
                "label": "chapter_one_draft",
                "text": (
                    f"Chapter 1, {first['title']}:\n\n"
                    f"Start by naming the friction the reader already feels. Then explain why that friction is not random; it comes from an outdated operating model. "
                    f"The goal of this chapter is to reset expectations and prepare the reader for a more useful framework."
                ),
            },
            {
                "label": "chapter_two_bridge_draft",
                "text": (
                    f"Bridge into Chapter 2, {second['title']}:\n\n"
                    f"Once the old model has been discredited, the reader is ready for the new one. "
                    f"This section should turn the argument into a practical framework the reader can remember and apply."
                ),
            },
        ]
    elif variant_seed == 1:
        sections = [
            {
                "label": "intro_draft",
                "text": (
                    f"Book introduction:\n\n"
                    f"Open with recognition, not abstraction. {audience} should feel that the book understands the frustration beneath the surface before it starts teaching."
                ),
            },
            {
                "label": "chapter_one_draft",
                "text": (
                    f"Chapter 1, {first['title']}:\n\n"
                    f"This chapter should read like a reframe. The reader first sees their current struggle more clearly, then understands why the old explanation was incomplete."
                ),
            },
            {
                "label": "chapter_two_bridge_draft",
                "text": (
                    f"Bridge into Chapter 2, {second['title']}:\n\n"
                    f"Only after the old frame has collapsed should the book introduce a cleaner one, with language simple enough to remember and strong enough to use."
                ),
            },
        ]
    else:
        sections = [
            {
                "label": "intro_draft",
                "text": (
                    f"Book introduction:\n\n"
                    f"This book is written for {audience}, and it should open like an operator memo: what is broken, what will change, and what the reader will be able to do differently."
                ),
            },
            {
                "label": "chapter_one_draft",
                "text": (
                    f"Chapter 1, {first['title']}:\n\n"
                    f"Name the bottleneck directly. Show that the current system creates predictable waste, then make the reader ready to replace it rather than optimize around it."
                ),
            },
            {
                "label": "chapter_two_bridge_draft",
                "text": (
                    f"Bridge into Chapter 2, {second['title']}:\n\n"
                    f"Once the reader accepts that the old model is expensive, chapter two should give them a practical replacement they can test immediately."
                ),
            },
        ]
    expanded_text = "\n\n".join(item["text"] for item in sections)
    return variant_id, sections, expanded_text


def _deepen_copy_units(units: list[dict[str, str]]) -> tuple[list[dict[str, str]], str]:
    deep_units = []
    additions = {
        "hero_draft": "Second-pass note:\n\nTighten the opening around one concrete buyer outcome so the page feels less descriptive and more decision-oriented.",
        "proof_draft": "Second-pass note:\n\nAdd one sharper proof signal, such as an operating metric, a customer example, or a before-and-after contrast.",
        "cta_draft": "Second-pass note:\n\nRephrase the CTA support copy so it removes one last hesitation rather than only repeating the action.",
    }
    fallback = "Second-pass note:\n\nSharpen this block with one more concrete detail."
    for item in units:
        label = str(item.get("label") or "")
        text = str(item.get("text") or "")
        addition = additions.get(label, fallback)
        deep_units.append({"label": label, "text": f"{text}\n\n{addition}"})
    return deep_units, "\n\n".join(unit["text"] for unit in deep_units)


def _deepen_story_units(units: list[dict[str, str]]) -> tuple[list[dict[str, str]], str]:
    deep_units = []
    additions = {
        "opening_scene_draft": "Second-pass note:\n\nAdd one sensory detail and one irreversible choice so the scene starts carrying consequence instead of only atmosphere.",
        "character_motion_draft": "Second-pass note:\n\nMake the contradiction between outer goal and hidden need visible through one behavioral habit or reflex.",
        "chapter_progression_draft": "Second-pass note:\n\nEnd the transition with a sharper loss condition so chapter two feels compelled, not merely suggested.",
    }
    fallback = "Second-pass note:\n\nPush the conflict one layer deeper."
    for item in units:
        label = str(item.get("label") or "")
        text = str(item.get("text") or "")
        addition = additions.get(label, fallback)
        deep_units.append({"label": label, "text": f"{text}\n\n{addition}"})
    return deep_units, "\n\n".join(unit["text"] for unit in deep_units)


def _deepen_book_units(units: list[dict[str, str]]) -> tuple[list[dict[str, str]], str]:
    deep_units = []
    additions = {
        "intro_draft": "Second-pass note:\n\nGive the reader one sharper promise about what they will be able to do differently after finishing the book.",
        "chapter_one_draft": "Second-pass note:\n\nAnchor the chapter in one recognizable operating mistake so the diagnosis feels earned.",
        "chapter_two_bridge_draft": "Second-pass note:\n\nName the first practical shift the reader can test immediately once the new model is introduced.",
    }
    fallback = "Second-pass note:\n\nClarify the practical takeaway more directly."
    for item in units:
        label = str(item.get("label") or "")
        text = str(item.get("text") or "")
        addition = additions.get(label, fallback)
        deep_units.append({"label": label, "text": f"{text}\n\n{addition}"})
    return deep_units, "\n\n".join(unit["text"] for unit in deep_units)


def _build_writing_expand_payload(*, requirement: str, deep: bool = False) -> tuple[dict[str, Any], int]:
    scaffold_payload, exit_code = _build_writing_scaffold_payload(requirement=requirement)
    if scaffold_payload.get("status") != "ok":
        payload = {
            **scaffold_payload,
            "entrypoint": "writing-expand",
            "expand_mode": "unavailable",
            "expand_depth": "none",
            "expanded_units": [],
            "expanded_unit_count": 0,
            "expanded_text": "",
        }
        return payload, exit_code

    scaffold = scaffold_payload.get("scaffold") or {}
    intent = scaffold_payload.get("writing_intent") or {}
    profile = str(scaffold_payload.get("expected_profile") or "")
    variant_seed = _writing_expand_variant_seed(requirement, profile)
    if profile == "copy_min":
        expand_variant, expanded_units, expanded_text = _copy_expand(scaffold, intent, variant_seed=variant_seed)
        if deep:
            expanded_units, expanded_text = _deepen_copy_units(expanded_units)
    elif profile == "story_min":
        expand_variant, expanded_units, expanded_text = _story_expand(scaffold, intent, variant_seed=variant_seed)
        if deep:
            expanded_units, expanded_text = _deepen_story_units(expanded_units)
    else:
        expand_variant, expanded_units, expanded_text = _book_expand(scaffold, intent, variant_seed=variant_seed)
        if deep:
            expanded_units, expanded_text = _deepen_book_units(expanded_units)

    payload = {
        **scaffold_payload,
        "entrypoint": "writing-expand",
        "expand_mode": "second_draft_pass" if deep else "first_draft_pass",
        "expand_depth": "deep" if deep else "base",
        "expand_variant": expand_variant,
        "expanded_units": expanded_units,
        "expanded_unit_count": len(expanded_units),
        "expanded_text": expanded_text,
        "next_steps": [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing brief {shlex.quote(requirement)} --emit-prompt",
            "review the expanded units and decide which one deserves a line-level rewrite next",
            "use the expanded_text as a draft layer, not as a finished final manuscript",
        ],
    }
    return payload, exit_code


def _draft_char_metrics(text: str) -> tuple[int, int]:
    char_count = len(text.strip())
    paragraph_count = len([item for item in re.split(r"\n\s*\n", text.strip()) if item.strip()])
    return char_count, paragraph_count


def _contains_cta_language(text_lower: str) -> bool:
    terms = [
        "book a demo",
        "request pricing",
        "start the conversation",
        "contact sales",
        "talk to sales",
        "get started",
        "sign up",
        "立即",
        "预约",
        "申请",
        "联系",
        "咨询",
        "购买",
        "开始使用",
        "cta",
    ]
    return any(term in text_lower for term in terms)


def _build_copy_review(requirement: str, draft_text: str, scaffold: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    text_lower = draft_text.lower()
    strengths: list[str] = []
    weak_spots: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 72

    if _contains_cta_language(text_lower):
        strengths.append("The draft already contains a recognizable CTA or conversion prompt.")
        score += 10
    else:
        drift_findings.append("The draft still lacks a clear CTA, so the copy lane is not yet landing on an obvious next action.")
        revision_targets.append("Add one explicit CTA block that tells the reader what to do next and why now.")
        score -= 14

    if any(term in text_lower for term in ["outcome", "result", "benefit", "faster", "reduce", "save", "increase", "增长", "降低", "提升", "节省"]):
        strengths.append("The message starts to translate the offer into an outcome rather than only describing features.")
        score += 8
    else:
        weak_spots.append("The draft describes the offer, but the buyer outcome is still too soft or too abstract.")
        revision_targets.append("Name one concrete buyer outcome in the headline or proof block.")
        score -= 10

    if len(draft_text.strip()) > 1400:
        weak_spots.append("The copy is drifting toward a longer article shape instead of a compact message hierarchy.")
        revision_targets.append("Compress the draft into hero, pain, solution, proof, and CTA blocks before expanding again.")
        score -= 8
    else:
        strengths.append("The draft length still fits a landing-style message hierarchy.")
        score += 4

    audience = str(intent.get("audience") or "").strip()
    if audience and audience.lower() in text_lower:
        strengths.append("The intended audience appears directly in the draft, which helps keep the positioning specific.")
        score += 4

    next_pass_prompt = (
        f"Revise this copy draft for the requirement '{requirement}'. "
        "Keep the structure recognizable as hero, pain, solution, proof, and CTA. "
        "Sharpen the buyer outcome, reduce descriptive filler, and make the CTA harder to miss. "
        f"Scaffold anchor: {json.dumps(scaffold, ensure_ascii=False)}"
    )
    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "weak_spots": weak_spots,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
        "next_pass_prompt": next_pass_prompt,
    }


def _build_story_review(requirement: str, draft_text: str, scaffold: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    text_lower = draft_text.lower()
    strengths: list[str] = []
    weak_spots: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 70

    if any(term in text_lower for term in ["conflict", "cost", "danger", "loss", "risk", "threat", "代价", "危险", "冲突", "失去"]):
        strengths.append("The draft already carries visible conflict or consequence, which fits the story scaffold well.")
        score += 10
    else:
        drift_findings.append("The draft feels atmospheric, but the conflict cost is still too hidden.")
        revision_targets.append("Add one explicit consequence, threat, or loss condition in the opening movement.")
        score -= 14

    if any(term in text_lower for term in ["chapter two", "scene", "choice", "decision", "chapter", "场景", "章节", "选择"]):
        strengths.append("The draft still points forward into scene or chapter progression rather than stalling inside one static moment.")
        score += 8
    else:
        weak_spots.append("The prose is not yet clearly pulling the reader toward the next chapter or scene beat.")
        revision_targets.append("End the passage with a decision, reversal, or motion into the next chapter beat.")
        score -= 8

    if any(term in text_lower for term in ["smell", "sound", "touch", "light", "cold", "heat", "breath", "声音", "气味", "光", "冷", "热"]):
        strengths.append("There is at least one sensory anchor, which helps the story draft feel embodied rather than purely conceptual.")
        score += 5
    else:
        weak_spots.append("The draft could use one sensory anchor so the scene feels lived-in rather than summarized.")
        revision_targets.append("Insert one sensory detail tied to the protagonist's immediate perception.")
        score -= 6

    constraints = intent.get("narrative_constraints") or []
    if constraints:
        strengths.append("The draft can still be revised against explicit narrative constraints, which keeps later passes easier to control.")

    next_pass_prompt = (
        f"Revise this story draft for the requirement '{requirement}'. "
        "Keep the scaffold intact: visible conflict, chapter motion, and protagonist pressure first. "
        "Make the consequence sharper, add one sensory detail, and end with a harder forward pull into the next beat. "
        f"Scaffold anchor: {json.dumps(scaffold, ensure_ascii=False)}"
    )
    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "weak_spots": weak_spots,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
        "next_pass_prompt": next_pass_prompt,
    }


def _build_book_review(requirement: str, draft_text: str, scaffold: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    text_lower = draft_text.lower()
    strengths: list[str] = []
    weak_spots: list[str] = []
    drift_findings: list[str] = []
    revision_targets: list[str] = []
    score = 71

    if any(term in text_lower for term in ["reader", "you", "your", "读者", "你", "你的"]):
        strengths.append("The draft already speaks to the reader directly, which fits the nonfiction blueprint lane.")
        score += 8
    else:
        weak_spots.append("The draft still sounds abstract and could address the reader more directly.")
        revision_targets.append("Rewrite at least one paragraph so the reader can see what changes for them.")
        score -= 8

    if any(term in text_lower for term in ["framework", "step", "system", "sequence", "example", "practice", "方法", "步骤", "系统", "案例", "实践"]):
        strengths.append("The draft contains practical or structural language, which supports the book blueprint surface.")
        score += 10
    else:
        drift_findings.append("The draft is still too conceptual and is not yet carrying enough practical structure.")
        revision_targets.append("Add one named framework, step sequence, or concrete example.")
        score -= 12

    if len(draft_text.strip()) < 260:
        weak_spots.append("The draft is still thin for a nonfiction chapter pass and needs more explanation depth.")
        revision_targets.append("Extend the chapter argument with one example and one practical takeaway.")
        score -= 10
    else:
        strengths.append("The passage has enough volume to review as a real chapter-direction draft.")
        score += 4

    next_pass_prompt = (
        f"Revise this nonfiction draft for the requirement '{requirement}'. "
        "Keep it aligned to the chapter blueprint, speak to the reader directly, and make the practical sequence more explicit. "
        "Prefer one framework, one example, and one actionable takeaway over abstract positioning language. "
        f"Scaffold anchor: {json.dumps(scaffold, ensure_ascii=False)}"
    )
    return {
        "score": max(0, min(100, score)),
        "strengths": strengths,
        "weak_spots": weak_spots,
        "drift_findings": drift_findings,
        "revision_targets": revision_targets,
        "next_pass_prompt": next_pass_prompt,
    }


def _alignment_band(score: int) -> str:
    if score >= 82:
        return "strong"
    if score >= 64:
        return "workable"
    return "drifting"


def _build_writing_review_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"writing_pack: {payload.get('writing_pack', '')}",
        f"expected_profile: {payload.get('expected_profile', '')}",
        f"review_mode: {payload.get('review_mode', '')}",
        f"alignment_score: {payload.get('alignment_score', 0)}",
        f"alignment_band: {payload.get('alignment_band', '')}",
        f"draft_char_count: {payload.get('draft_char_count', 0)}",
        f"draft_paragraph_count: {payload.get('draft_paragraph_count', 0)}",
        f"strength_count: {len(payload.get('strengths') or [])}",
        f"weak_spot_count: {len(payload.get('weak_spots') or [])}",
        f"drift_count: {len(payload.get('drift_findings') or [])}",
        f"revision_target_count: {len(payload.get('revision_targets') or [])}",
    ]
    if payload.get("revision_targets"):
        lines.append(f"first_revision_target: {(payload.get('revision_targets') or [''])[0]}")
    elif payload.get("strengths"):
        lines.append(f"first_strength: {(payload.get('strengths') or [''])[0]}")
    return "\n".join(lines)


def _build_writing_apply_check_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"writing_pack: {payload.get('writing_pack', '')}",
        f"expected_profile: {payload.get('expected_profile', '')}",
        f"apply_check_mode: {payload.get('apply_check_mode', '')}",
        f"apply_check_passed: {payload.get('apply_check_passed', False)}",
        f"alignment_score: {payload.get('alignment_score', 0)}",
        f"alignment_band: {payload.get('alignment_band', '')}",
        f"draft_char_count: {payload.get('draft_char_count', 0)}",
        f"draft_paragraph_count: {payload.get('draft_paragraph_count', 0)}",
        f"drift_count: {len(payload.get('drift_findings') or [])}",
        f"revision_target_count: {len(payload.get('revision_targets') or [])}",
    ]
    if payload.get("revision_targets"):
        lines.append(f"first_revision_target: {(payload.get('revision_targets') or [''])[0]}")
    elif payload.get("drift_findings"):
        lines.append(f"first_drift_finding: {(payload.get('drift_findings') or [''])[0]}")
    return "\n".join(lines)


def _build_writing_review_payload(*, requirement: str, draft_text: str) -> tuple[dict[str, Any], int]:
    scaffold_payload, exit_code = _build_writing_scaffold_payload(requirement=requirement)
    if scaffold_payload.get("status") != "ok":
        char_count, paragraph_count = _draft_char_metrics(draft_text)
        payload = {
            **scaffold_payload,
            "entrypoint": "writing-review",
            "review_mode": "unavailable",
            "draft_char_count": char_count,
            "draft_paragraph_count": paragraph_count,
            "alignment_score": 0,
            "alignment_band": "unavailable",
            "strengths": [],
            "weak_spots": [],
            "drift_findings": [],
            "revision_targets": [],
            "next_pass_prompt": "",
        }
        payload["summary_text"] = _build_writing_review_summary_text(payload)
        return payload, exit_code

    scaffold = scaffold_payload.get("scaffold") or {}
    intent = scaffold_payload.get("writing_intent") or {}
    profile = str(scaffold_payload.get("expected_profile") or "")
    if profile == "copy_min":
        review = _build_copy_review(requirement, draft_text, scaffold, intent)
    elif profile == "story_min":
        review = _build_story_review(requirement, draft_text, scaffold, intent)
    else:
        review = _build_book_review(requirement, draft_text, scaffold, intent)

    char_count, paragraph_count = _draft_char_metrics(draft_text)
    alignment_score = int(review["score"])
    payload = {
        **scaffold_payload,
        "entrypoint": "writing-review",
        "review_mode": "scaffold_alignment_review",
        "draft_text": draft_text,
        "draft_char_count": char_count,
        "draft_paragraph_count": paragraph_count,
        "alignment_score": alignment_score,
        "alignment_band": _alignment_band(alignment_score),
        "strengths": review["strengths"],
        "weak_spots": review["weak_spots"],
        "drift_findings": review["drift_findings"],
        "revision_targets": review["revision_targets"],
        "next_pass_prompt": review["next_pass_prompt"],
        "next_steps": [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing brief {shlex.quote(requirement)} --emit-prompt",
            "rewrite one weak spot at a time instead of replacing the whole draft at once",
            "use the next_pass_prompt as the prompt for the next editorial pass",
        ],
    }
    payload["summary_text"] = _build_writing_review_summary_text(payload)
    return payload, EXIT_OK


def _build_writing_apply_check_payload(*, requirement: str, draft_text: str) -> tuple[dict[str, Any], int]:
    review_payload, review_exit = _build_writing_review_payload(requirement=requirement, draft_text=draft_text)
    if review_payload.get("status") != "ok":
        payload = {
            **review_payload,
            "entrypoint": "writing-apply-check",
            "apply_check_mode": "unavailable",
            "apply_check_passed": False,
            "message": "Writing apply-check could not validate the draft because the requirement is outside the current scaffold-ready writing surface.",
        }
        payload["summary_text"] = _build_writing_apply_check_summary_text(payload)
        return payload, max(review_exit, EXIT_VALIDATION)

    drift_findings = list(review_payload.get("drift_findings") or [])
    alignment_band = str(review_payload.get("alignment_band") or "")
    apply_check_passed = bool(alignment_band in {"workable", "strong"} and not drift_findings)
    status = "ok" if apply_check_passed else "warning"
    message = (
        "The draft still looks aligned to the current scaffold boundary."
        if apply_check_passed
        else "The draft drifted far enough from the scaffold that it should be revised before handoff or bundling."
    )
    payload = {
        **review_payload,
        "status": status,
        "entrypoint": "writing-apply-check",
        "apply_check_mode": "external_draft_alignment_gate",
        "apply_check_passed": apply_check_passed,
        "message": message,
        "source_commands": {
            "writing_check": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check {shlex.quote(requirement)} --json",
            "writing_scaffold": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing scaffold {shlex.quote(requirement)} --json",
            "writing_review": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing review {shlex.quote(requirement)} --text-file /absolute/path/to/draft.txt --json",
            "writing_apply_check": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing apply-check {shlex.quote(requirement)} --text-file /absolute/path/to/draft.txt --json",
        },
        "next_steps": (
            [
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing bundle {shlex.quote(requirement)} --deep --json"
            ]
            if apply_check_passed
            else [
                "revise the drift findings before reusing this draft",
                "use the next_pass_prompt for the next repair pass",
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing apply-check {shlex.quote(requirement)} --text-file /absolute/path/to/revised-draft.txt --json",
            ]
        ),
    }
    payload["summary_text"] = _build_writing_apply_check_summary_text(payload)
    return payload, (EXIT_OK if apply_check_passed else EXIT_VALIDATION)


def _build_writing_bundle_summary_text(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status', '')}",
        f"writing_pack: {payload.get('writing_pack', '')}",
        f"expected_profile: {payload.get('expected_profile', '')}",
        f"manifest_version: {payload.get('manifest_version', '')}",
        f"bundle_created_at: {payload.get('bundle_created_at', '')}",
        f"bundle_root: {payload.get('bundle_root', '')}",
        f"deep_enabled: {payload.get('deep_enabled', False)}",
        f"zip_enabled: {payload.get('zip_enabled', False)}",
        f"review_source: {payload.get('review_source', '')}",
        f"file_count: {payload.get('file_count', 0)}",
    ]
    if payload.get("archive_path"):
        lines.append(f"archive_path: {payload.get('archive_path', '')}")
    if "copied_archive_path_to_clipboard" in payload:
        lines.append(f"copied_archive_path_to_clipboard: {payload.get('copied_archive_path_to_clipboard', False)}")
    if payload.get("copy_archive_path_error"):
        lines.append(f"copy_archive_path_error: {payload.get('copy_archive_path_error', '')}")
    files = payload.get("files") or {}
    if files:
        lines.append(f"brief_prompt_txt: {files.get('brief_prompt_txt', '')}")
        lines.append(f"expand_txt: {files.get('expand_txt', '')}")
        lines.append(f"review_summary_txt: {files.get('review_summary_txt', '')}")
    return "\n".join(lines)


def _build_writing_bundle_readme_text(
    *,
    requirement: str,
    writing_pack: str,
    expected_profile: str,
    manifest_version: str,
    bundle_created_at: str,
    deep_enabled: bool,
    zip_enabled: bool,
    review_source: str,
    files: dict[str, Path],
) -> str:
    return "\n".join(
        [
            "AIL Builder Writing Bundle",
            "",
            f"requirement: {requirement}",
            f"writing_pack: {writing_pack}",
            f"expected_profile: {expected_profile}",
            f"manifest_version: {manifest_version}",
            f"bundle_created_at: {bundle_created_at}",
            f"deep_enabled: {deep_enabled}",
            f"zip_enabled: {zip_enabled}",
            f"review_source: {review_source}",
            "",
            "Recommended reading order:",
            f"1. brief_prompt.txt -> {files['brief_prompt_txt']}",
            f"2. expand.txt -> {files['expand_txt']}",
            f"3. review_summary.txt -> {files['review_summary_txt']}",
            "",
            "Bundle contents:",
            f"- check.json: pack classification and boundary contract",
            f"- scaffold.json: low-token structural scaffold",
            f"- brief.json: structured brief payload with handoff metadata",
            f"- brief_prompt.txt: prompt-ready handoff text for an external model",
            f"- expand.json: structured first-draft or second-draft payload",
            f"- expand.txt: prose draft text",
            f"- review.json: structured review payload",
            f"- review_summary.txt: compact editorial review summary",
            f"- bundle_manifest.json: top-level bundle manifest",
            f"- README.txt: this file",
            "",
            "Working guidance:",
            "- Use brief_prompt.txt when handing the task to another model.",
            "- Use expand.txt as the current prose layer, not as a final manuscript.",
            "- Use review_summary.txt to decide the next targeted revision pass.",
        ]
    ) + "\n"


def _build_writing_bundle_payload(
    *,
    requirement: str,
    draft_text: str,
    deep: bool,
    output_dir: str | None,
    make_zip: bool,
    copy_archive_path: bool,
    copy_summary: bool,
) -> tuple[dict[str, Any], int]:
    check_payload, check_exit = _build_writing_check_payload(requirement=requirement)
    scaffold_payload, scaffold_exit = _build_writing_scaffold_payload(requirement=requirement)
    brief_payload, brief_exit = _build_writing_brief_payload(requirement=requirement)
    expand_payload, expand_exit = _build_writing_expand_payload(requirement=requirement, deep=deep)
    review_input = draft_text.strip() if draft_text.strip() else str(expand_payload.get("expanded_text") or "")
    review_source = "provided_draft" if draft_text.strip() else "expanded_text"
    review_payload, review_exit = _build_writing_review_payload(requirement=requirement, draft_text=review_input)
    manifest_version = "writing_bundle.v1"
    bundle_created_at = datetime.now().astimezone().isoformat(timespec="seconds")

    bundle_root = _resolve_writing_bundle_dir(requirement, output_dir)
    bundle_root.mkdir(parents=True, exist_ok=True)

    files = {
        "check_json": bundle_root / "check.json",
        "scaffold_json": bundle_root / "scaffold.json",
        "brief_json": bundle_root / "brief.json",
        "brief_prompt_txt": bundle_root / "brief_prompt.txt",
        "expand_json": bundle_root / "expand.json",
        "expand_txt": bundle_root / "expand.txt",
        "review_json": bundle_root / "review.json",
        "review_summary_txt": bundle_root / "review_summary.txt",
        "bundle_manifest_json": bundle_root / "bundle_manifest.json",
        "readme_txt": bundle_root / "README.txt",
    }

    _write_cli_output_file(files["check_json"], check_payload, as_json=True)
    _write_cli_output_file(files["scaffold_json"], scaffold_payload, as_json=True)
    _write_cli_output_file(files["brief_json"], brief_payload, as_json=True)
    _write_cli_output_file(files["brief_prompt_txt"], str(brief_payload.get("model_prompt", "")))
    _write_cli_output_file(files["expand_json"], expand_payload, as_json=True)
    _write_cli_output_file(files["expand_txt"], str(expand_payload.get("expanded_text", "")))
    _write_cli_output_file(files["review_json"], review_payload, as_json=True)
    _write_cli_output_file(files["review_summary_txt"], str(review_payload.get("summary_text", "")))
    _write_cli_output_file(
        files["readme_txt"],
        _build_writing_bundle_readme_text(
            requirement=requirement,
            writing_pack=str(check_payload.get("writing_pack", "")),
            expected_profile=str(check_payload.get("expected_profile", "")),
            manifest_version=manifest_version,
            bundle_created_at=bundle_created_at,
            deep_enabled=deep,
            zip_enabled=make_zip,
            review_source=review_source,
            files=files,
        ),
    )

    payload = {
        "status": "ok" if check_payload.get("status") == "ok" else check_payload.get("status", "error"),
        "entrypoint": "writing-bundle",
        "requirement": requirement,
        "writing_pack": check_payload.get("writing_pack", ""),
        "expected_profile": check_payload.get("expected_profile", ""),
        "manifest_version": manifest_version,
        "bundle_created_at": bundle_created_at,
        "bundle_root": str(bundle_root),
        "deep_enabled": deep,
        "zip_enabled": make_zip,
        "review_source": review_source,
        "review_input_char_count": len(review_input.strip()),
        "file_count": len(files),
        "files": {label: str(path) for label, path in files.items()},
        "check": check_payload,
        "scaffold": scaffold_payload,
        "brief": brief_payload,
        "expand": expand_payload,
        "review": review_payload,
        "next_steps": [
            f"open {files['brief_prompt_txt']}",
            f"open {files['expand_txt']}",
            f"open {files['review_summary_txt']}",
        ],
    }
    if make_zip:
        archive_base = str(bundle_root)
        archive_path = shutil.make_archive(archive_base, "zip", root_dir=bundle_root.parent, base_dir=bundle_root.name)
        payload["archive_path"] = str(Path(archive_path).resolve())
        payload["next_steps"].insert(0, f"share {payload['archive_path']}")
    if copy_archive_path:
        archive_path_value = str(payload.get("archive_path") or "").strip()
        if archive_path_value:
            copied_ok, copied_error = _copy_text_to_clipboard(archive_path_value)
            payload["copied_archive_path"] = archive_path_value
            payload["copied_archive_path_to_clipboard"] = copied_ok
            if copied_error:
                payload["copy_archive_path_error"] = copied_error
            elif copied_ok:
                payload["next_steps"].insert(0, "paste the copied bundle archive path into your handoff or chat tool")
        else:
            payload["copied_archive_path"] = ""
            payload["copied_archive_path_to_clipboard"] = False
            payload["copy_archive_path_error"] = "No bundle archive path was available to copy. Re-run with --zip first."
    payload["summary_text"] = _build_writing_bundle_summary_text(payload)
    if copy_summary:
        summary_text = str(payload.get("summary_text", ""))
        copied_ok, copied_error = _copy_text_to_clipboard(summary_text)
        payload["copied_summary"] = summary_text
        payload["copied_summary_to_clipboard"] = copied_ok
        if copied_error:
            payload["copy_summary_error"] = copied_error
        elif copied_ok:
            payload["next_steps"].insert(0, "paste the copied bundle summary into your handoff note or test report")
    _write_cli_output_file(files["bundle_manifest_json"], payload, as_json=True)
    exit_code = max(check_exit, scaffold_exit, brief_exit, expand_exit, review_exit)
    return payload, exit_code


def _build_writing_packs_payload() -> tuple[dict[str, Any], int]:
    packs = []
    for pack_id, meta in _writing_pack_metadata().items():
        if pack_id == "out_of_scope":
            continue
        packs.append(
            {
                "pack_id": pack_id,
                **meta,
            }
        )
    payload = {
        "status": "ok",
        "entrypoint": "writing-packs",
        "available_pack_count": len(packs),
        "packs": packs,
        "public_surface_note": "Current writing support is architecture-first and low-token by design: copy scaffolds, story scaffolds, and book blueprints come first; final full prose remains an iterative layer.",
        "next_steps": [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check \"写一个企业产品宣传文案\" --json",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing intent --json",
        ],
    }
    return payload, EXIT_OK


def _build_writing_intent_payload(
    *,
    audience: str | None,
    format_mode: str | None,
    genre: str | None,
    style_direction: str | None,
    localization_mode: str | None,
    target_length: str | None,
    notes: str | None,
    style_keywords: list[str] | None,
    tone_keywords: list[str] | None,
    narrative_constraints: list[str] | None,
    reset: bool,
) -> tuple[dict[str, Any], int]:
    existing = _load_writing_intent()
    writing_intent = _default_writing_intent() if reset else dict(existing)
    write_requested = reset or any(
        value is not None
        for value in (
            audience,
            format_mode,
            genre,
            style_direction,
            localization_mode,
            target_length,
            notes,
            style_keywords,
            tone_keywords,
            narrative_constraints,
        )
    )

    if audience is not None:
        writing_intent["audience"] = str(audience).strip()
    if format_mode is not None:
        writing_intent["format_mode"] = str(format_mode).strip()
    if genre is not None:
        writing_intent["genre"] = str(genre).strip()
    if style_direction is not None:
        writing_intent["style_direction"] = str(style_direction).strip()
    if localization_mode is not None:
        writing_intent["localization_mode"] = str(localization_mode).strip()
    if target_length is not None:
        writing_intent["target_length"] = str(target_length).strip()
    if notes is not None:
        writing_intent["notes"] = str(notes).strip()
    if style_keywords is not None:
        writing_intent["style_keywords"] = _normalize_string_list(style_keywords)
    if tone_keywords is not None:
        writing_intent["tone_keywords"] = _normalize_string_list(tone_keywords)
    if narrative_constraints is not None:
        writing_intent["narrative_constraints"] = _normalize_string_list(narrative_constraints)

    writing_intent_path = _writing_intent_path()
    action = "read"
    message = "Loaded the current writing intent."
    if reset:
        _save_writing_intent(writing_intent)
        action = "reset"
        message = "Reset the writing intent back to an empty baseline."
    elif write_requested:
        _save_writing_intent(writing_intent)
        action = "write"
        message = "Saved the current writing intent."

    next_steps = [
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing check \"<writing requirement>\" --json",
        f"inspect {writing_intent_path}",
    ]
    if action != "read":
        next_steps.append(f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli writing packs --json")

    payload = {
        "status": "ok",
        "entrypoint": "writing-intent",
        "repo_root": str(REPO_ROOT),
        "writing_intent_path": str(writing_intent_path),
        "writing_intent_exists": writing_intent_path.exists(),
        "action": action,
        "message": message,
        "writing_intent": writing_intent,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _website_pack_metadata() -> dict[str, dict[str, str]]:
    return {
        "personal_independent": {
            "pack": "Personal Independent Site Pack",
            "support_level": "Supported",
            "expected_profile": "landing",
            "safe_positioning": "Position as a personal independent site, portfolio-like site, or creator/freelancer website.",
        },
        "company_product": {
            "pack": "Company / Product Website Pack",
            "support_level": "Supported",
            "expected_profile": "landing",
            "safe_positioning": "Position as a company introduction site, product marketing website, or brand website.",
        },
        "ecommerce_storefront": {
            "pack": "Ecommerce Independent Storefront Pack",
            "support_level": "Supported",
            "expected_profile": "ecom_min",
            "safe_positioning": "Position as a minimal ecommerce storefront, not a full ecommerce platform.",
        },
        "after_sales": {
            "pack": "After-Sales Service Website Pack",
            "support_level": "Supported",
            "expected_profile": "after_sales",
            "safe_positioning": "Position as an after-sales service site, not a support console or internal operations tool.",
        },
        "blog_style": {
            "pack": "Personal Blog-Style Site Pack",
            "support_level": "Partial",
            "expected_profile": "landing",
            "safe_positioning": "Position as a blog-style personal site only; do not promise CMS, comments, or publishing backend behavior.",
        },
        "out_of_scope": {
            "pack": "Out Of Scope",
            "support_level": "Out of Scope",
            "expected_profile": "",
            "safe_positioning": "Narrow the request back to a website-oriented surface before treating it as current delivery scope.",
        },
    }


def _public_static_website_pack_ids() -> set[str]:
    return {"company_product", "personal_independent", "blog_style_partial"}


def _public_static_website_pack_names() -> set[str]:
    return {
        "Company / Product Website Pack",
        "Personal Independent Site Pack",
        "Personal Blog-Style Site Pack",
    }


def _website_visible_pack_ids(include_experimental_dynamic: bool) -> set[str]:
    visible = set(_public_static_website_pack_ids())
    if include_experimental_dynamic:
        visible.update({"ecom_storefront", "after_sales"})
    return visible


def _website_visible_pack_names(include_experimental_dynamic: bool) -> set[str]:
    visible = set(_public_static_website_pack_names())
    if include_experimental_dynamic:
        visible.update({
            "Ecommerce Independent Storefront Pack",
            "After-Sales Service Website Pack",
        })
    return visible


def _filter_website_assets_summary(summary: dict[str, Any], *, include_experimental_dynamic: bool) -> dict[str, Any]:
    if not summary:
        return {}
    filtered_assets = [
        item for item in list(summary.get("assets") or [])
        if str(item.get("pack_id") or "") in _website_visible_pack_ids(include_experimental_dynamic)
    ]
    supported_count = sum(1 for item in filtered_assets if str(item.get("support_level") or "") == "Supported")
    partial_count = sum(1 for item in filtered_assets if str(item.get("support_level") or "") == "Partial")
    delivery_ready_supported_count = sum(
        1
        for item in filtered_assets
        if str(item.get("support_level") or "") == "Supported" and bool(item.get("delivery_ready"))
    )
    delivery_ready_partial_count = sum(
        1
        for item in filtered_assets
        if str(item.get("support_level") or "") == "Partial" and bool(item.get("delivery_ready"))
    )
    return {
        **summary,
        "supported_count": supported_count,
        "partial_count": partial_count,
        "delivery_ready_supported_count": delivery_ready_supported_count,
        "delivery_ready_partial_count": delivery_ready_partial_count,
        "assets": filtered_assets,
        "public_surface_note": (
            "Experimental ecommerce and after-sales packs are included in this view."
            if include_experimental_dynamic else
            "Only static presentation-style website packs are exposed on the current public surface. "
            "Legacy ecommerce and after-sales packs are not part of the active public website scope."
        ),
        "experimental_dynamic_enabled": include_experimental_dynamic,
    }


def _filter_website_validation_payload(payload: dict[str, Any], *, include_experimental_dynamic: bool) -> dict[str, Any]:
    if not payload:
        return {}
    filtered_cases = [
        item for item in list(payload.get("cases") or [])
        if str(item.get("pack") or "") in _website_visible_pack_names(include_experimental_dynamic)
    ]
    summary = dict(payload.get("summary") or {})
    supported_ready_count = sum(
        1
        for item in filtered_cases
        if str(item.get("support_level") or "") == "Supported"
        and str(((item.get("validation") or {}).get("delivery_ready") or "")).lower() in {"true", "yes", "ok"}
    )
    partial_ready_count = sum(
        1
        for item in filtered_cases
        if str(item.get("support_level") or "") == "Partial"
        and str(((item.get("validation") or {}).get("delivery_ready") or "")).lower() in {"true", "yes", "ok"}
    )
    summary["cases_total"] = len(filtered_cases)
    summary["delivery_ready_count"] = supported_ready_count + partial_ready_count
    summary["supported_ready_count"] = supported_ready_count
    summary["partial_ready_count"] = partial_ready_count
    return {
        **payload,
        "summary": summary,
        "cases": filtered_cases,
    }


def _filter_website_demo_payload(payload: dict[str, Any], *, include_experimental_dynamic: bool) -> dict[str, Any]:
    if not payload:
        return {}
    filtered_cases = [
        item for item in list(payload.get("cases") or [])
        if str(item.get("pack") or "") in _website_visible_pack_names(include_experimental_dynamic)
    ]
    summary = dict(payload.get("summary") or {})
    supported_demo_ready_count = sum(
        1
        for item in filtered_cases
        if str(item.get("support_level") or "") == "Supported"
        and str(((item.get("validation") or {}).get("delivery_ready") or "")).lower() in {"true", "yes", "ok"}
    )
    partial_demo_ready_count = sum(
        1
        for item in filtered_cases
        if str(item.get("support_level") or "") == "Partial"
        and str(((item.get("validation") or {}).get("delivery_ready") or "")).lower() in {"true", "yes", "ok"}
    )
    summary["case_count"] = len(filtered_cases)
    summary["demo_ready_count"] = supported_demo_ready_count + partial_demo_ready_count
    summary["supported_demo_ready_count"] = supported_demo_ready_count
    summary["partial_demo_ready_count"] = partial_demo_ready_count
    return {
        **payload,
        "summary": summary,
        "cases": filtered_cases,
    }


def _analyze_website_requirement(requirement: str, *, include_experimental_dynamic: bool = False) -> dict[str, Any]:
    req = requirement.strip()
    req_lower = req.lower()
    matched_signals: list[str] = []
    boundary_findings: list[str] = []

    out_of_scope_terms = {
        "登录": "request includes login behavior",
        "login": "request includes login behavior",
        "用户中心": "request includes user-center behavior",
        "后台": "request includes backend or admin behavior",
        "admin": "request includes backend or admin behavior",
        "dashboard": "request includes dashboard behavior",
        "仪表盘": "request includes dashboard behavior",
        "cms": "request includes CMS behavior",
        "内容管理": "request includes CMS behavior",
        "发布系统": "request includes publishing-system behavior",
        "评论": "request includes comments behavior",
        "comments": "request includes comments behavior",
        "商家后台": "request includes merchant backend behavior",
        "订单管理": "request includes order-management behavior",
        "库存": "request includes inventory-management behavior",
        "crm": "request includes CRM behavior",
        "审批": "request includes approval-workflow behavior",
        "内部门户": "request includes internal-portal behavior",
        "控制台": "request includes console behavior",
        "api 控制台": "request includes API-console behavior",
        "平台": "request uses platform wording that exceeds the current website product surface",
        "平台化": "request uses platform wording that exceeds the current website product surface",
        "应用": "request uses app wording that exceeds the current website product surface",
        "app": "request uses app wording that exceeds the current website product surface",
        "dashboard product": "request uses dashboard-product wording that exceeds the current website product surface",
    }
    for needle, finding in out_of_scope_terms.items():
        if needle in req_lower:
            boundary_findings.append(finding)
            matched_signals.append(needle)

    meta = _website_pack_metadata()
    if boundary_findings:
        return {
            **meta["out_of_scope"],
            "classification_key": "out_of_scope",
            "website_reason": "Requirement crosses the current website boundary into app, platform, CMS, or back-office behavior.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    def _contains_any(terms: list[str]) -> bool:
        return any(term in req_lower for term in terms)

    if _contains_any(["博客", "blog", "文章", "article"]) and not _contains_any(["cms", "评论", "comments", "发布系统", "内容管理"]):
        matched_signals.extend([term for term in ["博客", "blog", "文章", "article"] if term in req_lower])
        return {
            **meta["blog_style"],
            "classification_key": "blog_style",
            "website_reason": "Requirement stays website-oriented, but blog-like asks remain partial because CMS and publishing-system behavior are still out of scope.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    if _contains_any(["售后", "退款", "换货", "投诉", "客服"]):
        matched_signals.extend([term for term in ["售后", "退款", "换货", "投诉", "客服"] if term in req_lower])
        if include_experimental_dynamic:
            return {
                **meta["after_sales"],
                "support_level": "Experimental",
                "classification_key": "after_sales",
                "website_reason": "Requirement maps to the experimental after-sales workflow lane.",
                "matched_signals": matched_signals,
                "boundary_findings": boundary_findings,
            }
        return {
            **meta["out_of_scope"],
            "classification_key": "out_of_scope",
            "website_reason": "Requirement asks for after-sales workflow behavior that exceeds the current public static website surface.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings + ["request includes after-sales workflow behavior outside the current static presentation scope"],
        }

    if _contains_any(["电商", "商城", "商品", "购物车", "结算", "店铺", "分类导航", "商品详情", "storefront", "shop"]):
        matched_signals.extend(
            [term for term in ["电商", "商城", "商品", "购物车", "结算", "店铺", "分类导航", "商品详情", "storefront", "shop"] if term in req_lower]
        )
        if include_experimental_dynamic:
            return {
                **meta["ecommerce_storefront"],
                "support_level": "Experimental",
                "classification_key": "ecommerce_storefront",
                "website_reason": "Requirement maps to the experimental ecommerce storefront lane.",
                "matched_signals": matched_signals,
                "boundary_findings": boundary_findings,
            }
        return {
            **meta["out_of_scope"],
            "classification_key": "out_of_scope",
            "website_reason": "Requirement asks for ecommerce behavior that exceeds the current public static website surface.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings + ["request includes ecommerce behavior outside the current static presentation scope"],
        }

    if _contains_any(["个人", "自由职业", "设计师", "作品集", "摄影师", "创作者", "个人独立站", "portfolio"]):
        matched_signals.extend(
            [term for term in ["个人", "自由职业", "设计师", "作品集", "摄影师", "创作者", "个人独立站", "portfolio"] if term in req_lower]
        )
        return {
            **meta["personal_independent"],
            "classification_key": "personal_independent",
            "website_reason": "Requirement maps cleanly to the current personal independent site surface.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    if _contains_any(["企业", "公司", "品牌", "官网", "产品", "功能介绍", "faq", "联系我们", "saas", "landing", "marketing", "website", "网站"]):
        matched_signals.extend(
            [term for term in ["企业", "公司", "品牌", "官网", "产品", "功能介绍", "faq", "联系我们", "saas", "landing", "marketing", "website", "网站"] if term in req_lower]
        )
        return {
            **meta["company_product"],
            "classification_key": "company_product",
            "website_reason": "Requirement maps cleanly to the current company and product website surface.",
            "matched_signals": matched_signals,
            "boundary_findings": boundary_findings,
        }

    return {
        **meta["out_of_scope"],
        "classification_key": "out_of_scope",
        "website_reason": "Requirement does not map clearly to the currently supported website packs.",
        "matched_signals": matched_signals,
        "boundary_findings": ["request does not clearly fit one supported website pack"],
    }


def _build_website_check_next_steps(
    *,
    support_level: str,
    delivery_decision: str,
    trial_project_path: str,
    trial_result: dict[str, Any] | None,
    expected_profile: str,
    base_url: str | None,
    include_experimental_dynamic: bool,
) -> list[str]:
    effective_base_url = _effective_base_url(base_url)
    if support_level == "Out of Scope":
        steps = [
            "narrow the requirement back to one website-oriented pack",
            "remove app, CMS, dashboard, or platform behavior from the request",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli website check \"<narrowed website requirement>\" --base-url {effective_base_url} --json",
        ]
        if not include_experimental_dynamic:
            steps.append(
                f"rerun with PYTHONPATH={REPO_ROOT_STR} python3 -m cli website check \"<dynamic requirement>\" --experimental-dynamic --base-url {effective_base_url} --json if you want the experimental ecommerce/after-sales lane"
            )
        return steps

    steps: list[str] = []
    if trial_project_path:
        steps.append(f"inspect {trial_project_path}")
        steps.append(
            f"run PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli project preview --base-url {effective_base_url} --json"
        )
        steps.append(
            f"run PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli project export-handoff --base-url {effective_base_url} --json"
        )
    if delivery_decision == "partial":
        steps.append("position the result as Partial and avoid CMS or full blog promises")
    elif delivery_decision == "experimental":
        steps.append("treat the result as experimental and do not promise stable dynamic behavior yet")
    elif delivery_decision == "supported":
        steps.append(f"position the result as Supported inside the `{expected_profile}` website surface")
    elif trial_result and trial_result.get("status") != "ok":
        steps.append("repair or narrow the requirement before calling the result deliverable")
    return steps


def _website_delivery_contract(
    classification_key: str,
    *,
    expected_profile: str,
) -> dict[str, Any]:
    if classification_key == "ecommerce_storefront":
        return {
            "surface": "experimental_dynamic_storefront",
            "supported_capabilities": [
                "catalog-style landing or shop entry pages",
                "product detail pages",
                "cart views",
                "checkout handoff pages",
                "category or search discovery routes when the generated profile includes them",
            ],
            "unsupported_capabilities": [
                "account login or registration",
                "real payment capture",
                "order management back-office",
                "inventory or merchant operations tooling",
                "database-backed commerce workflows",
            ],
            "operator_positioning": "Position this as an experimental storefront prototype, not as a production ecommerce stack.",
            "stability_note": "The ecommerce lane is still experimental. Treat route coverage and generated flow continuity as something to verify in each output.",
            "validation_focus": [
                "inspect the generated router before promising exact route coverage",
                "confirm product to cart to checkout continuity in the generated frontend",
                "avoid promising account, payment, or merchant-backend behavior",
            ],
            "expected_profile": expected_profile,
        }
    if classification_key == "after_sales":
        return {
            "surface": "experimental_after_sales_workflow",
            "supported_capabilities": [
                "refund request pages",
                "exchange request pages",
                "complaint or contact submission pages",
                "service-policy or support-entry presentation flows",
            ],
            "unsupported_capabilities": [
                "agent console workflows",
                "ticket routing backends",
                "internal approvals",
                "account login or case-management systems",
                "database-backed service operations",
            ],
            "operator_positioning": "Position this as an experimental after-sales website flow, not as a support platform or internal tool.",
            "stability_note": "The after-sales lane is still experimental. Generated workflow coverage should be verified per output before promising delivery behavior.",
            "validation_focus": [
                "inspect generated routes and forms before promising exact workflow coverage",
                "avoid promising internal operations or support-console behavior",
                "keep the requirement in a customer-facing website surface",
            ],
            "expected_profile": expected_profile,
        }
    if classification_key == "blog_style":
        return {
            "surface": "partial_blog_presentation",
            "supported_capabilities": [
                "blog-style landing or article presentation pages",
                "static sections for posts, writing themes, or archives",
            ],
            "unsupported_capabilities": [
                "CMS editing",
                "publishing backend behavior",
                "comments systems",
                "user accounts",
            ],
            "operator_positioning": "Position this as a presentation-oriented blog-style site only.",
            "stability_note": "Blog-like presentation is partial support. Treat anything requiring publishing operations as out of scope.",
            "validation_focus": [
                "avoid promising CMS or publishing workflows",
                "inspect generated routes if you need blog navigation beyond one main page",
            ],
            "expected_profile": expected_profile,
        }
    if classification_key in {"company_product", "personal_independent"}:
        return {
            "surface": "static_presentation_site",
            "supported_capabilities": [
                "landing-style homepage composition",
                "feature, pricing, FAQ, or about sections",
                "contact or CTA sections",
                "static brand or portfolio presentation",
            ],
            "unsupported_capabilities": [
                "login flows",
                "CMS behavior",
                "dashboard or admin behavior",
                "database-backed app workflows",
            ],
            "operator_positioning": "Position this as a static presentation website inside the current supported public surface.",
            "stability_note": "This is the strongest supported lane today, but most requests still realize as single-page section structures first.",
            "validation_focus": [
                "inspect the router before promising independent multi-page coverage",
                "keep the request in a presentation-oriented website surface",
            ],
            "expected_profile": expected_profile,
        }
    return {
        "surface": "out_of_scope",
        "supported_capabilities": [],
        "unsupported_capabilities": [],
        "operator_positioning": "Narrow the requirement back to a supported website surface before positioning it as deliverable.",
        "stability_note": "No delivery contract is available because the request is currently out of scope.",
        "validation_focus": [
            "remove app, CMS, dashboard, or back-office behavior from the request",
        ],
        "expected_profile": expected_profile,
    }


def _website_realization_expectation(classification_key: str, expected_profile: str) -> dict[str, str]:
    if classification_key in {"company_product", "personal_independent", "blog_style"}:
        return {
            "page_realization_mode": "single_page_sections_bias",
            "routing_expectation": "Requests for pages like features, pricing, about, or blog are currently often realized as sections on one main page rather than independent routes.",
            "route_expectation_detail": "Expect a single-page presentation structure first. Generated routes may stay minimal, such as `/` plus fallback routes like `/403`.",
        }
    if classification_key in {"ecommerce_storefront", "after_sales"}:
        return {
            "page_realization_mode": "profile_driven_routes",
            "routing_expectation": "This website pack can use dedicated route structures, but you should still inspect the generated router before promising exact page coverage.",
            "route_expectation_detail": f"Current expected profile is `{expected_profile}`.",
        }
    return {
        "page_realization_mode": "not_applicable",
        "routing_expectation": "No routing expectation is available because the requirement does not currently fit one supported website pack.",
        "route_expectation_detail": "Narrow the request to a supported website-oriented surface first.",
    }


def _build_website_check_payload(
    *,
    requirement: str,
    base_url: str | None,
    project_dir: str | None,
    keep_existing: bool,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    analysis = _analyze_website_requirement(
        requirement,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    delivery_contract = _website_delivery_contract(
        analysis["classification_key"],
        expected_profile=analysis["expected_profile"],
    )
    realization = _website_realization_expectation(
        analysis["classification_key"],
        analysis["expected_profile"],
    )
    support_level = analysis["support_level"]
    delivery_decision = (
        "out_of_scope" if support_level == "Out of Scope" else
        ("partial" if support_level == "Partial" else ("experimental" if support_level == "Experimental" else "supported"))
    )
    trial_result: dict[str, Any] | None = None
    trial_project_path = ""
    exit_code = EXIT_OK if support_level in {"Supported", "Partial", "Experimental"} else EXIT_VALIDATION
    status = (
        "experimental" if support_level == "Experimental" else
        ("ok" if support_level in {"Supported", "Partial"} else "out_of_scope")
    )

    if support_level in {"Supported", "Partial", "Experimental"}:
        root = Path(project_dir).resolve() if project_dir else Path(tempfile.mkdtemp(prefix="ail_website_check."))
        ctx = ProjectContext.discover(root, allow_uninitialized=True)
        if not keep_existing and ctx.ail_dir.exists():
            payload = {
                "status": "error",
                "entrypoint": "website-check",
                "requirement": requirement,
                "message": f"Refusing to reuse initialized project without --keep-existing: {ctx.root}",
            }
            return payload, EXIT_USAGE

        trial_result, trial_exit = _run_trial_flow(
            ctx,
            requirement=requirement,
            scenario="website_check",
            base_url=base_url,
        )
        trial_project_path = str(ctx.root)
        if trial_exit != EXIT_OK:
            status = trial_result.get("status", "validation_failed")
            exit_code = trial_exit
            delivery_decision = "validation_failed"

    payload = {
        "status": status,
        "entrypoint": "website-check",
        "requirement": requirement,
        "website_pack": analysis["pack"],
        "support_level": support_level,
        "expected_profile": analysis["expected_profile"],
        "delivery_decision": delivery_decision,
        "website_reason": analysis["website_reason"],
        "safe_positioning": analysis["safe_positioning"],
        "experimental_dynamic_enabled": include_experimental_dynamic,
        "delivery_contract": delivery_contract,
        "page_realization_mode": realization["page_realization_mode"],
        "routing_expectation": realization["routing_expectation"],
        "route_expectation_detail": realization["route_expectation_detail"],
        "matched_signals": analysis.get("matched_signals", []),
        "boundary_findings": analysis.get("boundary_findings", []),
        "trial_project_path": trial_project_path,
        "trial_result": trial_result,
    }
    payload["next_steps"] = _build_website_check_next_steps(
        support_level=support_level,
        delivery_decision=delivery_decision,
        trial_project_path=trial_project_path,
        trial_result=trial_result,
        expected_profile=analysis["expected_profile"],
        base_url=base_url,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    return payload, exit_code


def _build_website_assets_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    results_dir = REPO_ROOT / "testing/results"
    summary_path = results_dir / "website_delivery_assets_20260319.json"
    summary_md_path = results_dir / "website_delivery_assets_20260319.md"
    asset_dir = results_dir / "website_delivery_assets_20260319"

    summary = _filter_website_assets_summary(
        _load_json_optional(summary_path) or {},
        include_experimental_dynamic=include_experimental_dynamic,
    )
    if not summary:
        payload = {
            "status": "missing_assets",
            "entrypoint": "website-assets",
            "asset_scope": "missing",
            "requested_pack_id": pack_id or "",
            "available_pack_ids": [],
            "selected_pack": None,
                "artifacts": {
                    "assets_summary_json": str(summary_path),
                    "assets_summary_md": str(summary_md_path),
                    "assets_dir": str(asset_dir),
                    "build_command": f"bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}",
                },
                "next_steps": [
                    f"run bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}",
                    "rerun website assets after the reusable delivery assets are rebuilt",
                ],
        }
        return payload, EXIT_VALIDATION

    assets = summary.get("assets", [])
    asset_index = {str(item.get("pack_id") or ""): item for item in assets}
    requested_pack_id = (pack_id or "").strip()

    selected_pack = None
    selected_payload = None
    asset_scope = "summary"
    exit_code = EXIT_OK
    status = "ok"

    if requested_pack_id:
        selected_pack = asset_index.get(requested_pack_id)
        if not selected_pack:
            payload = {
                "status": "unknown_pack",
                "entrypoint": "website-assets",
                "asset_scope": "selection_error",
                "requested_pack_id": requested_pack_id,
                "available_pack_ids": sorted(asset_index.keys()),
                "selected_pack": None,
                "artifacts": {
                    "assets_summary_json": str(summary_path),
                    "assets_summary_md": str(summary_md_path),
                    "assets_dir": str(asset_dir),
                },
                "next_steps": [
                    "list available static-website pack ids",
                    "rerun website assets with one supported static-website pack id",
                    f"inspect {summary_md_path}",
                ],
            }
            return payload, EXIT_VALIDATION

        selected_payload = _load_json_optional(Path(str(selected_pack.get("json_path") or ""))) or {}
        asset_scope = "pack"
        status = selected_payload.get("validated_behavior", {}).get("delivery_ready") and "ok" or "attention"

    next_steps = []
    if selected_pack:
        next_steps.extend(
            [
                f"inspect {selected_pack.get('json_path', '')}",
                f"inspect {selected_pack.get('md_path', '')}",
            ]
        )
        if selected_payload:
            best_entry_command = selected_payload.get("best_entry_command")
            if best_entry_command:
                next_steps.append(f"run {best_entry_command}")
    else:
        next_steps.extend(
            [
                f"inspect {summary_md_path}",
                "select one pack id and rerun website assets for the per-pack bundle",
            ]
        )

    payload = {
        "status": status,
        "entrypoint": "website-assets",
        "asset_scope": asset_scope,
        "requested_pack_id": requested_pack_id,
        "available_pack_ids": sorted(asset_index.keys()),
        "summary": summary,
        "selected_pack": selected_pack,
        "selected_payload": selected_payload,
        "public_surface_note": summary.get("public_surface_note", ""),
        "experimental_dynamic_enabled": include_experimental_dynamic,
        "artifacts": {
            "assets_summary_json": str(summary_path),
            "assets_summary_md": str(summary_md_path),
            "assets_dir": str(asset_dir),
            "build_command": f"bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}",
        },
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_website_open_asset_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    assets_payload, exit_code = _build_website_assets_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    available_pack_ids = assets_payload.get("available_pack_ids", [])

    if assets_payload.get("status") not in {"ok", "attention"}:
        payload = {
            "status": assets_payload.get("status", "error"),
            "entrypoint": "website-open-asset",
            "asset_scope": assets_payload.get("asset_scope", "missing"),
            "requested_pack_id": pack_id or "",
            "available_pack_ids": available_pack_ids,
            "message": assets_payload.get("message", "Website assets are not ready."),
            "artifacts": assets_payload.get("artifacts", {}),
            "result": assets_payload,
            "next_steps": list(assets_payload.get("next_steps", [])),
        }
        return payload, exit_code

    asset_scope = assets_payload.get("asset_scope", "summary")
    requested_pack_id = assets_payload.get("requested_pack_id", "")

    if asset_scope == "pack":
        selected_pack = assets_payload.get("selected_pack") or {}
        selected_payload = assets_payload.get("selected_payload") or {}
        resolved_label = f"{selected_pack.get('pack_id', requested_pack_id)}_json_asset"
        target = {
            "label": resolved_label,
            "display_name": f"{selected_pack.get('pack', requested_pack_id)} JSON Asset",
            "kind": "file",
            "path": selected_pack.get("json_path", ""),
            "exists": Path(str(selected_pack.get("json_path", ""))).exists(),
        }
        related_targets = [
            {
                "label": f"{selected_pack.get('pack_id', requested_pack_id)}_md_asset",
                "display_name": f"{selected_pack.get('pack', requested_pack_id)} Markdown Asset",
                "kind": "file",
                "path": selected_pack.get("md_path", ""),
                "exists": Path(str(selected_pack.get("md_path", ""))).exists(),
            },
            {
                "label": "delivery_validation_json",
                "display_name": "Website Delivery Validation JSON",
                "kind": "file",
                "path": ((selected_payload.get("evidence") or {}).get("delivery_validation_json") or ""),
                "exists": Path(str((selected_payload.get("evidence") or {}).get("delivery_validation_json") or "")).exists(),
            },
            {
                "label": "demo_pack_run_json",
                "display_name": "Website Demo Pack Run JSON",
                "kind": "file",
                "path": ((selected_payload.get("evidence") or {}).get("demo_pack_run_json") or ""),
                "exists": Path(str((selected_payload.get("evidence") or {}).get("demo_pack_run_json") or "")).exists(),
            },
        ]
        inspect_command = f"inspect {target['path']}"
        next_steps = [
            inspect_command,
            f"inspect {selected_pack.get('md_path', '')}",
        ]
        best_entry_command = selected_payload.get("best_entry_command")
        if best_entry_command:
            next_steps.append(f"run {best_entry_command}")
        payload = {
            "status": "ok",
            "entrypoint": "website-open-asset",
            "asset_scope": "pack",
            "requested_pack_id": requested_pack_id,
            "resolved_label": resolved_label,
            "available_pack_ids": available_pack_ids,
            "target": target,
            "related_targets": related_targets,
            "inspect_command": inspect_command,
            "assets": assets_payload,
            "next_steps": next_steps,
        }
        return payload, EXIT_OK

    artifacts = assets_payload.get("artifacts") or {}
    target_path = artifacts.get("assets_summary_md", "")
    resolved_label = "website_assets_summary_md"
    target = {
        "label": resolved_label,
        "display_name": "Website Delivery Assets Summary",
        "kind": "file",
        "path": target_path,
        "exists": Path(str(target_path)).exists(),
    }
    related_targets = [
        {
            "label": "website_assets_summary_json",
            "display_name": "Website Delivery Assets Summary JSON",
            "kind": "file",
            "path": artifacts.get("assets_summary_json", ""),
            "exists": Path(str(artifacts.get("assets_summary_json", ""))).exists(),
        },
        {
            "label": "website_assets_directory",
            "display_name": "Website Delivery Assets Directory",
            "kind": "directory",
            "path": artifacts.get("assets_dir", ""),
            "exists": Path(str(artifacts.get("assets_dir", ""))).exists(),
        },
    ]
    inspect_command = f"inspect {target['path']}"
    payload = {
        "status": "ok",
        "entrypoint": "website-open-asset",
        "asset_scope": "summary",
        "requested_pack_id": requested_pack_id,
        "resolved_label": resolved_label,
        "available_pack_ids": available_pack_ids,
        "target": target,
        "related_targets": related_targets,
        "inspect_command": inspect_command,
        "assets": assets_payload,
        "next_steps": [
            inspect_command,
            "choose one of the available_pack_ids values and rerun website open-asset for a pack-specific bundle",
        ],
    }
    return payload, EXIT_OK


def _build_website_inspect_asset_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    open_payload, exit_code = _build_website_open_asset_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    if exit_code != EXIT_OK:
        payload = {
            "status": open_payload.get("status", "error"),
            "entrypoint": "website-inspect-asset",
            "asset_scope": open_payload.get("asset_scope", "missing"),
            "requested_pack_id": pack_id or "",
            "available_pack_ids": open_payload.get("available_pack_ids", []),
            "message": open_payload.get("message", "Unable to resolve website delivery asset target."),
            "result": open_payload,
            "next_steps": list(open_payload.get("next_steps", [])),
        }
        return payload, exit_code

    target = open_payload.get("target") or {}
    inspection = _inspect_resolved_target(target)
    status = "ok" if inspection.get("exists") else "warning"
    next_steps = list(open_payload.get("next_steps", []))
    if inspection.get("kind") == "file":
        follow_up = f"open or inspect {target.get('path', '')} in your editor"
    elif inspection.get("kind") == "directory":
        follow_up = f"inspect entries under {target.get('path', '')}"
    else:
        follow_up = None
    if follow_up and follow_up not in next_steps:
        next_steps.insert(0, follow_up)

    payload = {
        "status": status,
        "entrypoint": "website-inspect-asset",
        "asset_scope": open_payload.get("asset_scope", "summary"),
        "requested_pack_id": open_payload.get("requested_pack_id", ""),
        "resolved_label": open_payload.get("resolved_label"),
        "available_pack_ids": open_payload.get("available_pack_ids", []),
        "target": target,
        "inspection": inspection,
        "inspect_command": open_payload.get("inspect_command"),
        "related_targets": open_payload.get("related_targets", []),
        "assets": open_payload.get("assets"),
        "result": open_payload,
        "next_steps": next_steps,
    }
    return payload, (EXIT_OK if status == "ok" else EXIT_VALIDATION)


def _build_website_export_handoff_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    summary_payload, summary_exit = _build_website_summary_payload(
        include_experimental_dynamic=include_experimental_dynamic
    )
    assets_payload, assets_exit = _build_website_assets_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    open_payload, open_exit = _build_website_open_asset_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    inspect_payload, inspect_exit = _build_website_inspect_asset_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )

    exit_code = EXIT_OK
    status = "ok"
    for candidate_exit, candidate_payload in (
        (inspect_exit, inspect_payload),
        (open_exit, open_payload),
        (assets_exit, assets_payload),
        (summary_exit, summary_payload),
    ):
        if candidate_exit != EXIT_OK:
            exit_code = candidate_exit
            status = candidate_payload.get("status", "attention")
            break

    next_steps: list[str] = []
    for source in (
        inspect_payload.get("next_steps", []),
        open_payload.get("next_steps", []),
        assets_payload.get("next_steps", []),
        summary_payload.get("next_steps", []),
    ):
        for item in source:
            if item and item not in next_steps:
                next_steps.append(item)

    selected_pack = assets_payload.get("selected_pack") or {}
    selected_payload = assets_payload.get("selected_payload") or {}
    asset_scope = assets_payload.get("asset_scope", "summary")

    payload = {
        "status": status,
        "entrypoint": "website-export-handoff",
        "asset_scope": asset_scope,
        "requested_pack_id": assets_payload.get("requested_pack_id", ""),
        "available_pack_ids": assets_payload.get("available_pack_ids", []),
        "selected_pack": selected_pack,
        "selected_payload": selected_payload,
        "recommended_website_action": summary_payload.get("recommended_website_action"),
        "recommended_website_command": summary_payload.get("recommended_website_command"),
        "recommended_website_reason": summary_payload.get("recommended_website_reason"),
        "website_summary": summary_payload,
        "website_assets": assets_payload,
        "website_open_asset": open_payload,
        "website_inspect_asset": inspect_payload,
        "primary_target_label": open_payload.get("resolved_label"),
        "primary_target": open_payload.get("target"),
        "primary_inspection": inspect_payload.get("inspection"),
        "inspect_command": inspect_payload.get("inspect_command"),
        "related_targets": open_payload.get("related_targets", []),
        "documents": summary_payload.get("documents", {}),
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_website_run_inspect_command_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    inspect_payload, exit_code = _build_website_inspect_asset_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    target = inspect_payload.get("target") or {}
    inspection = inspect_payload.get("inspection") or {}
    next_steps = list(inspect_payload.get("next_steps", []))

    if inspection.get("kind") == "file":
        follow_up = f"open or inspect {target.get('path', '')} in your editor"
    elif inspection.get("kind") == "directory":
        follow_up = f"inspect entries under {target.get('path', '')}"
    else:
        follow_up = None
    if follow_up and follow_up not in next_steps:
        next_steps.insert(0, follow_up)

    payload = {
        "status": inspect_payload.get("status", "error"),
        "entrypoint": "website-run-inspect-command",
        "route_taken": "website_inspect_asset",
        "route_reason": "Website run-inspect-command executes the exact asset inspection step implied by the current website asset handoff without changing the underlying inspection semantics.",
        "asset_scope": inspect_payload.get("asset_scope", "summary"),
        "requested_pack_id": inspect_payload.get("requested_pack_id", ""),
        "resolved_label": inspect_payload.get("resolved_label"),
        "executed_inspect_command": inspect_payload.get("inspect_command"),
        "target": target,
        "inspection": inspection,
        "related_targets": inspect_payload.get("related_targets", []),
        "assets": inspect_payload.get("assets"),
        "result": inspect_payload,
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_website_preview_payload(
    *,
    pack_id: str | None,
    include_experimental_dynamic: bool,
) -> tuple[dict[str, Any], int]:
    export_payload, exit_code = _build_website_export_handoff_payload(
        pack_id=pack_id,
        include_experimental_dynamic=include_experimental_dynamic,
    )
    requested_pack_id = export_payload.get("requested_pack_id", "")
    asset_scope = export_payload.get("asset_scope", "summary")
    primary_target = export_payload.get("primary_target") or {}
    related_targets = export_payload.get("related_targets") or []
    open_targets = [primary_target] + [item for item in related_targets if item.get("label") != primary_target.get("label")]
    open_targets = [item for item in open_targets if item]

    if asset_scope == "pack":
        pack_name = (export_payload.get("selected_pack") or {}).get("pack", requested_pack_id or "selected website pack")
        preview_hint = (
            f"Open the validated website asset bundle for {pack_name}, then inspect the related Markdown and evidence files if you need richer delivery context."
        )
        surface_kind = "website_pack"
    else:
        preview_hint = "Open the website delivery assets summary first, then drill into one pack-specific bundle or its linked evidence files."
        surface_kind = "website_frontier"

    preview_handoff = {
        "status": "ok" if export_payload.get("status") == "ok" else export_payload.get("status", "attention"),
        "consumption_kind": "website",
        "surface_kind": surface_kind,
        "requested_pack_id": requested_pack_id,
        "primary_target": primary_target,
        "open_targets": open_targets,
        "preview_hint": preview_hint,
        "next_steps": list(export_payload.get("next_steps", [])),
    }

    website_preview_summary = {
        "surface_kind": surface_kind,
        "asset_scope": asset_scope,
        "primary_target_label": export_payload.get("primary_target_label"),
        "primary_target": primary_target,
        "selected_pack": export_payload.get("selected_pack"),
        "selected_payload": export_payload.get("selected_payload"),
    }

    payload = {
        "status": export_payload.get("status", "error"),
        "entrypoint": "website-preview",
        "asset_scope": asset_scope,
        "requested_pack_id": requested_pack_id,
        "website_summary": export_payload.get("website_summary"),
        "website_assets": export_payload.get("website_assets"),
        "website_export_handoff": export_payload,
        "website_preview_summary": website_preview_summary,
        "preview_handoff": preview_handoff,
        "preview_hint": preview_hint,
        "open_targets": open_targets,
        "primary_target_label": export_payload.get("primary_target_label"),
        "primary_target": primary_target,
        "next_steps": list(export_payload.get("next_steps", [])),
    }
    return payload, exit_code


def _build_website_summary_payload(*, include_experimental_dynamic: bool) -> tuple[dict[str, Any], int]:
    results_dir = REPO_ROOT / "testing/results"
    assets_json_path = results_dir / "website_delivery_assets_20260319.json"
    assets_md_path = results_dir / "website_delivery_assets_20260319.md"
    delivery_validation_json_path = results_dir / "website_delivery_validation_20260319.json"
    delivery_validation_md_path = results_dir / "website_delivery_validation_20260319.md"
    demo_pack_json_path = results_dir / "website_demo_pack_run_20260319.json"
    demo_pack_md_path = results_dir / "website_demo_pack_run_20260319.md"
    frontier_summary_path = REPO_ROOT / "WEBSITE_FRONTIER_SUMMARY_20260319.md"
    product_pack_path = REPO_ROOT / "WEBSITE_PRODUCT_PACK_20260319.md"
    delivery_checklist_path = REPO_ROOT / "WEBSITE_DELIVERY_CHECKLIST_20260319.md"
    requirement_templates_path = REPO_ROOT / "WEBSITE_REQUIREMENT_TEMPLATES_20260319.md"
    sales_positioning_path = REPO_ROOT / "WEBSITE_SALES_POSITIONING_20260319.md"

    assets = _filter_website_assets_summary(
        _load_json_optional(assets_json_path) or {},
        include_experimental_dynamic=include_experimental_dynamic,
    )
    delivery_validation = _filter_website_validation_payload(
        _load_json_optional(delivery_validation_json_path) or {},
        include_experimental_dynamic=include_experimental_dynamic,
    )
    demo_pack_run = _filter_website_demo_payload(
        _load_json_optional(demo_pack_json_path) or {},
        include_experimental_dynamic=include_experimental_dynamic,
    )

    supported_pack_count = int(assets.get("supported_count", 0) or 0)
    partial_pack_count = int(assets.get("partial_count", 0) or 0)
    assets_ok = assets.get("status") == "ok"
    delivery_ok = (delivery_validation.get("summary") or {}).get("status") == "ok"
    demo_ok = (demo_pack_run.get("summary") or {}).get("status") == "ok"
    status = "ok" if assets_ok and delivery_ok and demo_ok else "attention"

    if assets_ok:
        recommended_website_action = "website_assets"
        recommended_website_command = f'PYTHONPATH="{REPO_ROOT_STR}" python3 -m cli website assets --json'
        recommended_website_reason = (
            "Reusable static-website delivery assets are ready, so the highest-value next step is to consume the validated presentation-site bundles directly."
        )
    else:
        recommended_website_action = "build_website_delivery_assets"
        recommended_website_command = f"bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}"
        recommended_website_reason = (
            "Static-website delivery assets are missing or stale, so rebuild the reusable presentation-site bundles before consuming them."
        )

    payload = {
        "status": status,
        "entrypoint": "website-summary",
        "supported_pack_count": supported_pack_count,
        "partial_pack_count": partial_pack_count,
        "assets": {
            "status": assets.get("status", "missing"),
            "summary_json": str(assets_json_path),
            "summary_md": str(assets_md_path),
            "asset_dir": assets.get("asset_dir", str(results_dir / "website_delivery_assets_20260319")),
            "recommended_validation_flow": assets.get("recommended_validation_flow", ""),
            "public_surface_note": assets.get("public_surface_note", ""),
        },
        "delivery_validation": {
            "status": (delivery_validation.get("summary") or {}).get("status", "missing"),
            "supported_ready_count": (delivery_validation.get("summary") or {}).get("supported_ready_count"),
            "partial_ready_count": (delivery_validation.get("summary") or {}).get("partial_ready_count"),
            "json_path": str(delivery_validation_json_path),
            "md_path": str(delivery_validation_md_path),
        },
        "demo_pack_run": {
            "status": (demo_pack_run.get("summary") or {}).get("status", "missing"),
            "case_count": (demo_pack_run.get("summary") or {}).get("case_count"),
            "supported_demo_ready_count": (demo_pack_run.get("summary") or {}).get("supported_demo_ready_count"),
            "json_path": str(demo_pack_json_path),
            "md_path": str(demo_pack_md_path),
        },
        "documents": {
            "frontier_summary": str(frontier_summary_path),
            "product_pack": str(product_pack_path),
            "delivery_checklist": str(delivery_checklist_path),
            "requirement_templates": str(requirement_templates_path),
            "sales_positioning": str(sales_positioning_path),
        },
        "recommended_website_action": recommended_website_action,
        "recommended_website_command": recommended_website_command,
        "recommended_website_reason": recommended_website_reason,
        "experimental_dynamic_enabled": include_experimental_dynamic,
        "next_steps": [
            f"run {recommended_website_command}",
            f"inspect {assets_md_path}",
            f"inspect {delivery_validation_md_path}",
        ],
    }
    return payload, (EXIT_OK if status == "ok" else EXIT_VALIDATION)


def _run_website_go(*, include_experimental_dynamic: bool) -> tuple[dict[str, Any], int]:
    summary_payload, summary_exit = _build_website_summary_payload(
        include_experimental_dynamic=include_experimental_dynamic
    )
    executed_website_action = summary_payload["recommended_website_action"]

    if executed_website_action == "website_assets":
        result_payload, exit_code = _build_website_assets_payload(
            pack_id=None,
            include_experimental_dynamic=include_experimental_dynamic,
        )
    elif executed_website_action == "build_website_delivery_assets":
        command = ["bash", BUILD_WEBSITE_DELIVERY_ASSETS_SH]
        try:
            completed = subprocess.run(
                command,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            result_payload, exit_code = _build_website_assets_payload(
                pack_id=None,
                include_experimental_dynamic=include_experimental_dynamic,
            )
            result_payload = {
                **result_payload,
                "build_assets_result": {
                    "status": "ok",
                    "command": f"bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}",
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                },
            }
        except subprocess.CalledProcessError as exc:
            result_payload = {
                "status": "warning",
                "entrypoint": "website-assets-build",
                "message": "Website delivery asset build failed.",
                "build_assets_result": {
                    "status": "warning",
                    "command": f"bash {BUILD_WEBSITE_DELIVERY_ASSETS_SH}",
                    "stdout": (exc.stdout or "").strip(),
                    "stderr": (exc.stderr or "").strip(),
                    "exit_code": exc.returncode,
                },
                "next_steps": [
                    "review the build stderr for the asset-generation failure",
                    "rerun the website delivery asset build after fixing the blocking issue",
                ],
            }
            exit_code = EXIT_VALIDATION
    else:
        result_payload = {
            "status": "attention",
            "entrypoint": "website-go",
            "message": "Website go could not map the recommended website action to a supported execution path.",
            "next_steps": list(summary_payload.get("next_steps", [])),
        }
        exit_code = EXIT_VALIDATION

    payload = {
        "status": result_payload.get("status", "error"),
        "entrypoint": "website-go",
        "route_taken": executed_website_action,
        "route_reason": summary_payload["recommended_website_reason"],
        "executed_website_action": executed_website_action,
        "experimental_dynamic_enabled": include_experimental_dynamic,
        "recommended_website_action": summary_payload["recommended_website_action"],
        "recommended_website_command": summary_payload["recommended_website_command"],
        "recommended_website_reason": summary_payload["recommended_website_reason"],
        "website_summary": summary_payload,
        "result": result_payload,
        "next_steps": result_payload.get("next_steps", summary_payload.get("next_steps", [])),
    }
    return payload, exit_code if exit_code is not None else summary_exit


def _initialize_project(ctx: ProjectContext) -> tuple[list[str], list[str]]:
    manifest_service = ManifestService()
    created: list[str] = []
    existing: list[str] = []

    for directory in [ctx.ail_dir, ctx.patches_dir]:
        if directory.exists():
            existing.append(ctx.to_relative(directory))
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(ctx.to_relative(directory))

    for relpath in MANAGED_ROOTS + USER_ROOTS:
        path = ctx.root / relpath
        if path.exists():
            existing.append(relpath)
        else:
            path.mkdir(parents=True, exist_ok=True)
            created.append(relpath)

    source_template = "#PROFILE[landing]\n@PAGE[Home,/]\n#UI[landing:Header]{}\n#UI[landing:Hero]{}\n#UI[landing:FeatureGrid]{}\n#UI[landing:CTA]{}\n#UI[landing:Footer]{}\n"
    _safe_write(ctx.source_file, source_template, created, existing, ctx)
    _safe_write(ctx.manifest_file, manifest_service.make_initial_manifest(ctx.project_id), created, existing, ctx, as_json=True)
    _safe_write(ctx.last_build_file, manifest_service.make_initial_last_build(ctx.project_id), created, existing, ctx, as_json=True)
    return created, existing


def _safe_write(
    path: Path,
    payload: str | dict[str, Any],
    created: list[str],
    existing: list[str],
    ctx: ProjectContext,
    *,
    as_json: bool = False,
) -> None:
    if path.exists():
        existing.append(ctx.to_relative(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    created.append(ctx.to_relative(path))


def _read_requirement(args: argparse.Namespace) -> str:
    if args.from_file:
        return Path(args.from_file).read_text(encoding="utf-8").strip()
    if args.requirement:
        return args.requirement.strip()
    stdin_text = sys.stdin.read().strip()
    return stdin_text


def _read_requirement_optional(args: argparse.Namespace) -> str:
    if getattr(args, "requirement_file", None):
        return Path(args.requirement_file).read_text(encoding="utf-8").strip()
    if getattr(args, "requirement", None):
        return args.requirement.strip()
    return ""


def _read_review_text(args: argparse.Namespace, *, allow_stdin: bool = True) -> str:
    if getattr(args, "review_text_file", None):
        return Path(args.review_text_file).read_text(encoding="utf-8").strip()
    if getattr(args, "review_text", None):
        return str(args.review_text).strip()
    if not allow_stdin:
        return ""
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def _write_cli_output_file(path: Path, payload: str | dict[str, Any], *, as_json: bool = False) -> None:
    path = path.expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")


def _writing_bundle_root() -> Path:
    return _writing_intent_root() / "writing_bundles"


def _slugify_writing_requirement(requirement: str) -> str:
    lowered = requirement.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if slug:
        return slug[:48]
    utf_hex = requirement.strip().encode("utf-8", errors="ignore").hex()[:24]
    return f"writing-{utf_hex or 'bundle'}"


def _resolve_writing_bundle_dir(requirement: str, output_dir: str | None) -> Path:
    if output_dir:
        path = Path(output_dir).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path
    _writing_bundle_root().mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return (_writing_bundle_root() / f"{_slugify_writing_requirement(requirement)}-{stamp}").resolve()


def _resolve_ail_input(raw_input: str) -> Path:
    path = Path(raw_input).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"AIL input file not found: {path}")
    return path


def _default_requirement_for_ail(repair_mod: Any, ail_text: str) -> str:
    parsed = repair_mod.parse_program(ail_text)
    profiles = parsed.get("profiles") or []
    profile = profiles[0] if profiles else "landing"
    defaults = {
        "landing": "做一个 landing 官网",
        "ecom_min": "做一个电商网站，包含商品、购物车和结算",
        "after_sales": "做一个售后页面，包含退款、换货和客服",
        "app_min": "做一个 app 原型，包含顶部栏、底部 tab 和列表",
    }
    return defaults.get(profile, "做一个 landing 官网")


def _load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_matching_file(pattern: str) -> Path | None:
    matches = sorted(glob.glob(pattern))
    if not matches:
        return None
    return Path(matches[-1])


def _effective_base_url(base_url: str | None) -> str:
    return base_url or os.environ.get("AIL_CLOUD_BASE_URL") or "http://127.0.0.1:5002"


def _resolve_project_id_arg(project_id: str | None) -> str:
    if project_id and project_id.strip():
        return project_id.strip()
    ctx = ProjectContext.discover()
    return ctx.project_id


def _build_cloud_status_payload(client: AILCloudClient, *, project_id: str) -> dict[str, Any]:
    project_data = client.get_project(project_id)
    project_cloud = _query_cloud_summary(client)

    latest_build_id = str(project_data.get("latest_build_id") or "")
    builds_data = client.get_project_builds(project_id, limit=5)
    builds_cloud = _query_cloud_summary(client)

    latest_build = None
    build_cloud = None
    artifact = None
    artifact_cloud = None

    if latest_build_id:
        latest_build = client.get_build(latest_build_id)
        build_cloud = _query_cloud_summary(client)
        if latest_build.get("artifact_available"):
            artifact = client.get_build_artifact(latest_build_id)
            artifact_cloud = _query_cloud_summary(client)

    return {
        "status": "ok",
        "project_id": project_id,
        "project": project_data,
        "latest_build": latest_build,
        "latest_artifact": artifact,
        "recent_builds": builds_data.get("items") or [],
        "recent_build_count": len(builds_data.get("items") or []),
        "next_cursor": builds_data.get("next_cursor"),
        "cloud": {
            "project": project_cloud,
            "builds": builds_cloud,
            "build": build_cloud,
            "artifact": artifact_cloud,
        },
    }


def _hook_catalog_paths(ctx: ProjectContext) -> tuple[Path, Path]:
    return ctx.ail_dir / "hook_catalog.json", ctx.ail_dir / "hook_catalog.md"


def _last_hook_suggestions_path(ctx: ProjectContext) -> Path:
    return ctx.ail_dir / "last_hook_suggestions.json"


def _last_workspace_hook_init_path() -> Path:
    return REPO_ROOT / ".workspace_ail" / "last_workspace_hook_init.json"


def _write_last_hook_suggestions(
    ctx: ProjectContext,
    *,
    requested_hook_name: str | None,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    suggestions: Sequence[dict[str, Any]],
) -> None:
    ctx.ail_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "requested_hook_name": requested_hook_name or None,
        "page_key_filter": page_key_filter,
        "section_key_filter": section_key_filter,
        "slot_key_filter": slot_key_filter,
        "suggestion_count": len(suggestions),
        "hook_names": [str(item.get("hook_name") or "") for item in suggestions if item.get("hook_name")],
    }
    _last_hook_suggestions_path(ctx).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_last_hook_suggestions(ctx: ProjectContext) -> dict[str, Any] | None:
    path = _last_hook_suggestions_path(ctx)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _write_last_workspace_hook_init(
    *,
    project_name: str,
    project_root: str,
    route_taken: str,
    requested_hook_name: str | None,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
) -> None:
    path = _last_workspace_hook_init_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_name": project_name,
        "project_root": project_root,
        "route_taken": route_taken,
        "requested_hook_name": requested_hook_name or None,
        "page_key_filter": page_key_filter,
        "section_key_filter": section_key_filter,
        "slot_key_filter": slot_key_filter,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_last_workspace_hook_init() -> dict[str, Any] | None:
    path = _last_workspace_hook_init_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _workspace_recent_project_entry(projects: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    recent = _read_last_workspace_hook_init()
    if not recent:
        return None
    recent_root = str(recent.get("project_root") or "")
    recent_name = str(recent.get("project_name") or "")
    for item in projects:
        if recent_root and str(item.get("project_root") or "") == recent_root:
            return item
        if recent_name and str(item.get("project_name") or "") == recent_name:
            return item
    return None



def _workspace_recent_hook_query_for_project(project_name: str | None, project_root: str | None) -> dict[str, str]:
    recent = _read_last_workspace_hook_init()
    if not recent:
        return {}
    recent_root = str(recent.get("project_root") or "").strip()
    recent_name = str(recent.get("project_name") or "").strip()
    normalized_root = str(project_root or "").strip()
    normalized_name = str(project_name or "").strip()
    if normalized_root and recent_root and normalized_root != recent_root:
        return {}
    if normalized_name and recent_name and normalized_name != recent_name:
        return {}
    query: dict[str, str] = {}
    for key in ("requested_hook_name", "page_key_filter", "section_key_filter", "slot_key_filter"):
        value = str(recent.get(key) or "").strip()
        if value:
            query[key] = value
    return query


def _normalize_hook_catalog_page(page: dict[str, Any]) -> dict[str, Any]:
    context = page.get("context") or {}
    page_hooks = [str(item) for item in (page.get("pageHooks") or page.get("page_hooks") or [])]
    section_hooks = page.get("sectionHooks") or page.get("section_hooks") or []
    slot_hooks = page.get("slotHooks") or page.get("slot_hooks") or []
    return {
        "page_key": page.get("pageKey") or page.get("page_key") or "",
        "page_name": page.get("pageName") or page.get("page_name") or "",
        "page_path": page.get("pagePath") or page.get("page_path") or "",
        "page_hooks": page_hooks,
        "section_hooks": section_hooks,
        "slot_hooks": slot_hooks,
        "context": context,
    }



def _build_hook_catalog_summary(ctx: ProjectContext) -> dict[str, Any]:
    json_path, md_path = _hook_catalog_paths(ctx)
    raw = _load_json_optional(json_path) or {}
    pages = [_normalize_hook_catalog_page(page) for page in (raw.get("pages") or []) if isinstance(page, dict)]
    return {
        "exists": json_path.exists(),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "generated_at": raw.get("generated_at", ""),
        "page_count": len(pages),
        "page_keys": [page["page_key"] for page in pages if page.get("page_key")],
        "section_hook_count": sum(len(page.get("section_hooks") or []) for page in pages),
        "slot_hook_count": sum(len(page.get("slot_hooks") or []) for page in pages),
        "pages": pages,
    }


def _workspace_hook_catalog_project_roots() -> tuple[list[Path], bool, str]:
    output_projects_root = REPO_ROOT / "output_projects"
    project_roots: list[Path] = []
    seen: set[str] = set()

    if output_projects_root.exists():
        for child in sorted(output_projects_root.iterdir()):
            if not child.is_dir():
                continue
            if not (child / ".ail" / "hook_catalog.json").exists():
                continue
            resolved = str(child.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            project_roots.append(child.resolve())

    current_project_included = False
    current_project_root = ""
    try:
        current_ctx = ProjectContext.discover(Path.cwd())
        current_catalog_json, _ = _hook_catalog_paths(current_ctx)
        if current_catalog_json.exists():
            current_root = current_ctx.root.resolve()
            current_project_root = str(current_root)
            if current_project_root not in seen:
                seen.add(current_project_root)
                project_roots.append(current_root)
            current_project_included = True
    except Exception:
        pass

    return project_roots, current_project_included, current_project_root


def _build_workspace_hooks_payload() -> dict[str, Any]:
    output_projects_root = REPO_ROOT / "output_projects"
    scanned_project_count = 0
    if output_projects_root.exists():
        scanned_project_count = sum(1 for child in output_projects_root.iterdir() if child.is_dir())

    project_roots, current_project_included, current_project_root = _workspace_hook_catalog_project_roots()
    projects: list[dict[str, Any]] = []
    for root in project_roots:
        ctx = ProjectContext.from_root(root)
        catalog = _build_hook_catalog_summary(ctx)
        default_page_key = str(catalog["page_keys"][0]) if catalog["page_keys"] else ""
        recommended_hook_suggest_command = (
            f"cd {root} && " + _build_project_hook_suggest_command(default_page_key or "home", page_key_filter=default_page_key or None)
            if default_page_key
            else ""
        )
        projects.append(
            {
                "project_name": root.name,
                "project_id": ctx.project_id,
                "project_root": str(root),
                "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                "available_page_keys": catalog["page_keys"],
                "recommended_hook_suggest_command": recommended_hook_suggest_command,
                "recommended_workspace_hook_suggest_command": (
                    _build_workspace_hook_init_command(
                        default_page_key or "home",
                        project_name=root.name,
                        suggest=True,
                        page_key_filter=default_page_key or None,
                    )
                    if default_page_key
                    else ""
                ),
                "recommended_workspace_hook_pick_command": (
                    _build_workspace_hook_init_command(
                        requested_hook_name=default_page_key or "home",
                        project_name=root.name,
                        suggest=True,
                        page_key_filter=default_page_key or None,
                        pick_recommended=True,
                    )
                    if default_page_key
                    else ""
                ),
            }
        )

    projects.sort(
        key=lambda item: (
            str((item.get("hook_catalog") or {}).get("generated_at") or ""),
            str(item.get("project_name") or ""),
        ),
        reverse=True,
    )

    recent_project = _workspace_recent_project_entry(projects)
    recommended_workspace_hook_suggest_command = ""
    recommended_workspace_hook_pick_command = ""
    recent_workspace_hook_suggest_command = ""
    recent_workspace_hook_pick_command = ""
    preferred_workspace_hook_command = ""
    preferred_workspace_hook_reason = ""

    next_steps = [f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace hooks --json"]
    if projects:
        first_project = projects[0]
        first_page_key = str((first_project.get("available_page_keys") or [""])[0] or "")
        if first_page_key:
            recommended_workspace_hook_suggest_command = _build_workspace_hook_init_command(
                first_page_key,
                use_recommended_project=True,
                suggest=True,
                page_key_filter=first_page_key,
            )
            recommended_workspace_hook_pick_command = _build_workspace_hook_init_command(
                follow_recommended=True,
            )
        next_steps.extend(
            [
                f"cd {first_project['project_root']} && PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                f"inspect {first_project['hook_catalog']['markdown_path']}",
            ]
        )
        if first_project.get("recommended_hook_suggest_command"):
            next_steps.append(f"run {first_project['recommended_hook_suggest_command']}")
        if first_project.get("recommended_workspace_hook_suggest_command"):
            next_steps.append(f"run {first_project['recommended_workspace_hook_suggest_command']}")
        if recommended_workspace_hook_pick_command:
            next_steps.append(f"run {recommended_workspace_hook_pick_command}")
    if recent_project:
        recent_workspace_hook_suggest_command = _build_workspace_hook_init_command(
            use_last_project=True,
            suggest=True,
        )
        recent_workspace_hook_pick_command = _build_workspace_hook_init_command(
            use_last_project=True,
            pick_recommended=True,
        )
        next_steps.append(f"run {recent_workspace_hook_suggest_command}")
        preferred_workspace_hook_command = recent_workspace_hook_pick_command or recent_workspace_hook_suggest_command
        preferred_workspace_hook_reason = "Continue from the most recent workspace hook project and its last narrowed hook query when available."
    elif recommended_workspace_hook_pick_command:
        preferred_workspace_hook_command = recommended_workspace_hook_pick_command
        preferred_workspace_hook_reason = "Use the current recommended workspace project and its first recommended hook path."
    else:
        next_steps.append(
            "generate or rebuild one project to emit /.ail/hook_catalog.json before inspecting hook coverage"
        )

    return {
        "status": "ok",
        "entrypoint": "workspace-hooks",
        "repo_root": str(REPO_ROOT),
        "output_projects_root": str(output_projects_root),
        "scanned_project_count": scanned_project_count,
        "catalog_project_count": len(projects),
        "current_project_included": current_project_included,
        "current_project_root": current_project_root,
        "page_count": sum((item.get("hook_catalog") or {}).get("page_count", 0) for item in projects),
        "section_hook_count": sum((item.get("hook_catalog") or {}).get("section_hook_count", 0) for item in projects),
        "slot_hook_count": sum((item.get("hook_catalog") or {}).get("slot_hook_count", 0) for item in projects),
        "available_projects": [item["project_name"] for item in projects],
        "projects": projects,
        "recommended_hook_project": projects[0]["project_name"] if projects else "",
        "recommended_hook_project_root": projects[0]["project_root"] if projects else "",
        "recommended_hook_suggest_command": projects[0].get("recommended_hook_suggest_command", "") if projects else "",
        "recommended_workspace_hook_suggest_command": recommended_workspace_hook_suggest_command,
        "recommended_workspace_hook_pick_command": recommended_workspace_hook_pick_command,
        "recent_hook_project": recent_project.get("project_name", "") if recent_project else "",
        "recent_hook_project_root": recent_project.get("project_root", "") if recent_project else "",
        "recent_workspace_hook_suggest_command": recent_workspace_hook_suggest_command,
        "recent_workspace_hook_pick_command": recent_workspace_hook_pick_command,
        "preferred_workspace_hook_command": preferred_workspace_hook_command,
        "preferred_workspace_hook_reason": preferred_workspace_hook_reason,
        "next_steps": next_steps,
    }


def _resolve_workspace_hook_init_project(project_name: str | None, *, use_last_project: bool = False) -> tuple[ProjectContext | None, dict[str, Any] | None, str]:
    requested_project_name = (project_name or "").strip()
    try:
        current_ctx = ProjectContext.discover(Path.cwd())
        if not requested_project_name or current_ctx.root.name == requested_project_name:
            return current_ctx, None, "current_project"
    except Exception:
        current_ctx = None

    workspace_hooks = _build_workspace_hooks_payload()
    projects = workspace_hooks.get("projects") or []
    if use_last_project:
        recent_project = _workspace_recent_project_entry(projects)
        if not recent_project:
            return None, workspace_hooks, "missing_recent_workspace_project"
        return ProjectContext.from_root(Path(str(recent_project["project_root"]))), workspace_hooks, "recent_workspace_project"
    if requested_project_name:
        match = next((item for item in projects if str(item.get("project_name") or "") == requested_project_name), None)
        if not match:
            return None, workspace_hooks, "missing_requested_project"
        return ProjectContext.from_root(Path(str(match["project_root"]))), workspace_hooks, "named_workspace_project"
    if projects:
        first = projects[0]
        return ProjectContext.from_root(Path(str(first["project_root"]))), workspace_hooks, "recommended_workspace_project"
    return None, workspace_hooks, "no_workspace_projects"


def _run_workspace_hook_init(
    *,
    hook_name: str,
    project_name: str | None,
    use_recommended_project: bool,
    use_last_project: bool,
    follow_recommended: bool,
    template_kind: str,
    suggest: bool,
    last_suggest: bool,
    open_catalog: bool,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    reuse_last_suggest: bool,
    pick: bool,
    pick_recommended: bool,
    pick_index: int | None,
    dry_run: bool,
    force: bool,
) -> tuple[dict[str, Any], int]:
    if follow_recommended and (
        project_name
        or use_recommended_project
        or use_last_project
        or hook_name
        or suggest
        or last_suggest
        or open_catalog
        or page_key_filter
        or section_key_filter
        or slot_key_filter
        or reuse_last_suggest
        or pick
        or pick_recommended
        or pick_index is not None
    ):
        return (
            {
                "status": "error",
                "entrypoint": "workspace-hook-init",
                "route_taken": "invalid_usage",
                "route_reason": "Workspace hook-init follow-recommended is a one-step shortcut and cannot be mixed with other selection flags.",
                "requested_project_name": (project_name or "").strip() or None,
                "use_recommended_project": bool(use_recommended_project),
                "use_last_project": bool(use_last_project),
                "follow_recommended": True,
                "dry_run": bool(dry_run),
                "message": "Use --follow-recommended by itself, optionally with --force.",
                "next_steps": [
                    "re-run workspace hook-init with only --follow-recommended",
                    "or use the longer workspace hook-init flags explicitly",
                ],
            },
            EXIT_USAGE,
        )

    if follow_recommended:
        use_recommended_project = True
        pick_recommended = True

    if int(bool(project_name)) + int(bool(use_recommended_project)) + int(bool(use_last_project)) > 1:
        return (
            {
                "status": "error",
                "entrypoint": "workspace-hook-init",
                "route_taken": "invalid_usage",
                "route_reason": "Workspace hook-init can target one explicit project selector at a time.",
                "requested_project_name": (project_name or "").strip() or None,
                "use_recommended_project": bool(use_recommended_project),
                "use_last_project": bool(use_last_project),
                "follow_recommended": bool(follow_recommended),
                "dry_run": bool(dry_run),
                "message": "Use only one of --project-name, --use-recommended-project, or --use-last-project.",
                "next_steps": [
                    "re-run workspace hook-init with only --project-name",
                    "or re-run workspace hook-init with only --use-recommended-project",
                    "or re-run workspace hook-init with only --use-last-project",
                ],
            },
            EXIT_USAGE,
        )

    ctx, workspace_hooks, route_taken = _resolve_workspace_hook_init_project(
        None if (use_recommended_project or use_last_project) else project_name,
        use_last_project=use_last_project,
    )
    requested_project_name = (project_name or "").strip() or None
    if use_recommended_project and ctx is not None and route_taken == "recommended_workspace_project":
        route_taken = "recommended_workspace_project_explicit"
    if use_last_project and ctx is not None and route_taken == "recent_workspace_project":
        route_taken = "recent_workspace_project_explicit"

    auto_seeded_recommended_query = False
    auto_seeded_requested_hook_name: str | None = None
    auto_seeded_page_key_filter: str | None = None
    auto_seeded_section_key_filter: str | None = None
    auto_seeded_slot_key_filter: str | None = None
    auto_seeded_from_recent_project_memory = False
    selected_project_name = ctx.root.name if ctx is not None else None

    if ctx is None:
        workspace_hooks = workspace_hooks or _build_workspace_hooks_payload()
        message = (
            f"Unknown workspace project: {requested_project_name}"
            if route_taken == "missing_requested_project"
            else "No generated workspace project with a hook catalog is available yet."
        )
        next_steps = list(workspace_hooks.get("next_steps") or [])
        return (
            {
                "status": "warning",
                "entrypoint": "workspace-hook-init",
                "route_taken": route_taken,
                "route_reason": "Workspace hook-init needs one concrete generated project before it can delegate to project hook-init.",
                "requested_project_name": requested_project_name,
                "use_recommended_project": use_recommended_project,
                "use_last_project": use_last_project,
                "follow_recommended": follow_recommended,
                "dry_run": dry_run,
                "message": message,
                "workspace_hooks": workspace_hooks,
                "next_steps": next_steps,
            },
            EXIT_OK,
        )

    if (
        route_taken in {"named_workspace_project", "recommended_workspace_project", "recommended_workspace_project_explicit", "recent_workspace_project", "recent_workspace_project_explicit"}
        and not hook_name
        and not page_key_filter
        and not section_key_filter
        and not slot_key_filter
        and not reuse_last_suggest
        and not last_suggest
        and not open_catalog
        and (suggest or pick or pick_recommended or pick_index is not None)
    ):
        catalog = _build_hook_catalog_summary(ctx)
        recent_memory = _read_last_hook_suggestions(ctx)
        recent_requested_hook_name = str((recent_memory or {}).get("requested_hook_name") or "").strip()
        recent_page_key = str((recent_memory or {}).get("page_key_filter") or "").strip()
        recent_section_key = str((recent_memory or {}).get("section_key_filter") or "").strip()
        recent_slot_key = str((recent_memory or {}).get("slot_key_filter") or "").strip()
        if recent_memory and int(recent_memory.get("suggestion_count") or 0) > 0 and (
            recent_requested_hook_name or recent_page_key or recent_section_key or recent_slot_key
        ):
            hook_name = recent_requested_hook_name or recent_page_key
            page_key_filter = recent_page_key or None
            section_key_filter = recent_section_key or None
            slot_key_filter = recent_slot_key or None
            auto_seeded_recommended_query = True
            auto_seeded_from_recent_project_memory = True
            auto_seeded_requested_hook_name = (hook_name or "").strip() or None
            auto_seeded_page_key_filter = (page_key_filter or "").strip() or None
            auto_seeded_section_key_filter = (section_key_filter or "").strip() or None
            auto_seeded_slot_key_filter = (slot_key_filter or "").strip() or None
        else:
            default_page_key = str((catalog.get("page_keys") or [""])[0] or "")
            if default_page_key:
                hook_name = default_page_key
                page_key_filter = default_page_key
                auto_seeded_recommended_query = True
                auto_seeded_requested_hook_name = default_page_key
                auto_seeded_page_key_filter = default_page_key

    result_payload, exit_code = _run_project_hook_init(
        ctx,
        hook_name=hook_name,
        template_kind=template_kind,
        suggest=suggest,
        last_suggest=last_suggest,
        open_catalog=open_catalog,
        page_key_filter=page_key_filter,
        section_key_filter=section_key_filter,
        slot_key_filter=slot_key_filter,
        reuse_last_suggest=reuse_last_suggest,
        pick=pick,
        pick_recommended=pick_recommended,
        pick_index=pick_index,
        dry_run=dry_run,
        force=force,
    )
    effective_hook_name = (hook_name or "").strip() or None
    effective_page_key_filter = (page_key_filter or "").strip() or None
    effective_section_key_filter = (section_key_filter or "").strip() or None
    effective_slot_key_filter = (slot_key_filter or "").strip() or None
    recommended_next_command = None
    rerun_without_dry_run_command = None
    if ctx is not None:
        workspace_command_project_name = None if route_taken in {"current_project", "recommended_workspace_project_explicit", "recent_workspace_project_explicit"} else selected_project_name
        workspace_command_use_recommended = (route_taken == "recommended_workspace_project_explicit")
        workspace_command_use_last = (route_taken == "recent_workspace_project_explicit")
        if dry_run and result_payload.get("target_path"):
            if route_taken == "current_project":
                rerun_without_dry_run_command = _build_project_hook_init_command(
                    str(result_payload.get("hook_name") or ""),
                    template_kind=str(result_payload.get("requested_template") or "auto"),
                    force=force,
                )
            else:
                rerun_without_dry_run_command = _build_workspace_hook_init_command(
                    str(result_payload.get("hook_name") or ""),
                    project_name=workspace_command_project_name,
                    use_recommended_project=workspace_command_use_recommended,
                    use_last_project=workspace_command_use_last,
                    follow_recommended=False,
                    force=force,
                )
        if result_payload.get("entrypoint") == "project-hook-suggest" and result_payload.get("recommended_next_command"):
            recommended_next_command = _build_workspace_recommended_next_command(
                requested_hook_name=effective_hook_name or auto_seeded_requested_hook_name or "",
                project_name=workspace_command_project_name,
                use_recommended_project=workspace_command_use_recommended,
                use_last_project=workspace_command_use_last,
                follow_recommended=(route_taken == "recommended_workspace_project_explicit" and auto_seeded_recommended_query and not auto_seeded_from_recent_project_memory),
                page_key_filter=effective_page_key_filter or auto_seeded_page_key_filter,
                section_key_filter=effective_section_key_filter or auto_seeded_section_key_filter,
                slot_key_filter=effective_slot_key_filter or auto_seeded_slot_key_filter,
                reuse_last_suggest=bool(result_payload.get("used_recent_suggestion_memory")),
                dry_run=dry_run,
                force=force,
            )
        elif result_payload.get("entrypoint") == "project-hook-last-suggest" and result_payload.get("recommended_next_command"):
            recommended_next_command = _build_workspace_recommended_next_command(
                requested_hook_name="",
                project_name=workspace_command_project_name,
                use_recommended_project=workspace_command_use_recommended,
                use_last_project=workspace_command_use_last,
                follow_recommended=False,
                page_key_filter=None,
                section_key_filter=None,
                slot_key_filter=None,
                reuse_last_suggest=True,
                dry_run=dry_run,
                force=force,
            )
    route_reason = {
        "current_project": "Current working directory is already inside an initialized AIL project, so workspace hook-init delegates to project hook-init for that project.",
        "named_workspace_project": "Workspace hook-init matched the requested generated project name and delegated there.",
        "recommended_workspace_project": "Workspace hook-init picked the current recommended generated project from workspace hook coverage and delegated there.",
        "recommended_workspace_project_explicit": "Workspace hook-init used the explicit recommended-project path and delegated to the current recommended generated project from workspace hook coverage.",
        "recent_workspace_project": "Workspace hook-init reused the most recent workspace hook project and delegated there.",
        "recent_workspace_project_explicit": "Workspace hook-init used the explicit recent-project path and delegated to the most recent workspace hook project.",
    }.get(route_taken, "Workspace hook-init delegated to one concrete project-level hook-init flow.")
    next_steps = list(result_payload.get("next_steps") or [])
    if ctx is not None and result_payload.get("entrypoint") and not dry_run:
        _write_last_workspace_hook_init(
            project_name=ctx.root.name,
            project_root=str(ctx.root),
            route_taken=route_taken,
            requested_hook_name=effective_hook_name or auto_seeded_requested_hook_name,
            page_key_filter=effective_page_key_filter or auto_seeded_page_key_filter,
            section_key_filter=effective_section_key_filter or auto_seeded_section_key_filter,
            slot_key_filter=effective_slot_key_filter or auto_seeded_slot_key_filter,
        )
    explanation_blocks = [
        {
            "label": "route",
            "summary": route_reason,
            "detail": (
                f"route_taken={route_taken} project={ctx.root.name}"
                + (
                    " auto_seeded_query=true"
                    if auto_seeded_recommended_query
                    else ""
                )
            ),
        },
        {
            "label": "selection",
            "summary": (
                "A recent narrowed hook query was reused."
                if auto_seeded_from_recent_project_memory
                else "One explicit hook query or hook name was delegated to the selected project."
            ),
            "detail": (
                f"hook={effective_hook_name or auto_seeded_requested_hook_name or '-'} "
                f"page={effective_page_key_filter or auto_seeded_page_key_filter or '-'} "
                f"section={effective_section_key_filter or auto_seeded_section_key_filter or '-'} "
                f"slot={effective_slot_key_filter or auto_seeded_slot_key_filter or '-'}"
            ),
        },
        {
            "label": "target",
            "summary": (
                str((result_payload.get("dry_run_summary") or "")).strip()
                or f"Resolved {str(result_payload.get('target_relative_path') or '').strip() or 'one live hook target'} in the selected project."
            ),
            "detail": (
                str((result_payload.get("target_reason") or "")).strip()
                or f"target_path={str(result_payload.get('target_path') or '').strip() or '(unknown)'}"
            ),
        },
        {
            "label": "followup",
            "summary": (
                "The delegated project hook-init confirm command is the shortest next step."
                if rerun_without_dry_run_command
                else "A recommended follow-up command is available from the delegated project hook-init flow."
            ),
            "detail": rerun_without_dry_run_command or recommended_next_command or "",
        },
    ]
    return (
        {
            "status": result_payload.get("status", "ok"),
            "entrypoint": "workspace-hook-init",
            "route_taken": route_taken,
            "route_reason": route_reason,
            "requested_project_name": requested_project_name,
            "use_recommended_project": use_recommended_project,
            "use_last_project": use_last_project,
            "follow_recommended": follow_recommended,
            "dry_run": dry_run,
            "selected_project_name": ctx.root.name,
            "selected_project_root": str(ctx.root),
            "auto_seeded_recommended_query": auto_seeded_recommended_query,
            "auto_seeded_from_recent_project_memory": auto_seeded_from_recent_project_memory,
            "auto_seeded_requested_hook_name": auto_seeded_requested_hook_name,
            "auto_seeded_page_key_filter": auto_seeded_page_key_filter,
            "auto_seeded_section_key_filter": auto_seeded_section_key_filter,
            "auto_seeded_slot_key_filter": auto_seeded_slot_key_filter,
            "recommended_next_command": recommended_next_command,
            "rerun_without_dry_run_command": rerun_without_dry_run_command,
            "workspace_hooks": workspace_hooks,
            "result": result_payload,
            "explanation_blocks": explanation_blocks,
            "message": result_payload.get("message", ""),
            "next_steps": next_steps,
        },
        exit_code,
    )

def _run_workspace_hook_continue(*, force: bool, broaden_to: str | None, dry_run: bool) -> tuple[dict[str, Any], int]:
    workspace_hooks = _build_workspace_hooks_payload()
    if workspace_hooks.get("recent_hook_project"):
        recent_query = _workspace_recent_hook_query_for_project(
            workspace_hooks.get("recent_hook_project"),
            workspace_hooks.get("recent_hook_project_root"),
        )
        base_requested_hook_name = recent_query.get("requested_hook_name") or ""
        base_page_key_filter = recent_query.get("page_key_filter") or None
        base_section_key_filter = recent_query.get("section_key_filter") or None
        base_slot_key_filter = recent_query.get("slot_key_filter") or None

        def _query_for_level(level: str | None) -> tuple[str, str | None, str | None, str | None]:
            requested_hook_name = base_requested_hook_name
            page_key_filter = base_page_key_filter
            section_key_filter = base_section_key_filter
            slot_key_filter = base_slot_key_filter
            if recent_query and level == "section":
                slot_key_filter = None
                requested_hook_name = page_key_filter or requested_hook_name
            elif recent_query and level == "page":
                section_key_filter = None
                slot_key_filter = None
                requested_hook_name = page_key_filter or requested_hook_name
            return requested_hook_name, page_key_filter, section_key_filter, slot_key_filter

        def _attempt_continue(level: str | None) -> tuple[dict[str, Any], int, str, str | None, str | None, str | None]:
            requested_hook_name, page_key_filter, section_key_filter, slot_key_filter = _query_for_level(level)
            payload, exit_code = _run_workspace_hook_init(
                hook_name=requested_hook_name,
                project_name=None,
                use_recommended_project=False,
                use_last_project=True,
                follow_recommended=False,
                template_kind="auto",
                suggest=False,
                last_suggest=False,
                open_catalog=False,
                page_key_filter=page_key_filter,
                section_key_filter=section_key_filter,
                slot_key_filter=slot_key_filter,
                reuse_last_suggest=False,
                pick=False,
                pick_recommended=True,
                pick_index=None,
                dry_run=dry_run,
                force=force,
            )
            return payload, exit_code, requested_hook_name, page_key_filter, section_key_filter, slot_key_filter

        attempted_levels: list[str] = []
        auto_broaden_attempted = False
        auto_broaden_resolved_to = "exact"
        fallback_reason = ""

        if recent_query and broaden_to == "auto":
            attempt_plan = ["exact", "section", "page"]
        elif broaden_to in {"section", "page"}:
            attempt_plan = [broaden_to]
        else:
            attempt_plan = ["exact"]

        payload: dict[str, Any] = {}
        exit_code = EXIT_OK
        requested_hook_name = ""
        page_key_filter = None
        section_key_filter = None
        slot_key_filter = None
        for index, level in enumerate(attempt_plan):
            attempted_levels.append(level)
            payload, exit_code, requested_hook_name, page_key_filter, section_key_filter, slot_key_filter = _attempt_continue(None if level == "exact" else level)
            if payload.get("status") == "ok":
                auto_broaden_resolved_to = level
                if broaden_to == "auto" and index > 0:
                    auto_broaden_attempted = True
                break
            if broaden_to == "auto" and level != attempt_plan[-1]:
                auto_broaden_attempted = True
                fallback_reason = str(payload.get("message") or payload.get("continue_reason") or payload.get("route_reason") or "")

        payload = dict(payload)
        payload["entrypoint"] = "workspace-hook-continue"
        payload["continue_strategy"] = "recent_workspace_project"
        payload["continue_summary"] = "Continued from the most recent workspace hook project and reused its last narrowed hook query when available."
        payload["continue_reason"] = "Reused the most recent workspace hook project and continued from its most recent narrowed hook query when available."
        payload["dry_run"] = dry_run
        payload["used_workspace_recent_query_memory"] = bool(recent_query)
        payload["broaden_to"] = broaden_to
        payload["broadened_recent_query"] = auto_broaden_resolved_to in {"section", "page"}
        payload["auto_broaden_attempted"] = auto_broaden_attempted
        payload["auto_broaden_resolved_to"] = auto_broaden_resolved_to
        payload["auto_broaden_attempts"] = attempted_levels
        payload["auto_broaden_fallback_reason"] = fallback_reason or None
        payload["continued_requested_hook_name"] = requested_hook_name or None
        payload["continued_page_key_filter"] = page_key_filter
        payload["continued_section_key_filter"] = section_key_filter
        payload["continued_slot_key_filter"] = slot_key_filter
        payload["selected_strategy_command"] = _build_workspace_hook_init_command(
            requested_hook_name=requested_hook_name,
            use_last_project=True,
            page_key_filter=page_key_filter,
            section_key_filter=section_key_filter,
            slot_key_filter=slot_key_filter,
            pick_recommended=True,
            dry_run=dry_run,
            force=force,
        )
        payload["alternate_strategy_command"] = _build_workspace_hook_init_command(
            follow_recommended=True,
            dry_run=dry_run,
            force=force,
        )
        payload["resume_exact_command"] = _build_workspace_hook_continue_command(force=force, dry_run=dry_run)
        payload["broaden_to_section_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="section", dry_run=dry_run)
        payload["broaden_to_page_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="page", dry_run=dry_run)
        payload["auto_broaden_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="auto", dry_run=dry_run)
        if broaden_to == "auto":
            payload["preferred_followup_command"] = payload["auto_broaden_command"]
            payload["preferred_followup_reason"] = "Keep using auto-broaden when you want the repo-root continue flow to retry the remembered surface first and widen only when needed."
        elif auto_broaden_resolved_to == "page":
            payload["preferred_followup_command"] = payload["broaden_to_page_command"]
            payload["preferred_followup_reason"] = "This run already resolved to page scope, so staying at page scope is the most consistent next continue path."
        elif auto_broaden_resolved_to == "section":
            payload["preferred_followup_command"] = payload["broaden_to_section_command"]
            payload["preferred_followup_reason"] = "This run resolved to section scope, so continuing at section scope is the most consistent next follow-up."
        else:
            payload["preferred_followup_command"] = payload["resume_exact_command"]
            payload["preferred_followup_reason"] = "The remembered surface still worked as-is, so resuming the exact continue path is the shortest next step."
        payload["rerun_with_force_command"] = _build_workspace_hook_continue_command(force=True, dry_run=dry_run)
        payload["rerun_without_dry_run_command"] = (
            _build_workspace_hook_continue_command(force=force, broaden_to=broaden_to)
            if dry_run
            else ""
        )
        target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
        payload["recommended_next_command"] = (
            payload.get("recommended_next_command")
            or (payload.get("result") or {}).get("recommended_next_command")
            or (f"inspect {target_path}" if target_path else "")
        )
        if dry_run:
            hook_name = str(((payload.get("result") or {}).get("hook_name") or "")).strip()
            template = str(((payload.get("result") or {}).get("template") or "")).strip()
            target_name = Path(target_path).name if target_path else ""
            scope_label = auto_broaden_resolved_to if auto_broaden_resolved_to in {"section", "page"} else "exact"
            payload["dry_run_summary"] = (
                f"Would continue at {scope_label} scope and prepare {target_name or 'the next live hook file'}."
            )
            payload["dry_run_target_reason"] = (
                f"The continue flow resolved to hook {hook_name} using template {template or 'auto'}."
                if hook_name
                else "The continue flow resolved the next live hook target from the current workspace memory."
            )
            payload["dry_run_confirm_command"] = payload["rerun_without_dry_run_command"] or payload["selected_strategy_command"]
        payload["next_steps"] = list(payload.get("next_steps") or [])
        payload["next_steps"].extend(
            [
                f"run {payload['selected_strategy_command']}",
                f"run {payload['alternate_strategy_command']}",
                f"run {payload['resume_exact_command']}",
                f"run {payload['broaden_to_section_command']}",
                f"run {payload['broaden_to_page_command']}",
                f"run {payload['auto_broaden_command']}",
                f"run {payload['rerun_with_force_command']}",
            ]
        )
        if payload["rerun_without_dry_run_command"]:
            payload["next_steps"].append(f"run {payload['rerun_without_dry_run_command']}")
        payload["explanation_blocks"] = [
            {
                "label": "strategy",
                "summary": payload["continue_summary"],
                "detail": payload["continue_reason"],
            },
            {
                "label": "memory",
                "summary": (
                    "Recent workspace hook memory was reused."
                    if payload.get("used_workspace_recent_query_memory")
                    else "No recent workspace hook memory was reused."
                ),
                "detail": (
                    f"page={payload.get('continued_page_key_filter') or '-'} "
                    f"section={payload.get('continued_section_key_filter') or '-'} "
                    f"slot={payload.get('continued_slot_key_filter') or '-'}"
                    if payload.get("used_workspace_recent_query_memory")
                    else "The continue flow did not have a recent narrowed page/section/slot surface to reuse."
                ),
            },
            {
                "label": "resolution",
                "summary": (
                    f"Continue scope resolved to {payload.get('auto_broaden_resolved_to') or 'exact'}."
                ),
                "detail": (
                    f"Attempts: {', '.join(payload.get('auto_broaden_attempts') or [])}"
                    if payload.get("auto_broaden_attempts")
                    else "The continue flow used one direct path without fallback."
                ),
            },
            {
                "label": "target",
                "summary": payload.get("dry_run_summary")
                or "The continue flow resolved the next live hook target.",
                "detail": payload.get("dry_run_target_reason")
                or f"Target path: {str(((payload.get('result') or {}).get('target_path') or '')).strip() or '(unknown)'}",
            },
            {
                "label": "followup",
                "summary": payload.get("preferred_followup_reason")
                or "One follow-up command was selected as the preferred next step.",
                "detail": payload.get("preferred_followup_command")
                or payload.get("recommended_next_command")
                or "",
            },
        ]
        return payload, exit_code

    payload, exit_code = _run_workspace_hook_init(
        hook_name="",
        project_name=None,
        use_recommended_project=False,
        use_last_project=False,
        follow_recommended=True,
        template_kind="auto",
        suggest=False,
        last_suggest=False,
        open_catalog=False,
        page_key_filter=None,
        section_key_filter=None,
        slot_key_filter=None,
        reuse_last_suggest=False,
        pick=False,
        pick_recommended=False,
        pick_index=None,
        dry_run=dry_run,
        force=force,
    )
    payload = dict(payload)
    payload["entrypoint"] = "workspace-hook-continue"
    payload["continue_strategy"] = "recommended_workspace_project"
    payload["continue_summary"] = "No recent workspace hook project was available, so the flow continued from the current recommended workspace hook path."
    payload["continue_reason"] = "No recent workspace hook project was available, so the flow fell back to the current recommended one-step workspace hook path."
    payload["dry_run"] = dry_run
    payload["used_workspace_recent_query_memory"] = False
    payload["broaden_to"] = broaden_to
    payload["broadened_recent_query"] = False
    payload["continued_requested_hook_name"] = None
    payload["continued_page_key_filter"] = None
    payload["continued_section_key_filter"] = None
    payload["continued_slot_key_filter"] = None
    payload["selected_strategy_command"] = _build_workspace_hook_init_command(
        follow_recommended=True,
        dry_run=dry_run,
        force=force,
    )
    payload["alternate_strategy_command"] = ""
    payload["resume_exact_command"] = _build_workspace_hook_continue_command(force=force, dry_run=dry_run)
    payload["broaden_to_section_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="section", dry_run=dry_run)
    payload["broaden_to_page_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="page", dry_run=dry_run)
    payload["auto_broaden_command"] = _build_workspace_hook_continue_command(force=force, broaden_to="auto", dry_run=dry_run)
    payload["preferred_followup_command"] = payload["resume_exact_command"]
    payload["preferred_followup_reason"] = "No recent workspace hook memory was available, so the shortest repeatable continue path is still the default repo-root continue command."
    payload["rerun_with_force_command"] = _build_workspace_hook_continue_command(force=True, dry_run=dry_run)
    payload["rerun_without_dry_run_command"] = (
        _build_workspace_hook_continue_command(force=force, broaden_to=broaden_to)
        if dry_run
        else ""
    )
    target_path = str(((payload.get("result") or {}).get("target_path") or "")).strip()
    payload["recommended_next_command"] = (
        payload.get("recommended_next_command")
        or (payload.get("result") or {}).get("recommended_next_command")
        or (f"inspect {target_path}" if target_path else "")
    )
    if dry_run:
        hook_name = str(((payload.get("result") or {}).get("hook_name") or "")).strip()
        template = str(((payload.get("result") or {}).get("template") or "")).strip()
        target_name = Path(target_path).name if target_path else ""
        payload["dry_run_summary"] = (
            f"Would continue from the recommended workspace path and prepare {target_name or 'the next live hook file'}."
        )
        payload["dry_run_target_reason"] = (
            f"The fallback path resolved to hook {hook_name} using template {template or 'auto'}."
            if hook_name
            else "The fallback path resolved the next live hook target from the current recommended workspace project."
        )
        payload["dry_run_confirm_command"] = payload["rerun_without_dry_run_command"] or payload["selected_strategy_command"]
    payload["next_steps"] = list(payload.get("next_steps") or [])
    payload["next_steps"].extend(
        [
            f"run {payload['selected_strategy_command']}",
            f"run {payload['resume_exact_command']}",
            f"run {payload['broaden_to_section_command']}",
            f"run {payload['broaden_to_page_command']}",
            f"run {payload['auto_broaden_command']}",
            f"run {payload['rerun_with_force_command']}",
        ]
    )
    if payload["rerun_without_dry_run_command"]:
        payload["next_steps"].append(f"run {payload['rerun_without_dry_run_command']}")
    payload["explanation_blocks"] = [
        {
            "label": "strategy",
            "summary": payload["continue_summary"],
            "detail": payload["continue_reason"],
        },
        {
            "label": "memory",
            "summary": "No recent workspace hook memory was reused.",
            "detail": "The continue flow fell back to the recommended workspace project because no recent project memory was available.",
        },
        {
            "label": "resolution",
            "summary": "Continue scope resolved through the recommended workspace path.",
            "detail": "No recent narrowed surface was available, so the flow used the recommended one-step workspace path.",
        },
        {
            "label": "target",
            "summary": payload.get("dry_run_summary")
            or "The recommended workspace path resolved the next live hook target.",
            "detail": payload.get("dry_run_target_reason")
            or f"Target path: {str(((payload.get('result') or {}).get('target_path') or '')).strip() or '(unknown)'}",
        },
        {
            "label": "followup",
            "summary": payload.get("preferred_followup_reason")
            or "One follow-up command was selected as the preferred next step.",
            "detail": payload.get("preferred_followup_command")
            or payload.get("recommended_next_command")
            or "",
        },
    ]
    return payload, exit_code


def _project_hook_examples_dir(ctx: ProjectContext) -> Path:
    return ctx.root / "frontend" / "src" / "ail-overrides" / "components" / "examples"


def _project_hook_components_dir(ctx: ProjectContext) -> Path:
    return ctx.root / "frontend" / "src" / "ail-overrides" / "components"


def _collect_known_hook_names(catalog: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for page in catalog.get("pages") or []:
        for hook_name in page.get("page_hooks") or []:
            if hook_name:
                names.add(str(hook_name))
        for section in page.get("section_hooks") or []:
            for hook_name in section.get("hooks") or []:
                if hook_name:
                    names.add(str(hook_name))
        for slot in page.get("slot_hooks") or []:
            for hook_name in slot.get("hooks") or []:
                if hook_name:
                    names.add(str(hook_name))
    return names


def _collect_hook_name_records(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page in catalog.get("pages") or []:
        page_key = str(page.get("page_key") or "")
        page_name = str(page.get("page_name") or "")
        page_path = str(page.get("page_path") or "")
        for hook_name in page.get("page_hooks") or []:
            records.append(
                {
                    "hook_name": str(hook_name),
                    "scope": "page",
                    "page_key": page_key,
                    "page_name": page_name,
                    "page_path": page_path,
                    "section_key": "",
                    "slot_key": "",
                }
            )
        for section in page.get("section_hooks") or []:
            section_key = str(section.get("sectionKey") or section.get("section_key") or "")
            for hook_name in section.get("hooks") or []:
                records.append(
                    {
                        "hook_name": str(hook_name),
                        "scope": "section",
                        "page_key": page_key,
                        "page_name": page_name,
                        "page_path": page_path,
                        "section_key": section_key,
                        "slot_key": "",
                    }
                )
        for slot in page.get("slot_hooks") or []:
            section_key = str(slot.get("sectionKey") or slot.get("section_key") or "")
            slot_key = str(slot.get("slotKey") or slot.get("slot_key") or "")
            for hook_name in slot.get("hooks") or []:
                records.append(
                    {
                        "hook_name": str(hook_name),
                        "scope": "slot",
                        "page_key": page_key,
                        "page_name": page_name,
                        "page_path": page_path,
                        "section_key": section_key,
                        "slot_key": slot_key,
                    }
                )
    return records


def _suggest_hook_records(
    catalog: dict[str, Any],
    query: str,
    *,
    page_key_filter: str | None = None,
    section_key_filter: str | None = None,
    slot_key_filter: str | None = None,
) -> list[dict[str, Any]]:
    records = _collect_hook_name_records(catalog)
    normalized_page_key = (page_key_filter or "").strip().lower()
    normalized_section_key = (section_key_filter or "").strip().lower()
    normalized_slot_key = (slot_key_filter or "").strip().lower()
    if normalized_page_key:
        records = [item for item in records if str(item.get("page_key") or "").lower() == normalized_page_key]
    if normalized_section_key:
        records = [item for item in records if str(item.get("section_key") or "").lower() == normalized_section_key]
    if normalized_slot_key:
        records = [item for item in records if str(item.get("slot_key") or "").lower() == normalized_slot_key]
    normalized_query = _normalize_project_hook_name(query).lower() if query else ""
    raw_query = (query or "").strip().lower()

    def _score(item: dict[str, Any]) -> tuple[int, int, int, str]:
        hook_name = str(item.get("hook_name") or "")
        haystack = " ".join(
            [
                hook_name.lower(),
                str(item.get("page_key") or "").lower(),
                str(item.get("section_key") or "").lower(),
                str(item.get("slot_key") or "").lower(),
            ]
        )
        if not raw_query:
            base = 0
        elif hook_name.lower() == normalized_query or hook_name.lower() == raw_query:
            base = 0
        elif hook_name.lower().startswith(normalized_query) or hook_name.lower().startswith(raw_query):
            base = 1
        elif normalized_query and normalized_query in haystack:
            base = 2
        elif raw_query and raw_query in haystack:
            base = 3
        else:
            base = 9
        scope_rank = {"page": 0, "section": 1, "slot": 2}.get(str(item.get("scope") or ""), 9)
        return (base, scope_rank, len(hook_name), hook_name)

    filtered = [item for item in records if _score(item)[0] < 9]
    if not raw_query:
        filtered = records
    filtered.sort(key=_score)
    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in filtered:
        hook_name = str(item.get("hook_name") or "")
        if hook_name in seen:
            continue
        seen.add(hook_name)
        enriched = dict(item)
        enriched["suggestion_index"] = len(suggestions) + 1
        enriched["default_template"] = _resolve_project_hook_template(hook_name, "auto")
        suggestions.append(enriched)
        if len(suggestions) >= 16:
            break
    return suggestions


def _project_hook_example_source(ctx: ProjectContext, template_kind: str) -> Path:
    examples_dir = _project_hook_examples_dir(ctx)
    filename = (
        "page.home.before.example.vue"
        if template_kind == "vue"
        else "page.home.section.hero.after.example.html"
    )
    return examples_dir / filename


def _write_live_project_hook(
    ctx: ProjectContext,
    *,
    requested_hook_name: str,
    normalized_hook_name: str,
    template_kind: str,
    force: bool,
    catalog: dict[str, Any],
    selected_from_suggestions: bool = False,
    used_recent_suggestion_memory: bool = False,
    reuse_last_suggest: bool = False,
    dry_run: bool = False,
) -> tuple[dict[str, Any], int]:
    resolved_template_kind = _resolve_project_hook_template(normalized_hook_name, template_kind)
    source_example_path = _project_hook_example_source(ctx, resolved_template_kind)
    components_dir = _project_hook_components_dir(ctx)
    target_path = components_dir / f"{normalized_hook_name}.{resolved_template_kind}"
    target_relative_path = str(target_path.relative_to(ctx.root))
    confirm_command = _build_project_hook_init_command(
        normalized_hook_name,
        template_kind=template_kind,
        dry_run=False,
        force=force,
    )
    next_steps = [f"inspect {target_path}"]

    def _project_hook_init_explanation_blocks(*, wrote: bool) -> list[dict[str, str]]:
        selection_summary = (
            "The scaffold path came from a suggested hook selection."
            if selected_from_suggestions
            else "The scaffold path came from one exact hook name."
        )
        selection_detail = (
            f"requested={requested_hook_name or normalized_hook_name} normalized={normalized_hook_name}"
        )
        if used_recent_suggestion_memory:
            selection_detail += " recent_suggestion_memory=reused"
        elif reuse_last_suggest:
            selection_detail += " recent_suggestion_memory=requested"
        target_summary = (
            f"Scaffolded {target_relative_path} from the {resolved_template_kind} starter example."
            if wrote
            else f"Would scaffold {target_relative_path} from the {resolved_template_kind} starter example."
        )
        followup_detail = confirm_command if not wrote else f"inspect {target_path}"
        followup_summary = (
            "Re-run without --dry-run to write the live hook file."
            if not wrote
            else "Open or edit the copied live hook file next."
        )
        return [
            {
                "label": "selection",
                "summary": selection_summary,
                "detail": selection_detail,
            },
            {
                "label": "template",
                "summary": f"Template kind resolved to {resolved_template_kind}.",
                "detail": f"requested_template={template_kind} source_example={source_example_path.name}",
            },
            {
                "label": "target",
                "summary": target_summary,
                "detail": f"Hook name resolves to {target_relative_path} and template auto-selection resolved to {resolved_template_kind}.",
            },
            {
                "label": "followup",
                "summary": followup_summary,
                "detail": followup_detail,
            },
        ]

    if not source_example_path.exists():
        return (
            {
                "status": "error",
                "entrypoint": "project-hook-init",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_hook_name": requested_hook_name,
                "hook_name": normalized_hook_name,
                "requested_template": template_kind,
                "template": resolved_template_kind,
                "target_path": str(target_path),
                "target_relative_path": target_relative_path,
                "source_example_path": str(source_example_path),
                "message": "No starter example exists yet for this project. Rebuild the frontend override scaffold first.",
                "next_steps": [
                    "rebuild the project so frontend/src/ail-overrides/components/examples is scaffolded",
                    f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                ],
            },
            EXIT_VALIDATION,
        )

    known_hook_names = _collect_known_hook_names(catalog)
    hook_catalog_verified = False
    hook_catalog_warning = ""
    if catalog["exists"]:
        hook_catalog_verified = normalized_hook_name in known_hook_names
        if not hook_catalog_verified:
            return (
                {
                    "status": "error",
                    "entrypoint": "project-hook-init",
                    "project_id": ctx.project_id,
                    "project_root": str(ctx.root),
                    "requested_hook_name": requested_hook_name,
                    "hook_name": normalized_hook_name,
                    "requested_template": template_kind,
                    "template": resolved_template_kind,
                    "target_path": str(target_path),
                    "target_relative_path": target_relative_path,
                    "source_example_path": str(source_example_path),
                    "available_page_keys": catalog.get("page_keys") or [],
                    "message": f"Unknown hook name: {normalized_hook_name}",
                    "next_steps": [
                        f"inspect {catalog['markdown_path']}",
                        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                    ],
                },
                EXIT_VALIDATION,
            )
    else:
        hook_catalog_warning = "No generated hook catalog was found, so the helper copied the starter file without verifying the hook name."
        next_steps.insert(0, "rebuild the project later to emit /.ail/hook_catalog.md and verify hook names")

    if target_path.exists() and not force:
        return (
            {
                "status": "error",
                "entrypoint": "project-hook-init",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_hook_name": requested_hook_name,
                "hook_name": normalized_hook_name,
                "requested_template": template_kind,
                "template": resolved_template_kind,
                "target_path": str(target_path),
                "target_relative_path": target_relative_path,
                "source_example_path": str(source_example_path),
                "selected_from_suggestions": selected_from_suggestions,
                "used_recent_suggestion_memory": used_recent_suggestion_memory,
                "reuse_last_suggest": reuse_last_suggest,
                "dry_run": dry_run,
                "dry_run_summary": f"Would scaffold {target_relative_path} from the {resolved_template_kind} starter example.",
                "target_reason": f"Hook name resolves to {target_relative_path} and template auto-selection resolved to {resolved_template_kind}.",
                "rerun_without_dry_run_command": confirm_command,
                "would_overwrite": True,
                "explanation_blocks": _project_hook_init_explanation_blocks(wrote=False),
                "message": "Target hook file already exists. Re-run with --force to overwrite it.",
                "next_steps": next_steps,
            },
            EXIT_VALIDATION,
        )

    overwritten = target_path.exists()
    if dry_run:
        next_steps.extend(
            [
                "re-run without --dry-run to scaffold the live hook file",
                f"inspect {source_example_path}",
            ]
        )
        payload = {
            "status": "ok",
            "entrypoint": "project-hook-init",
            "project_id": ctx.project_id,
            "project_root": str(ctx.root),
            "requested_hook_name": requested_hook_name,
            "hook_name": normalized_hook_name,
            "requested_template": template_kind,
            "template": resolved_template_kind,
            "target_path": str(target_path),
            "target_relative_path": target_relative_path,
            "source_example_path": str(source_example_path),
            "hook_catalog_verified": hook_catalog_verified,
            "hook_catalog_warning": hook_catalog_warning,
            "selected_from_suggestions": selected_from_suggestions,
            "used_recent_suggestion_memory": used_recent_suggestion_memory,
            "reuse_last_suggest": reuse_last_suggest,
            "dry_run": True,
            "wrote": False,
            "would_write": True,
            "overwritten": False,
            "would_overwrite": overwritten,
            "dry_run_summary": f"Would scaffold {target_relative_path} from the {resolved_template_kind} starter example.",
            "target_reason": f"Hook name resolves to {target_relative_path} and template auto-selection resolved to {resolved_template_kind}.",
            "rerun_without_dry_run_command": confirm_command,
            "message": "Dry run only. No hook file was written.",
            "next_steps": next_steps,
            "explanation_blocks": _project_hook_init_explanation_blocks(wrote=False),
        }
        return payload, EXIT_OK

    components_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_example_path, target_path)
    next_steps.extend(
        [
            "edit the copied hook file and replace the starter text",
            "run your frontend build or refresh your preview to see the override",
        ]
    )
    payload = {
        "status": "ok",
        "entrypoint": "project-hook-init",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "requested_hook_name": requested_hook_name,
        "hook_name": normalized_hook_name,
        "requested_template": template_kind,
        "template": resolved_template_kind,
        "target_path": str(target_path),
        "target_relative_path": target_relative_path,
        "source_example_path": str(source_example_path),
        "hook_catalog_verified": hook_catalog_verified,
        "hook_catalog_warning": hook_catalog_warning,
        "selected_from_suggestions": selected_from_suggestions,
        "used_recent_suggestion_memory": used_recent_suggestion_memory,
        "reuse_last_suggest": reuse_last_suggest,
        "dry_run": False,
        "wrote": True,
        "would_write": True,
        "overwritten": overwritten,
        "would_overwrite": overwritten,
        "next_steps": next_steps,
        "explanation_blocks": _project_hook_init_explanation_blocks(wrote=True),
    }
    return payload, EXIT_OK


def _normalize_project_hook_name(hook_name: str) -> str:
    normalized = (hook_name or "").strip()
    if normalized and not normalized.startswith("page."):
        normalized = f"page.{normalized}"
    return normalized


def _resolve_project_hook_template(hook_name: str, requested_template: str) -> str:
    if requested_template in {"vue", "html"}:
        return requested_template
    if ".section." in hook_name and hook_name.endswith(".after"):
        return "html"
    return "vue"


def _build_project_hook_pick_index_command(
    requested_hook_name: str,
    *,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    pick_index: int,
    force: bool = False,
) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli project hook-init",
        shlex.quote(requested_hook_name or ""),
        "--suggest",
    ]
    if page_key_filter:
        parts.extend(["--page-key", shlex.quote(page_key_filter)])
    if section_key_filter:
        parts.extend(["--section-key", shlex.quote(section_key_filter)])
    if slot_key_filter:
        parts.extend(["--slot-key", shlex.quote(slot_key_filter)])
    parts.extend(["--pick-index", str(pick_index)])
    if force:
        parts.append("--force")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_project_hook_init_command(
    requested_hook_name: str,
    *,
    template_kind: str = "auto",
    suggest: bool = False,
    page_key_filter: str | None = None,
    section_key_filter: str | None = None,
    slot_key_filter: str | None = None,
    reuse_last_suggest: bool = False,
    pick: bool = False,
    pick_recommended: bool = False,
    pick_index: int | None = None,
    open_catalog: bool = False,
    last_suggest: bool = False,
    dry_run: bool = False,
    run_command: bool = False,
    run_open_command: bool = False,
    yes: bool = False,
    force: bool = False,
) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli project hook-init",
    ]
    if requested_hook_name:
        parts.append(shlex.quote(requested_hook_name))
    if template_kind and template_kind != "auto":
        parts.extend(["--template", shlex.quote(template_kind)])
    if suggest:
        parts.append("--suggest")
    if page_key_filter:
        parts.extend(["--page-key", shlex.quote(page_key_filter)])
    if section_key_filter:
        parts.extend(["--section-key", shlex.quote(section_key_filter)])
    if slot_key_filter:
        parts.extend(["--slot-key", shlex.quote(slot_key_filter)])
    if reuse_last_suggest:
        parts.append("--reuse-last-suggest")
    if pick:
        parts.append("--pick")
    if pick_recommended:
        parts.append("--pick-recommended")
    if pick_index is not None:
        parts.extend(["--pick-index", str(pick_index)])
    if open_catalog:
        parts.append("--open-catalog")
    if last_suggest:
        parts.append("--last-suggest")
    if dry_run:
        parts.append("--dry-run")
    if run_command:
        parts.append("--run-command")
    if run_open_command:
        parts.append("--run-open-command")
    if yes:
        parts.append("--yes")
    if force:
        parts.append("--force")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_project_hook_pick_recommended_command(
    requested_hook_name: str,
    *,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    reuse_last_suggest: bool = False,
    force: bool = False,
) -> str:
    return _build_project_hook_init_command(
        requested_hook_name if not reuse_last_suggest else "",
        suggest=not reuse_last_suggest,
        page_key_filter=page_key_filter if not reuse_last_suggest else None,
        section_key_filter=section_key_filter if not reuse_last_suggest else None,
        slot_key_filter=slot_key_filter if not reuse_last_suggest else None,
        reuse_last_suggest=reuse_last_suggest,
        pick_recommended=True,
        force=force,
    )


def _build_project_hook_suggest_command(
    requested_hook_name: str,
    *,
    page_key_filter: str | None = None,
    section_key_filter: str | None = None,
    slot_key_filter: str | None = None,
) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli project hook-init",
        shlex.quote(requested_hook_name or ""),
        "--suggest",
    ]
    if page_key_filter:
        parts.extend(["--page-key", shlex.quote(page_key_filter)])
    if section_key_filter:
        parts.extend(["--section-key", shlex.quote(section_key_filter)])
    if slot_key_filter:
        parts.extend(["--slot-key", shlex.quote(slot_key_filter)])
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_workspace_hook_init_command(
    requested_hook_name: str = "",
    *,
    project_name: str | None = None,
    use_recommended_project: bool = False,
    use_last_project: bool = False,
    follow_recommended: bool = False,
    suggest: bool = False,
    page_key_filter: str | None = None,
    section_key_filter: str | None = None,
    slot_key_filter: str | None = None,
    reuse_last_suggest: bool = False,
    pick: bool = False,
    pick_recommended: bool = False,
    pick_index: int | None = None,
    open_catalog: bool = False,
    last_suggest: bool = False,
    dry_run: bool = False,
    run_command: bool = False,
    run_open_command: bool = False,
    yes: bool = False,
    force: bool = False,
) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli workspace hook-init",
    ]
    if follow_recommended:
        parts.append("--follow-recommended")
        if force:
            parts.append("--force")
        parts.append("--json")
        return " ".join(part for part in parts if part)
    if project_name:
        parts.extend(["--project-name", shlex.quote(project_name)])
    elif use_recommended_project:
        parts.append("--use-recommended-project")
    elif use_last_project:
        parts.append("--use-last-project")
    if requested_hook_name:
        parts.append(shlex.quote(requested_hook_name))
    if suggest:
        parts.append("--suggest")
    if page_key_filter:
        parts.extend(["--page-key", shlex.quote(page_key_filter)])
    if section_key_filter:
        parts.extend(["--section-key", shlex.quote(section_key_filter)])
    if slot_key_filter:
        parts.extend(["--slot-key", shlex.quote(slot_key_filter)])
    if reuse_last_suggest:
        parts.append("--reuse-last-suggest")
    if pick:
        parts.append("--pick")
    if pick_recommended:
        parts.append("--pick-recommended")
    if pick_index is not None:
        parts.extend(["--pick-index", str(pick_index)])
    if open_catalog:
        parts.append("--open-catalog")
    if last_suggest:
        parts.append("--last-suggest")
    if dry_run:
        parts.append("--dry-run")
    if run_command:
        parts.append("--run-command")
    if run_open_command:
        parts.append("--run-open-command")
    if yes:
        parts.append("--yes")
    if force:
        parts.append("--force")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_project_hook_init_run_open_command(
    requested_hook_name: str,
    *,
    template_kind: str = "auto",
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> str:
    return _build_project_hook_init_command(
        requested_hook_name,
        template_kind=template_kind,
        dry_run=dry_run,
        run_open_command=True,
        force=force,
        yes=yes,
    )


def _build_project_hook_init_run_command(
    requested_hook_name: str,
    *,
    template_kind: str = "auto",
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> str:
    return _build_project_hook_init_command(
        requested_hook_name,
        template_kind=template_kind,
        dry_run=dry_run,
        run_command=True,
        force=force,
        yes=yes,
    )


def _build_workspace_hook_init_run_open_command(
    requested_hook_name: str = "",
    *,
    project_name: str | None = None,
    use_recommended_project: bool = False,
    use_last_project: bool = False,
    follow_recommended: bool = False,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> str:
    return _build_workspace_hook_init_command(
        requested_hook_name,
        project_name=project_name,
        use_recommended_project=use_recommended_project,
        use_last_project=use_last_project,
        follow_recommended=follow_recommended,
        dry_run=dry_run,
        run_open_command=True,
        force=force,
        yes=yes,
    )


def _build_workspace_hook_init_run_command(
    requested_hook_name: str = "",
    *,
    project_name: str | None = None,
    use_recommended_project: bool = False,
    use_last_project: bool = False,
    follow_recommended: bool = False,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> str:
    return _build_workspace_hook_init_command(
        requested_hook_name,
        project_name=project_name,
        use_recommended_project=use_recommended_project,
        use_last_project=use_last_project,
        follow_recommended=follow_recommended,
        dry_run=dry_run,
        run_command=True,
        force=force,
        yes=yes,
    )


def _build_workspace_hook_continue_command(*, force: bool = False, broaden_to: str | None = None, dry_run: bool = False) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli workspace hook-continue",
    ]
    if broaden_to:
        parts.extend(["--broaden-to", shlex.quote(broaden_to)])
    if dry_run:
        parts.append("--dry-run")
    if force:
        parts.append("--force")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_workspace_hook_continue_run_command(*, force: bool = False, broaden_to: str | None = None, dry_run: bool = False, yes: bool = False) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli workspace hook-continue",
    ]
    if broaden_to:
        parts.extend(["--broaden-to", shlex.quote(broaden_to)])
    if dry_run:
        parts.append("--dry-run")
    parts.append("--run-command")
    if yes:
        parts.append("--yes")
    if force:
        parts.append("--force")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _build_workspace_hook_continue_run_open_command(*, force: bool = False, broaden_to: str | None = None, dry_run: bool = False, yes: bool = False) -> str:
    parts = [
        f"PYTHONPATH={REPO_ROOT_STR}",
        "python3 -m cli workspace hook-continue",
    ]
    if broaden_to:
        parts.extend(["--broaden-to", shlex.quote(broaden_to)])
    if dry_run:
        parts.append("--dry-run")
    if force:
        parts.append("--force")
    parts.append("--run-open-command")
    if yes:
        parts.append("--yes")
    parts.append("--json")
    return " ".join(part for part in parts if part)


def _copy_text_to_clipboard(text: str) -> tuple[bool, str]:
    try:
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            check=True,
        )
        return True, ""
    except FileNotFoundError:
        return False, "Clipboard helper pbcopy is not available in this environment."
    except subprocess.CalledProcessError as exc:
        return False, f"pbcopy exited with status {exc.returncode}."


def _run_shell_command(command: str) -> tuple[bool, str, str, int, dict[str, Any] | None]:
    if not command.strip():
        return False, "", "No next command was available to run.", EXIT_USAGE, None
    completed = subprocess.run(
        ["/bin/zsh", "-lc", command],
        text=True,
        capture_output=True,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    parsed_json = None
    stripped = stdout.strip()
    if stripped:
        try:
            parsed_json = json.loads(stripped)
        except Exception:
            parsed_json = None
    return completed.returncode == 0, stdout, stderr, completed.returncode, parsed_json


def _build_workspace_recommended_next_command(
    *,
    requested_hook_name: str,
    project_name: str | None,
    use_recommended_project: bool,
    use_last_project: bool,
    follow_recommended: bool,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    reuse_last_suggest: bool,
    dry_run: bool,
    force: bool,
) -> str:
    return _build_workspace_hook_init_command(
        requested_hook_name,
        project_name=project_name,
        use_recommended_project=use_recommended_project,
        use_last_project=use_last_project,
        follow_recommended=follow_recommended,
        suggest=not reuse_last_suggest,
        page_key_filter=page_key_filter if not reuse_last_suggest else None,
        section_key_filter=section_key_filter if not reuse_last_suggest else None,
        slot_key_filter=slot_key_filter if not reuse_last_suggest else None,
        reuse_last_suggest=reuse_last_suggest,
        pick_recommended=True,
        dry_run=dry_run,
        force=force,
    )


def _recommended_pick_index_command(suggestions: Sequence[dict[str, Any]]) -> str | None:
    if len(suggestions) <= 1:
        return None
    first_command = suggestions[0].get("pick_index_command")
    return str(first_command) if first_command else None


def _resolve_recent_hook_suggestion_query(
    ctx: ProjectContext,
    *,
    requested_hook_name: str,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    reuse_last_suggest: bool,
    pick: bool,
    pick_recommended: bool,
    pick_index: int | None,
) -> tuple[str, str | None, str | None, str | None, bool, dict[str, Any] | None]:
    memory = _read_last_hook_suggestions(ctx)
    if requested_hook_name or page_key_filter or section_key_filter or slot_key_filter:
        return requested_hook_name, page_key_filter, section_key_filter, slot_key_filter, False, memory
    if not reuse_last_suggest and not pick and not pick_recommended and pick_index is None:
        return requested_hook_name, page_key_filter, section_key_filter, slot_key_filter, False, memory
    if not memory:
        return requested_hook_name, page_key_filter, section_key_filter, slot_key_filter, False, memory
    return (
        str(memory.get("requested_hook_name") or ""),
        (memory.get("page_key_filter") or None),
        (memory.get("section_key_filter") or None),
        (memory.get("slot_key_filter") or None),
        True,
        memory,
    )


def _run_project_hook_init(
    ctx: ProjectContext,
    *,
    hook_name: str,
    template_kind: str,
    suggest: bool,
    last_suggest: bool,
    open_catalog: bool,
    page_key_filter: str | None,
    section_key_filter: str | None,
    slot_key_filter: str | None,
    reuse_last_suggest: bool,
    pick: bool,
    pick_recommended: bool,
    pick_index: int | None,
    dry_run: bool,
    force: bool,
) -> tuple[dict[str, Any], int]:
    requested_hook_name = (hook_name or "").strip()
    catalog = _build_hook_catalog_summary(ctx)
    normalized_page_key_filter = (page_key_filter or "").strip() or None
    normalized_section_key_filter = (section_key_filter or "").strip() or None
    normalized_slot_key_filter = (slot_key_filter or "").strip() or None
    (
        requested_hook_name,
        normalized_page_key_filter,
        normalized_section_key_filter,
        normalized_slot_key_filter,
        used_recent_suggestion_memory,
        recent_suggestion_memory,
    ) = _resolve_recent_hook_suggestion_query(
        ctx,
        requested_hook_name=requested_hook_name,
        page_key_filter=normalized_page_key_filter,
        section_key_filter=normalized_section_key_filter,
        slot_key_filter=normalized_slot_key_filter,
        reuse_last_suggest=reuse_last_suggest,
        pick=pick,
        pick_recommended=pick_recommended,
        pick_index=pick_index,
    )
    if used_recent_suggestion_memory and (pick or pick_recommended or pick_index is not None):
        suggest = True
    if pick_recommended:
        suggest = True
    normalized_hook_name = _normalize_project_hook_name(requested_hook_name)

    pick_mode_count = int(bool(pick)) + int(bool(pick_recommended)) + int(pick_index is not None)
    if pick_mode_count > 1:
        return (
            {
                "status": "error",
                "entrypoint": "project-hook-init",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "message": "Use only one of --pick, --pick-recommended, or --pick-index at a time.",
            },
            EXIT_USAGE,
        )

    if open_catalog:
        return (
            {
                "status": "ok",
                "entrypoint": "project-hook-open-catalog",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_hook_name": requested_hook_name or None,
                "page_key_filter": normalized_page_key_filter,
                "section_key_filter": normalized_section_key_filter,
                "slot_key_filter": normalized_slot_key_filter,
                "reuse_last_suggest": reuse_last_suggest,
                "used_recent_suggestion_memory": used_recent_suggestion_memory,
                "pick": pick,
                "pick_recommended": pick_recommended,
                "pick_index": pick_index,
                "dry_run": dry_run,
                "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                "next_steps": [
                    f"inspect {catalog['markdown_path']}",
                    f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                ],
            },
            EXIT_OK,
        )

    if last_suggest:
        payload = {
            "project_id": ctx.project_id,
            "project_root": str(ctx.root),
            "recent_suggestion_memory_path": str(_last_hook_suggestions_path(ctx)),
        }
        if recent_suggestion_memory:
            recommended_next_command = (
                f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-init --reuse-last-suggest --pick-recommended --json"
                if int(recent_suggestion_memory.get("suggestion_count") or 0) > 0
                else None
            )
            return (
                {
                    "status": "ok",
                    "entrypoint": "project-hook-last-suggest",
                    **payload,
                    "last_suggest": recent_suggestion_memory,
                    "recommended_next_command": recommended_next_command,
                    "next_steps": [
                        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-init --reuse-last-suggest --pick-recommended --json",
                        f"inspect {catalog['markdown_path']}",
                    ],
                },
                EXIT_OK,
            )
        return (
            {
                "status": "warning",
                "entrypoint": "project-hook-last-suggest",
                **payload,
                "message": "No recent hook suggestion memory found yet. Run project hook-init --suggest first.",
                "next_steps": [
                    f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-init home --suggest --json",
                    f"inspect {catalog['markdown_path']}",
                ],
            },
            EXIT_OK,
        )

    if (
        not requested_hook_name
        and not normalized_page_key_filter
        and not normalized_section_key_filter
        and not normalized_slot_key_filter
        and (reuse_last_suggest or pick or pick_recommended or pick_index is not None)
        and not used_recent_suggestion_memory
    ):
        return (
            {
                "status": "warning",
                "entrypoint": "project-hook-suggest",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_hook_name": None,
                "page_key_filter": None,
                "section_key_filter": None,
                "slot_key_filter": None,
                "reuse_last_suggest": reuse_last_suggest,
                "used_recent_suggestion_memory": False,
                "pick": pick,
                "pick_recommended": pick_recommended,
                "pick_index": pick_index,
                "message": "No recent hook suggestion memory found yet. Run project hook-init --suggest first, then re-run --pick, --pick-recommended, or --pick-index.",
                "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                "suggestions": [],
                "recent_suggestion_memory_path": str(_last_hook_suggestions_path(ctx)),
                "next_steps": [
                    f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-init home --suggest --json",
                    f"inspect {catalog['markdown_path']}",
                ],
            },
            EXIT_OK,
        )

    if suggest or not normalized_hook_name:
        if not catalog["exists"]:
            return (
                {
                    "status": "warning",
                    "entrypoint": "project-hook-suggest",
                    "project_id": ctx.project_id,
                    "project_root": str(ctx.root),
                    "requested_hook_name": requested_hook_name or None,
                    "page_key_filter": normalized_page_key_filter,
                    "section_key_filter": normalized_section_key_filter,
                    "slot_key_filter": normalized_slot_key_filter,
                    "reuse_last_suggest": reuse_last_suggest,
                    "used_recent_suggestion_memory": used_recent_suggestion_memory,
                    "pick": pick,
                    "pick_recommended": pick_recommended,
                    "pick_index": pick_index,
                    "message": "No generated hook catalog found yet. Rebuild the project first to emit /.ail/hook_catalog.json and /.ail/hook_catalog.md.",
                    "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                    "suggestions": [],
                    "next_steps": [
                        f"inspect {catalog['markdown_path']}",
                        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                    ],
                },
                EXIT_OK,
            )
        suggestions = _suggest_hook_records(
            catalog,
            requested_hook_name,
            page_key_filter=normalized_page_key_filter,
            section_key_filter=normalized_section_key_filter,
            slot_key_filter=normalized_slot_key_filter,
        )
        for item in suggestions:
            item["pick_index_command"] = _build_project_hook_pick_index_command(
                requested_hook_name or str(item.get("hook_name") or ""),
                page_key_filter=normalized_page_key_filter,
                section_key_filter=normalized_section_key_filter,
                slot_key_filter=normalized_slot_key_filter,
                pick_index=int(item.get("suggestion_index") or 1),
            )
        recommended_pick_command = (
            _build_project_hook_pick_recommended_command(
                requested_hook_name or str(suggestions[0].get("hook_name") or ""),
                page_key_filter=normalized_page_key_filter,
                section_key_filter=normalized_section_key_filter,
                slot_key_filter=normalized_slot_key_filter,
                reuse_last_suggest=used_recent_suggestion_memory
                and not (requested_hook_name or normalized_page_key_filter or normalized_section_key_filter or normalized_slot_key_filter),
            )
            if suggestions
            else None
        )
        _write_last_hook_suggestions(
            ctx,
            requested_hook_name=requested_hook_name or None,
            page_key_filter=normalized_page_key_filter,
            section_key_filter=normalized_section_key_filter,
            slot_key_filter=normalized_slot_key_filter,
            suggestions=suggestions,
        )
        if pick_index is not None:
            if pick_index < 1:
                return (
                    {
                        "status": "error",
                        "entrypoint": "project-hook-suggest",
                        "project_id": ctx.project_id,
                        "project_root": str(ctx.root),
                        "requested_hook_name": requested_hook_name or None,
                        "page_key_filter": normalized_page_key_filter,
                        "section_key_filter": normalized_section_key_filter,
                        "slot_key_filter": normalized_slot_key_filter,
                        "reuse_last_suggest": reuse_last_suggest,
                        "used_recent_suggestion_memory": used_recent_suggestion_memory,
                        "pick": pick,
                        "pick_recommended": pick_recommended,
                        "pick_index": pick_index,
                        "dry_run": dry_run,
                        "message": "--pick-index must be 1 or greater.",
                        "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                        "suggestions": suggestions,
                        "next_steps": [
                            f"inspect {catalog['markdown_path']}",
                            "re-run project hook-init with a valid --pick-index value",
                        ],
                    },
                    EXIT_USAGE,
                )
            if pick_index > len(suggestions):
                return (
                    {
                        "status": "warning",
                        "entrypoint": "project-hook-suggest",
                        "project_id": ctx.project_id,
                        "project_root": str(ctx.root),
                        "requested_hook_name": requested_hook_name or None,
                        "page_key_filter": normalized_page_key_filter,
                        "section_key_filter": normalized_section_key_filter,
                        "slot_key_filter": normalized_slot_key_filter,
                        "reuse_last_suggest": reuse_last_suggest,
                        "used_recent_suggestion_memory": used_recent_suggestion_memory,
                        "pick": pick,
                        "pick_recommended": pick_recommended,
                        "pick_index": pick_index,
                        "dry_run": dry_run,
                        "message": f"--pick-index {pick_index} is out of range for {len(suggestions)} suggestions.",
                        "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                        "suggestions": suggestions,
                        "next_steps": [
                            f"inspect {catalog['markdown_path']}",
                            "re-run project hook-init with a smaller --pick-index value",
                        ],
                    },
                    EXIT_OK,
                )
            selected = suggestions[pick_index - 1]
            return _write_live_project_hook(
                ctx,
                requested_hook_name=requested_hook_name or str(selected.get("hook_name") or ""),
                normalized_hook_name=str(selected.get("hook_name") or ""),
                template_kind=str(selected.get("default_template") or template_kind),
                force=force,
                catalog=catalog,
                selected_from_suggestions=True,
                used_recent_suggestion_memory=used_recent_suggestion_memory,
                reuse_last_suggest=reuse_last_suggest,
                dry_run=dry_run,
            )
        if pick_recommended:
            if not suggestions:
                return (
                    {
                        "status": "warning",
                        "entrypoint": "project-hook-suggest",
                        "project_id": ctx.project_id,
                        "project_root": str(ctx.root),
                        "requested_hook_name": requested_hook_name or None,
                        "page_key_filter": normalized_page_key_filter,
                        "section_key_filter": normalized_section_key_filter,
                        "slot_key_filter": normalized_slot_key_filter,
                        "reuse_last_suggest": reuse_last_suggest,
                        "used_recent_suggestion_memory": used_recent_suggestion_memory,
                        "pick": pick,
                        "pick_recommended": True,
                        "pick_index": pick_index,
                        "dry_run": dry_run,
                        "message": "No matching hooks were found to scaffold.",
                        "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                        "suggestions": [],
                        "next_steps": [
                            f"inspect {catalog['markdown_path']}",
                            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json",
                        ],
                    },
                    EXIT_OK,
                )
            selected = suggestions[0]
            return _write_live_project_hook(
                ctx,
                requested_hook_name=requested_hook_name or str(selected.get("hook_name") or ""),
                normalized_hook_name=str(selected.get("hook_name") or ""),
                template_kind=str(selected.get("default_template") or template_kind),
                force=force,
                catalog=catalog,
                selected_from_suggestions=True,
                used_recent_suggestion_memory=used_recent_suggestion_memory,
                reuse_last_suggest=reuse_last_suggest,
                dry_run=dry_run,
            )
        if pick:
            if len(suggestions) == 1:
                selected = suggestions[0]
                return _write_live_project_hook(
                    ctx,
                    requested_hook_name=requested_hook_name or str(selected.get("hook_name") or ""),
                    normalized_hook_name=str(selected.get("hook_name") or ""),
                    template_kind=template_kind,
                    force=force,
                    catalog=catalog,
                    selected_from_suggestions=True,
                    used_recent_suggestion_memory=used_recent_suggestion_memory,
                    reuse_last_suggest=reuse_last_suggest,
                    dry_run=dry_run,
                )
            message = (
                "No matching hooks were found to scaffold."
                if not suggestions
                else "More than one matching hook was found. Narrow the query or use one exact suggested hook name."
            )
            next_steps = [f"inspect {catalog['markdown_path']}"]
            if suggestions:
                next_steps.append("re-run with a narrower --page-key, --section-key, or --slot-key filter")
                next_steps.append("or re-run project hook-init with one exact suggested hook name")
            else:
                next_steps.append(f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json")
            return (
                {
                    "status": "warning",
                    "entrypoint": "project-hook-suggest",
                    "project_id": ctx.project_id,
                    "project_root": str(ctx.root),
                    "requested_hook_name": requested_hook_name or None,
                    "page_key_filter": normalized_page_key_filter,
                    "section_key_filter": normalized_section_key_filter,
                    "slot_key_filter": normalized_slot_key_filter,
                    "reuse_last_suggest": reuse_last_suggest,
                    "used_recent_suggestion_memory": used_recent_suggestion_memory,
                    "pick": True,
                    "pick_recommended": pick_recommended,
                    "pick_index": pick_index,
                    "dry_run": dry_run,
                    "message": message,
                    "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                    "suggestions": suggestions,
                    "next_steps": next_steps,
                },
                EXIT_OK,
            )
        return (
            {
                "status": "ok",
                "entrypoint": "project-hook-suggest",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_hook_name": requested_hook_name or None,
                "page_key_filter": normalized_page_key_filter,
                "section_key_filter": normalized_section_key_filter,
                "slot_key_filter": normalized_slot_key_filter,
                "reuse_last_suggest": reuse_last_suggest,
                "used_recent_suggestion_memory": used_recent_suggestion_memory,
                "pick": pick,
                "pick_recommended": pick_recommended,
                "pick_index": pick_index,
                "dry_run": dry_run,
                "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                "suggestions": suggestions,
                "suggestion_pick_examples": [item.get("pick_index_command") for item in suggestions[:3]],
                "recommended_pick_index_command": _recommended_pick_index_command(suggestions),
                "recommended_pick_command": recommended_pick_command,
                "recommended_next_command": recommended_pick_command,
                "recent_suggestion_memory_path": str(_last_hook_suggestions_path(ctx)),
                "recent_suggestion_memory": recent_suggestion_memory if used_recent_suggestion_memory else None,
                "next_steps": [
                    f"inspect {catalog['markdown_path']}",
                    "re-run project hook-init with one suggested hook name to scaffold a live file",
                ],
            },
            EXIT_OK,
        )

    if not normalized_hook_name:
        return (
            {
                "status": "error",
                "entrypoint": "project-hook-init",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "message": "Hook name is required.",
            },
            EXIT_USAGE,
        )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", normalized_hook_name):
        return (
            {
                "status": "error",
                "entrypoint": "project-hook-init",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "hook_name": normalized_hook_name,
                "message": "Hook name may only contain letters, numbers, dots, underscores, and hyphens.",
            },
            EXIT_USAGE,
        )

    return _write_live_project_hook(
        ctx,
        requested_hook_name=requested_hook_name,
        normalized_hook_name=normalized_hook_name,
        template_kind=template_kind,
        force=force,
        catalog=catalog,
        selected_from_suggestions=False,
        used_recent_suggestion_memory=used_recent_suggestion_memory,
        reuse_last_suggest=reuse_last_suggest,
        dry_run=dry_run,
    )


def _build_project_hooks_payload(ctx: ProjectContext, *, page_key: str | None = None) -> tuple[dict[str, Any], int]:
    catalog = _build_hook_catalog_summary(ctx)
    next_steps = [
        f"inspect {catalog['markdown_path']}",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project summary --json",
    ]
    if not catalog["exists"]:
        payload = {
            "status": "warning",
            "entrypoint": "project-hooks",
            "project_id": ctx.project_id,
            "project_root": str(ctx.root),
            "requested_page_key": page_key,
            "message": "No generated hook catalog found yet. Rebuild the project first to emit /.ail/hook_catalog.json and /.ail/hook_catalog.md.",
            "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
            "next_steps": next_steps,
        }
        return payload, EXIT_OK

    pages = catalog["pages"]
    selected_page = None
    requested_page_key = (page_key or "").strip()
    if requested_page_key:
        selected_page = next((page for page in pages if page.get("page_key") == requested_page_key), None)
        if selected_page is None:
            payload = {
                "status": "error",
                "entrypoint": "project-hooks",
                "project_id": ctx.project_id,
                "project_root": str(ctx.root),
                "requested_page_key": requested_page_key,
                "available_page_keys": catalog["page_keys"],
                "message": f"Unknown hook catalog page: {requested_page_key}",
                "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
                "next_steps": next_steps,
            }
            return payload, EXIT_USAGE

    recommended_page_key = requested_page_key or (str(catalog["page_keys"][0]) if catalog["page_keys"] else "")
    recommended_hook_suggest_command = (
        _build_project_hook_suggest_command(recommended_page_key, page_key_filter=recommended_page_key)
        if recommended_page_key
        else ""
    )
    if recommended_hook_suggest_command:
        next_steps.append(f"run {recommended_hook_suggest_command}")

    payload = {
        "status": "ok",
        "entrypoint": "project-hooks",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "requested_page_key": requested_page_key or None,
        "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
        "available_page_keys": catalog["page_keys"],
        "selected_page": selected_page,
        "pages": pages if not selected_page else [selected_page],
        "recommended_hook_page_key": recommended_page_key or None,
        "recommended_hook_suggest_command": recommended_hook_suggest_command or None,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_project_hook_guide_payload(ctx: ProjectContext) -> tuple[dict[str, Any], int]:
    catalog = _build_hook_catalog_summary(ctx)
    recommended_page_key = str((catalog.get("page_keys") or [""])[0] or "")
    recommended_hook_name = f"{recommended_page_key}.before" if recommended_page_key else "home.before"
    recommended_suggest_command = (
        _build_project_hook_suggest_command(recommended_page_key, page_key_filter=recommended_page_key)
        if recommended_page_key
        else f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json"
    )
    recommended_dry_run_command = _build_project_hook_init_command(
        recommended_hook_name,
        dry_run=True,
    )
    recommended_explain_command = _build_project_hook_init_command(
        recommended_hook_name,
        dry_run=True,
    ).replace(" --json", " --explain")
    preferred_project_hook_command = recommended_explain_command
    preferred_project_hook_run_command = recommended_suggest_command
    preferred_project_hook_reason = "Use the explain path first when you want one concrete scaffold target plus the exact follow-up command without writing yet."
    preferred_project_hook_run_reason = "Run the JSON suggest path when you want a machine-readable delegated result without touching an existing live hook target."
    cheat_sheet_path = REPO_ROOT / "CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md"
    guide_sections = [
        {
            "label": "catalog",
            "summary": "Open the current project's hook catalog first when you want the full page/section/slot map.",
            "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-init --open-catalog --json",
        },
        {
            "label": "suggest",
            "summary": "Start from one page-focused suggestion query to narrow the available hook surface.",
            "command": recommended_suggest_command,
        },
        {
            "label": "dry_run",
            "summary": "Preview one concrete live hook target before writing anything.",
            "command": recommended_dry_run_command,
        },
        {
            "label": "explain",
            "summary": "Use the structured explain view when you want the scaffold decision and follow-up spelled out.",
            "command": recommended_explain_command,
        },
    ]
    next_steps = [f"run {section['command']}" for section in guide_sections]
    next_steps.append(f"inspect {cheat_sheet_path}")
    payload = {
        "status": "ok",
        "entrypoint": "project-hook-guide",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "hook_catalog": {key: value for key, value in catalog.items() if key != "pages"},
        "recommended_page_key": recommended_page_key or None,
        "recommended_hook_name": recommended_hook_name,
        "recommended_suggest_command": recommended_suggest_command,
        "recommended_dry_run_command": recommended_dry_run_command,
        "recommended_explain_command": recommended_explain_command,
        "preferred_project_hook_command": preferred_project_hook_command,
        "preferred_project_hook_run_command": preferred_project_hook_run_command,
        "preferred_project_hook_reason": preferred_project_hook_reason,
        "preferred_project_hook_run_reason": preferred_project_hook_run_reason,
        "cheat_sheet_path": str(cheat_sheet_path),
        "guide_sections": guide_sections,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_workspace_hook_guide_payload() -> tuple[dict[str, Any], int]:
    workspace_hooks = _build_workspace_hooks_payload()
    recommended_project_name = str(workspace_hooks.get("recommended_hook_project") or "")
    cheat_sheet_path = REPO_ROOT / "CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md"
    recommended_suggest_command = (
        str(workspace_hooks.get("recommended_workspace_hook_suggest_command") or "")
        or f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace hooks --json"
    )
    preferred_command = str(workspace_hooks.get("preferred_workspace_hook_command") or "")
    if not preferred_command:
        preferred_command = str(workspace_hooks.get("recommended_workspace_hook_pick_command") or "")
    recommended_explain_command = (
        _build_workspace_hook_init_command(
            f"{str((workspace_hooks.get('projects') or [{}])[0].get('available_page_keys', ['home'])[0] or 'home')}.before",
            project_name=recommended_project_name or None,
            dry_run=True,
        ).replace(" --json", " --explain")
        if recommended_project_name
        else ""
    )
    guide_sections = [
        {
            "label": "workspace_hooks",
            "summary": "Scan every generated project that already has a hook catalog.",
            "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace hooks --json",
        },
        {
            "label": "suggest",
            "summary": "Start from the current recommended workspace project and its first page-focused suggestion query.",
            "command": recommended_suggest_command,
        },
        {
            "label": "continue",
            "summary": "Use the current preferred repo-root continue path when you want the shortest repeatable next step.",
            "command": preferred_command,
        },
        {
            "label": "explain",
            "summary": "Use the delegated explain view when you want the selected project route, target, and next step spelled out.",
            "command": recommended_explain_command or recommended_suggest_command,
        },
    ]
    next_steps = [f"run {section['command']}" for section in guide_sections if section.get("command")]
    next_steps.append(f"inspect {cheat_sheet_path}")
    preferred_workspace_hook_run_command = str(workspace_hooks.get("recent_workspace_hook_suggest_command") or "") or str(workspace_hooks.get("recommended_workspace_hook_suggest_command") or "") or preferred_command or str(workspace_hooks.get("recommended_workspace_hook_pick_command") or "") or recommended_suggest_command
    payload = {
        "status": "ok",
        "entrypoint": "workspace-hook-guide",
        "repo_root": str(REPO_ROOT),
        "recommended_project_name": recommended_project_name or None,
        "preferred_workspace_hook_command": workspace_hooks.get("preferred_workspace_hook_command") or None,
        "preferred_workspace_hook_run_command": preferred_workspace_hook_run_command or None,
        "preferred_workspace_hook_reason": workspace_hooks.get("preferred_workspace_hook_reason") or None,
        "recommended_workspace_hook_suggest_command": workspace_hooks.get("recommended_workspace_hook_suggest_command") or None,
        "recommended_workspace_hook_pick_command": workspace_hooks.get("recommended_workspace_hook_pick_command") or None,
        "cheat_sheet_path": str(cheat_sheet_path),
        "workspace_hooks": {
            "catalog_project_count": workspace_hooks.get("catalog_project_count"),
            "page_count": workspace_hooks.get("page_count"),
            "section_hook_count": workspace_hooks.get("section_hook_count"),
            "slot_hook_count": workspace_hooks.get("slot_hook_count"),
        },
        "guide_sections": guide_sections,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK



def _build_project_summary_payload(ctx: ProjectContext, *, base_url: str | None, project_id: str | None = None) -> dict[str, Any]:
    resolved_project_id = _resolve_project_id_arg(project_id or ctx.project_id)
    payload = _build_cloud_status_payload(AILCloudClient(base_url=base_url), project_id=resolved_project_id)
    handoff = _build_trial_handoff(ctx, payload)
    check_payload, diagnosis_payload, recommended_action, doctor_status, findings, _, _ = _analyze_project_doctor_state(
        ctx,
        base_url=base_url,
    )
    recommendation = _project_summary_recommendation(
        ctx,
        recommended_action=recommended_action,
        doctor_status=doctor_status,
    )
    hook_catalog = _build_hook_catalog_summary(ctx)
    next_steps = list(handoff["next_steps"])
    if hook_catalog["exists"]:
        hook_step = f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json"
        if hook_step not in next_steps:
            next_steps.append(hook_step)
    return {
        "status": "ok",
        "project_id": resolved_project_id,
        "project_root": str(ctx.root),
        "source_of_truth": str(ctx.source_file),
        "manifest": str(ctx.manifest_file),
        "last_build": str(ctx.last_build_file),
        "managed_roots": MANAGED_ROOTS,
        "user_roots": USER_ROOTS,
        "project_check": check_payload,
        "source_diagnosis": diagnosis_payload,
        "doctor_status": doctor_status,
        "doctor_findings": findings,
        "recommended_action": recommended_action,
        "cloud_status": payload,
        "preview_handoff": handoff,
        "preview_hint": handoff["preview_hint"],
        "open_targets": handoff["open_targets"],
        "hook_catalog": {key: value for key, value in hook_catalog.items() if key != "pages"},
        "next_steps": next_steps,
        **recommendation,
    }


def _build_project_preview_payload(ctx: ProjectContext, *, base_url: str | None) -> dict[str, Any]:
    summary = _build_project_summary_payload(ctx, base_url=base_url, project_id=ctx.project_id)
    cloud_status = summary.get("cloud_status") or {}
    latest_build = cloud_status.get("latest_build") or {}
    latest_artifact = cloud_status.get("latest_artifact") or {}
    handoff = summary.get("preview_handoff") or _build_trial_handoff(ctx, cloud_status)

    next_steps = list(handoff.get("next_steps") or [])
    recommended_command = summary.get("recommended_primary_command")
    if recommended_command and f"run {recommended_command}" not in next_steps:
        next_steps.append(f"run {recommended_command}")

    return {
        "status": "ok",
        "entrypoint": "project-preview",
        "project_id": summary["project_id"],
        "project_root": summary["project_root"],
        "doctor_status": summary.get("doctor_status", ""),
        "recommended_action": summary.get("recommended_action", ""),
        "recommended_primary_action": summary.get("recommended_primary_action", ""),
        "recommended_primary_command": summary.get("recommended_primary_command", ""),
        "recommended_primary_reason": summary.get("recommended_primary_reason", ""),
        "latest_build_id": latest_build.get("build_id", "") or cloud_status.get("project", {}).get("latest_build_id", ""),
        "latest_artifact_id": latest_artifact.get("artifact_id", ""),
        "latest_artifact_format": latest_artifact.get("format", ""),
        "latest_artifact_local_path": latest_artifact.get("local_path", ""),
        "website_preview_summary": handoff.get("website_summary"),
        "website_delivery_summary": _build_website_delivery_summary(
            project_id=summary["project_id"],
            project_root=summary["project_root"],
            doctor_status=summary.get("doctor_status"),
            recommended_action=summary.get("recommended_action"),
            expected_or_detected_profile=((summary.get("source_diagnosis") or {}).get("diagnosis") or {}).get("detected_profile"),
            latest_build_id=latest_build.get("build_id", "") or cloud_status.get("project", {}).get("latest_build_id", ""),
            latest_artifact_id=latest_artifact.get("artifact_id", ""),
            latest_artifact_format=latest_artifact.get("format", ""),
            preview_handoff=handoff,
            project_check=summary.get("project_check"),
        ),
        "preview_handoff": handoff,
        "preview_hint": handoff["preview_hint"],
        "open_targets": handoff["open_targets"],
        "cloud_status": cloud_status,
        "next_steps": next_steps,
    }


def _npm_command() -> str | None:
    return shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")


def _serve_command_display(*, host: str, port: int) -> str:
    return f"npm run dev -- --host {host} --port {port}"


def _read_log_tail(path: Path, *, max_chars: int = 2000) -> str:
    if not path.exists():
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return content[-max_chars:]


def _build_project_serve_payload(
    ctx: ProjectContext,
    *,
    host: str,
    port: int,
    install_if_needed: bool,
    dry_run: bool,
) -> tuple[dict[str, Any], int]:
    frontend_root = ctx.root / "frontend"
    package_json = frontend_root / "package.json"
    node_modules = frontend_root / "node_modules"
    serve_command = _serve_command_display(host=host, port=port)
    local_url = f"http://{host}:{port}"
    npm = _npm_command()
    log_dir = ctx.ail_dir / "serve"
    log_path = log_dir / "project-serve.log"

    base_payload: dict[str, Any] = {
        "entrypoint": "project-serve",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "frontend_root": str(frontend_root),
        "package_json": str(package_json),
        "host": host,
        "port": port,
        "local_url": local_url,
        "command": serve_command,
        "dry_run": dry_run,
        "install_if_needed": install_if_needed,
        "npm_found": bool(npm),
        "npm_path": npm or "",
        "dependencies_installed": node_modules.exists(),
        "log_path": str(log_path),
    }

    if not frontend_root.exists() or not frontend_root.is_dir():
        payload = {
            **base_payload,
            "status": "error",
            "message": "Frontend directory was not found for the current generated project.",
            "next_steps": [
                "run website check or compile/sync to generate the frontend first",
                f"inspect {ctx.root}",
            ],
        }
        return payload, EXIT_VALIDATION

    if not package_json.exists():
        payload = {
            **base_payload,
            "status": "error",
            "message": "frontend/package.json was not found, so the frontend cannot be served with npm.",
            "next_steps": [
                f"inspect {frontend_root}",
                "regenerate the website project or check whether frontend generation failed",
            ],
        }
        return payload, EXIT_VALIDATION

    if dry_run:
        payload = {
            **base_payload,
            "status": "ok",
            "started": False,
            "message": "Dry run only. The frontend dev server was not started.",
            "next_steps": [
                f"cd {frontend_root}",
                "npm install" if not node_modules.exists() else serve_command,
                f"open {local_url}",
            ],
        }
        if not npm:
            payload["message"] = "Dry run only. npm was not found on PATH, so install Node.js/npm before serving."
            payload["next_steps"].insert(0, "install Node.js and npm")
        return payload, EXIT_OK

    if not npm:
        payload = {
            **base_payload,
            "status": "error",
            "started": False,
            "message": "npm was not found on PATH. Install Node.js/npm before serving the generated frontend.",
            "next_steps": [
                "install Node.js and npm",
                f"cd {frontend_root}",
                serve_command,
            ],
        }
        return payload, EXIT_VALIDATION

    install_result: dict[str, Any] | None = None
    if not node_modules.exists():
        if not install_if_needed:
            payload = {
                **base_payload,
                "status": "error",
                "started": False,
                "message": "Frontend dependencies are not installed yet.",
                "recommended_next_command": "npm install",
                "next_steps": [
                    f"cd {frontend_root}",
                    "npm install",
                    serve_command,
                    f"open {local_url}",
                ],
            }
            return payload, EXIT_VALIDATION

        install_proc = subprocess.run(
            [npm, "install"],
            cwd=frontend_root,
            text=True,
            capture_output=True,
        )
        install_result = {
            "command": "npm install",
            "exit_code": install_proc.returncode,
            "stdout_tail": install_proc.stdout[-2000:],
            "stderr_tail": install_proc.stderr[-2000:],
        }
        if install_proc.returncode != 0:
            payload = {
                **base_payload,
                "status": "error",
                "started": False,
                "install_result": install_result,
                "message": "npm install failed, so the frontend dev server was not started.",
                "next_steps": [
                    f"cd {frontend_root}",
                    "inspect npm install output",
                    "fix frontend dependency installation",
                ],
            }
            return payload, EXIT_GENERAL_ERROR

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    command = [npm, "run", "dev", "--", "--host", host, "--port", str(port)]
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=frontend_root,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=os.name != "nt",
        creationflags=creationflags,
    )
    log_file.close()
    time.sleep(1)
    early_exit = process.poll()
    if early_exit is not None:
        payload = {
            **base_payload,
            "status": "error",
            "started": False,
            "pid": process.pid,
            "process_exit_code": early_exit,
            "install_result": install_result,
            "log_tail": _read_log_tail(log_path),
            "message": "The frontend dev server exited immediately. Inspect the serve log for details.",
            "next_steps": [
                f"inspect {log_path}",
                f"cd {frontend_root}",
                serve_command,
            ],
        }
        return payload, EXIT_GENERAL_ERROR

    payload = {
        **base_payload,
        "status": "ok",
        "started": True,
        "pid": process.pid,
        "install_result": install_result,
        "message": "Frontend dev server started in the background for the current generated website project.",
        "next_steps": [
            f"open {local_url}",
            f"inspect {log_path}",
            "stop the dev server from your process manager when finished",
        ],
    }
    return payload, EXIT_OK


def _build_project_open_target_payload(
    ctx: ProjectContext,
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    preview = _build_project_preview_payload(ctx, base_url=base_url)
    handoff = preview["preview_handoff"]
    targets = handoff.get("open_targets") or []
    available_labels = [item["label"] for item in targets]
    resolved_label = label or handoff["primary_target"]["label"]
    target = next((item for item in targets if item["label"] == resolved_label), None)

    if target is None:
        payload = {
            "status": "error",
            "entrypoint": "project-open-target",
            "project_id": preview["project_id"],
            "project_root": preview["project_root"],
            "requested_label": label,
            "available_labels": available_labels,
            "message": f"Unknown project preview target: {resolved_label}",
            "next_steps": [
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project preview --base-url embedded://local --json",
                "choose one of the available_labels values and rerun project open-target",
            ],
        }
        return payload, EXIT_USAGE

    inspect_command = f"inspect {target['path']}"
    next_steps = [
        inspect_command,
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project preview --base-url embedded://local --json",
    ]
    if preview.get("recommended_primary_command"):
        next_steps.append(f"run {preview['recommended_primary_command']}")

    payload = {
        "status": "ok",
        "entrypoint": "project-open-target",
        "project_id": preview["project_id"],
        "project_root": preview["project_root"],
        "requested_label": label,
        "resolved_label": resolved_label,
        "available_labels": available_labels,
        "target": target,
        "inspect_command": inspect_command,
        "preview_handoff": handoff,
        "preview_hint": preview["preview_hint"],
        "recommended_primary_action": preview.get("recommended_primary_action"),
        "recommended_primary_command": preview.get("recommended_primary_command"),
        "recommended_primary_reason": preview.get("recommended_primary_reason"),
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _inspect_resolved_target(target: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(target.get("path") or ""))
    kind = str(target.get("kind") or "")
    exists = path.exists()

    if kind == "file":
        if not exists:
            return {
                "kind": "file",
                "path": str(path),
                "exists": False,
                "size_bytes": 0,
                "line_count": 0,
                "content_preview": "",
                "preview_truncated": False,
            }
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            preview_lines = lines[:40]
            return {
                "kind": "file",
                "path": str(path),
                "exists": True,
                "size_bytes": path.stat().st_size,
                "line_count": len(lines),
                "content_preview": "\n".join(preview_lines),
                "preview_truncated": len(lines) > len(preview_lines),
            }
        except UnicodeDecodeError:
            return {
                "kind": "file",
                "path": str(path),
                "exists": True,
                "size_bytes": path.stat().st_size,
                "line_count": 0,
                "content_preview": "[binary file omitted]",
                "preview_truncated": False,
            }

    if kind == "directory":
        if not exists:
            return {
                "kind": "directory",
                "path": str(path),
                "exists": False,
                "entry_count": 0,
                "entries": [],
                "preview_truncated": False,
            }
        children = sorted(path.iterdir(), key=lambda item: _directory_entry_priority(item.name))
        entries = [
            {
                "name": child.name,
                "path": str(child),
                "kind": "directory" if child.is_dir() else "file",
                "exists": True,
            }
            for child in children[:20]
        ]
        return {
            "kind": "directory",
            "path": str(path),
            "exists": True,
            "entry_count": len(children),
            "entries": entries,
            "preview_truncated": len(children) > len(entries),
        }

    return {
        "kind": kind or "unknown",
        "path": str(path),
        "exists": exists,
    }


def _inspect_hook_target_path(target_path: str) -> dict[str, Any]:
    path = Path(target_path)
    target = {
        "label": "hook_target",
        "kind": "file",
        "path": str(path),
    }
    parent_target = {
        "label": "hook_target_parent",
        "kind": "directory",
        "path": str(path.parent),
    }
    return {
        "target": target,
        "inspection": _inspect_resolved_target(target),
        "parent_target": parent_target,
        "parent_inspection": _inspect_resolved_target(parent_target),
    }


def _build_project_inspect_target_payload(
    ctx: ProjectContext,
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    open_payload, open_exit = _build_project_open_target_payload(
        ctx,
        label=label,
        base_url=base_url,
    )
    if open_exit != EXIT_OK:
        payload = {
            "status": open_payload.get("status", "error"),
            "entrypoint": "project-inspect-target",
            "project_id": open_payload.get("project_id"),
            "project_root": open_payload.get("project_root"),
            "requested_label": label,
            "available_labels": open_payload.get("available_labels", []),
            "message": open_payload.get("message", "Unable to resolve project preview target."),
            "preview_handoff": open_payload.get("preview_handoff"),
            "preview_hint": open_payload.get("preview_hint"),
            "next_steps": open_payload.get("next_steps", []),
        }
        return payload, open_exit

    inspection = _inspect_resolved_target(open_payload["target"])
    status = "ok" if inspection.get("exists") else "warning"
    exit_code = EXIT_OK if status == "ok" else EXIT_VALIDATION
    next_steps = list(open_payload.get("next_steps", []))
    if open_payload.get("recommended_primary_command"):
        next_steps.append(f"run {open_payload['recommended_primary_command']}")

    payload = {
        "status": status,
        "entrypoint": "project-inspect-target",
        "project_id": open_payload["project_id"],
        "project_root": open_payload["project_root"],
        "requested_label": label,
        "resolved_label": open_payload["resolved_label"],
        "target": open_payload["target"],
        "inspection": inspection,
        "inspect_command": open_payload["inspect_command"],
        "available_labels": open_payload["available_labels"],
        "preview_handoff": open_payload["preview_handoff"],
        "preview_hint": open_payload["preview_hint"],
        "recommended_primary_action": open_payload.get("recommended_primary_action"),
        "recommended_primary_command": open_payload.get("recommended_primary_command"),
        "recommended_primary_reason": open_payload.get("recommended_primary_reason"),
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_project_export_handoff_payload(ctx: ProjectContext, *, base_url: str | None) -> tuple[dict[str, Any], int]:
    summary = _build_project_summary_payload(ctx, base_url=base_url, project_id=ctx.project_id)
    preview = _build_project_preview_payload(ctx, base_url=base_url)
    open_payload, open_exit = _build_project_open_target_payload(ctx, label=None, base_url=base_url)
    inspect_payload, inspect_exit = _build_project_inspect_target_payload(ctx, label=None, base_url=base_url)

    status = "ok"
    exit_code = EXIT_OK
    if inspect_exit != EXIT_OK:
        status = inspect_payload.get("status", "warning")
        exit_code = inspect_exit
    elif open_exit != EXIT_OK:
        status = open_payload.get("status", "warning")
        exit_code = open_exit

    next_steps = []
    for source in (
        inspect_payload.get("next_steps", []),
        preview.get("next_steps", []),
        [f"run {summary.get('recommended_primary_command')}"] if summary.get("recommended_primary_command") else [],
    ):
        for item in source:
            if item and item not in next_steps:
                next_steps.append(item)

    payload = {
        "status": status,
        "entrypoint": "project-export-handoff",
        "project_id": summary["project_id"],
        "project_root": summary["project_root"],
        "doctor_status": summary.get("doctor_status"),
        "recommended_action": summary.get("recommended_action"),
        "recommended_primary_action": summary.get("recommended_primary_action"),
        "recommended_primary_command": summary.get("recommended_primary_command"),
        "recommended_primary_reason": summary.get("recommended_primary_reason"),
        "website_preview_summary": preview.get("website_preview_summary"),
        "website_delivery_summary": preview.get("website_delivery_summary"),
        "preview_handoff": preview.get("preview_handoff"),
        "preview_hint": preview.get("preview_hint"),
        "open_targets": preview.get("open_targets", []),
        "primary_target_label": open_payload.get("resolved_label"),
        "primary_target": open_payload.get("target"),
        "primary_inspection": inspect_payload.get("inspection"),
        "inspect_command": inspect_payload.get("inspect_command"),
        "available_labels": open_payload.get("available_labels", []),
        "cloud_status": summary.get("cloud_status"),
        "project_summary": summary,
        "project_preview": preview,
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_local_project_style_brief_context(ctx: ProjectContext, *, base_url: str | None, cloud_error: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_service = ManifestService()
    last_build = manifest_service.load_last_build(ctx.last_build_file)
    build_id = str((last_build or {}).get("build_id") or "")
    preview_handoff = _build_preview_handoff(
        artifact_path=str(ctx.root),
        source_path=str(ctx.source_file),
        manifest_path=str(ctx.manifest_file),
        last_build_path=str(ctx.last_build_file),
        generated_views_dir=str(ctx.root / "src/views/generated"),
        generated_router_dir=str(ctx.root / "src/router/generated"),
        generated_backend_dir=str(ctx.root / "backend/generated"),
        project_id=ctx.project_id,
        build_id=build_id,
        base_url=base_url,
        include_build_artifact_step=False,
    )
    check_payload, diagnosis_payload, recommended_action, doctor_status, findings, _, _ = _analyze_project_doctor_state(
        ctx,
        base_url=base_url,
    )
    recommendation = _project_summary_recommendation(
        ctx,
        recommended_action=recommended_action,
        doctor_status=doctor_status,
    )
    hook_catalog = _build_hook_catalog_summary(ctx)
    next_steps = list(preview_handoff.get("next_steps") or [])
    hook_step = f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hooks --json"
    if hook_catalog.get("exists") and hook_step not in next_steps:
        next_steps.append(hook_step)

    summary = {
        "status": "warning",
        "entrypoint": "project-summary",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "source_of_truth": str(ctx.source_file),
        "manifest": str(ctx.manifest_file),
        "last_build": str(ctx.last_build_file),
        "managed_roots": MANAGED_ROOTS,
        "user_roots": USER_ROOTS,
        "project_check": check_payload,
        "source_diagnosis": diagnosis_payload,
        "doctor_status": doctor_status,
        "doctor_findings": findings,
        "recommended_action": recommended_action,
        "cloud_status": {
            "status": "warning",
            "message": "Cloud status was unavailable for this local project context.",
            "error": cloud_error,
            "project": {"project_id": ctx.project_id, "latest_build_id": build_id},
            "latest_build": {"build_id": build_id, "source_project_root": str(ctx.root)},
            "latest_artifact": {"local_path": str(ctx.root)},
        },
        "preview_handoff": preview_handoff,
        "preview_hint": preview_handoff["preview_hint"],
        "open_targets": preview_handoff["open_targets"],
        "hook_catalog": {key: value for key, value in hook_catalog.items() if key != "pages"},
        "next_steps": next_steps,
        **recommendation,
    }
    preview = {
        "status": "warning",
        "entrypoint": "project-preview",
        "project_id": summary["project_id"],
        "project_root": summary["project_root"],
        "doctor_status": summary.get("doctor_status", ""),
        "recommended_action": summary.get("recommended_action", ""),
        "recommended_primary_action": summary.get("recommended_primary_action", ""),
        "recommended_primary_command": summary.get("recommended_primary_command", ""),
        "recommended_primary_reason": summary.get("recommended_primary_reason", ""),
        "latest_build_id": build_id,
        "latest_artifact_id": "",
        "latest_artifact_format": "",
        "latest_artifact_local_path": str(ctx.root),
        "website_preview_summary": preview_handoff.get("website_summary"),
        "website_delivery_summary": _build_website_delivery_summary(
            project_id=summary["project_id"],
            project_root=summary["project_root"],
            doctor_status=summary.get("doctor_status"),
            recommended_action=summary.get("recommended_action"),
            expected_or_detected_profile=((summary.get("source_diagnosis") or {}).get("diagnosis") or {}).get("detected_profile"),
            latest_build_id=build_id,
            latest_artifact_id="",
            latest_artifact_format="",
            preview_handoff=preview_handoff,
            project_check=summary.get("project_check"),
        ),
        "preview_handoff": preview_handoff,
        "preview_hint": preview_handoff["preview_hint"],
        "open_targets": preview_handoff["open_targets"],
        "cloud_status": summary["cloud_status"],
        "next_steps": list(summary.get("next_steps") or []),
    }
    export_payload = {
        "status": "warning",
        "entrypoint": "project-export-handoff",
        "project_id": summary["project_id"],
        "project_root": summary["project_root"],
        "doctor_status": summary.get("doctor_status"),
        "recommended_action": summary.get("recommended_action"),
        "recommended_primary_action": summary.get("recommended_primary_action"),
        "recommended_primary_command": summary.get("recommended_primary_command"),
        "recommended_primary_reason": summary.get("recommended_primary_reason"),
        "website_preview_summary": preview.get("website_preview_summary"),
        "website_delivery_summary": preview.get("website_delivery_summary"),
        "preview_handoff": preview_handoff,
        "preview_hint": preview.get("preview_hint"),
        "open_targets": preview.get("open_targets", []),
        "primary_target_label": (preview_handoff.get("primary_target") or {}).get("label", ""),
        "primary_target": preview_handoff.get("primary_target"),
        "primary_inspection": _inspect_resolved_target(preview_handoff.get("primary_target") or {}),
        "inspect_command": f"inspect {(preview_handoff.get('primary_target') or {}).get('path', '')}",
        "available_labels": [item.get("label", "") for item in (preview.get("open_targets") or [])],
        "cloud_status": summary.get("cloud_status"),
        "project_summary": summary,
        "project_preview": preview,
        "next_steps": list(preview.get("next_steps") or []),
    }
    return summary, preview, export_payload


def _style_intent_path(ctx: ProjectContext) -> Path:
    return ctx.ail_dir / "style_intent.json"


def _default_style_intent() -> dict[str, Any]:
    return {
        "audience": "",
        "brand_keywords": [],
        "tone_keywords": [],
        "style_direction": "",
        "localization_mode": "",
        "visual_constraints": [],
        "notes": "",
    }


def _normalize_string_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for item in values or []:
        for part in str(item or "").split(","):
            normalized = part.strip()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
    return cleaned


def _load_project_style_intent(ctx: ProjectContext) -> dict[str, Any]:
    payload = _default_style_intent()
    path = _style_intent_path(ctx)
    if not path.exists():
        return payload
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return payload
    if not isinstance(raw, dict):
        return payload
    payload["audience"] = str(raw.get("audience") or "").strip()
    payload["brand_keywords"] = _normalize_string_list(list(raw.get("brand_keywords") or []))
    payload["tone_keywords"] = _normalize_string_list(list(raw.get("tone_keywords") or []))
    payload["style_direction"] = str(raw.get("style_direction") or "").strip()
    payload["localization_mode"] = str(raw.get("localization_mode") or "").strip()
    payload["visual_constraints"] = _normalize_string_list(list(raw.get("visual_constraints") or []))
    payload["notes"] = str(raw.get("notes") or "").strip()
    return payload


def _save_project_style_intent(ctx: ProjectContext, payload: dict[str, Any]) -> Path:
    ctx.ail_dir.mkdir(parents=True, exist_ok=True)
    path = _style_intent_path(ctx)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _build_project_style_intent_payload(
    ctx: ProjectContext,
    *,
    audience: str | None,
    style_direction: str | None,
    localization_mode: str | None,
    notes: str | None,
    brand_keywords: list[str] | None,
    tone_keywords: list[str] | None,
    visual_constraints: list[str] | None,
    reset: bool,
) -> tuple[dict[str, Any], int]:
    existing = _load_project_style_intent(ctx)
    style_intent = _default_style_intent() if reset else dict(existing)
    write_requested = reset or any(
        value is not None
        for value in (
            audience,
            style_direction,
            localization_mode,
            notes,
            brand_keywords,
            tone_keywords,
            visual_constraints,
        )
    )

    if audience is not None:
        style_intent["audience"] = str(audience).strip()
    if style_direction is not None:
        style_intent["style_direction"] = str(style_direction).strip()
    if localization_mode is not None:
        style_intent["localization_mode"] = str(localization_mode).strip()
    if notes is not None:
        style_intent["notes"] = str(notes).strip()
    if brand_keywords is not None:
        style_intent["brand_keywords"] = _normalize_string_list(brand_keywords)
    if tone_keywords is not None:
        style_intent["tone_keywords"] = _normalize_string_list(tone_keywords)
    if visual_constraints is not None:
        style_intent["visual_constraints"] = _normalize_string_list(visual_constraints)

    style_intent_path = _style_intent_path(ctx)
    action = "read"
    message = "Loaded the current project style intent."
    if reset:
        _save_project_style_intent(ctx, style_intent)
        action = "reset"
        message = "Reset the project style intent back to an empty baseline."
    elif write_requested:
        _save_project_style_intent(ctx, style_intent)
        action = "write"
        message = "Saved the current project style intent."

    next_steps = [
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-brief --base-url embedded://local --json",
        f"inspect {style_intent_path}",
    ]
    if action != "read":
        next_steps.append(f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-apply-check --base-url embedded://local --json")

    payload = {
        "status": "ok",
        "entrypoint": "project-style-intent",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "style_intent_path": str(style_intent_path),
        "style_intent_exists": style_intent_path.exists(),
        "action": action,
        "message": message,
        "style_intent": style_intent,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_project_style_prompt_text(style_brief: dict[str, Any]) -> str:
    design_intent = style_brief.get("design_intent") or {}
    write_contract = style_brief.get("write_contract") or {}
    override_surface = style_brief.get("override_surface") or {}
    architecture_contract = style_brief.get("architecture_contract") or {}

    brand_keywords = ", ".join(design_intent.get("brand_keywords") or []) or "(not specified)"
    tone_keywords = ", ".join(design_intent.get("tone_keywords") or []) or "(not specified)"
    visual_constraints = "\n".join(f"- {item}" for item in (design_intent.get("visual_constraints") or [])) or "- (not specified)"
    allowed_paths = "\n".join(f"- {item}" for item in (write_contract.get("allowed_write_roots") or [])) or "- (none)"
    forbidden_paths = "\n".join(f"- {item}" for item in (write_contract.get("forbidden_write_roots") or [])) or "- (none)"
    open_targets = "\n".join(f"- {item}" for item in (architecture_contract.get("open_target_labels") or [])) or "- artifact_root"

    return (
        "You are styling an AIL Builder project.\n\n"
        "Keep the architecture, routes, generated continuity, and preview flow intact.\n"
        "Do not reposition this as a backend, CMS, dashboard, or production auth/payment system.\n\n"
        f"Project root:\n- {style_brief.get('project_root', '')}\n\n"
        "Current project intent:\n"
        f"- audience: {design_intent.get('audience') or '(not specified)'}\n"
        f"- style_direction: {design_intent.get('style_direction') or '(not specified)'}\n"
        f"- localization_mode: {design_intent.get('localization_mode') or '(not specified)'}\n"
        f"- brand_keywords: {brand_keywords}\n"
        f"- tone_keywords: {tone_keywords}\n"
        f"- notes: {design_intent.get('notes') or '(none)'}\n\n"
        "Visual constraints:\n"
        f"{visual_constraints}\n\n"
        "Safe write scope:\n"
        f"{allowed_paths}\n\n"
        "Do not edit these managed roots directly for durable styling work:\n"
        f"{forbidden_paths}\n\n"
        "Recommended override surfaces:\n"
        f"- theme tokens: {override_surface.get('theme_tokens_path', '')}\n"
        f"- custom CSS: {override_surface.get('custom_css_path', '')}\n"
        f"- override components: {override_surface.get('component_overrides_dir', '')}\n"
        f"- override assets: {override_surface.get('asset_overrides_dir', '')}\n"
        f"- public override assets: {override_surface.get('public_asset_overrides_dir', '')}\n\n"
        "Keep these project continuity targets intact:\n"
        f"{open_targets}\n\n"
        "Working rules:\n"
        "- start with theme tokens and custom CSS before replacing structure\n"
        "- only add override-owned components when visual expression needs extra markup\n"
        "- do not break router wiring to ail-managed continuity files\n"
        "- preserve mobile and desktop readability\n\n"
        "After styling, validate with:\n"
        f"- {((style_brief.get('source_commands') or {}).get('project_style_intent') or '').strip()}\n"
        f"- {((style_brief.get('source_commands') or {}).get('project_serve') or '').strip()}\n"
        f"- PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-apply-check --base-url embedded://local --json\n"
    )


def _build_project_style_apply_summary_text(payload: dict[str, Any]) -> str:
    managed_boundary = payload.get("managed_boundary") or {}
    route_contract = payload.get("route_contract") or {}
    runtime_entry_contract = payload.get("runtime_entry_contract") or {}
    serve_dry_run = payload.get("serve_dry_run") or {}
    override_surface_summary = payload.get("override_surface_summary") or {}
    lines = [
        f"status: {payload.get('status', '')}",
        f"project_root: {payload.get('project_root', '')}",
        f"managed_verified: {managed_boundary.get('verified_count', 0)}",
        f"managed_violations: {managed_boundary.get('violation_count', 0)}",
        f"managed_missing_mirrors: {managed_boundary.get('missing_mirror_count', 0)}",
        f"route_contract_ok: {str(bool(route_contract.get('route_contract_ok'))).lower()}",
        f"runtime_entry_ok: {str(bool(runtime_entry_contract.get('runtime_entry_ok'))).lower()}",
        f"serve_dry_run_status: {serve_dry_run.get('status', '')}",
        f"override_component_files: {override_surface_summary.get('override_component_file_count', 0)}",
        f"override_asset_files: {override_surface_summary.get('override_asset_file_count', 0)}",
    ]
    if payload.get("message"):
        lines.append(f"message: {payload['message']}")
    return "\n".join(lines)


def _build_project_style_brief_payload(ctx: ProjectContext, *, base_url: str | None) -> tuple[dict[str, Any], int]:
    local_mode_reason = ""
    try:
        summary = _build_project_summary_payload(ctx, base_url=base_url, project_id=ctx.project_id)
        preview = _build_project_preview_payload(ctx, base_url=base_url)
        export_payload, export_exit = _build_project_export_handoff_payload(ctx, base_url=base_url)
    except CloudClientError as exc:
        local_mode_reason = str(exc)
        summary, preview, export_payload = _build_local_project_style_brief_context(
            ctx,
            base_url=base_url,
            cloud_error=local_mode_reason,
        )
        export_exit = EXIT_OK
    hook_guide_payload, hook_exit = _build_project_hook_guide_payload(ctx)

    def _abs_path(relpath: str) -> str:
        return str((ctx.root / relpath).resolve())

    allowed_write_roots = [_abs_path(relpath) for relpath in USER_ROOTS]
    discouraged_write_roots = [
        _abs_path("frontend/src/"),
        _abs_path("frontend/public/"),
        _abs_path("src/"),
        _abs_path("backend/"),
    ]
    forbidden_write_roots = [_abs_path(relpath) for relpath in MANAGED_ROOTS]
    override_surface = {
        "root": _abs_path("frontend/src/ail-overrides/"),
        "theme_tokens_path": _abs_path("frontend/src/ail-overrides/theme.tokens.css"),
        "custom_css_path": _abs_path("frontend/src/ail-overrides/custom.css"),
        "component_overrides_dir": _abs_path("frontend/src/ail-overrides/components/"),
        "asset_overrides_dir": _abs_path("frontend/src/ail-overrides/assets/"),
        "public_asset_overrides_dir": _abs_path("frontend/public/ail-overrides/"),
        "readme_path": _abs_path("frontend/src/ail-overrides/README.md"),
    }

    preview_handoff = preview.get("preview_handoff") or {}
    primary_target = preview_handoff.get("primary_target") or {}
    source_diagnosis = (summary.get("source_diagnosis") or {}).get("diagnosis") or {}
    website_delivery_summary = preview.get("website_delivery_summary") or {}
    generated_pages_entries = website_delivery_summary.get("generated_pages_entries") or []
    generated_routes_entries = website_delivery_summary.get("generated_routes_entries") or []
    open_targets = preview.get("open_targets") or []
    style_intent = _load_project_style_intent(ctx)

    recommended_commands = []
    for command in (
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-intent --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-brief --base-url embedded://local --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project export-handoff --base-url embedded://local --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-guide --json",
        f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project serve --install-if-needed --json",
        summary.get("recommended_primary_command"),
    ):
        normalized = str(command or "").strip()
        if normalized and normalized not in recommended_commands:
            recommended_commands.append(normalized)

    next_steps = []
    for source in (
        [f"inspect {_style_intent_path(ctx)}"],
        [f"inspect {override_surface['readme_path']}"],
        [f"inspect {override_surface['theme_tokens_path']}", f"inspect {override_surface['custom_css_path']}"],
        [f"run {command}" for command in recommended_commands],
        export_payload.get("next_steps", []),
        preview.get("next_steps", []),
        hook_guide_payload.get("next_steps", []),
    ):
        for item in source:
            normalized = str(item or "").strip()
            if normalized and normalized not in next_steps:
                next_steps.append(normalized)

    payload = {
        "status": "ok" if export_exit == EXIT_OK and hook_exit == EXIT_OK else "warning",
        "entrypoint": "project-style-brief",
        "project_id": summary["project_id"],
        "project_root": summary["project_root"],
        "style_mode": "architecture_first_model_styling",
        "operator_positioning": "AIL owns architecture and managed generation; external models should style the project through override-safe surfaces.",
        "local_mode": bool(local_mode_reason),
        "local_mode_reason": local_mode_reason,
        "current_profile": source_diagnosis.get("detected_profile", ""),
        "design_intent": {
            **style_intent,
            "style_intent_path": str(_style_intent_path(ctx)),
        },
        "doctor_status": summary.get("doctor_status"),
        "recommended_action": summary.get("recommended_action"),
        "recommended_primary_action": summary.get("recommended_primary_action"),
        "recommended_primary_command": summary.get("recommended_primary_command"),
        "recommended_primary_reason": summary.get("recommended_primary_reason"),
        "preview_hint": preview.get("preview_hint"),
        "website_preview_summary": preview.get("website_preview_summary"),
        "website_delivery_summary": website_delivery_summary,
        "primary_target_label": primary_target.get("label", ""),
        "primary_target_path": primary_target.get("path", ""),
        "open_targets": open_targets,
        "architecture_contract": {
            "surface_kind": (preview.get("website_preview_summary") or {}).get("surface_kind", ""),
            "primary_target_label": primary_target.get("label", ""),
            "primary_target_path": primary_target.get("path", ""),
            "generated_pages_path": website_delivery_summary.get("generated_pages_path", ""),
            "generated_pages_entries": generated_pages_entries,
            "generated_routes_path": website_delivery_summary.get("generated_routes_path", ""),
            "generated_routes_entries": generated_routes_entries,
            "open_target_labels": [item.get("label", "") for item in open_targets],
        },
        "write_contract": {
            "allowed_write_roots": allowed_write_roots,
            "discouraged_write_roots": discouraged_write_roots,
            "forbidden_write_roots": forbidden_write_roots,
            "managed_boundary_rule": "Do not edit managed generated files directly for long-term styling. Prefer token, CSS, component, and asset overrides under frontend/src/ail-overrides or frontend/public/ail-overrides.",
        },
        "override_surface": override_surface,
        "hook_surface": {
            "entrypoint": hook_guide_payload.get("entrypoint"),
            "recommended_page_key": hook_guide_payload.get("recommended_page_key"),
            "recommended_hook_name": hook_guide_payload.get("recommended_hook_name"),
            "preferred_project_hook_command": hook_guide_payload.get("preferred_project_hook_command"),
            "preferred_project_hook_run_command": hook_guide_payload.get("preferred_project_hook_run_command"),
            "cheat_sheet_path": hook_guide_payload.get("cheat_sheet_path"),
        },
        "managed_boundary_rule": "Keep structural generation in managed files. Push lasting visual customization into override-safe files and hook-owned components.",
        "design_prompt_scaffold": {
            "goal": "Keep routes, generated structure, and preview continuity intact while restyling the current website surface.",
            "allowed_edit_strategy": [
                "adjust design tokens first",
                "add scoped CSS overrides next",
                "add hook-owned or override-owned Vue components when layout expression needs new markup",
            ],
            "avoid": [
                "do not rewrite generated router or managed generated views in-place for durable styling work",
                "do not remove required preview targets or managed continuity files",
            ],
        },
        "recommended_commands": recommended_commands,
        "source_commands": {
            "project_style_intent": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-intent --json",
            "project_export_handoff": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project export-handoff --base-url embedded://local --json",
            "project_hook_guide": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project hook-guide --json",
            "project_serve": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project serve --install-if-needed --json",
        },
        "next_steps": next_steps,
    }
    payload["model_prompt"] = _build_project_style_prompt_text(payload)
    return payload, EXIT_OK if payload["status"] == "ok" else max(export_exit, hook_exit)


def _count_files_under(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _managed_mirror_live_path(ctx: ProjectContext, managed_file: Path) -> Path | None:
    try:
        rel = managed_file.resolve().relative_to((ctx.root / "frontend/src/ail-managed").resolve()).as_posix()
    except ValueError:
        return None
    if rel.startswith("views/"):
        return ctx.root / "frontend/src/views" / rel[len("views/"):]
    if rel.startswith("router/"):
        return ctx.root / "frontend/src/router" / rel[len("router/"):]
    return None


def _files_identical(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists() or not left.is_file() or not right.is_file():
        return False
    return left.read_bytes() == right.read_bytes()


def _build_project_style_apply_check_payload(ctx: ProjectContext, *, base_url: str | None) -> tuple[dict[str, Any], int]:
    style_brief_payload, _ = _build_project_style_brief_payload(ctx, base_url=base_url)
    serve_payload, serve_exit = _build_project_serve_payload(
        ctx,
        host="127.0.0.1",
        port=5173,
        install_if_needed=False,
        dry_run=True,
    )

    managed_root = ctx.root / "frontend/src/ail-managed"
    managed_files = sorted(item for item in managed_root.rglob("*") if item.is_file()) if managed_root.exists() else []
    mirror_checks: list[dict[str, Any]] = []
    violation_count = 0
    missing_mirror_count = 0
    verified_count = 0

    for managed_file in managed_files:
        live_path = _managed_mirror_live_path(ctx, managed_file)
        if live_path is None:
            mirror_checks.append(
                {
                    "managed_path": str(managed_file),
                    "live_path": "",
                    "verified": False,
                    "reason": "no_runtime_mirror_rule",
                }
            )
            continue
        verified_count += 1
        live_exists = live_path.exists()
        identical = _files_identical(managed_file, live_path) if live_exists else False
        if not live_exists:
            missing_mirror_count += 1
        elif not identical:
            violation_count += 1
        mirror_checks.append(
            {
                "managed_path": str(managed_file),
                "live_path": str(live_path),
                "verified": True,
                "live_exists": live_exists,
                "identical": identical,
                "status": "ok" if live_exists and identical else ("missing" if not live_exists else "violation"),
            }
        )

    route_index_path = ctx.root / "frontend/src/router/index.ts"
    route_index_text = route_index_path.read_text(encoding="utf-8", errors="replace") if route_index_path.exists() else ""
    route_contract = {
        "route_index_path": str(route_index_path),
        "route_index_exists": route_index_path.exists(),
        "imports_managed_routes": '@/ail-managed/router/routes.generated' in route_index_text,
        "imports_managed_roles": '@/ail-managed/router/roles.generated' in route_index_text,
        "managed_routes_path": str(ctx.root / "frontend/src/ail-managed/router/routes.generated.ts"),
        "managed_routes_exists": (ctx.root / "frontend/src/ail-managed/router/routes.generated.ts").exists(),
        "managed_roles_path": str(ctx.root / "frontend/src/ail-managed/router/roles.generated.ts"),
        "managed_roles_exists": (ctx.root / "frontend/src/ail-managed/router/roles.generated.ts").exists(),
    }
    route_contract["route_contract_ok"] = bool(
        route_contract["route_index_exists"]
        and route_contract["imports_managed_routes"]
        and route_contract["imports_managed_roles"]
        and route_contract["managed_routes_exists"]
        and route_contract["managed_roles_exists"]
    )

    override_root = ctx.root / "frontend/src/ail-overrides"
    override_components_dir = override_root / "components"
    override_assets_dir = override_root / "assets"
    public_override_dir = ctx.root / "frontend/public/ail-overrides"
    override_surface_summary = {
        "override_root": str(override_root),
        "override_root_exists": override_root.exists(),
        "theme_tokens_path": str(override_root / "theme.tokens.css"),
        "theme_tokens_exists": (override_root / "theme.tokens.css").exists(),
        "custom_css_path": str(override_root / "custom.css"),
        "custom_css_exists": (override_root / "custom.css").exists(),
        "override_components_dir": str(override_components_dir),
        "override_component_file_count": _count_files_under(override_components_dir),
        "override_assets_dir": str(override_assets_dir),
        "override_asset_file_count": _count_files_under(override_assets_dir),
        "public_override_dir": str(public_override_dir),
        "public_override_file_count": _count_files_under(public_override_dir),
    }

    runtime_entry_paths = [
        ctx.root / "frontend/src/App.vue",
        ctx.root / "frontend/src/main.ts",
        ctx.root / "frontend/src/main.js",
        ctx.root / "frontend/package.json",
        ctx.root / "frontend/vite.config.ts",
        ctx.root / "frontend/vite.config.js",
    ]
    runtime_entry_summary = {
        "existing_runtime_entries": [str(path) for path in runtime_entry_paths if path.exists()],
        "missing_runtime_entries": [str(path) for path in runtime_entry_paths if not path.exists()],
    }
    runtime_entry_summary["runtime_entry_ok"] = bool(
        (ctx.root / "frontend/package.json").exists()
        and any(path.exists() for path in (ctx.root / "frontend/src/main.ts", ctx.root / "frontend/src/main.js"))
        and any(path.exists() for path in (ctx.root / "frontend/vite.config.ts", ctx.root / "frontend/vite.config.js"))
    )

    managed_boundary = {
        "managed_root": str(managed_root),
        "managed_root_exists": managed_root.exists(),
        "managed_file_count": len(managed_files),
        "verified_count": verified_count,
        "missing_mirror_count": missing_mirror_count,
        "violation_count": violation_count,
        "verification_scope_note": "This check can locally prove mirror integrity for managed router and view files that have runtime copies. It does not claim a full historical diff for every non-override file without a baseline.",
        "mirror_checks": mirror_checks,
    }

    next_steps: list[str] = []
    for item in (
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project style-brief --base-url embedded://local --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project serve --install-if-needed --json",
        f"inspect {override_surface_summary['theme_tokens_path']}",
        f"inspect {override_surface_summary['custom_css_path']}",
    ):
        if item not in next_steps:
            next_steps.append(item)
    for check in mirror_checks:
        if check.get("status") in {"missing", "violation"} and check.get("live_path"):
            step = f"inspect {check['live_path']}"
            if step not in next_steps:
                next_steps.append(step)
    if not route_contract["route_contract_ok"]:
        next_steps.append(f"inspect {route_contract['route_index_path']}")
    for item in serve_payload.get("next_steps", []):
        if item not in next_steps:
            next_steps.append(item)

    status = "ok"
    message = "Style application stayed inside the expected architecture boundary and the local preview path still looks intact."
    exit_code = EXIT_OK
    if not managed_boundary["managed_root_exists"]:
        status = "warning"
        message = "Managed continuity files were not found, so style-apply-check could only run partial local validation."
        exit_code = EXIT_VALIDATION
    if violation_count or missing_mirror_count:
        status = "warning"
        message = "Managed mirror mismatches were found. A styling pass may have edited runtime files that should still match managed continuity copies."
        exit_code = EXIT_VALIDATION
    if not route_contract["route_contract_ok"] or not runtime_entry_summary["runtime_entry_ok"]:
        status = "warning"
        message = "Runtime continuity checks failed. Inspect router or runtime entry files before accepting the styling pass."
        exit_code = EXIT_VALIDATION
    if serve_exit != EXIT_OK:
        status = "warning"
        message = "The style boundary checks ran, but preview dry-run is not currently ready."
        exit_code = max(exit_code, serve_exit)

    payload = {
        "status": status,
        "entrypoint": "project-style-apply-check",
        "project_id": style_brief_payload.get("project_id", ctx.project_id),
        "project_root": style_brief_payload.get("project_root", str(ctx.root)),
        "verification_mode": "local_boundary_and_runtime_continuity",
        "message": message,
        "style_brief": style_brief_payload,
        "managed_boundary": managed_boundary,
        "route_contract": route_contract,
        "runtime_entry_contract": runtime_entry_summary,
        "override_surface_summary": override_surface_summary,
        "serve_dry_run": serve_payload,
        "next_steps": next_steps,
    }
    payload["summary_text"] = _build_project_style_apply_summary_text(payload)
    return payload, exit_code


def _build_project_run_inspect_command_payload(
    ctx: ProjectContext,
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    inspect_payload, exit_code = _build_project_inspect_target_payload(
        ctx,
        label=label,
        base_url=base_url,
    )
    executed_inspect_command = inspect_payload.get("inspect_command")
    next_steps = list(inspect_payload.get("next_steps", []))
    preview_handoff = inspect_payload.get("preview_handoff")
    target = inspect_payload.get("target") or {}
    inspection = inspect_payload.get("inspection") or {}

    if inspection.get("kind") == "file":
        follow_up = f"open or inspect {target.get('path', '')} in your editor"
    elif inspection.get("kind") == "directory":
        follow_up = f"inspect generated entries under {target.get('path', '')}"
    else:
        follow_up = None
    if follow_up and follow_up not in next_steps:
        next_steps.insert(0, follow_up)

    payload = {
        "status": inspect_payload.get("status", "error"),
        "entrypoint": "project-run-inspect-command",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "route_taken": "project_inspect_target",
        "route_reason": "Project run-inspect-command executes the exact inspect target implied by the current preview handoff without changing the underlying inspection semantics.",
        "requested_label": label,
        "resolved_label": inspect_payload.get("resolved_label"),
        "executed_inspect_command": executed_inspect_command,
        "target": target,
        "inspection": inspection,
        "preview_handoff": preview_handoff,
        "preview_hint": inspect_payload.get("preview_hint"),
        "available_labels": inspect_payload.get("available_labels", []),
        "recommended_primary_action": inspect_payload.get("recommended_primary_action"),
        "recommended_primary_command": inspect_payload.get("recommended_primary_command"),
        "recommended_primary_reason": inspect_payload.get("recommended_primary_reason"),
        "result": inspect_payload,
        "next_steps": next_steps,
    }
    return payload, exit_code


def _target_entry(label: str, path: str | Path | None, kind: str) -> dict[str, Any] | None:
    if path is None:
        return None
    path_str = str(path).strip()
    if not path_str:
        return None
    display_name_map = {
        "artifact_root": "Website Output Root",
        "source_of_truth": "AIL Source of Truth",
        "manifest": "AIL Delivery Manifest",
        "last_build": "Last Build Cache",
        "generated_views_dir": "Generated Website Pages",
        "generated_router_dir": "Generated Route Wiring",
        "generated_backend_dir": "Generated Backend Stubs",
        "latest_trial_batch_report": "Latest Website Trial Batch Report",
        "latest_trial_batch_json": "Latest Website Trial Batch JSON",
        "readiness_report": "Website Readiness Report",
        "readiness_snapshot_json": "Website Readiness Snapshot JSON",
        "rc_report": "Website RC Report",
        "rc_results_json": "Website RC Results JSON",
        "project_context": "Project Context",
    }
    website_role_map = {
        "artifact_root": "website_output_root",
        "source_of_truth": "source_of_truth",
        "manifest": "delivery_manifest",
        "last_build": "last_build_cache",
        "generated_views_dir": "generated_pages",
        "generated_router_dir": "generated_routes",
        "generated_backend_dir": "generated_backend",
        "latest_trial_batch_report": "website_trial_report",
        "latest_trial_batch_json": "website_trial_data",
        "readiness_report": "website_readiness_report",
        "readiness_snapshot_json": "website_readiness_data",
        "rc_report": "website_rc_report",
        "rc_results_json": "website_rc_data",
        "project_context": "project_context",
    }
    return {
        "label": label,
        "display_name": display_name_map.get(label, label.replace("_", " ").title()),
        "path": path_str,
        "kind": kind,
        "exists": Path(path_str).exists(),
        "website_role": website_role_map.get(label, "generic_target"),
    }


def _preview_target_priority(label: str) -> int:
    order = {
        "artifact_root": 0,
        "generated_views_dir": 1,
        "generated_router_dir": 2,
        "source_of_truth": 3,
        "generated_backend_dir": 4,
        "manifest": 5,
        "last_build": 6,
        "latest_trial_batch_report": 0,
        "readiness_report": 1,
        "rc_report": 2,
        "project_context": 3,
        "latest_trial_batch_json": 4,
        "readiness_snapshot_json": 5,
        "rc_results_json": 6,
    }
    return order.get(label, 99)


def _target_by_label(open_targets: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    return next((item for item in open_targets if item.get("label") == label), None)


def _build_website_preview_summary(
    open_targets: list[dict[str, Any]],
    primary_target: dict[str, Any],
) -> dict[str, Any]:
    return {
        "surface_kind": "website",
        "primary_target_label": primary_target.get("label", ""),
        "primary_target_display_name": primary_target.get("display_name", ""),
        "primary_target_path": primary_target.get("path", ""),
        "generated_pages_target": _target_by_label(open_targets, "generated_views_dir"),
        "generated_routes_target": _target_by_label(open_targets, "generated_router_dir"),
        "generated_backend_target": _target_by_label(open_targets, "generated_backend_dir"),
        "source_of_truth_target": _target_by_label(open_targets, "source_of_truth"),
        "delivery_manifest_target": _target_by_label(open_targets, "manifest"),
    }


def _list_directory_entries(path_str: str | None, *, limit: int = 12) -> list[str]:
    if not path_str:
        return []
    path = Path(path_str)
    if not path.exists() or not path.is_dir():
        return []
    return [item.name for item in sorted(path.iterdir(), key=lambda item: _directory_entry_priority(item.name))[:limit]]


def _build_website_delivery_summary(
    *,
    project_id: str,
    project_root: str,
    doctor_status: str | None,
    recommended_action: str | None,
    expected_or_detected_profile: str | None,
    latest_build_id: str | None,
    latest_artifact_id: str | None,
    latest_artifact_format: str | None,
    preview_handoff: dict[str, Any] | None,
    project_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    handoff = preview_handoff or {}
    website_preview_summary = handoff.get("website_summary") or {}
    pages_target = website_preview_summary.get("generated_pages_target") or {}
    routes_target = website_preview_summary.get("generated_routes_target") or {}
    backend_target = website_preview_summary.get("generated_backend_target") or {}
    source_target = website_preview_summary.get("source_of_truth_target") or {}
    manifest_target = website_preview_summary.get("delivery_manifest_target") or {}
    check_payload = project_check or {}
    checks = check_payload.get("checks") or {}
    return {
        "surface_kind": "website_delivery",
        "project_id": project_id,
        "project_root": project_root,
        "profile": expected_or_detected_profile or "",
        "doctor_status": doctor_status or "",
        "recommended_action": recommended_action or "",
        "latest_build_id": latest_build_id or "",
        "latest_artifact_id": latest_artifact_id or "",
        "latest_artifact_format": latest_artifact_format or "",
        "primary_preview_target_label": (handoff.get("primary_target") or {}).get("label", ""),
        "primary_preview_target_path": (handoff.get("primary_target") or {}).get("path", ""),
        "generated_pages_path": pages_target.get("path", ""),
        "generated_pages_entries": _list_directory_entries(pages_target.get("path")),
        "generated_routes_path": routes_target.get("path", ""),
        "generated_routes_entries": _list_directory_entries(routes_target.get("path")),
        "generated_backend_path": backend_target.get("path", ""),
        "generated_backend_entries": _list_directory_entries(backend_target.get("path")),
        "source_of_truth_path": source_target.get("path", ""),
        "delivery_manifest_path": manifest_target.get("path", ""),
        "ready_for_sync": checks.get("ready_for_sync"),
        "managed_file_count": (check_payload.get("manifest_summary") or {}).get("managed_file_count"),
    }


def _build_workspace_website_surface_summary() -> dict[str, Any]:
    return {
        "surface_kind": "website_frontier",
        "supported_packs": [
            "Personal Independent Site Pack",
            "Company / Product Website Pack",
            "Ecommerce Independent Storefront Pack",
            "After-Sales Service Website Pack",
        ],
        "partial_packs": [
            "Personal Blog-Style Site Pack",
        ],
        "not_supported": [
            "Full Blog or CMS Platform",
            "Full Ecommerce Platform",
            "Full Application or Dashboard Product",
        ],
        "frontier_summary_path": str(REPO_ROOT / "WEBSITE_FRONTIER_SUMMARY_20260319.md"),
        "delivery_checklist_path": str(REPO_ROOT / "WEBSITE_DELIVERY_CHECKLIST_20260319.md"),
        "demo_pack_path": str(REPO_ROOT / "WEBSITE_DEMO_PACK_20260319.md"),
        "recommended_validation_flow": "trial-run -> project go -> project preview -> project export-handoff",
    }


def _directory_entry_priority(name: str) -> tuple[int, str]:
    preferred = {
        "src": 0,
        "backend": 1,
        ".ail": 2,
        "public": 3,
        "package.json": 4,
        "vite.config.ts": 5,
        "vite.config.js": 6,
        "tsconfig.json": 7,
        "index.html": 8,
        "README.md": 9,
    }
    return (preferred.get(name, 99), name)


def _build_preview_handoff(
    *,
    artifact_path: str | None = None,
    source_path: str | None = None,
    manifest_path: str | None = None,
    last_build_path: str | None = None,
    generated_views_dir: str | None = None,
    generated_router_dir: str | None = None,
    generated_backend_dir: str | None = None,
    project_id: str | None = None,
    build_id: str | None = None,
    base_url: str | None = None,
    include_build_artifact_step: bool = True,
) -> dict[str, Any]:
    targets = [
        _target_entry("artifact_root", artifact_path, "directory"),
        _target_entry("source_of_truth", source_path, "file"),
        _target_entry("manifest", manifest_path, "file"),
        _target_entry("last_build", last_build_path, "file"),
        _target_entry("generated_views_dir", generated_views_dir, "directory"),
        _target_entry("generated_router_dir", generated_router_dir, "directory"),
        _target_entry("generated_backend_dir", generated_backend_dir, "directory"),
    ]
    open_targets = sorted(
        [item for item in targets if item is not None],
        key=lambda item: _preview_target_priority(str(item.get("label") or "")),
    )
    primary_target = open_targets[0] if open_targets else {
        "label": "workspace_root",
        "display_name": "Workspace Root",
        "path": str(REPO_ROOT),
        "kind": "directory",
        "exists": True,
        "website_role": "workspace_root",
    }
    effective_base_url = _effective_base_url(base_url)
    website_summary = _build_website_preview_summary(open_targets, primary_target)

    if primary_target["label"] == "artifact_root":
        preview_hint = f"Open the website output root at {primary_target['path']}"
    elif primary_target["label"] == "generated_views_dir":
        preview_hint = f"Open the generated website pages at {primary_target['path']}"
    elif primary_target["label"] == "source_of_truth":
        preview_hint = f"Open the AIL source of truth at {primary_target['path']}"
    else:
        preview_hint = f"Start with {primary_target['path']}"

    next_steps = [f"inspect {primary_target['path']}"]
    if build_id and include_build_artifact_step:
        next_steps.append(
            f"run PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli build artifact {build_id} --base-url {effective_base_url} --json"
        )
    elif build_id:
        next_steps.append(
            f"run PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli build show {build_id} --base-url {effective_base_url} --json"
        )
    elif project_id:
        next_steps.append(
            f"run PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli cloud status {project_id} --base-url {effective_base_url} --json"
        )
    if source_path:
        next_steps.append(f"inspect {source_path}")

    return {
        "status": "ok",
        "primary_target": primary_target,
        "consumption_kind": "website",
        "website_summary": website_summary,
        "preview_hint": preview_hint,
        "open_targets": open_targets,
        "next_steps": next_steps,
    }


def _project_root_from_cloud_status(cloud_status: dict[str, Any]) -> Path | None:
    latest_build = cloud_status.get("latest_build") or {}
    source_project_root = str(latest_build.get("source_project_root") or "").strip()
    if not source_project_root:
        return None
    return Path(source_project_root)


def _build_cloud_preview_handoff(
    cloud_status: dict[str, Any],
    *,
    project_id: str,
    base_url: str | None,
) -> dict[str, Any]:
    latest_artifact = cloud_status.get("latest_artifact") or {}
    latest_build = cloud_status.get("latest_build") or {}
    project_root = _project_root_from_cloud_status(cloud_status)
    return _build_preview_handoff(
        artifact_path=str(latest_artifact.get("local_path") or ""),
        source_path=str(project_root / ".ail/source.ail") if project_root else None,
        manifest_path=str(project_root / ".ail/manifest.json") if project_root else None,
        last_build_path=str(project_root / ".ail/last_build.json") if project_root else None,
        generated_views_dir=str(project_root / "src/views/generated") if project_root else None,
        generated_router_dir=str(project_root / "src/router/generated") if project_root else None,
        generated_backend_dir=str(project_root / "backend/generated") if project_root else None,
        project_id=project_id,
        build_id=str(latest_build.get("build_id") or ""),
        base_url=base_url,
    )


def _build_trial_handoff(ctx: ProjectContext, cloud_status: dict[str, Any]) -> dict[str, Any]:
    latest_artifact = cloud_status.get("latest_artifact") or {}
    latest_build = cloud_status.get("latest_build") or {}
    return _build_preview_handoff(
        artifact_path=str(latest_artifact.get("local_path") or ""),
        source_path=str(ctx.source_file),
        manifest_path=str(ctx.manifest_file),
        last_build_path=str(ctx.last_build_file),
        generated_views_dir=str(ctx.root / "src/views/generated"),
        generated_router_dir=str(ctx.root / "src/router/generated"),
        generated_backend_dir=str(ctx.root / "backend/generated"),
        project_id=ctx.project_id,
        build_id=str(latest_build.get("build_id") or ""),
        base_url=None,
    )


def _run_project_compile_sync(ctx: ProjectContext, *, base_url: str | None) -> dict[str, Any]:
    manifest_service = ManifestService()
    current_manifest = manifest_service.load_manifest(ctx.manifest_file)
    ail_source = ctx.source_file.read_text(encoding="utf-8")
    client = AILCloudClient(base_url=base_url)
    build_payload = client.compile_ail(ctx.project_id, ail_source, current_manifest)
    manifest_service.save_last_build(ctx.last_build_file, build_payload)
    compile_notices = _compile_notices(client)

    sync_engine = SyncEngine(manifest_service)
    sync_result = sync_engine.sync(
        ctx,
        build_payload,
        current_manifest,
        backup_and_overwrite=False,
    )
    manifest_service.save_manifest(ctx.manifest_file, build_payload["manifest"])

    cloud_status = _build_cloud_status_payload(client, project_id=ctx.project_id)
    handoff = _build_trial_handoff(ctx, cloud_status)
    return {
        "status": "ok",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "action": "compile_sync",
        "build_id": build_payload.get("build_id", ""),
        "managed_files_written": sync_result.written,
        "deleted": sync_result.deleted,
        "compile_notices": compile_notices,
        "cloud": _cloud_summary(client),
        "cloud_status": cloud_status,
        "preview_handoff": handoff,
        "preview_hint": handoff["preview_hint"],
        "open_targets": handoff["open_targets"],
        "next_steps": handoff["next_steps"],
    }


def _build_project_check_payload(ctx: ProjectContext, *, base_url: str | None) -> dict[str, Any]:
    manifest_service = ManifestService()
    sync_engine = SyncEngine(manifest_service)

    source_exists = ctx.source_file.exists()
    manifest_exists = ctx.manifest_file.exists()
    last_build_exists = ctx.last_build_file.exists()

    current_manifest = manifest_service.load_manifest(ctx.manifest_file) if manifest_exists else {}
    last_build = manifest_service.load_last_build(ctx.last_build_file) if last_build_exists else {}
    managed_files = (current_manifest or {}).get("managed_files") or {}
    cached_files = list((last_build or {}).get("files") or [])
    deleted_files = list((last_build or {}).get("deleted_files") or [])

    sync_conflicts: list[dict[str, Any]] = []
    sync_conflict_error = ""
    if manifest_exists and last_build_exists and (cached_files or deleted_files):
        try:
            sync_conflicts = sync_engine.detect_conflicts(ctx, last_build, current_manifest)
        except (SyncError, ValueError) as exc:
            sync_conflict_error = str(exc)

    cloud_status = None
    cloud_status_error = ""
    cloud_status_available = False
    if str((last_build or {}).get("build_id") or "").strip():
        try:
            cloud_status = _build_cloud_status_payload(AILCloudClient(base_url=base_url), project_id=ctx.project_id)
            cloud_status_available = True
        except CloudClientError as exc:
            cloud_status_error = str(exc)

    handoff = _build_trial_handoff(ctx, cloud_status or {"latest_artifact": None})
    checks = {
        "ail_initialized": ctx.ail_dir.exists(),
        "source_exists": source_exists,
        "manifest_exists": manifest_exists,
        "last_build_exists": last_build_exists,
        "cached_build_present": bool(str((last_build or {}).get("build_id") or "").strip()),
        "cached_build_files_present": bool(cached_files),
        "cloud_status_available": cloud_status_available,
        "sync_conflicts_detected": bool(sync_conflicts),
        "ready_for_compile_sync": source_exists,
        "ready_for_sync": bool(cached_files) and not sync_conflicts and not sync_conflict_error,
    }
    manifest_summary = {
        "manifest_version": int((current_manifest or {}).get("manifest_version", 0) or 0),
        "current_build_id": str((current_manifest or {}).get("current_build_id") or ""),
        "managed_file_count": len(managed_files),
    }
    last_build_summary = {
        "build_id": str((last_build or {}).get("build_id") or ""),
        "status": str((last_build or {}).get("status") or ""),
        "created_at": (last_build or {}).get("created_at"),
        "file_count": len(cached_files),
        "deleted_file_count": len(deleted_files),
    }

    status = "ok"
    if not source_exists or not manifest_exists:
        status = "error"
    elif sync_conflicts or sync_conflict_error:
        status = "conflict"
    elif not last_build_exists or cloud_status_error:
        status = "warning"

    return {
        "status": status,
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "checks": checks,
        "manifest_summary": manifest_summary,
        "last_build_summary": last_build_summary,
        "cloud_status": cloud_status,
        "cloud_status_error": cloud_status_error or None,
        "sync_conflicts": sync_conflicts,
        "sync_conflict_summary": SyncEngine.explain_conflicts(sync_conflicts) if sync_conflicts else None,
        "sync_conflict_error": sync_conflict_error or None,
        "preview_handoff": handoff,
        "preview_hint": handoff["preview_hint"],
        "open_targets": handoff["open_targets"],
        "next_steps": _project_check_next_steps(ctx, status, checks, sync_conflicts, cloud_status_available),
    }


def _project_check_next_steps(
    ctx: ProjectContext,
    status: str,
    checks: dict[str, bool],
    sync_conflicts: list[dict[str, Any]],
    cloud_status_available: bool,
) -> list[str]:
    if not checks["source_exists"]:
        return [
            f"create or regenerate {ctx.source_file}",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli generate \"<requirement>\"",
        ]
    if not checks["manifest_exists"]:
        return [
            f"reinitialize manifest at {ctx.manifest_file}",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli init {ctx.root}",
        ]
    if sync_conflicts:
        return [
            "read the drift as a managed sync safety warning, not necessarily a failed website generation",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli conflicts --json",
            "preview the existing output if it already looks useful",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli sync --backup-and-overwrite only when you want backup copies before overwrite",
        ]
    if not checks["last_build_exists"] or not checks["cached_build_files_present"]:
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --compile-sync --base-url embedded://local",
            f"inspect {ctx.source_file}",
        ]
    if not cloud_status_available:
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli cloud status --base-url embedded://local --json",
            "verify the cloud API is reachable for this environment",
        ]
    return [
        f"inspect {ctx.root / 'src/views/generated'}",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project summary --base-url embedded://local --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --compile-sync --base-url embedded://local when source changes",
    ]


def _analyze_project_doctor_state(
    ctx: ProjectContext,
    *,
    base_url: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, str, str, list[str], list[str], list[dict[str, str]]]:
    check_payload = _build_project_check_payload(ctx, base_url=base_url)

    diagnosis_payload = None
    recommended_action = "project_summary"
    doctor_status = check_payload["status"]
    findings: list[str] = []

    if check_payload["status"] == "error":
        findings.append("Project is missing required local AIL state.")
        recommended_action = "repair_project_structure"
    elif check_payload["status"] == "conflict":
        findings.append("Managed-file drift is blocking safe sync.")
        recommended_action = "resolve_sync_conflicts"
    else:
        if check_payload["checks"]["source_exists"]:
            repair_mod = load_repair_module()
            ail_source = ctx.source_file.read_text(encoding="utf-8")
            requirement = _default_requirement_for_ail(repair_mod, ail_source)
            diagnosis = repair_mod.diagnose(requirement, ail_source)
            diagnosis_payload = {
                "requirement": requirement,
                "diagnosis": {
                    key: value
                    for key, value in diagnosis.items()
                    if key != "parsed"
                },
            }
            if diagnosis["compile_recommended"] != "yes":
                doctor_status = "validation_failed"
                findings.append("Current source is not yet a compile candidate.")
                recommended_action = "repair_source"
            elif check_payload["status"] == "warning":
                findings.append("Source is healthy, but project state is incomplete or cloud status is unavailable.")
                recommended_action = "refresh_build_state"
            else:
                findings.append("Source, build cache, cloud status, and sync safety are all healthy.")
                recommended_action = "continue_iteration"

    next_steps = _project_doctor_next_steps(ctx, doctor_status, recommended_action, check_payload, diagnosis_payload)
    fix_plan = _build_project_doctor_fix_plan(ctx, recommended_action)
    return check_payload, diagnosis_payload, recommended_action, doctor_status, findings, next_steps, fix_plan


def _project_summary_recommendation(
    ctx: ProjectContext,
    *,
    recommended_action: str,
    doctor_status: str,
) -> dict[str, str]:
    if doctor_status == "error":
        return {
            "recommended_primary_action": "project_doctor_apply_safe_fixes",
            "recommended_primary_command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project doctor --apply-safe-fixes --base-url embedded://local --json",
            "recommended_primary_reason": f"Restore missing local AIL structure under {ctx.ail_dir} before continuing.",
        }
    if doctor_status == "conflict":
        return {
            "recommended_primary_action": "project_doctor",
            "recommended_primary_command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project doctor --fix-plan --base-url embedded://local --json",
            "recommended_primary_reason": "Managed-file drift is a sync safety guard. Existing output can still be inspected, but make an explicit conflict-resolution decision before overwriting managed files.",
        }
    if recommended_action == "repair_source":
        return {
            "recommended_primary_action": "project_doctor_apply_safe_fixes_and_continue",
            "recommended_primary_command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project doctor --apply-safe-fixes --and-continue --base-url embedded://local --json",
            "recommended_primary_reason": "Current source is not yet a compile candidate; safe repair and continue is the shortest supported recovery path.",
        }
    if recommended_action == "refresh_build_state":
        return {
            "recommended_primary_action": "project_continue_diagnose_compile_sync",
            "recommended_primary_command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local --json",
            "recommended_primary_reason": "Source is healthy, but build or cloud state should be refreshed before further iteration.",
        }
    return {
        "recommended_primary_action": "project_continue_diagnose_compile_sync",
        "recommended_primary_command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local --json",
        "recommended_primary_reason": "Project is healthy; use the safe continue path as the default next iteration action after source changes.",
    }


def _build_project_doctor_payload(
    ctx: ProjectContext,
    *,
    base_url: str | None,
    include_fix_plan: bool = False,
    apply_safe_fixes: bool = False,
    and_continue: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str]], int]:
    check_payload, diagnosis_payload, recommended_action, doctor_status, findings, next_steps, fix_plan = _analyze_project_doctor_state(
        ctx,
        base_url=base_url,
    )
    payload = {
        "status": doctor_status,
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "recommended_action": recommended_action,
        "findings": findings,
        "project_check": check_payload,
        "source_diagnosis": diagnosis_payload,
        "next_steps": next_steps,
    }
    if include_fix_plan:
        payload["fix_plan"] = {
            "mode": "guided_recovery",
            "steps": fix_plan,
        }
    if apply_safe_fixes:
        applied = _apply_project_doctor_safe_fixes(
            ctx,
            recommended_action=recommended_action,
            base_url=base_url,
            diagnosis_payload=diagnosis_payload,
        )
        payload["safe_fix_result"] = applied
        if applied.get("updated_status"):
            payload["status"] = applied["updated_status"]
        if applied.get("updated_recommended_action"):
            payload["recommended_action"] = applied["updated_recommended_action"]
        if applied.get("updated_findings"):
            payload["findings"] = applied["updated_findings"]
        if applied.get("updated_project_check"):
            payload["project_check"] = applied["updated_project_check"]
        if applied.get("updated_source_diagnosis"):
            payload["source_diagnosis"] = applied["updated_source_diagnosis"]
        if applied.get("updated_next_steps"):
            payload["next_steps"] = applied["updated_next_steps"]
    if and_continue:
        continue_result = _continue_after_project_doctor(
            ctx,
            status=payload["status"],
            recommended_action=payload["recommended_action"],
            base_url=base_url,
            safe_fix_result=payload.get("safe_fix_result"),
        )
        payload["continue_result"] = continue_result
        if continue_result.get("status") == "ok":
            payload["status"] = "ok"
            payload["recommended_action"] = "continue_iteration"
            payload["findings"] = [
                "Project doctor completed safe recovery and continued through compile and sync."
            ]
            payload["project_check"] = _build_project_check_payload(ctx, base_url=base_url)
            payload["next_steps"] = continue_result.get("next_steps", payload["next_steps"])
            payload["cloud_status"] = continue_result.get("cloud_status")
            payload["preview_handoff"] = continue_result.get("preview_handoff")
            payload["preview_hint"] = continue_result.get("preview_hint")
            payload["open_targets"] = continue_result.get("open_targets")
        elif continue_result.get("updated_status"):
            payload["status"] = continue_result["updated_status"]
            payload["next_steps"] = continue_result.get("updated_next_steps", payload["next_steps"])

    if payload["status"] == "validation_failed":
        exit_code = EXIT_VALIDATION
    elif payload["status"] == "conflict":
        exit_code = EXIT_CONFLICT
    elif payload["status"] == "error":
        exit_code = EXIT_VALIDATION
    else:
        exit_code = EXIT_OK
    return payload, fix_plan, exit_code


def _run_project_diagnose_compile_sync(ctx: ProjectContext, *, base_url: str | None) -> tuple[dict[str, Any], int]:
    repair_mod = load_repair_module()
    ail_source = ctx.source_file.read_text(encoding="utf-8")
    requirement = _default_requirement_for_ail(repair_mod, ail_source)
    diagnosis = repair_mod.diagnose(requirement, ail_source)
    if diagnosis["compile_recommended"] != "yes":
        payload = {
            "status": "validation_failed",
            "project_id": ctx.project_id,
            "project_root": str(ctx.root),
            "action": "diagnose_compile_sync",
            "requirement": requirement,
            "diagnosis": {
                key: value
                for key, value in diagnosis.items()
                if key != "parsed"
            },
            "next_steps": [
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli diagnose {ctx.source_file} --json",
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli repair {ctx.source_file} --write --json",
                "rerun project continue --diagnose-compile-sync after the source becomes a compile candidate",
            ],
        }
        return payload, EXIT_VALIDATION

    payload = _run_project_compile_sync(ctx, base_url=base_url)
    payload["action"] = "diagnose_compile_sync"
    payload["diagnosed_first"] = True
    return payload, EXIT_OK


def _run_trial_flow(
    ctx: ProjectContext,
    *,
    requirement: str,
    scenario: str,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    created, existing = _initialize_project(ctx)
    repair_mod = load_repair_module()
    manifest_service = ManifestService()
    sync_engine = SyncEngine(manifest_service)
    client = AILCloudClient(base_url=base_url)

    generated_ail = client.generate_ail(requirement)
    normalized = normalize_for_user_source(generated_ail)
    ctx.source_file.write_text(normalized.text.rstrip() + "\n", encoding="utf-8")
    generate_notices = _generate_notices(client, normalized)

    diagnosis = repair_mod.diagnose(requirement, normalized.text)
    detected_profile = diagnosis["detected_profile"]
    repair_used = False
    if diagnosis["compile_recommended"] != "yes":
        repaired = repair_mod.repair(requirement, normalized.text)
        ctx.source_file.write_text(repaired.rstrip() + "\n", encoding="utf-8")
        diagnosis = repair_mod.diagnose(requirement, repaired)
        repair_used = True
        detected_profile = diagnosis["detected_profile"]
        if diagnosis["compile_recommended"] != "yes":
            return (
                {
                    "status": "error",
                    "entrypoint": "trial-run",
                    "route_taken": "trial_run_canonical_flow",
                    "route_reason": "Trial entry uses the canonical frozen-profile flow: generate, diagnose, repair if needed, compile, and sync.",
                    "project_path": str(ctx.root),
                    "scenario": scenario,
                    "detected_profile": detected_profile,
                    "repair_used": repair_used,
                    "diagnosis": {k: v for k, v in diagnosis.items() if k != "parsed"},
                },
                EXIT_VALIDATION,
            )

    current_manifest = manifest_service.load_manifest(ctx.manifest_file)
    build_payload = client.compile_ail(ctx.project_id, ctx.source_file.read_text(encoding="utf-8"), current_manifest)
    manifest_service.save_last_build(ctx.last_build_file, build_payload)
    compile_notices = _compile_notices(client)
    sync_result = sync_engine.sync(ctx, build_payload, current_manifest, backup_and_overwrite=False)
    manifest_service.save_manifest(ctx.manifest_file, build_payload["manifest"])
    notices = [*generate_notices, *compile_notices]
    cloud_status = _build_cloud_status_payload(client, project_id=ctx.project_id)
    handoff = _build_trial_handoff(ctx, cloud_status)
    check_payload, diagnosis_payload, recommended_action, doctor_status, findings, _, _ = _analyze_project_doctor_state(
        ctx,
        base_url=base_url,
    )
    recommendation = _project_summary_recommendation(
        ctx,
        recommended_action=recommended_action,
        doctor_status=doctor_status,
    )

    payload = {
        "status": "ok",
        "entrypoint": "trial-run",
        "route_taken": "trial_run_canonical_flow",
        "route_reason": "Trial entry uses the canonical frozen-profile flow: generate, diagnose, repair if needed, compile, and sync.",
        "project_path": str(ctx.root),
        "scenario": scenario,
        "requirement": requirement,
        "detected_profile": detected_profile,
        "repair_used": repair_used,
        "build_id": build_payload.get("build_id", ""),
        "managed_files_written": sync_result.written,
        "source_of_truth": str(ctx.source_file),
        "manifest": str(ctx.manifest_file),
        "created": created,
        "existing": existing,
        "generate_notices": generate_notices,
        "compile_notices": compile_notices,
        "notices": notices,
        "cloud": _cloud_summary(client),
        "cloud_status": cloud_status,
        "project_check": check_payload,
        "source_diagnosis": diagnosis_payload,
        "doctor_status": doctor_status,
        "doctor_findings": findings,
        "recommended_action": recommended_action,
        "preview_handoff": handoff,
        "preview_hint": handoff["preview_hint"],
        "open_targets": handoff["open_targets"],
        "artifacts": {
            "source_of_truth": str(ctx.source_file),
            "manifest": str(ctx.manifest_file),
            "last_build": str(ctx.last_build_file),
            "generated_views_dir": str(ctx.root / "src/views/generated"),
            "generated_router_dir": str(ctx.root / "src/router/generated"),
            "generated_backend_dir": str(ctx.root / "backend/generated"),
        },
        "next_steps": handoff["next_steps"],
        **recommendation,
    }
    return payload, EXIT_OK


def _run_project_go(
    ctx: ProjectContext,
    *,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    check_payload, diagnosis_payload, recommended_action, doctor_status, _, _, _ = _analyze_project_doctor_state(
        ctx,
        base_url=base_url,
    )
    recommendation = _project_summary_recommendation(
        ctx,
        recommended_action=recommended_action,
        doctor_status=doctor_status,
    )
    executed_primary_action = recommendation["recommended_primary_action"]

    if executed_primary_action == "project_continue_diagnose_compile_sync":
        result_payload, exit_code = _run_project_diagnose_compile_sync(ctx, base_url=base_url)
    elif executed_primary_action == "project_doctor_apply_safe_fixes_and_continue":
        result_payload, _, exit_code = _build_project_doctor_payload(
            ctx,
            base_url=base_url,
            apply_safe_fixes=True,
            and_continue=True,
        )
    elif executed_primary_action == "project_doctor_apply_safe_fixes":
        result_payload, _, exit_code = _build_project_doctor_payload(
            ctx,
            base_url=base_url,
            apply_safe_fixes=True,
        )
    else:
        result_payload, _, exit_code = _build_project_doctor_payload(
            ctx,
            base_url=base_url,
        )

    payload = {
        "status": result_payload.get("status", "error"),
        "entrypoint": "project-go",
        "project_id": ctx.project_id,
        "project_root": str(ctx.root),
        "doctor_status": doctor_status,
        "recommended_action": recommended_action,
        "recommended_primary_action": recommendation["recommended_primary_action"],
        "recommended_primary_command": recommendation["recommended_primary_command"],
        "recommended_primary_reason": recommendation["recommended_primary_reason"],
        "route_taken": executed_primary_action,
        "route_reason": recommendation["recommended_primary_reason"],
        "executed_primary_action": executed_primary_action,
        "project_check": check_payload,
        "source_diagnosis": diagnosis_payload,
        "result": result_payload,
        "next_steps": result_payload.get("next_steps", []),
    }
    if result_payload.get("cloud_status") is not None:
        payload["cloud_status"] = result_payload.get("cloud_status")
    if result_payload.get("preview_handoff") is not None:
        payload["preview_handoff"] = result_payload.get("preview_handoff")
    if result_payload.get("preview_hint") is not None:
        payload["preview_hint"] = result_payload.get("preview_hint")
    if result_payload.get("open_targets") is not None:
        payload["open_targets"] = result_payload.get("open_targets")
    return payload, exit_code


def _run_workspace_go(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    workspace_payload = _build_workspace_status_payload(base_url=base_url)
    executed_workspace_action = workspace_payload["recommended_workspace_action"]

    if executed_workspace_action == "project_go":
        ctx = ProjectContext.discover()
        result_payload, exit_code = _run_project_go(ctx, base_url=base_url)
    elif executed_workspace_action == "trial_run_landing":
        root = Path(tempfile.mkdtemp(prefix="ail_workspace_go."))
        ctx = ProjectContext.discover(root, allow_uninitialized=True)
        result_payload, exit_code = _run_trial_flow(
            ctx,
            requirement=_scenario_requirement("landing"),
            scenario="landing",
            base_url=base_url,
        )
    else:
        result_payload = {
            "status": "warning",
            "entrypoint": "workspace-go",
            "reason": "workspace_not_ready_for_execution",
            "next_steps": [
                f"run bash {RUN_READINESS_SNAPSHOT_SH}",
                "review the latest readiness and RC artifacts before continuing",
            ],
        }
        exit_code = EXIT_VALIDATION

    payload = {
        "status": result_payload.get("status", "error"),
        "entrypoint": "workspace-go",
        "route_taken": executed_workspace_action,
        "route_reason": workspace_payload["recommended_workspace_reason"],
        "executed_workspace_action": executed_workspace_action,
        "recommended_workspace_action": workspace_payload["recommended_workspace_action"],
        "recommended_workspace_command": workspace_payload["recommended_workspace_command"],
        "recommended_workspace_reason": workspace_payload["recommended_workspace_reason"],
        "workspace_status": workspace_payload,
        "result": result_payload,
        "next_steps": result_payload.get("next_steps", workspace_payload.get("next_steps", [])),
    }
    if result_payload.get("preview_handoff") is not None:
        payload["preview_handoff"] = result_payload.get("preview_handoff")
    if result_payload.get("preview_hint") is not None:
        payload["preview_hint"] = result_payload.get("preview_hint")
    if result_payload.get("open_targets") is not None:
        payload["open_targets"] = result_payload.get("open_targets")
    return payload, exit_code


def _run_workspace_continue(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    workspace_payload = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_payload.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        result_payload, exit_code = _run_project_diagnose_compile_sync(ctx, base_url=base_url)
        payload = {
            "status": result_payload.get("status", "error"),
            "entrypoint": "workspace-continue",
            "route_taken": "project_continue_diagnose_compile_sync",
            "route_reason": "Current directory is already inside an initialized AIL project, so the default workspace follow-up path is the safe project continue action.",
            "executed_workspace_action": "project_continue_diagnose_compile_sync",
            "recommended_workspace_action": "project_continue_diagnose_compile_sync",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project continue --diagnose-compile-sync --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the safe project continue path as the default follow-up action after source changes inside the current project.",
            "workspace_status": workspace_payload,
            "result": result_payload,
            "next_steps": result_payload.get("next_steps", workspace_payload.get("next_steps", [])),
        }
        if result_payload.get("preview_handoff") is not None:
            payload["preview_handoff"] = result_payload.get("preview_handoff")
        if result_payload.get("preview_hint") is not None:
            payload["preview_hint"] = result_payload.get("preview_hint")
        if result_payload.get("open_targets") is not None:
            payload["open_targets"] = result_payload.get("open_targets")
        return payload, exit_code

    if workspace_payload.get("readiness_snapshot", {}).get("status") == "ok":
        result_payload, exit_code = _run_workspace_go(base_url=base_url)
        payload = {
            "status": result_payload.get("status", "error"),
            "entrypoint": "workspace-continue",
            "route_taken": "workspace_go",
            "route_reason": "Workspace is healthy and not inside a project, so the default workspace follow-up path is the current repo-level execution route.",
            "executed_workspace_action": "workspace_go",
            "recommended_workspace_action": "workspace_go",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli workspace go --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the current repo-level workspace execution path when no active AIL project is open.",
            "workspace_status": workspace_payload,
            "result": result_payload,
            "next_steps": result_payload.get("next_steps", workspace_payload.get("next_steps", [])),
        }
        if result_payload.get("preview_handoff") is not None:
            payload["preview_handoff"] = result_payload.get("preview_handoff")
        if result_payload.get("preview_hint") is not None:
            payload["preview_hint"] = result_payload.get("preview_hint")
        if result_payload.get("open_targets") is not None:
            payload["open_targets"] = result_payload.get("open_targets")
        return payload, exit_code

    result_payload, exit_code = _build_workspace_doctor_payload(base_url=base_url)
    payload = {
        "status": result_payload.get("status", "error"),
        "entrypoint": "workspace-continue",
        "route_taken": "workspace_doctor",
        "route_reason": "Workspace readiness is not green, so the default workspace follow-up path first routes through workspace recovery diagnosis.",
        "executed_workspace_action": "workspace_doctor",
        "recommended_workspace_action": "workspace_doctor",
        "recommended_workspace_command": (
            f"PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli workspace doctor --base-url {effective_base_url} --json"
        ),
        "recommended_workspace_reason": "Use workspace doctor when repo-level RC or readiness is not yet safe for direct execution.",
        "workspace_status": workspace_payload,
        "result": result_payload,
        "next_steps": result_payload.get("next_steps", workspace_payload.get("next_steps", [])),
    }
    return payload, exit_code


def _build_workspace_doctor_payload(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    workspace_payload = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_payload.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_payload, _, exit_code = _build_project_doctor_payload(
            ctx,
            base_url=base_url,
            include_fix_plan=True,
        )
        payload = {
            "status": project_payload.get("status", "error"),
            "entrypoint": "workspace-doctor",
            "repo_root": str(REPO_ROOT),
            "cwd": str(Path.cwd().resolve()),
            "inside_ail_project": True,
            "route_taken": "project_doctor",
            "route_reason": "Current directory is already inside an initialized AIL project, so the workspace recovery path delegates to the project doctor workbench.",
            "recommended_workspace_action": "project_doctor",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project doctor --fix-plan --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the project doctor to inspect fix plans, conflicts, and safe recovery paths for the current project.",
            "workspace_status": workspace_payload,
            "findings": [
                "Workspace doctor delegated to the current project because an initialized AIL project is active in this directory.",
            ],
            "result": project_payload,
            "next_steps": project_payload.get("next_steps", workspace_payload.get("next_steps", [])),
        }
        return payload, exit_code

    rc_payload = _build_rc_check_payload(base_url=base_url)
    readiness = workspace_payload.get("readiness_snapshot") or {}
    rc_status = rc_payload.get("rc", {}).get("status") or rc_payload.get("status")
    readiness_status = readiness.get("status")

    if rc_payload.get("status") == "ok":
        findings = [
            "Workspace-level RC and readiness are healthy.",
            "The frozen-profile surface is ready for the canonical repo-level trial entry.",
        ]
        payload = {
            "status": "ok",
            "entrypoint": "workspace-doctor",
            "repo_root": str(REPO_ROOT),
            "cwd": str(Path.cwd().resolve()),
            "inside_ail_project": False,
            "route_taken": "workspace_healthy",
            "route_reason": "Workspace-level readiness and RC are green, so the safest next repo-level action is the canonical frozen-profile trial path.",
            "recommended_workspace_action": "trial_run_landing",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli trial-run --scenario landing --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the canonical landing trial to enter the current healthy repo-level workflow.",
            "workspace_status": workspace_payload,
            "rc_check": rc_payload,
            "findings": findings,
            "next_steps": [
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli trial-run --scenario landing --base-url embedded://local --json",
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace go --base-url embedded://local --json",
            ],
        }
        return payload, EXIT_OK

    findings = [
        f"Workspace readiness is currently `{readiness_status or 'unknown'}`.",
        f"RC status is currently `{rc_status or 'unknown'}`.",
        "Refresh the higher-level release view before taking another repo-level execution path.",
    ]
    payload = {
        "status": "attention",
        "entrypoint": "workspace-doctor",
        "repo_root": str(REPO_ROOT),
        "cwd": str(Path.cwd().resolve()),
        "inside_ail_project": False,
        "route_taken": "workspace_rc_recovery",
        "route_reason": "Workspace-level readiness or RC is not green, so the safest repo-level recovery action is to refresh and inspect the release-facing aggregates.",
        "recommended_workspace_action": "rc_check_refresh",
        "recommended_workspace_command": (
            f"PYTHONPATH={REPO_ROOT_STR} "
            f"python3 -m cli rc-check --refresh --base-url {effective_base_url} --json"
        ),
        "recommended_workspace_reason": "Refresh readiness before selecting another workspace execution path.",
        "workspace_status": workspace_payload,
        "rc_check": rc_payload,
        "findings": findings,
        "next_steps": [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli rc-check --refresh --base-url embedded://local --json",
            f"run bash {RUN_RC_CHECKS_SH}",
            "review the latest readiness and RC reports before retrying workspace go",
        ],
    }
    return payload, EXIT_VALIDATION


def _build_workspace_summary_payload(*, base_url: str | None) -> dict[str, Any]:
    payload = _build_workspace_status_payload(base_url=base_url)
    readiness = payload.get("readiness_snapshot") or {}
    rc = payload.get("rc_checks") or {}
    batch = payload.get("latest_trial_batch") or {}
    current_project = payload.get("current_project")
    hook_catalogs = _build_workspace_hooks_payload()

    return {
        "status": "ok",
        "entrypoint": "workspace-summary",
        "repo_root": payload["repo_root"],
        "cwd": payload["cwd"],
        "inside_ail_project": payload["inside_ail_project"],
        "product_surface": {
            "frozen_profiles": ["landing", "ecom_min", "after_sales"],
            "experimental_profiles": ["app_min"],
        },
        "current_project": (
            {
                "project_id": current_project.get("project_id", ""),
                "project_root": current_project.get("project_root", ""),
                "doctor_status": current_project.get("doctor_status", ""),
                "recommended_primary_action": current_project.get("recommended_primary_action", ""),
                "recommended_primary_command": current_project.get("recommended_primary_command", ""),
                "recommended_primary_reason": current_project.get("recommended_primary_reason", ""),
            }
            if current_project
            else None
        ),
        "readiness": {
            "status": readiness.get("status", ""),
            "stage": readiness.get("stage", ""),
            "project_workbench_primary_action_converged": readiness.get("signals", {}).get(
                "project_workbench_primary_action_converged"
            ),
            "trial_entry_route_converged": readiness.get("signals", {}).get("trial_entry_route_converged"),
        },
        "rc": {
            "status": rc.get("status", ""),
            "benchmark_ok": rc.get("checks", {}).get("benchmark_ok"),
            "project_go_ok": rc.get("checks", {}).get("project_go_ok"),
            "project_workbench_primary_action_converged": rc.get("checks", {}).get(
                "project_workbench_primary_action_converged"
            ),
            "trial_entry_route_converged": rc.get("checks", {}).get("trial_entry_route_converged"),
        },
        "latest_trial_batch": {
            "status": batch.get("status", ""),
            "record_count": batch.get("record_count", 0),
            "success_count": batch.get("success_count", 0),
            "repair_required_count": batch.get("repair_required_count", 0),
            "recommended_primary_action_distribution": batch.get("recommended_primary_action_distribution", {}),
            "route_taken_distribution": batch.get("route_taken_distribution", {}),
        },
        "hook_catalogs": {
            key: value
            for key, value in hook_catalogs.items()
            if key not in {"projects", "next_steps", "status", "entrypoint"}
        },
        "recommended_workspace_action": payload["recommended_workspace_action"],
        "recommended_workspace_command": payload["recommended_workspace_command"],
        "recommended_workspace_reason": payload["recommended_workspace_reason"],
        "next_steps": payload["next_steps"],
    }


def _build_workspace_preview_payload(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    workspace_status = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_status.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_preview = _build_project_preview_payload(ctx, base_url=base_url)
        payload = {
            "status": project_preview.get("status", "error"),
            "entrypoint": "workspace-preview",
            "route_taken": "project_preview",
            "route_reason": "Current directory is already inside an initialized AIL project, so workspace preview delegates to the project-level preview handoff.",
            "recommended_workspace_action": "project_preview",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project preview --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the project-level preview handoff when an active project is already open.",
            "workspace_status": workspace_status,
            "result": project_preview,
            "website_preview_summary": project_preview.get("website_preview_summary"),
            "website_delivery_summary": project_preview.get("website_delivery_summary"),
            "preview_handoff": project_preview["preview_handoff"],
            "preview_hint": project_preview["preview_hint"],
            "open_targets": project_preview["open_targets"],
            "next_steps": project_preview["next_steps"],
        }
        return payload, EXIT_OK

    results_dir = REPO_ROOT / "testing/results"
    latest_trial_batch_md = _latest_matching_file(str(results_dir / "first_user_trial_batch_recorded_summary_*.md"))
    latest_trial_batch_json = _latest_matching_file(str(results_dir / "first_user_trial_batch_recorded_summary_*.json"))
    readiness_md = results_dir / "readiness_snapshot.md"
    readiness_json = results_dir / "readiness_snapshot.json"
    rc_report_md = results_dir / "rc_checks_report.md"
    rc_results_json = results_dir / "rc_checks_results.json"

    primary_path = latest_trial_batch_md if latest_trial_batch_md and latest_trial_batch_md.exists() else readiness_md
    primary_label = "latest_trial_batch_report" if latest_trial_batch_md and latest_trial_batch_md.exists() else "readiness_report"
    open_targets = [
        _target_entry(primary_label, primary_path, "file"),
        _target_entry("latest_trial_batch_json", latest_trial_batch_json, "file"),
        _target_entry("readiness_report", readiness_md, "file"),
        _target_entry("readiness_snapshot_json", readiness_json, "file"),
        _target_entry("rc_report", rc_report_md, "file"),
        _target_entry("rc_results_json", rc_results_json, "file"),
        _target_entry("project_context", REPO_ROOT / "PROJECT_CONTEXT.md", "file"),
    ]
    open_targets = sorted(
        [item for item in open_targets if item is not None],
        key=lambda item: _preview_target_priority(str(item.get("label") or "")),
    )
    primary_target = open_targets[0]
    preview_hint = f"Start with {primary_target['path']} to inspect the current website demo, delivery, and readiness surface."

    next_steps = [
        f"inspect {primary_target['path']}",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace go --base-url {effective_base_url} --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli rc-check --refresh --base-url {effective_base_url} --json",
    ]

    payload = {
        "status": "ok",
        "entrypoint": "workspace-preview",
        "route_taken": "workspace_preview_root",
        "route_reason": "No initialized AIL project is active in the current directory, so workspace preview starts from repo-level readiness, RC, and trial artifacts.",
        "recommended_workspace_action": workspace_status["recommended_workspace_action"],
        "recommended_workspace_command": workspace_status["recommended_workspace_command"],
        "recommended_workspace_reason": workspace_status["recommended_workspace_reason"],
        "workspace_status": workspace_status,
        "website_surface_summary": _build_workspace_website_surface_summary(),
        "preview_handoff": {
            "status": "ok",
            "consumption_kind": "website_workspace",
            "primary_target": primary_target,
            "preview_hint": preview_hint,
            "open_targets": open_targets,
            "next_steps": next_steps,
        },
        "preview_hint": preview_hint,
        "open_targets": open_targets,
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_workspace_open_target_payload(
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    workspace_status = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_status.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_payload, exit_code = _build_project_open_target_payload(
            ctx,
            label=label,
            base_url=base_url,
        )
        resolved_for_command = project_payload.get("resolved_label") or label or ""
        command_suffix = f" {resolved_for_command}" if resolved_for_command else ""
        payload = {
            "status": project_payload.get("status", "error"),
            "entrypoint": "workspace-open-target",
            "route_taken": "project_open_target",
            "route_reason": "Current directory is already inside an initialized AIL project, so workspace open-target delegates to the project-level preview target resolver.",
            "requested_label": label,
            "recommended_workspace_action": "project_open_target",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project open-target{command_suffix} --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Resolve one concrete project preview target when an active project is already open.",
            "workspace_status": workspace_status,
            "result": project_payload,
            "next_steps": project_payload.get("next_steps", []),
        }
        for key in (
            "preview_handoff",
            "preview_hint",
            "resolved_label",
            "available_labels",
            "target",
            "inspect_command",
            "message",
        ):
            if project_payload.get(key) is not None:
                payload[key] = project_payload.get(key)
        return payload, exit_code

    preview_payload, _ = _build_workspace_preview_payload(base_url=base_url)
    handoff = preview_payload["preview_handoff"]
    targets = handoff.get("open_targets") or []
    available_labels = [item["label"] for item in targets]
    resolved_label = label or handoff["primary_target"]["label"]
    target = next((item for item in targets if item["label"] == resolved_label), None)

    if target is None:
        payload = {
            "status": "error",
            "entrypoint": "workspace-open-target",
            "route_taken": "workspace_preview_root",
            "route_reason": "No initialized AIL project is active, so workspace open-target resolves one target out of the repo-level preview handoff.",
            "requested_label": label,
            "available_labels": available_labels,
            "message": f"Unknown workspace preview target: {resolved_label}",
            "workspace_status": workspace_status,
            "preview_handoff": handoff,
            "preview_hint": preview_payload.get("preview_hint", ""),
            "next_steps": [
                f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace preview --base-url {effective_base_url} --json",
                "choose one of the available_labels values and rerun workspace open-target",
            ],
        }
        return payload, EXIT_USAGE

    inspect_command = f"inspect {target['path']}"
    next_steps = [
        inspect_command,
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli workspace preview --base-url {effective_base_url} --json",
    ]
    if preview_payload.get("recommended_workspace_command"):
        next_steps.append(f"run {preview_payload['recommended_workspace_command']}")

    payload = {
        "status": "ok",
        "entrypoint": "workspace-open-target",
        "route_taken": "workspace_preview_root",
        "route_reason": "No initialized AIL project is active, so workspace open-target resolves one target out of the repo-level preview handoff.",
        "requested_label": label,
        "resolved_label": resolved_label,
        "available_labels": available_labels,
        "target": target,
        "inspect_command": inspect_command,
        "recommended_workspace_action": preview_payload.get("recommended_workspace_action"),
        "recommended_workspace_command": preview_payload.get("recommended_workspace_command"),
        "recommended_workspace_reason": preview_payload.get("recommended_workspace_reason"),
        "workspace_status": workspace_status,
        "preview_handoff": handoff,
        "preview_hint": preview_payload.get("preview_hint", ""),
        "next_steps": next_steps,
    }
    return payload, EXIT_OK


def _build_workspace_inspect_target_payload(
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    workspace_status = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_status.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_payload, exit_code = _build_project_inspect_target_payload(
            ctx,
            label=label,
            base_url=base_url,
        )
        resolved_for_command = project_payload.get("resolved_label") or label or ""
        command_suffix = f" {resolved_for_command}" if resolved_for_command else ""
        payload = {
            "status": project_payload.get("status", "error"),
            "entrypoint": "workspace-inspect-target",
            "route_taken": "project_inspect_target",
            "route_reason": "Current directory is already inside an initialized AIL project, so workspace inspect-target delegates to the project-level preview target inspector.",
            "requested_label": label,
            "recommended_workspace_action": "project_inspect_target",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project inspect-target{command_suffix} --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Inspect one concrete project preview target when an active project is already open.",
            "workspace_status": workspace_status,
            "result": project_payload,
            "next_steps": project_payload.get("next_steps", []),
        }
        for key in (
            "preview_handoff",
            "preview_hint",
            "resolved_label",
            "available_labels",
            "target",
            "inspection",
            "inspect_command",
            "message",
        ):
            if project_payload.get(key) is not None:
                payload[key] = project_payload.get(key)
        return payload, exit_code

    open_payload, open_exit = _build_workspace_open_target_payload(
        label=label,
        base_url=base_url,
    )
    if open_exit != EXIT_OK:
        payload = {
            "status": open_payload.get("status", "error"),
            "entrypoint": "workspace-inspect-target",
            "requested_label": label,
            "available_labels": open_payload.get("available_labels", []),
            "message": open_payload.get("message", "Unable to resolve workspace preview target."),
            "workspace_status": workspace_status,
            "preview_handoff": open_payload.get("preview_handoff"),
            "preview_hint": open_payload.get("preview_hint"),
            "next_steps": open_payload.get("next_steps", []),
        }
        return payload, open_exit

    inspection = _inspect_resolved_target(open_payload["target"])
    status = "ok" if inspection.get("exists") else "warning"
    exit_code = EXIT_OK if status == "ok" else EXIT_VALIDATION
    next_steps = list(open_payload.get("next_steps", []))
    if open_payload.get("recommended_workspace_command"):
        next_steps.append(f"run {open_payload['recommended_workspace_command']}")

    payload = {
        "status": status,
        "entrypoint": "workspace-inspect-target",
        "route_taken": "workspace_preview_root",
        "route_reason": "No initialized AIL project is active, so workspace inspect-target reads one resolved repo-level preview target directly.",
        "requested_label": label,
        "resolved_label": open_payload["resolved_label"],
        "target": open_payload["target"],
        "inspection": inspection,
        "inspect_command": open_payload["inspect_command"],
        "available_labels": open_payload["available_labels"],
        "recommended_workspace_action": open_payload.get("recommended_workspace_action"),
        "recommended_workspace_command": open_payload.get("recommended_workspace_command"),
        "recommended_workspace_reason": open_payload.get("recommended_workspace_reason"),
        "workspace_status": workspace_status,
        "preview_handoff": open_payload["preview_handoff"],
        "preview_hint": open_payload["preview_hint"],
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_workspace_export_handoff_payload(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    workspace_status = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_status.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_payload, exit_code = _build_project_export_handoff_payload(ctx, base_url=base_url)
        payload = {
            "status": project_payload.get("status", "error"),
            "entrypoint": "workspace-export-handoff",
            "route_taken": "project_export_handoff",
            "route_reason": "Current directory is already inside an initialized AIL project, so workspace export-handoff delegates to the consolidated project handoff bundle.",
            "recommended_workspace_action": "project_export_handoff",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project export-handoff --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Use the consolidated project handoff bundle when an active project is already open.",
            "workspace_status": workspace_status,
            "result": project_payload,
            "project_summary": project_payload.get("project_summary"),
            "project_preview": project_payload.get("project_preview"),
            "website_preview_summary": project_payload.get("website_preview_summary"),
            "website_delivery_summary": project_payload.get("website_delivery_summary"),
            "preview_handoff": project_payload.get("preview_handoff"),
            "preview_hint": project_payload.get("preview_hint"),
            "open_targets": project_payload.get("open_targets", []),
            "primary_target_label": project_payload.get("primary_target_label"),
            "primary_target": project_payload.get("primary_target"),
            "primary_inspection": project_payload.get("primary_inspection"),
            "inspect_command": project_payload.get("inspect_command"),
            "available_labels": project_payload.get("available_labels", []),
            "next_steps": project_payload.get("next_steps", []),
        }
        return payload, exit_code

    summary = _build_workspace_summary_payload(base_url=base_url)
    preview, preview_exit = _build_workspace_preview_payload(base_url=base_url)
    open_payload, open_exit = _build_workspace_open_target_payload(label=None, base_url=base_url)
    inspect_payload, inspect_exit = _build_workspace_inspect_target_payload(label=None, base_url=base_url)

    status = "ok"
    exit_code = EXIT_OK
    if inspect_exit != EXIT_OK:
        status = inspect_payload.get("status", "warning")
        exit_code = inspect_exit
    elif open_exit != EXIT_OK:
        status = open_payload.get("status", "warning")
        exit_code = open_exit
    elif preview_exit != EXIT_OK:
        status = preview.get("status", "warning")
        exit_code = preview_exit

    next_steps: list[str] = []
    for source in (
        inspect_payload.get("next_steps", []),
        preview.get("next_steps", []),
        [f"run {summary.get('recommended_workspace_command')}"] if summary.get("recommended_workspace_command") else [],
    ):
        for item in source:
            if item and item not in next_steps:
                next_steps.append(item)

    payload = {
        "status": status,
        "entrypoint": "workspace-export-handoff",
        "route_taken": "workspace_export_root",
        "route_reason": "No initialized AIL project is active, so workspace export-handoff combines repo-level summary, preview, target resolution, and target inspection into one bundle.",
        "repo_root": summary["repo_root"],
        "cwd": summary["cwd"],
        "inside_ail_project": summary["inside_ail_project"],
        "recommended_workspace_action": summary.get("recommended_workspace_action"),
        "recommended_workspace_command": summary.get("recommended_workspace_command"),
        "recommended_workspace_reason": summary.get("recommended_workspace_reason"),
        "workspace_status": workspace_status,
        "workspace_summary": summary,
        "workspace_preview": preview,
        "website_preview_summary": preview.get("website_preview_summary"),
        "website_surface_summary": _build_workspace_website_surface_summary(),
        "preview_handoff": preview.get("preview_handoff"),
        "preview_hint": preview.get("preview_hint"),
        "open_targets": preview.get("open_targets", []),
        "primary_target_label": open_payload.get("resolved_label"),
        "primary_target": open_payload.get("target"),
        "primary_inspection": inspect_payload.get("inspection"),
        "inspect_command": inspect_payload.get("inspect_command"),
        "available_labels": open_payload.get("available_labels", []),
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_workspace_run_inspect_command_payload(
    *,
    label: str | None,
    base_url: str | None,
) -> tuple[dict[str, Any], int]:
    workspace_status = _build_workspace_status_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    if workspace_status.get("inside_ail_project"):
        ctx = ProjectContext.discover()
        project_payload, exit_code = _build_project_run_inspect_command_payload(
            ctx,
            label=label,
            base_url=base_url,
        )
        resolved_for_command = project_payload.get("resolved_label") or label or ""
        command_suffix = f" {resolved_for_command}" if resolved_for_command else ""
        payload = {
            "status": project_payload.get("status", "error"),
            "entrypoint": "workspace-run-inspect-command",
            "route_taken": "project_run_inspect_command",
            "route_reason": "Current directory is already inside an initialized AIL project, so workspace run-inspect-command delegates to the project-level inspection execution entrypoint.",
            "requested_label": label,
            "recommended_workspace_action": "project_run_inspect_command",
            "recommended_workspace_command": (
                f"PYTHONPATH={REPO_ROOT_STR} "
                f"python3 -m cli project run-inspect-command{command_suffix} --base-url {effective_base_url} --json"
            ),
            "recommended_workspace_reason": "Execute the project-level preview inspection step directly when an active project is already open.",
            "workspace_status": workspace_status,
            "result": project_payload,
            "resolved_label": project_payload.get("resolved_label"),
            "executed_inspect_command": project_payload.get("executed_inspect_command"),
            "target": project_payload.get("target"),
            "inspection": project_payload.get("inspection"),
            "preview_handoff": project_payload.get("preview_handoff"),
            "preview_hint": project_payload.get("preview_hint"),
            "available_labels": project_payload.get("available_labels", []),
            "next_steps": project_payload.get("next_steps", []),
        }
        return payload, exit_code

    inspect_payload, exit_code = _build_workspace_inspect_target_payload(
        label=label,
        base_url=base_url,
    )
    executed_inspect_command = inspect_payload.get("inspect_command")
    next_steps = list(inspect_payload.get("next_steps", []))
    target = inspect_payload.get("target") or {}
    inspection = inspect_payload.get("inspection") or {}

    if inspection.get("kind") == "file":
        follow_up = f"open or inspect {target.get('path', '')} in your editor"
    elif inspection.get("kind") == "directory":
        follow_up = f"inspect repo-level entries under {target.get('path', '')}"
    else:
        follow_up = None
    if follow_up and follow_up not in next_steps:
        next_steps.insert(0, follow_up)

    payload = {
        "status": inspect_payload.get("status", "error"),
        "entrypoint": "workspace-run-inspect-command",
        "route_taken": "workspace_inspect_target",
        "route_reason": "Workspace run-inspect-command executes the exact inspection step implied by the current workspace preview handoff without changing the underlying inspection semantics.",
        "requested_label": label,
        "resolved_label": inspect_payload.get("resolved_label"),
        "executed_inspect_command": executed_inspect_command,
        "target": target,
        "inspection": inspection,
        "preview_handoff": inspect_payload.get("preview_handoff"),
        "preview_hint": inspect_payload.get("preview_hint"),
        "available_labels": inspect_payload.get("available_labels", []),
        "recommended_workspace_action": inspect_payload.get("recommended_workspace_action"),
        "recommended_workspace_command": inspect_payload.get("recommended_workspace_command"),
        "recommended_workspace_reason": inspect_payload.get("recommended_workspace_reason"),
        "workspace_status": workspace_status,
        "result": inspect_payload,
        "next_steps": next_steps,
    }
    return payload, exit_code


def _build_rc_check_payload(*, base_url: str | None) -> dict[str, Any]:
    results_dir = REPO_ROOT / "testing/results"
    rc_path = results_dir / "rc_checks_results.json"
    readiness_path = results_dir / "readiness_snapshot.json"
    latest_trial_batch_path = _latest_matching_file(str(results_dir / "first_user_trial_batch_recorded_summary_*.json"))

    rc = _load_json_optional(rc_path) or {}
    readiness = _load_json_optional(readiness_path) or {}
    trial_batch = _load_json_optional(latest_trial_batch_path) if latest_trial_batch_path else {}
    workspace_summary = _build_workspace_summary_payload(base_url=base_url)
    effective_base_url = _effective_base_url(base_url)

    rc_ok = rc.get("status") == "ok"
    readiness_ok = readiness.get("status") == "ok"
    if rc_ok and readiness_ok:
        recommended_release_action = "workspace_go"
        recommended_release_command = (
            f'PYTHONPATH="{REPO_ROOT_STR}" '
            f"python3 -m cli workspace go --base-url {effective_base_url} --json"
        )
        recommended_release_reason = (
            "RC and readiness are both green; the highest-value next move is to use the unified workspace execution path."
        )
    else:
        recommended_release_action = "run_rc_checks"
        recommended_release_command = f"bash {RUN_RC_CHECKS_SH}"
        recommended_release_reason = (
            "RC or readiness is not green; refresh the release aggregate before taking the next trial or workbench action."
        )

    return {
        "status": "ok" if rc_ok and readiness_ok else "attention",
        "entrypoint": "rc-check",
        "repo_root": str(REPO_ROOT),
        "rc": {
            "status": rc.get("status", ""),
            "benchmark_ok": rc.get("checks", {}).get("benchmark_ok"),
            "project_workbench_primary_action_converged": rc.get("checks", {}).get(
                "project_workbench_primary_action_converged"
            ),
            "trial_entry_route_converged": rc.get("checks", {}).get("trial_entry_route_converged"),
        },
        "readiness": {
            "status": readiness.get("status", ""),
            "stage": readiness.get("stage", ""),
            "project_workbench_ok": readiness.get("project_workbench_ok"),
            "trial_batch_ok": readiness.get("trial_batch_ok"),
            "trial_entry_ok": readiness.get("trial_entry_ok"),
        },
        "benchmark": {
            "release_baseline_ok": readiness.get("signals", {}).get("benchmark_release_baseline_ok"),
            "release_baseline_passed": readiness.get("signals", {}).get("benchmark_release_baseline_passed"),
            "release_baseline_failed": readiness.get("signals", {}).get("benchmark_release_baseline_failed"),
            "release_decision": readiness.get("signals", {}).get("benchmark_release_decision"),
        },
        "latest_trial_batch": {
            "status": (trial_batch or {}).get("status", ""),
            "record_count": (trial_batch or {}).get("record_count", 0),
            "success_count": (trial_batch or {}).get("success_count", 0),
            "repair_required_count": (trial_batch or {}).get("repair_required_count", 0),
            "recommended_primary_action_distribution": (trial_batch or {}).get(
                "recommended_primary_action_distribution", {}
            ),
            "route_taken_distribution": (trial_batch or {}).get("route_taken_distribution", {}),
        },
        "workspace_summary": workspace_summary,
        "recommended_release_action": recommended_release_action,
        "recommended_release_command": recommended_release_command,
        "recommended_release_reason": recommended_release_reason,
        "artifacts": {
            "rc_checks_json": str(rc_path),
            "readiness_snapshot_json": str(readiness_path),
            "latest_trial_batch_json": str(latest_trial_batch_path) if latest_trial_batch_path else "",
        },
        "next_steps": [
            f"run {recommended_release_command}",
            "review the latest RC and readiness summaries before expanding scope",
        ],
    }


def _run_rc_go(*, base_url: str | None) -> tuple[dict[str, Any], int]:
    rc_payload = _build_rc_check_payload(base_url=base_url)
    executed_release_action = rc_payload["recommended_release_action"]

    if executed_release_action == "workspace_go":
        result_payload, exit_code = _run_workspace_go(base_url=base_url)
    else:
        result_payload = {
            "status": "attention",
            "entrypoint": "rc-go",
            "reason": "rc_not_ready_for_execution",
            "next_steps": [
                f"run bash {RUN_RC_CHECKS_SH}",
                "review the latest RC and readiness summaries before continuing",
            ],
        }
        exit_code = EXIT_VALIDATION

    payload = {
        "status": result_payload.get("status", "error"),
        "entrypoint": "rc-go",
        "route_taken": executed_release_action,
        "route_reason": rc_payload["recommended_release_reason"],
        "executed_release_action": executed_release_action,
        "recommended_release_action": rc_payload["recommended_release_action"],
        "recommended_release_command": rc_payload["recommended_release_command"],
        "recommended_release_reason": rc_payload["recommended_release_reason"],
        "rc_check": rc_payload,
        "result": result_payload,
        "next_steps": result_payload.get("next_steps", rc_payload.get("next_steps", [])),
    }
    if result_payload.get("preview_handoff") is not None:
        payload["preview_handoff"] = result_payload.get("preview_handoff")
    if result_payload.get("preview_hint") is not None:
        payload["preview_hint"] = result_payload.get("preview_hint")
    if result_payload.get("open_targets") is not None:
        payload["open_targets"] = result_payload.get("open_targets")
    return payload, exit_code


def _refresh_rc_check_sources() -> dict[str, Any]:
    command = ["bash", RUN_READINESS_SNAPSHOT_SH]
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "status": "ok",
            "refreshed_readiness": True,
            "refreshed_rc": False,
            "command": f"bash {RUN_READINESS_SNAPSHOT_SH}",
            "reason": "Refreshed readiness snapshot before reading the current RC and readiness state.",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except subprocess.CalledProcessError as exc:
        return {
            "status": "warning",
            "refreshed_readiness": False,
            "refreshed_rc": False,
            "command": f"bash {RUN_READINESS_SNAPSHOT_SH}",
            "reason": "Readiness refresh failed, so rc-check is reporting the latest existing artifacts instead.",
            "stdout": (exc.stdout or "").strip(),
            "stderr": (exc.stderr or "").strip(),
            "exit_code": exc.returncode,
        }


def _build_workspace_status_payload(*, base_url: str | None) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    results_dir = REPO_ROOT / "testing/results"
    readiness_path = results_dir / "readiness_snapshot.json"
    rc_path = results_dir / "rc_checks_results.json"
    trial_smoke_path = results_dir / "trial_run_smoke_results.json"
    latest_trial_batch_path = _latest_matching_file(str(results_dir / "first_user_trial_batch_recorded_summary_*.json"))

    readiness_snapshot = _load_json_optional(readiness_path) or {}
    rc_checks = _load_json_optional(rc_path) or {}
    trial_entry = _load_json_optional(trial_smoke_path) or {}
    latest_trial_batch = _load_json_optional(latest_trial_batch_path) if latest_trial_batch_path else None

    current_project = None
    current_project_error = None
    inside_ail_project = False
    try:
        ctx = ProjectContext.discover(cwd)
        inside_ail_project = True
        current_project = _build_project_summary_payload(ctx, base_url=base_url)
    except Exception as exc:
        current_project_error = str(exc)

    effective_base_url = _effective_base_url(base_url)
    if current_project:
        recommended_workspace_action = "project_go"
        recommended_workspace_command = (
            f'PYTHONPATH="{REPO_ROOT_STR}" '
            f"python3 -m cli project go --base-url {effective_base_url} --json"
        )
        recommended_workspace_reason = (
            "Current directory is already inside an initialized AIL project; use the unified project workbench entrypoint."
        )
    elif readiness_snapshot.get("status") == "ok":
        recommended_workspace_action = "trial_run_landing"
        recommended_workspace_command = (
            f'PYTHONPATH="{REPO_ROOT_STR}" '
            f"python3 -m cli trial-run --scenario landing --base-url {effective_base_url} --json"
        )
        recommended_workspace_reason = (
            "Workspace-level readiness is healthy; the fastest supported repo-level entry remains the frozen-profile trial path."
        )
    else:
        recommended_workspace_action = "run_readiness_snapshot"
        recommended_workspace_command = f"bash {RUN_READINESS_SNAPSHOT_SH}"
        recommended_workspace_reason = (
            "Workspace-level readiness is not fully green; refresh the readiness snapshot before choosing the next execution path."
        )

    next_steps = [f"run {recommended_workspace_command}"]
    if current_project:
        next_steps.append(
            "inspect the current project summary and doctor status before making any manual conflict-resolution decision"
        )
    else:
        next_steps.append(
            "inspect the latest readiness snapshot and recorded trial batch before expanding scope"
        )

    return {
        "status": "ok",
        "entrypoint": "workspace-status",
        "repo_root": str(REPO_ROOT),
        "cwd": str(cwd),
        "inside_ail_project": inside_ail_project,
        "current_project": current_project,
        "current_project_error": current_project_error,
        "readiness_snapshot": readiness_snapshot,
        "rc_checks": rc_checks,
        "trial_entry": trial_entry,
        "latest_trial_batch": latest_trial_batch,
        "latest_trial_batch_path": str(latest_trial_batch_path) if latest_trial_batch_path else "",
        "recommended_workspace_action": recommended_workspace_action,
        "recommended_workspace_command": recommended_workspace_command,
        "recommended_workspace_reason": recommended_workspace_reason,
        "next_steps": next_steps,
    }


def _project_doctor_next_steps(
    ctx: ProjectContext,
    status: str,
    recommended_action: str,
    check_payload: dict[str, Any],
    diagnosis_payload: dict[str, Any] | None,
) -> list[str]:
    if recommended_action == "repair_project_structure":
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli init {ctx.root}",
            f"inspect {ctx.ail_dir}",
        ]
    if recommended_action == "resolve_sync_conflicts":
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli conflicts --json",
            "inspect the conflicting managed files reported by project check",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli sync --backup-and-overwrite only if preserving local drift is the right move",
        ]
    if recommended_action == "repair_source":
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli diagnose {ctx.source_file} --json",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli repair {ctx.source_file} --write --json",
            f"rerun PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local",
        ]
    if recommended_action == "refresh_build_state":
        return [
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli cloud status --base-url embedded://local --json",
        ]
    return [
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project summary --base-url embedded://local --json",
        f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local when the source changes",
        f"inspect {ctx.root / 'src/views/generated'}",
    ]


def _build_project_doctor_fix_plan(ctx: ProjectContext, recommended_action: str) -> list[dict[str, str]]:
    plans = {
        "repair_project_structure": [
            {
                "step": "1",
                "title": "Recreate the local AIL project structure",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli init {ctx.root}",
                "rationale": "Restore missing .ail metadata before any higher-level recovery work.",
            },
            {
                "step": "2",
                "title": "Regenerate or restore the source of truth",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli generate \"<requirement>\"",
                "rationale": "Recreate .ail/source.ail so the project can re-enter the mainline workflow.",
            },
        ],
        "resolve_sync_conflicts": [
            {
                "step": "1",
                "title": "Inspect the managed-file drift",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli conflicts --json",
                "rationale": "Confirm which generated files changed locally. This protects local edits and does not by itself mean generation failed.",
            },
            {
                "step": "2",
                "title": "Apply an explicit sync strategy",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli sync --backup-and-overwrite",
                "rationale": "Preserve local drift under .ail/conflicts before restoring managed-zone consistency.",
            },
        ],
        "repair_source": [
            {
                "step": "1",
                "title": "Reconfirm the current source diagnosis",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli diagnose {ctx.source_file} --json",
                "rationale": "Capture the exact validation failure before rewriting the source.",
            },
            {
                "step": "2",
                "title": "Repair the source in place",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli repair {ctx.source_file} --write --json",
                "rationale": "Bring the source back inside the current supported system boundary.",
            },
            {
                "step": "3",
                "title": "Continue through the safe compile path",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local",
                "rationale": "Verify the repaired source and refresh generated output in one step.",
            },
        ],
        "refresh_build_state": [
            {
                "step": "1",
                "title": "Refresh the cached build and manifest",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local",
                "rationale": "Rebuild the current source and sync managed output back into a consistent state.",
            },
            {
                "step": "2",
                "title": "Recheck cloud status",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli cloud status --base-url embedded://local --json",
                "rationale": "Confirm latest build and artifact metadata after the refresh.",
            },
        ],
        "continue_iteration": [
            {
                "step": "1",
                "title": "Review the current project summary",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project summary --base-url embedded://local --json",
                "rationale": "Start from a complete project-level view before the next iteration.",
            },
            {
                "step": "2",
                "title": "Use the safe continue path after editing source",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project continue --diagnose-compile-sync --base-url embedded://local",
                "rationale": "Keep diagnose, compile, and sync aligned during day-to-day iteration.",
            },
        ],
    }
    return plans.get(
        recommended_action,
        [
            {
                "step": "1",
                "title": "Review the current project summary",
                "command": f"PYTHONPATH={REPO_ROOT_STR} python3 -m cli project summary --base-url embedded://local --json",
                "rationale": "Use the project summary as the safest fallback starting point.",
            }
        ],
    )


def _apply_project_doctor_safe_fixes(
    ctx: ProjectContext,
    *,
    recommended_action: str,
    base_url: str | None,
    diagnosis_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    applied_fixes: list[str] = []

    if recommended_action == "repair_project_structure":
        created, existing = _initialize_project(ctx)
        updated_check = _build_project_check_payload(ctx, base_url=base_url)
        updated_status = updated_check["status"]
        updated_recommended_action = "continue_iteration" if updated_status == "ok" else (
            "refresh_build_state" if updated_status == "warning" else "repair_project_structure"
        )
        return {
            "status": "applied",
            "applied_fixes": [*([f"created:{item}" for item in created]), *([f"verified_existing:{item}" for item in existing])],
            "updated_status": updated_status,
            "updated_recommended_action": updated_recommended_action,
            "updated_findings": [
                "Local AIL project structure was initialized or verified.",
            ] if updated_status != "error" else [
                "Project structure repair ran, but the project still needs additional recovery work.",
            ],
            "updated_project_check": updated_check,
            "updated_source_diagnosis": diagnosis_payload,
            "updated_next_steps": _project_doctor_next_steps(
                ctx,
                updated_status,
                updated_recommended_action,
                updated_check,
                diagnosis_payload,
            ),
        }

    if recommended_action == "repair_source":
        if not ctx.source_file.exists():
            return {
                "status": "blocked",
                "applied_fixes": applied_fixes,
                "reason": "source_missing",
                "updated_next_steps": [
                    f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli init {ctx.root}",
                    "regenerate the source before attempting source repair",
                ],
            }
        repair_mod = load_repair_module()
        ail_source = ctx.source_file.read_text(encoding="utf-8")
        requirement = _read_requirement_optional(argparse.Namespace(requirement=None, requirement_file=None)) or _default_requirement_for_ail(repair_mod, ail_source)
        repaired = repair_mod.repair(requirement, ail_source)
        ctx.source_file.write_text(repaired.rstrip() + "\n", encoding="utf-8")
        applied_fixes.append(f"repaired_source:{ctx.source_file}")
        diagnosis_after_raw = repair_mod.diagnose(requirement, repaired)
        diagnosis_after = {
            key: value
            for key, value in diagnosis_after_raw.items()
            if key != "parsed"
        }
        updated_check = _build_project_check_payload(ctx, base_url=base_url)
        updated_status = "warning" if diagnosis_after["compile_recommended"] == "yes" and updated_check["status"] == "warning" else (
            "ok" if diagnosis_after["compile_recommended"] == "yes" and updated_check["status"] == "ok" else "validation_failed"
        )
        updated_recommended_action = (
            "refresh_build_state"
            if diagnosis_after["compile_recommended"] == "yes" and updated_check["status"] == "warning"
            else "continue_iteration"
            if diagnosis_after["compile_recommended"] == "yes"
            else "repair_source"
        )
        return {
            "status": "applied",
            "applied_fixes": applied_fixes,
            "updated_status": updated_status,
            "updated_recommended_action": updated_recommended_action,
            "updated_findings": [
                "Current source was repaired in place using the supported recovery path."
            ] if diagnosis_after["compile_recommended"] == "yes" else [
                "Source repair ran, but the result is still not a compile candidate."
            ],
            "updated_project_check": updated_check,
            "updated_source_diagnosis": {
                "requirement": requirement,
                "diagnosis": diagnosis_after,
            },
            "updated_next_steps": _project_doctor_next_steps(
                ctx,
                updated_status,
                updated_recommended_action,
                updated_check,
                {
                    "requirement": requirement,
                    "diagnosis": diagnosis_after,
                },
            ),
        }

    if recommended_action == "refresh_build_state":
        payload = _run_project_compile_sync(ctx, base_url=base_url)
        applied_fixes.append("refreshed_build_state")
        updated_check = _build_project_check_payload(ctx, base_url=base_url)
        return {
            "status": "applied",
            "applied_fixes": applied_fixes,
            "updated_status": "ok",
            "updated_recommended_action": "continue_iteration",
            "updated_findings": [
                "Build cache, manifest, and managed output were refreshed through compile and sync."
            ],
            "updated_project_check": updated_check,
            "updated_source_diagnosis": diagnosis_payload,
            "updated_next_steps": payload["next_steps"],
            "compile_sync_result": payload,
        }

    if recommended_action == "continue_iteration":
        return {
            "status": "noop",
            "applied_fixes": applied_fixes,
            "updated_status": "ok",
            "updated_recommended_action": "continue_iteration",
            "updated_findings": [
                "No safe fixes were needed; the project is already in a healthy iteration state."
            ],
            "updated_project_check": _build_project_check_payload(ctx, base_url=base_url),
            "updated_source_diagnosis": diagnosis_payload,
            "updated_next_steps": _project_doctor_next_steps(
                ctx,
                "ok",
                "continue_iteration",
                _build_project_check_payload(ctx, base_url=base_url),
                diagnosis_payload,
            ),
        }

    return {
        "status": "blocked",
        "applied_fixes": applied_fixes,
        "reason": "manual_decision_required",
        "updated_next_steps": [
            "review the fix plan before applying any destructive or conflict-resolution action",
            f"run PYTHONPATH={REPO_ROOT_STR} python3 -m cli project doctor --fix-plan --json",
        ],
    }


def _continue_after_project_doctor(
    ctx: ProjectContext,
    *,
    status: str,
    recommended_action: str,
    base_url: str | None,
    safe_fix_result: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_fix_result = safe_fix_result or {}

    if safe_fix_result.get("status") == "applied" and safe_fix_result.get("compile_sync_result"):
        return safe_fix_result["compile_sync_result"]

    if status in {"conflict", "error", "validation_failed"}:
        return {
            "status": "blocked",
            "reason": "state_not_safe_to_continue",
            "updated_status": status,
            "updated_next_steps": safe_fix_result.get("updated_next_steps") or [
                "resolve the blocking project doctor state before attempting compile and sync"
            ],
        }

    if recommended_action in {"continue_iteration", "refresh_build_state"}:
        return _run_project_compile_sync(ctx, base_url=base_url)

    return {
        "status": "blocked",
        "reason": "manual_decision_required",
        "updated_status": status,
        "updated_next_steps": safe_fix_result.get("updated_next_steps") or [
            "review the project doctor fix plan before continuing"
        ],
    }


def _compile_notices(client: AILCloudClient) -> list[str]:
    info = client.last_compile_info or {}
    notices: list[str] = []
    if info.get("removed_flow"):
        notices.append("prepared source for the current compiler by removing unsupported #FLOW lines")
    if info.get("normalized_ui"):
        notices.append("prepared source for the current compiler by normalizing bare #UI tokens")
    if info.get("inserted_sys"):
        notices.append("applied compiler compatibility metadata automatically during compile")
    if info.get("api_variant") == "legacy_compile" and info.get("base_url") != "embedded://local":
        notices.append("used the legacy cloud compile endpoint for server compatibility")
    return notices


def _generate_notices(client: AILCloudClient, normalized: Any) -> list[str]:
    notices: list[str] = []
    used_fallback = bool(client.last_generate_info.get("used_fallback"))
    removed_sys = bool(getattr(normalized, "removed_sys", False))
    if used_fallback and removed_sys:
        notices.append("generated source using the local fallback path and saved it in editable AIL form")
        return notices
    if used_fallback:
        notices.append("generated source using the local fallback path in this environment")
    if removed_sys:
        notices.append("saved user source in editable AIL form for diagnose and iteration")
    return notices


def _cloud_summary(client: AILCloudClient) -> dict[str, str]:
    info = client.last_compile_info or client.last_generate_info or {}
    return {
        "base_url": str(info.get("base_url") or client.base_url),
        "api_variant": str(info.get("api_variant") or "unknown"),
        "endpoint": str(info.get("endpoint") or ""),
    }


def _query_cloud_summary(client: AILCloudClient) -> dict[str, str]:
    info = client.last_query_info or {}
    return {
        "base_url": str(info.get("base_url") or client.base_url),
        "api_variant": str(info.get("api_variant") or "unknown"),
        "endpoint": str(info.get("endpoint") or ""),
    }


def _json_enabled(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def _emit_command_error(args: argparse.Namespace, exit_code: int, code: str, message: str) -> int:
    if _json_enabled(args):
        _print_json_error(code, message, exit_code=exit_code)
    else:
        print(f"error: {message}", file=sys.stderr)
    return exit_code


def _print_json_error(
    code: str,
    message: str,
    *,
    exit_code: int,
    details: dict[str, Any] | None = None,
) -> None:
    error = {
        "code": code,
        "message": message,
        "exit_code": exit_code,
    }
    if details:
        error["details"] = details
    print(
        json.dumps(
            {
                "status": "error",
                "error": error,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
