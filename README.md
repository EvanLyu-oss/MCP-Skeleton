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

## Quickstart

For macOS, from a cloned or downloaded checkout:

```bash
sh install.sh
mcp-skeleton demo
mcp-skeleton quick --input-dir .
mcp-skeleton quick --reuse-if-fresh --input-dir .
```

What these do:

- `install.sh` installs an isolated local command and prints PATH guidance.
- `demo` runs a safe sample bundle so you can see the workflow before using your own project.
- `quick` creates a restore-safe bundle for the current directory and prints the skeleton, manifest, inspect, and restore commands.
- `quick --reuse-if-fresh` reuses the last unchanged bundle instead of recompressing large projects.

The human output for `quick`, `doctor`, and `recent` starts with an `At a glance` card so first-time users can immediately see status, restore safety, token savings, speed/freshness, and the next command to copy. `quick` also explains the slowest visible phase, suggests the best next command (`--fast` or `--reuse-if-fresh`) for large or slower runs, and explains why tiny projects may expand instead of saving tokens.

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
- non-UTF-8 and UTF-16/BOM text inputs keep original bytes for restore while using best-effort decode fallback for skeleton structure
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

macOS one-command local install from a cloned or downloaded checkout:

```bash
sh install.sh
```

This creates an isolated virtual environment under `~/.mcp-skeleton`, installs tokenizer-backed metrics, and links the `mcp-skeleton` command into `~/.local/bin`.
The installer finishes with a command check, PATH status, a first-run self-check, and a copy/paste `quick` command so you can start on the current project immediately.

Check the installed command:

```bash
mcp-skeleton version
```

`mcp-skeleton version` reports install readiness, Python status, command availability, and the first `quick` / `doctor` commands to run.

Update from a newer downloaded checkout:

```bash
sh install.sh --update
```

Uninstall the managed command and virtual environment:

```bash
sh install.sh --uninstall
```

If `~/.local/bin` is not on your PATH, add:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Python package install:

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

Zero-learning project setup:

```bash
mcp-skeleton start --input-dir .
```

`context start` recommends a config, writes `.mcp-skeleton.json`, writes `mcp-skeleton-onboarding.md`, runs a restore-safety doctor check, and prints a copy/paste-ready command plus plain next steps. JSON output also includes `recommended_command_text` and `action_plan` for wrappers or test machines.
If you do not pass `--preset`, `--focus-mode`, or `--skeleton-density`, MCP-Skeleton now chooses practical defaults from the input type: code directories use codebase/imports/adaptive, prose files use writing/writing-outline/adaptive, and explicit CLI/config choices still win.

One-command bundle creation:

Try MCP-Skeleton without preparing your own project first:

```bash
mcp-skeleton demo
```

`demo` creates a lightweight sample project, builds a safe bundle, verifies restore safety, shows token impact, and prints inspect/restore commands.

One-command bundle creation for your project:

```bash
mcp-skeleton quick --input-dir .
```

`context quick` runs the zero-friction setup, checks restore safety, writes a full bundle, and prints the bundle path plus inspect/restore commands. It also points out the exact `context_skeleton.mcp` file to give to an AI or IDE, the bundle folder to keep, and a copy/paste `open <bundle>` command for locating the generated files on macOS.
The first screen includes a `Use this now` section with the skeleton file, estimated token savings, restore command, and inspect command.
It also prints performance advice with `fast / ok / slow` status and copy/paste `--fast` / `--reuse-if-fresh` commands when those paths improve the experience.

To preview the plan without writing a bundle:

```bash
mcp-skeleton quick --preview --input-dir .
```

`--preview` checks restore safety, estimates token savings, shows the planned bundle/manifest paths, prints performance advice, and gives the exact command to run for real.

To open the bundle folder automatically on macOS after creation:

```bash
mcp-skeleton quick --input-dir . --open
```

To copy the generated skeleton text directly to the macOS clipboard:

```bash
mcp-skeleton quick --input-dir . --copy-command
```

To find the last quick bundle for the current project later:

```bash
mcp-skeleton recent --input-dir .
```

`recent` reads `.workspace_ail/recent_quick.json` and prints the last bundle path, skeleton file, manifest, open command, clipboard command, inspect command, and restore command.
It also checks whether the project appears to have changed since the last quick bundle; if the bundle may be stale, it prints a copy/paste refresh command.

For very large directories where you want the fastest safe bundle path, use:

```bash
mcp-skeleton quick --fast --input-dir .
```

`--fast` skips config recommendation/onboarding generation but still runs sandbox restore verification before creating the bundle.
Standard `quick` will also print a speed tip with a copy/paste `--fast` command when the input is large enough that the faster path is likely to feel better.

If you already created a quick bundle and want to avoid recompressing unchanged projects:

```bash
mcp-skeleton quick --reuse-if-fresh --input-dir .
```

