# MCP-Skeleton Cross-Platform Validation Report

Date: 2026-05-21
Candidate: v0.1.3
Repository: https://github.com/EvanLyu-oss/Ailoom-Context
Historical validation source: https://github.com/EvanLyu-oss/MCP-Skeleton

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

The final v0.1.3 Windows validation for commit `0bdb452` reported:

- Python smoke runner: `25/25`
- `context_scale_benchmark_quick_json_ok`: pass
- stress benchmark: `70/70` cases restored
- `stress_overall_status`: `ready`
- `stress_scale_profile`: `stress`
- stress monorepo fixture: `10` packages x `120` files per package
- `stress_monorepo_max_token_ratio`: `0.0841`
- `stress_realistic_directory_max_token_ratio`: `0.073`
- `stress_best_large_directory_savings_percent`: `93.45`
- `stress_best_long_text_savings_percent`: `54.51`
- `failed`: `0`

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

Windows validation for the v0.1.3 tag (`0bdb452`) reported:

- quick smoke: `25/25`
- stress benchmark: `70/70`
- stress overall status: `ready`
- stress scale profile: `stress`
- stress monorepo fixture: `10` packages x `120` files per package
- best large-directory savings: `93.45%`
- best long-text savings: `54.51%`

## Post-v0.1.3 Dogfood And Config-Onboarding Baseline

After v0.1.3, the project added a safer onboarding path for real repositories:

- `context config` emits and validates `.mcp-skeleton.json`
- `context config --recommend` generates project defaults from real compression analysis
- `context config --recommend --output-report-file ...` writes an audit-friendly Markdown onboarding report
- `testing/dogfood_self_check.py` runs the full sandboxed self-use chain cross-platform

The Python dogfood self-check validates:

- config recommendation
- onboarding report generation
- config validation
- bundle
- inspect
- restore
- SHA256 parity against included source files

macOS validation for commit `3f9c638` reported:

- Python dogfood self-check: `31/31` files restored with matching SHA256
- `config_recommend_status`: `ok`
- `config_validate_status`: `ok`
- `bundle_status`: `ok`
- `inspect_status`: `ok`
- `restore_status`: `ok`
- `compression_ratio`: `0.0076`
- `missing_count`: `0`
- `mismatched_count`: `0`
- Python smoke runner: `28/28`
- Bash smoke runner: `36/36`
- Bash dogfood wrapper: pass

Windows validation for commit `3f9c638` reported:

- Python dogfood self-check: `30/30` files restored with matching SHA256
- `config_recommend_status`: `ok`
- `config_validate_status`: `ok`
- `bundle_status`: `ok`
- `inspect_status`: `ok`
- `restore_status`: `ok`
- `compression_ratio`: `0.0076`
- `missing_count`: `0`
- `mismatched_count`: `0`
- Python smoke runner: `28/28`
- `failed`: `0`

The one-file count difference is expected for this snapshot because the macOS local validation included the newly added Python dogfood script in the source tree before the same update was validated from the Windows tarball context.

## v0.1.4 Release Baseline

v0.1.4 collects the post-v0.1.3 onboarding and dogfood improvements into a release baseline.

macOS validation for commit `4175af0` reported:

- `py_compile`: pass for CLI, compression, benchmark, Python smoke, and Python dogfood entrypoints
- `git diff --check`: pass
- Python smoke runner: `28/28`
- Python dogfood self-check: `31/31` files restored with matching SHA256
- Bash smoke runner: `36/36`
- quick benchmark: `ready`
- quick benchmark restore verification: `93/93`
- quick benchmark scale health: `ok`
- quick benchmark release readiness: `ready`
- quick benchmark regression trends: `no-baseline`
- `monorepo_max_token_ratio`: `0.6554`
- `realistic_directory_max_token_ratio`: `0.084`
- `best_large_directory_savings_percent`: `92.82`
- `best_long_text_savings_percent`: `54.41`

Windows validation for commit `4175af0` reported:

- `py_compile`: pass with exit code `0`
- Python smoke runner: `28/28`
- Python dogfood self-check: `30/30` files restored with matching SHA256
- `dogfood_self_check.status`: `ok`
- `restore_status`: `ok`
- `missing_count`: `0`
- `mismatched_count`: `0`
- quick benchmark: `ready`
- quick benchmark restore verification: `62/62`
- quick benchmark scale health: `ok`
- quick benchmark release readiness: `ready`
- `monorepo_max_token_ratio`: `0.5313`
- `realistic_directory_max_token_ratio`: `0.0718`
- `best_large_directory_savings_percent`: `92.62`
- `best_long_text_savings_percent`: `54.53`

## v0.1.5 macOS Readiness Snapshot

v0.1.5 adds a release-readiness workflow around `context doctor`, structured compression explanations, recommended command args, explicit benchmark baseline saving, and stronger dogfood self-use.

macOS validation for this release-hardening snapshot reported:

- release readiness runner: `6/6`
- Python smoke runner: `32/32`
- Python dogfood self-check: `33/33` files restored with matching SHA256
- dogfood recommended trial compression: `ok`
- `context doctor.restore_check.status`: `ok`
- `context doctor.readiness_status`: `watch` because the full-repo default focus produces advisory recommendations, not blocking restore failures
- Bash smoke runner: `36/36`
- quick benchmark release readiness: `ready`
- quick benchmark restore verification: `93/93`
- quick benchmark scale health: `ok`
- quick benchmark regression trends: `no-baseline`
- quick benchmark baseline saved: `testing/results/release_quick_baseline.json`
- `monorepo_max_token_ratio`: `0.6559`
- `realistic_directory_max_token_ratio`: `0.0821`
- `best_large_directory_savings_percent`: `93.06`
- `best_long_text_savings_percent`: `54.41`

Windows v0.1.5 validation should run `python testing/release_readiness_check.py` after pulling the release candidate. Bash smoke may be skipped automatically on Windows, but Python smoke, dogfood, doctor, quick benchmark, and baseline save should all pass.

Windows validation for commit `3d5f8cd` reported:

- `py_compile`: pass with exit code `0`
- Python smoke runner: `32/32`
- Python dogfood self-check: `32/32` files restored with matching SHA256
- dogfood recommended trial compression: `ok`
- `context doctor.status`: `ok`
- `context doctor.readiness_status`: `watch`
- `context doctor.restore_check.status`: `ok`
- `context doctor.checked/missing/mismatched`: `32/0/0`
- release readiness runner: `5/5` with Bash smoke skipped on Windows
- quick benchmark release readiness: `ready`
- quick benchmark restore verification: `62/62`
- quick benchmark scale health: `ok`
- quick benchmark baseline saved: `testing/results/release_quick_baseline.json`

The Windows `watch` doctor status is advisory only; it reflects the full-repo default focus recommendation and does not indicate a restore or byte-fidelity failure.

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
- Dogfood self-use workflow: validated on macOS and Windows with config recommendation, onboarding report generation, sandbox restore, and SHA256 parity
- Release readiness: `ready` on macOS and Windows

## Notes

This report is a public validation snapshot. It intentionally excludes internal roadmap planning.
