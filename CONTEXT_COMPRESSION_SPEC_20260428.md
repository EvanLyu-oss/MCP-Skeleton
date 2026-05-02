# Context Compression Spec 2026-04-28

## Goal

Add one universal `context` entrypoint that can compress long raw text, one source file, or one whole project directory into an AI-facing MCP skeleton while keeping one exact restore package next to it.

This feature is intentionally architecture-first:

- the skeleton is what another AI or IDE should read
- the restore package is what the machine should use to reconstruct the original content exactly
- existing website, ecommerce, writing, and project workflows stay untouched

## Current CLI Surface

### Compress

```bash
PYTHONPATH="$PWD" python3 -m cli context preset --json
PYTHONPATH="$PWD" python3 -m cli context preset website --json
PYTHONPATH="$PWD" python3 -m cli context compress --text-file /absolute/path/to/long-text.md --json
PYTHONPATH="$PWD" python3 -m cli context compress --input-file /absolute/path/to/app.py --emit-skeleton
PYTHONPATH="$PWD" python3 -m cli context compress --preset website --input-dir /absolute/path/to/project --output-dir /absolute/path/to/context-bundle --json
```

### Restore

```bash
PYTHONPATH="$PWD" python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --emit-text
PYTHONPATH="$PWD" python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --output-file /absolute/path/to/restored.txt
PYTHONPATH="$PWD" python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --output-dir /absolute/path/to/restore-root --json
```

### Inspect

```bash
PYTHONPATH="$PWD" python3 -m cli context inspect --package-file /absolute/path/to/context-bundle/context_manifest.json --emit-summary
PYTHONPATH="$PWD" python3 -m cli context inspect --package-file /absolute/path/to/context-bundle/context_manifest.json --json
```

### Apply-check

```bash
PYTHONPATH="$PWD" python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/edited-text.md --emit-summary
PYTHONPATH="$PWD" python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --input-file /absolute/path/to/edited-file.py --json
PYTHONPATH="$PWD" python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --json
```

### Bundle

```bash
PYTHONPATH="$PWD" python3 -m cli context bundle --preset website --input-dir /absolute/path/to/project --zip --output-dir /absolute/path/to/context-bundle --json
PYTHONPATH="$PWD" python3 -m cli context bundle --preset writing --text-file /absolute/path/to/long-text.md --candidate-text-file /absolute/path/to/edited-text.md --emit-summary
```

### Patch

```bash
PYTHONPATH="$PWD" python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --zip --output-dir /absolute/path/to/context-patch --json
PYTHONPATH="$PWD" python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/edited-text.md --emit-summary
```