When the previous bundle is still fresh, this reuses it immediately and prints the same handoff commands. If the project changed or the bundle files are missing, MCP-Skeleton falls back to a normal quick run.

Generated MCP-Skeleton work artifacts under `.workspace_ail/` are skipped by default so repeated `context quick` or dogfood runs do not pollute later compression or benchmark results.

Explain a bundle in plain language:

```bash
mcp-skeleton explain \
  --package-file /absolute/path/to/context-bundle/context_manifest.json
```

`context explain` translates a bundle into “what this is”, “why it is useful”, and “what to do next”, including restore guidance. It is the fastest way to hand a bundle to another AI, IDE, or teammate without making them learn the manifest shape.

Compress a directory:

```bash
mcp-skeleton compress \
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
mcp-skeleton compress \
  --preset codebase \
  --focus-mode symbols \
  --input-dir ./cli \
  --json
```

Presets do not change restore fidelity, but they do change the AI-facing skeleton strategy. For example, `codebase` spends more budget on imports, symbols, and code-heavy hot subtrees, while `writing` spends more budget on chapter folds, headings, and prose entries.

Compress a long book draft with a tighter skeleton budget:

```bash
mcp-skeleton compress \
  --preset writing \
  --skeleton-density compact \
  --text-file /absolute/path/to/book-draft.md \
  --json
```

Inspect it:

```bash
mcp-skeleton inspect \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --emit-summary
```

Restore it:

```bash
mcp-skeleton restore \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --output-dir /absolute/path/to/restore-root \
  --json
```

Create a patch bundle:

```bash
mcp-skeleton patch \
  --package-file /absolute/path/to/context-bundle/context_manifest.json \
  --input-dir /absolute/path/to/edited-project \
  --output-dir /absolute/path/to/context-patch \
  --json
```

Preview replay without writing files:

```bash
mcp-skeleton patch-apply \
  --patch-file /absolute/path/to/context-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-bundle/context_manifest.json \
  --dry-run \
  --write-dry-run-report /absolute/path/to/dry-run-report.json \
  --output-dir /absolute/path/to/replayed-project \
  --json
```

Preview one incremental replay with incremental metadata in the dry-run report:

```bash
mcp-skeleton patch-apply \
  --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --dry-run \
  --write-dry-run-report /absolute/path/to/incremental-dry-run-report.json \
  --output-dir /absolute/path/to/replayed-incremental-surface \
  --json
```

Compress only the git change surface:

```bash
mcp-skeleton compress \
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
python3 testing/dogfood_self_check.py
bash testing/dogfood_self_check.sh
```

The dogfood self-check recommends an ignored `.mcp-skeleton.json`, writes an onboarding report, validates the config, trial-runs the recommended compression argv, compresses this repository, inspects the bundle, restores into `testing/results/dogfood-self-check/restore`, and verifies restored file hashes against the included source files. Keep dogfood restore and replay outputs outside the source tree or under ignored result directories. Prefer `patch-apply --dry-run --write-dry-run-report ...` until the replay surface has been inspected.

Readiness doctor for one source:

```bash
mcp-skeleton doctor --input-dir . --preset codebase --json
mcp-skeleton doctor --input-dir . --preset codebase --write-report mcp-skeleton-readiness.md --json
```

`context doctor` resolves config defaults, runs compression analysis, emits warnings/recommendations/explanations, restores into a temporary sandbox, and verifies the restored files against the original included hashes. It reports `readiness_status` as `ready`, `watch`, or `blocked`, plus `recommended_command_text` and `action_plan` so users know exactly what to do next.

If something goes wrong:

```bash
mcp-skeleton quick --input-dir ./missing --json
```

Error JSON includes `recovery_steps` and, when MCP-Skeleton can suggest one safely, `fix_command_text`. Human-readable errors print the same recovery hints. `context quick` also refuses to write into a non-empty `--output-dir`, so an existing bundle is not overwritten by accident.

Validate one edited incremental surface:

```bash
mcp-skeleton apply-check \
  --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json \
  --input-dir /absolute/path/to/edited-incremental-surface \
  --json
```

Extract one writing-outline skeleton from long-form text:

```bash
mcp-skeleton compress \
  --preset writing \
  --focus-mode writing-outline \
  --text-file /absolute/path/to/book-draft.md \
  --emit-skeleton
```

Replay one edited incremental surface:

```bash
mcp-skeleton patch-apply \
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

Named benchmark scale profiles:

```bash
python3 testing/context_scale_benchmark.py --scale-profile quick
python3 testing/context_scale_benchmark.py --scale-profile standard
python3 testing/context_scale_benchmark.py --scale-profile stress
```

Save a run as the next regression baseline:

```bash
python3 testing/context_scale_benchmark.py --scale-profile quick --save-baseline-json testing/results/context_scale_baseline.json
```

Cross-platform smoke checks, including Windows environments without Bash:

```bash
python3 testing/run_cli_checks.py
```

Quickstart drift check for the README install/demo/quick/reuse path:

```bash
python3 testing/quickstart_check.py
```

Release readiness check before tagging:

```bash
python3 testing/release_readiness_check.py
```

The release readiness JSON includes a top-level `executive_summary` with the quick answer: total passed/failed checks, smoke and quickstart counts, dogfood restore status, doctor readiness, benchmark health, restore coverage, and the next action.

For repeatable test-machine prompts, stress benchmark commands, and result reporting templates, see [CROSS_PLATFORM_TESTING.md](CROSS_PLATFORM_TESTING.md).

This Python runner covers key text, writing-outline, text-density, directory, bundle, filtering, focus/density, directory symbols/aggregation, incremental, clean incremental diagnostics, apply-check drift, text and incremental patch manifests, incremental patch replay, patch/replay, merge-conflict, dry-run report, policy template/block, invalid-input, invalid-restore-path, and benchmark readiness paths.

`context compress --json` also emits `source_scale_profile`, `compression_warnings`, `compression_recommendations`, `recommended_config`, and `recommended_command_args` so users can spot token expansion, large-directory risk, missing filters, or low-savings configurations and switch to a better focus/density without changing restore fidelity. `recommended_command_args` is a machine-readable argv list that scripts can reuse for the next compression run.

Project defaults can live in `.mcp-skeleton.json`, `.mcp-skeleton.yaml`, or `.mcp-skeleton.yml` next to the input directory, or be passed explicitly with `--config`:

```json
{
  "preset": "codebase",
  "focus_mode": "imports",
  "skeleton_density": "adaptive",
  "exclude": ["node_modules/", "dist/", "*.map"]
}
```

CLI flags override config values, while config and CLI `--exclude` patterns are combined.

Generate or validate a config file from the CLI:

```bash
mcp-skeleton config init --json
mcp-skeleton init --output-file .mcp-skeleton.yaml --json
mcp-skeleton config --output-file .mcp-skeleton.json --json
mcp-skeleton config --validate --config .mcp-skeleton.json --json
```

The config command reports supported presets, focus modes, density modes, and resolved defaults, which makes mis-typed values fail early before a long compression run.

Ask MCP-Skeleton to recommend project defaults from a real input:

```bash
mcp-skeleton config --recommend --input-dir . --preset codebase --output-file .mcp-skeleton.json --json
```

Recommendation mode runs the same compression analysis used by `context compress`, then writes a reusable config with the suggested focus, density, and exclude patterns.
Its JSON output includes `recommended_command_args`, a machine-readable trial compression argv list using the recommended config.
Add `--output-report-file mcp-skeleton-onboarding.md` to write an audit-friendly Markdown report with the source scale profile, current-vs-recommended token estimate, recommended command args, warnings, and next steps.

Install a lightweight git pre-commit hook for local self-use:

```bash
mcp-skeleton install-hook --json
```

The hook validates `.mcp-skeleton.json/yaml/yml` if present and runs CLI syntax checks. It does not apply patches, replay changes, or modify source files.

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
- synthetic monorepo-style package trees across full, tree, imports, and symbols focus modes
- large-directory recommendations that identify the lowest-token verified focus/density choice per backend and sample type
- long-text recommendations that identify the lowest-token verified focus/density choice for manuscript-scale inputs
- per-source recommendation diagnostics with candidate counts, savings percentage vs baseline, token-ratio span, and compression-time comparison
- release-readiness summaries that separate blocking restore failures from watch-level scale/token signals
- optional baseline JSON comparisons for non-blocking restore, token-ratio, and compression-time regression trends
- executive summaries for quick test-machine handoff of readiness, regression, restore, and recommended modes
- stdout executive summaries from the benchmark command so CI and test-machine logs carry the key result without opening report files
- stdout stress-handoff fields for scale profile, case count, monorepo fixture size, token-ratio guardrails, and best savings signals
- named benchmark scale profiles for quick smoke coverage, standard release checks, and stress test-machine runs
- configurable scale-health checks for restore verification, monorepo file floor, and large-directory token ratios
- scale-health guardrails for best verified monorepo and realistic-directory size ratio versus full+standard baselines
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
- `/Users/carwynmac/MCP-Skeleton/CONTEXT_CROSS_PLATFORM_VALIDATION_REPORT_20260520.md`
- `/Users/carwynmac/MCP-Skeleton/CROSS_PLATFORM_TESTING.md`
- `/Users/carwynmac/MCP-Skeleton/RELEASE_CHECKLIST_0_1.md`

## Scope

This repository is intentionally focused on one line of work:

- lossless context compression
- exact restore
- structural review
- patch and replay workflows
- incremental context transport for large repositories

It does not include the broader website, ecommerce, personal-site, or writing-generation surfaces from the original private parent repository.
