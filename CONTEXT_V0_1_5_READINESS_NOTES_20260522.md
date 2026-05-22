# MCP-Skeleton v0.1.5 Readiness Notes

## Goal

v0.1.5 focuses on making MCP-Skeleton safer and easier to use on real large repositories and long text projects without expanding into unrelated product lines.

## Completed Scope

- `context doctor` provides a single readiness check for config resolution, compression advice, temporary sandbox restore, and byte/hash parity.
- `context compress --json` includes structured `compression_explanations` alongside warnings, recommendations, recommended config, and recommended command args.
- `context config --recommend` includes recommended command args in JSON and Markdown onboarding reports.
- `testing/context_scale_benchmark.py --save-baseline-json` saves a current run as a future regression baseline.
- `testing/dogfood_self_check.py` now trial-runs the recommended compression args before bundle, inspect, restore, and SHA256 parity checks.

## Stability Contract

- Restore remains byte-exact for included files and text/file payloads.
- Doctor and dogfood restore into temporary or ignored result directories; they do not patch or replay source trees.
- Warnings and explanations are advisory signals only; they do not change restore-package content.
- Benchmark baselines are explicit files and do not modify source code.

## Suggested Validation Before Tagging

```bash
python3 -m py_compile cli/ail_cli.py cli/context_compression.py testing/context_scale_benchmark.py testing/run_cli_checks.py testing/dogfood_self_check.py
python3 testing/run_cli_checks.py
python3 testing/dogfood_self_check.py
bash testing/run_cli_checks.sh
python3 testing/context_scale_benchmark.py --scale-profile quick --save-baseline-json testing/results/context_scale_baseline.json
```

## Windows Handoff

After macOS validation passes, run the Python smoke runner and dogfood self-check on Windows first. Run the quick benchmark with `--save-baseline-json` only after the smoke and dogfood checks pass.
