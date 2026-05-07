# MCP-Skeleton

MCP-Skeleton is a dedicated open-source project for lossless context compression.

It turns long text, source files, and directory trees into two coordinated layers:

1. An AI-facing structural skeleton (`MCP-SKL.v1`)
2. A machine-facing exact restore package

That gives us a practical workflow for large repositories and long documents:

- lower token pressure
- exact reconstruction
- structural drift checks
- patch export and controlled replay
- incremental compression for git-scoped change surfaces

## What it does

- `context compress`: build one skeleton + restore package from text, file, or directory input
- `context inspect`: read one bundle without restoring the original source
- `context restore`: reconstruct the original text, file, or directory exactly
- `context apply-check`: check whether an edited candidate still matches the original skeleton boundary
- `context bundle`: export a reusable bundle with compression + inspect + optional apply-check artifacts
- `context patch`: export a patch bundle against the original context package
- `context patch-apply`: replay a patch bundle with dry-run, policy, and merge gates
- `context compress --incremental`: compress only the git change surface for a directory
- `context bundle --incremental`: export one incremental bundle instead of rebundling the full project
- `context patch` and `context patch-apply` on incremental bundles: keep replay scoped to the git change surface

## Why this is different from summarization

This project does not rely on lossy summarization alone.

Instead it separates context into:

- `skeleton_text`: the small, structured surface for AI tools
- `restore_package`: the exact machine-readable source required for lossless restore

That means we can reduce prompt weight without pretending the original source no longer exists.

## Install

```bash
python3 -m pip install .
```

Optional tokenizer-backed metrics:

```bash
python3 -m pip install '.[context-metrics]'
```

On Windows, prefer:

```powershell
py -3 -m pip install '.[context-metrics]'
```

## Quick start

Compress a directory:

```bash
PYTHONPATH="$PWD" python3 -m cli context compress \
  --preset codebase \
  --input-dir ./cli \
  --output-dir /absolute/path/to/context-bundle \
  --json
```

Inspect it:

```bash
PYTHONPATH="$PWD" python3 -m cli context inspect \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --emit-summary
```

Restore it:

```bash
PYTHONPATH="$PWD" python3 -m cli context restore \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --output-dir /absolute/path/to/restore-root \
  --json
```

Create a patch bundle:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --input-dir /absolute/path/to/edited-project \
  --output-dir /absolute/path/to/context-patch \
  --json
```

Preview replay without writing files:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-bundle/context_manifest.json \
  --dry-run \
  --write-dry-run-report /absolute/path/to/dry-run-report.json \
  --output-dir /absolute/path/to/replayed-project \
  --json
```

Preview one incremental replay with incremental metadata in the dry-run report:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --dry-run \
  --write-dry-run-report /absolute/path/to/incremental-dry-run-report.json \
  --output-dir /absolute/path/to/replayed-incremental-surface \
  --json
```

Compress only the git change surface:

```bash
PYTHONPATH="$PWD" python3 -m cli context compress \
  --input-dir ./cli \
  --incremental \
  --base-commit HEAD~1 \
  --output-dir /absolute/path/to/context-incremental-bundle \
  --json
```

Validate one edited incremental surface:

```bash
PYTHONPATH="$PWD" python3 -m cli context apply-check \
  --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --input-dir /absolute/path/to/edited-incremental-surface \
  --json
```

Replay one edited incremental surface:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --output-dir /absolute/path/to/replayed-incremental-surface \
  --json
```

## Benchmarking

Quick benchmark:

```bash
python3 testing/context_scale_benchmark.py --quick
```

Repo-scale benchmark:

```bash
python3 testing/context_scale_benchmark.py --directory ./cli --iterations 2
```

The benchmark compares:

- heuristic metrics
- auto metrics
- tokenizer-backed metrics when available
- full directory bundles vs incremental bundles
- restore verification for both text and directory cases

## Documentation

- `/Users/carwynmac/MCP-Skeleton/CONTEXT_COMPRESSION_PRINCIPLES_20260507.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_COMPRESSION_SPEC_20260428.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_PATCH_POLICY_TEMPLATE_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_TEST_MATRIX_20260428.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_REPO_SCALE_PERFORMANCE_REPORT_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_TOKENIZER_REPO_SCALE_REPORT_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_INCREMENTAL_BENCHMARK_REPORT_20260508.md`

## Scope

This repository is intentionally focused on one line of work:

- lossless context compression
- exact restore
- structural review
- patch and replay workflows
- incremental context transport for large repositories

It does not include the broader website, ecommerce, personal-site, or writing-generation surfaces from the original private parent repository.
