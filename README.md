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
- `context compress --focus-mode ...`: reshape the skeleton for symbols, imports, tree, or writing-outline views
- `context compress --skeleton-density ...`: keep the restore package exact while making large repo and long-text skeletons more selective
- `context compress --exclude ...` plus `.mcp-skeletonignore`: trim generated, dependency, cache, or build paths from directory and incremental bundles
- large directory skeletons now include grouped directory and extension overviews so omitted file-entry detail still keeps structural continuity
- large directory skeletons now prioritize hot subtrees for entry expansion and fold colder subtrees into compact overview blocks
- long-form text skeletons now emit folded chapter outlines so very long drafts keep narrative shape with a lower token budget

## v0.1 stability contract

The current `0.1.x` line is intended to be usable for early public workflows where exact restore matters more than a polished product shell.

Stable in `0.1.x`:

- compressing text, one file, or one directory into `MCP-SKL.v1` plus an exact restore package
- inspecting and restoring text, file, directory, and incremental directory bundles
- full directory restore reconstructs every file, symlink, and empty directory included in the restore package; by default directory compression skips `.git`, `__pycache__`, and `.pytest_cache`
- non-UTF-8 text inputs keep original bytes for restore while using best-effort decode fallback for skeleton structure
- `apply-check` structural drift gates for text, files, directories, and incremental directory surfaces
- patch export and patch replay for text, files, directories, and incremental bundles
- dry-run replay reports, policy-aware replay, and merge-aware replay checks
- skeleton focus modes: `full`, `tree`, `imports`, `symbols`, `writing-outline`
- skeleton density modes: `adaptive`, `standard`, `compact`
- preset-specific skeleton strategies for `generic`, `codebase`, `writing`, `website`, and `ecommerce`
- benchmark reports for synthetic and repeatable repo-derived samples

Experimental in `0.1.x`:

- exact wording and ordering of `skeleton_text`
- scoring thresholds inside `apply-check`
- the adaptive budgeting heuristics for hot subtrees, folded chapters, and omitted entries
- benchmark timings across machines and tokenizer installations
- automatic encoding detection is best-effort when multiple legacy encodings can decode the same byte stream

Command exit behavior:

- exit `0`: command completed and validation gates passed
- exit `2`: invalid usage or invalid input contract
- exit `3`: validation warning, such as `apply-check` drift, policy block, or merge conflict block

When a command returns exit `3` with `--json`, the JSON payload is still the primary artifact to inspect.

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
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --output-dir /absolute/path/to/context-bundle \
  --json
```

For repeatable project-level filtering, add a `.mcp-skeletonignore` file at the input directory root. Blank lines and `#` comments are ignored; simple relative paths and globs such as `dist/`, `node_modules/`, `*.map`, and `generated/*.json` are supported.

Compress the same directory with one symbols-focused skeleton:

```bash
PYTHONPATH="$PWD" python3 -m cli context compress \
  --preset codebase \
  --focus-mode symbols \
  --input-dir ./cli \
  --json
```

Presets do not change restore fidelity, but they do change the AI-facing skeleton strategy. For example, `codebase` spends more budget on imports, symbols, and code-heavy hot subtrees, while `writing` spends more budget on chapter folds, headings, and prose entries.

Compress a long book draft with a tighter skeleton budget:

```bash
PYTHONPATH="$PWD" python3 -m cli context compress \
  --preset writing \
  --skeleton-density compact \
  --text-file /absolute/path/to/book-draft.md \
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

If an incremental bundle reports zero changed, added, and removed paths, inspect `incremental_diagnostics`. A clean git working tree, a path outside the changed scope, ignored files, or filters from `.mcp-skeletonignore` / `--exclude` can all legitimately produce an empty incremental surface.

Incremental restore intentionally reconstructs only that git change surface plus an `.ail_incremental_manifest.json` removed-path manifest. Use a non-incremental directory bundle when you need a complete project-tree restore.

Safe dogfood workflow for active development:

```bash
bash testing/dogfood_self_check.sh
```

The dogfood self-check compresses this repository, inspects the bundle, restores into `testing/results/dogfood-self-check/restore`, and verifies restored file hashes against the included source files. Keep dogfood restore and replay outputs outside the source tree or under ignored result directories. Prefer `patch-apply --dry-run --write-dry-run-report ...` until the replay surface has been inspected.

Validate one edited incremental surface:

```bash
PYTHONPATH="$PWD" python3 -m cli context apply-check \
  --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --input-dir /absolute/path/to/edited-incremental-surface \
  --json
```

Extract one writing-outline skeleton from long-form text:

```bash
PYTHONPATH="$PWD" python3 -m cli context compress \
  --preset writing \
  --focus-mode writing-outline \
  --text-file /absolute/path/to/book-draft.md \
  --emit-skeleton
```

Replay one edited incremental surface:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --output-dir /absolute/path/to/replayed-incremental-surface \
  --json
```

## Roadmap

Current development priorities are tracked in [ROADMAP_20260520.md](ROADMAP_20260520.md). The roadmap keeps future work centered on lossless context compression, exact restore, patch/replay, incremental transport, large-repo benchmarks, and safe dogfood validation.

## Benchmarking

Quick benchmark:

```bash
python3 testing/context_scale_benchmark.py --quick
```

Repo-scale benchmark:

```bash
python3 testing/context_scale_benchmark.py --directory ./cli --iterations 2
```

Realistic repo benchmark:

```bash
python3 testing/context_scale_benchmark.py \
  --directory ./cli \
  --real-directory . \
  --real-text-files README.md CONTEXT_COMPRESSION_PRINCIPLES_20260507.md CONTEXT_COMPRESSION_SPEC_20260428.md CHANGELOG.md
```

The benchmark compares:

- heuristic metrics
- auto metrics
- tokenizer-backed metrics when available
- full directory bundles vs incremental bundles
- focus-mode skeleton variants vs the default full skeleton
- skeleton-density variants for the default full skeleton
- synthetic fixtures vs realistic repo-scale directory/text corpora
- restore verification for both text and directory cases

Recent repeatable benchmark signals on this repository:

- realistic directory corpus: about `661704` source chars to `30903` skeleton chars, with restore verification passing
- realistic text corpus: about `39793` source chars to `3076` skeleton chars, with restore verification passing
- long synthetic manuscript: adaptive and compact chapter-fold skeletons reduced the standard skeleton footprint to about `44.8%`

## Documentation

- `/Users/carwynmac/MCP-Skeleton/CONTEXT_COMPRESSION_PRINCIPLES_20260507.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_COMPRESSION_SPEC_20260428.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_PATCH_POLICY_TEMPLATE_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_TEST_MATRIX_20260428.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_REPO_SCALE_PERFORMANCE_REPORT_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_TOKENIZER_REPO_SCALE_REPORT_20260429.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_INCREMENTAL_BENCHMARK_REPORT_20260508.md`
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_FOCUS_BENCHMARK_REPORT_20260508.md`
- `/Users/carwynmac/MCP-Skeleton/RELEASE_CHECKLIST_0_1.md`

## Scope

This repository is intentionally focused on one line of work:

- lossless context compression
- exact restore
- structural review
- patch and replay workflows
- incremental context transport for large repositories

It does not include the broader website, ecommerce, personal-site, or writing-generation surfaces from the original private parent repository.