### Patch-apply

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --output-dir /absolute/path/to/replayed-project --json
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --dry-run --output-dir /absolute/path/to/replayed-project --emit-summary
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --dry-run --output-dir /absolute/path/to/replayed-project --write-dry-run-report /absolute/path/to/dry-run-report.json --json
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --merge-mode reject-conflicts --output-dir /absolute/path/to/replayed-project --emit-summary
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --merge-mode reject-conflicts --write-merge-report /absolute/path/to/merge-report.json --json
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --output-file /absolute/path/to/replayed.txt --emit-summary
PYTHONPATH="$PWD" python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --policy-mode safe --output-dir /absolute/path/to/replayed-project --emit-summary
PYTHONPATH="$PWD" python3 -m cli context patch-apply --sample-policy strict --emit-policy-template
PYTHONPATH="$PWD" python3 -m cli context patch-apply --policy-mode strict --allow-root src --forbid-root src/generated --emit-policy-template
PYTHONPATH="$PWD" python3 -m cli context patch-apply --policy-mode safe --allow-root docs --write-policy-template /absolute/path/to/context-policy.json
```

## Presets

Current presets:

- `generic`
- `codebase`
- `writing`
- `website`
- `ecommerce`

Presets do not change restore accuracy.
They change the declared compression emphasis and the guidance written into the MCP skeleton and bundle metadata.

## Bundle Shape

When `context compress` is run with `--output-dir`, it writes:

- `context_manifest.json`
- `context_skeleton.mcp`
- `context_restore.json`
- `README.txt`

When `context bundle` is run, it writes the same base package plus:

- `inspect.json`
- `inspect_summary.txt`
- `bundle_manifest.json`
- optional `apply_check.json`
- optional `apply_check_summary.txt`
- optional zip archive next to the bundle directory

When `context patch` is run, it writes:

- `patch_manifest.json`
- `patch_summary.txt`
- `apply_check.json`
- `apply_check_summary.txt`
- one diff or patch-preview artifact
- one candidate snapshot file or directory
- optional zip archive next to the patch directory

`context patch-apply` replays the patch package into a safe output target.

Use `--dry-run` when you want a preview of the replay target and affected paths without writing any files.
Use `--write-dry-run-report` when you want the preview manifest exported as one structured JSON artifact.

For now it is intentionally conservative:

- text patch -> writes the candidate snapshot back to one file path
- file patch -> writes the candidate snapshot back to one file path
- directory patch -> restores the original source package into a fresh output root, overlays changed and added files, and removes paths recorded in the patch manifest

It now also supports optional replay policies.

- `--policy-mode open` keeps the default permissive replay
- `--policy-mode safe` requires a passing apply-check result and blocks removed paths
- `--policy-mode strict` also blocks added paths and caps the touched path count
- `--sample-policy safe|strict` starts from one reusable project-oriented sample before other overrides are applied
- `--policy-file` can refine those defaults with explicit JSON settings
- `--allow-root` and `--forbid-root` let operators constrain replay to relative path prefixes

It also supports one merge-aware replay gate:

- `--merge-mode overwrite`
  - current default behavior
  - replays directly into the chosen output target

- `--merge-mode reject-conflicts`
  - compares the current output target against the original source-package base
  - blocks replay if the target already diverged on one path the patch needs to touch
  - returns:
    - `status = warning`
    - `apply_mode = merge_conflict_blocked`
    - `merge_conflicts`
  - can also write one structured merge report with:
    - `--write-merge-report /absolute/path/to/merge-report.json`

Formal example policy files now live at:

- `/Users/carwynmac/ai-cl/examples/context_patch_policy.safe.json`
- `/Users/carwynmac/ai-cl/CONTEXT_PATCH_POLICY_TEMPLATE_20260429.md`

When a replay is blocked by policy, `context patch-apply` returns:

- `status = warning`
- `apply_mode = policy_blocked`
- `policy_passed = false`
- `policy_findings`

and exits with the validation status instead of mutating the output target.

If you want a reusable starter JSON without replaying any patch at all, use:

- `--emit-policy-template`
- or `--write-policy-template /absolute/path/to/context-policy.json`

That mode resolves the current preset plus CLI overrides and prints the final JSON policy body you can save for later reuse.

## Skeleton Language

The AI-facing output is currently:

- `MCP-SKL.v1`

It carries:

- compression mode
- source kind
- source label
- core counts and hashes
- code imports, symbol definitions, and relationship markers
- text headings, sections, and theme terms
- directory tree plus per-file structural summaries

## Metrics Surface

`context compress` and `context inspect` now emit a formal `metrics` object.

Current fields:

- `source_char_count`
- `skeleton_char_count`
- `estimated_token_count_source`
- `estimated_token_count_skeleton`
- `estimated_tokens_saved`
- `estimated_token_delta_from_source`
- `estimated_token_direction`
- `estimated_token_reduction_ratio`
- `estimated_token_size_ratio`
- `char_reduction_ratio`
- `token_estimate_basis`
- `token_estimate_backend`
- `token_estimate_model`
- `token_estimate_requested_backend`
- `token_estimate_fallback_used`
- `heuristic_token_count_source`
- `heuristic_token_count_skeleton`
- `tokenizer_available`

Current token estimation modes:

- default fallback: `heuristic_chars_div_4`
- optional tokenizer-backed mode: `tiktoken:<encoding>`

This is intentionally approximate.
It is useful for operator reporting and cross-run comparison, not for billing-grade token accounting.

If `tiktoken` is installed, operators can request tokenizer-backed metrics with:

- `context compress --tokenizer-backend tiktoken`
- `context inspect --tokenizer-backend tiktoken`
- `context bundle --tokenizer-backend tiktoken`

Important nuance:

- on very small inputs the MCP skeleton can be larger than the original source
- in those cases `estimated_token_direction` will report `expanded`
- this is expected and more honest than forcing every case into a fake reduction claim

## Exact Restore Strategy

The skeleton does **not** try to hold the original content verbatim.
Instead, the manifest stores a separate restore blob:

- encoding: `zlib+base64+json`
- exact payload checksum
- exact text, file bytes, or directory tree contents

This is what makes the feature practical:

- the skeleton stays compact enough for AI context windows
- the original source stays exactly recoverable

## Supported Inputs

- inline long text via `--text`
- long-form text files via `--text-file`
- one code or project file via `--input-file`
- one directory tree via `--input-dir`

## Supported Restore Modes

- text package back to stdout or one file
- single file package back to one file path
- directory package back to one restored project tree under `--output-dir`

## Current Positioning

This feature is designed to solve:

- oversized repo context
- oversized writing context
- forced lossy prompt compression
- IDE / MCP window overflow
- hallucination risk caused by blunt truncation

It is not yet positioned as:

- semantic diffing
- merge-aware source regeneration
- AST-perfect language-specific recompilation
- cross-file dependency reasoning beyond the exported skeleton surface

## Apply-check Positioning

`context apply-check` is a structural continuity gate.

It currently checks whether edited content still broadly preserves:

- major heading and section structure for text bundles
- import and symbol surface for code files
- file-tree continuity and file-kind continuity for directory bundles

It is useful for:

- checking whether an AI pass drifted too far from the compressed skeleton
- catching missing files or missing core symbols before handoff
- deciding whether to re-run compression, repair the edited output, or restore the original baseline

## Bundle Positioning

`context bundle` is the formal handoff surface for compression workflows.

It combines:

- compression output
- bundle inspection output
- optional apply-check output
- optional zip packaging

It is useful for:

- handing one compact MCP skeleton plus one exact restore package to another AI or IDE
- attaching an inspect summary so operators can review the package without opening the full manifest
- attaching an apply-check result when an edited candidate already exists
- preserving one stable artifact set for testing, collaboration, and rollback

## Patch Positioning

`context patch` is the operator-facing delta surface for one edited candidate.

It combines:

- structural continuity validation from `context apply-check`
- one human-readable diff or patch preview
- one exact candidate snapshot for changed payloads
- optional zip packaging for handoff

It is useful for:

- reviewing what changed after another AI worked from the compressed skeleton
- handing a compact delta package to another AI, IDE, or teammate
- preserving edited payloads without losing the original restore bundle

## Patch-apply Positioning

`context patch-apply` is a controlled replay step.

It is not a merge-aware patch engine.
It is a safe reconstruction path that:

- uses the candidate snapshot files already exported by `context patch`
- uses the original source bundle when directory replay is needed
- rebuilds the edited surface into a fresh output target instead of mutating an active project tree in place

## Recommended Workflow

1. feed the raw long context into `context compress`
2. hand only `context_skeleton.mcp` or `skeleton_text` to the target AI
3. keep the manifest and restore blob together while the AI works
4. run `context restore` when you need the original content back

## Current Validation

The current smoke coverage locks in:

- text compression bundle generation
- text restore summary generation
- code skeleton extraction
- directory compression and exact file restore
- bundle inspection summary generation
- bundle inspection JSON payload generation
- apply-check pass/fail coverage for aligned and drifting candidates
- preset catalog and selected-preset coverage
- bundle export coverage
- bundle zip export coverage
- bundle apply-check export coverage
- bundle summary output coverage
- patch export coverage for text candidates
- patch export coverage for directory candidates
- patch summary output coverage
- patch-apply replay coverage for text candidates
- patch-apply replay coverage for directory candidates, including removed-path handling
