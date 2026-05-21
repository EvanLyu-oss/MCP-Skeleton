# MCP-Skeleton Cross-Platform Validation Report

Date: 2026-05-21
Candidate: v0.1.3
Repository: https://github.com/EvanLyu-oss/MCP-Skeleton

## Summary

MCP-Skeleton reached a cross-platform `ready` benchmark state after validation on macOS and Windows. The v0.1.3 candidate extends the v0.1.2 baseline with stronger benchmark diagnostics, named quick/standard/stress scale profiles, large-directory recommendation guardrails, richer stdout handoff fields, and a public cross-platform testing guide.

The final Windows quick benchmark reported:

- `executive_summary.overall_status`: `ready`
- `release_readiness.status`: `ready`
- `scale_health.status`: `ok`
- `restore_verified`: `62/62`
- `regression_trends.status`: `no-baseline`

The final macOS quick benchmark reported:

- `executive_summary.overall_status`: `ready`
- `release_readiness.status`: `ready`
- `scale_health.status`: `ok`
- `restore_verified`: `93/93`
- `regression_trends.status`: `no-baseline`

The different case counts are expected because the macOS run included tokenizer-backed coverage that was not present in the Windows quick run.

The final v0.1.3 macOS candidate validation reported:

- Python smoke runner: `25/25`
- Bash smoke runner: `36/36`
- dogfood self-check: `30/30` files restored with matching SHA256
- `py_compile`: pass

The final post-v0.1.2 Windows validation before the v0.1.3 candidate reported:

- Python smoke runner: `25/25`
- `context_scale_benchmark_quick_json_ok`: pass
- `failed`: `0`

The Windows v0.1.3 final quick smoke is intentionally left for the external Windows test machine to confirm from the `v0.1.3` tag.

## Validated Fixes

### Windows text restore verification

Earlier Windows validation reported `38/62` restore coverage because text benchmark verification restored through stdout via `--emit-text`, then wrote the emitted text back to disk. On Windows, text-mode stdout handling can introduce newline translation and produce false SHA256 mismatches.

The benchmark now restores text inputs with `context restore --output-file --json` and compares the restored file bytes directly. After the fix, Windows restore coverage improved from `38/62` to `62/62`.

### Large-directory standard density

The synthetic monorepo benchmark exposed an oversized `standard` density skeleton for large directory inputs. The large-directory `standard` profile is now bounded so it remains more complete than adaptive while avoiding skeleton expansion past the source token footprint.

Windows validation after the fix reported:

- `scale_health.status`: `ok`
- `monorepo_token_ratio`: `0.5313`, below the `0.75` threshold
- `realistic_directory_token_ratio`: `0.0724`, below the `0.25` threshold

macOS validation after the fix reported:

- `scale_health.status`: `ok`
- `monorepo_token_ratio`: `0.6557`, below the `0.75` threshold
- `restore_verified`: `93/93`

## macOS Validation

Commands run on macOS:

```bash
python3 -m py_compile cli/ail_cli.py cli/context_compression.py testing/context_scale_benchmark.py
git diff --check
python3 testing/context_scale_benchmark.py --quick --output-json testing/results/standard_density_watch_fix_2.json --output-md testing/results/standard_density_watch_fix_2.md
bash testing/run_cli_checks.sh
bash testing/dogfood_self_check.sh
```

Results:

- `py_compile`: pass
- `git diff --check`: pass
- quick benchmark: pass, `ready`
- CLI smoke: `36/36`
- dogfood self-check: `27/27` files restored with matching SHA256

## Windows Validation

Commands run on Windows:

```powershell
python -m py_compile cli/ail_cli.py cli/context_compression.py testing/context_scale_benchmark.py
python testing/context_scale_benchmark.py --quick --output-json testing/results/windows_quick_benchmark.json --output-md testing/results/windows_quick_benchmark.md
```

Windows did not have Bash available, so `testing/run_cli_checks.sh` was not executed there.

Results:

- `py_compile`: pass
- quick benchmark: pass, `ready`
- `restore_verified`: `62/62`
- `release_readiness.status`: `ready`
- `scale_health.status`: `ok`
- `regression_trends.status`: `no-baseline`

## Post-v0.1.1 Windows Python Smoke

After v0.1.1, a Python-native smoke runner was added for Windows environments without Bash:

```powershell
python testing/run_cli_checks.py
```

Windows validation initially reported `10/11` checks passing and exposed a real text patch replay issue: text patch candidate snapshots were written and replayed through text-mode file handling, which could alter newline layout and break byte-level SHA256 equality.

The text patch path now writes candidate snapshots as raw bytes and replays those bytes directly. After the fix, Windows validation reported:

- `runner`: `python`
- `check_count`: `11`
- `passed`: `11`
- `failed`: `0`
- `context_apply_patch_roundtrip_json_ok`: pass

This confirms that text patch snapshot/replay now preserves candidate bytes exactly across platforms.

## v0.1.2 Python Smoke Baseline

After the text patch fix, the Python runner was expanded from `11` checks to `25` checks so Windows can validate more of the same context surface that the Bash runner covers on macOS and Unix-like environments.

Newly covered paths include:

- `context_compress_text_writing_outline_json_ok`
- `context_compress_text_density_json_ok`
- `context_compress_directory_symbols_json_ok`
- `context_compress_directory_aggregation_json_ok`
- `context_patch_text_json_ok`
- `context_patch_incremental_json_ok`

macOS validation for commit `a47b5fc` reported:

- Python smoke runner: `25/25`
- Bash smoke runner: `36/36`
- dogfood self-check: `29/29` files restored with matching SHA256

Windows validation for the same mainline update reported:

- Python smoke runner: `25/25`
- `failed`: `0`
- update method: tarball download, because Git HTTPS timed out on the test machine

## v0.1.3 Benchmark And Testing Baseline

After v0.1.2, the benchmark harness was expanded to make large-directory and long-text tuning easier to validate:

- recommendation diagnostics now include per-source grouping, candidate counts, token savings percentages, token-ratio span, and compression-time comparisons
- the writing preset now preserves text-density budgets for single text inputs, restoring meaningful adaptive/compact long-text savings without changing restore fidelity
- scale-health checks now guard the best verified monorepo and realistic-directory skeleton size ratio versus `full + standard` baselines
- `--scale-profile quick`, `--scale-profile standard`, and `--scale-profile stress` provide repeatable test-machine benchmark profiles while preserving the legacy `--quick` shortcut
- benchmark stdout `executive_summary` now carries scale profile, case count, monorepo fixture size, token-ratio guardrails, and best savings signals
- `CROSS_PLATFORM_TESTING.md` documents quick smoke, stress benchmark, and compact result reporting flows

macOS validation for commit `677d11e` reported:

- Python smoke runner: `25/25`
- Bash smoke runner: `36/36`
- dogfood self-check: `30/30` files restored with matching SHA256
- `py_compile`: pass

## Release Readiness

The v0.1.3 candidate has no known blocking restore failures in the validated surfaces.

Current status:

- Lossless restore: validated on macOS and Windows quick benchmark paths
- Directory restore: validated on macOS smoke and quick benchmark, and Windows quick benchmark
- Text restore: validated on macOS and Windows quick benchmark
- Monorepo benchmark health: `ok`
- Large-directory token guardrails: `ok`
- Benchmark scale profiles: `quick`, `standard`, and `stress`
- Cross-platform testing workflow: documented in `CROSS_PLATFORM_TESTING.md`
- Release readiness: `ready`

## Notes

This report is a public validation snapshot. It intentionally excludes internal roadmap planning.
