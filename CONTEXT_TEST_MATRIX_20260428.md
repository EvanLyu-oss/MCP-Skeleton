# Context Test Matrix 2026-04-28

## Goal

Validate the full `context` workflow across text, single-file, and directory inputs.

This matrix is designed to confirm four things:

1. compression is structurally useful for AI handoff
2. restore remains exact
3. apply-check catches structural drift without blocking aligned edits
4. bundle and patch exports are stable enough for cross-tool collaboration
5. patch replay can rebuild edited output into a safe target without mutating the original source tree

## Test Environment Notes

Record these before each run:

- latest commit from `git log --oneline -3`
- shell: `zsh`, PowerShell, `cmd`, or Git Bash
- `python3 --version` or `python --version`
- whether `PYTHONPATH` is set
- whether clipboard or zip behavior differs on the current platform

## Fast Sanity Pass

Run these first when you only need a quick signal.

```bash
python3 -m cli context compress --preset writing --text "# Context Compression\n\nPreserve business logic." --output-dir /absolute/path/to/context-fast-bundle --json
python3 -m cli context preset --json
python3 -m cli context inspect --package-file /absolute/path/to/context-fast-bundle/context_manifest.json --emit-summary
python3 -m cli context bundle --preset writing --text "# Context Compression\n\nPreserve business logic." --emit-summary
python3 -m cli context patch --package-file /absolute/path/to/context-fast-bundle/context_manifest.json --text "# Context Compression\n\nPreserve business logic and route continuity." --emit-summary
```

Expected:

- every command returns `status: ok`
- no hangs in wrapped shells
- `context bundle` and `context patch` complete in a few seconds on small inputs
- `context patch` is always run against a package whose mode matches the candidate input mode

## Preset Matrix

### P1. Preset catalog

```bash
python3 -m cli context preset --json
```

Expected:

- `entrypoint = context-preset`
- `preset_count >= 5`
- includes:
  - `generic`
  - `codebase`
  - `writing`
  - `website`
  - `ecommerce`

### P2. One selected preset

```bash
python3 -m cli context preset website --json
```

Expected:

- `selected_preset.preset_id = website`
- `selected_preset.focus` is non-empty

## Text Workflow Tests

### T1. Compress long-form text

```bash
python3 -m cli context compress --preset writing --text-file /absolute/path/to/long-text.md --json
```

Check:

- `entrypoint = context-compress`
- `compression_mode = text`
- `source_kind = text | markdown`
- `skeleton_language = MCP-SKL.v1`
- `compression_ratio` is meaningfully smaller than `1`
- `metrics.source_char_count > 0`
- `metrics.estimated_token_count_source > 0`
- `metrics.estimated_token_count_skeleton > 0`
- `metrics.estimated_token_direction in {reduced, expanded, flat}`
- `metrics.token_estimate_backend in {heuristic, tiktoken}`
- `metrics.token_estimate_basis is non-empty`

### T1b. Compress long-form text with writing-outline focus

```bash
python3 -m cli context compress --preset writing --focus-mode writing-outline --text-file /absolute/path/to/long-text.md --json
```

Check:

- `focus_mode = writing-outline`
- `skeleton_text` contains `FOCUS_MODE: writing-outline`
- `skeleton_text` contains `HEADINGS:`
- `skeleton_text` contains `SECTIONS:`

### T2. Restore long-form text

```bash
python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --output-file /absolute/path/to/restored.txt --json
```

Expected:

- `entrypoint = context-restore`
- restored output exactly matches the original text file

### T3. Apply-check aligned text

```bash
python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/aligned-text.md --json
```

Expected:

- `status = ok`
- `apply_check_passed = true`
- `alignment_band = workable | strong`

### T4. Apply-check drifting text

### T5. Apply-check incremental directory surface

```bash
python3 -m cli context apply-check --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json --input-dir /absolute/path/to/edited-incremental-surface --json
```

Expected:

- `status = ok | warning`
- `incremental_mode = true`
- `incremental_changed_paths` and `incremental_added_paths` are present
- `summary_text` includes `incremental_changed_count`, `incremental_added_count`, and `incremental_removed_count`

```bash
python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/drifting-text.md --emit-summary
```

Expected:

- `status = warning`
- `apply_check_passed = false`
- summary includes `alignment_score` and one revision target or drift finding

### T5. Text patch export

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/edited-text.md --output-dir /absolute/path/to/context-patch --json
```

Expected:

- `entrypoint = context-patch`
- `patch_mode = text_unified_diff`
- `files.patch_diff` exists
- `files.candidate_snapshot_file` exists
- `apply_check_passed` reflects whether the edited text stayed aligned

## Single-file Workflow Tests

### F1. Compress one code file

```bash
python3 -m cli context compress --preset codebase --input-file /absolute/path/to/app.py --emit-skeleton
```

Expected skeleton markers:

- `PRESET: codebase`
- `MODE: file`
- `SOURCE_KIND: code`
- `IMPORTS:`
- `SYMBOLS:`

### F1b. Compress one code file with symbols focus

```bash
python3 -m cli context compress --preset codebase --focus-mode symbols --input-file /absolute/path/to/app.py --json
```

Expected:

- `focus_mode = symbols`
- `skeleton_text` contains `FOCUS_MODE: symbols`
- `skeleton_text` contains `SYMBOLS:`
- `skeleton_text` does not contain `IMPORTS:`

### F2. Inspect one code-file package

```bash
python3 -m cli context inspect --package-file /absolute/path/to/context-bundle/context_manifest.json --json
```

Expected:

- `restore_mode = file`
- `source_kind = code | text | binary`
- `summary_text` present
- `metrics` present

### F3. Patch one edited file

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-file /absolute/path/to/edited-app.py --json
```

Expected:

- `patch_mode = file_unified_diff` for text/code files
- or `patch_mode = file_binary_replace` for binary files
- candidate snapshot exists
- `apply_check.json` exists

## Directory Workflow Tests

### D1. Compress one project tree

```bash
python3 -m cli context compress --preset website --input-dir /absolute/path/to/project --output-dir /absolute/path/to/context-bundle --json
```

Expected:

- `compression_mode = directory`
- `source_kind = mixed_project`
- `source_summary.total_files > 0`
- bundle files exist:
  - `context_manifest.json`
  - `context_skeleton.mcp`
  - `context_restore.json`
  - `README.txt`

### D1b. Compress one project tree with symbols focus

```bash
python3 -m cli context compress --preset codebase --focus-mode symbols --input-dir /absolute/path/to/project --json
```

Expected:

- `focus_mode = symbols`
- `skeleton_text` contains `SYMBOLS:`
- `skeleton_text` does not contain `IMPORTS:`
- `skeleton_text` does not contain `TREE:`

### D2. Restore one project tree

```bash
python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --output-dir /absolute/path/to/restore-root --json
```

Expected:

- restored tree matches the original source tree
- file contents are byte-identical for the tested sample set

### D3. Inspect one project tree bundle

```bash
python3 -m cli context inspect --package-file /absolute/path/to/context-bundle/context_manifest.json --emit-summary
```

Expected:

- `compression_mode: directory`
- `source_kind: mixed_project`
- `tree_preview_count:` present
- estimated token fields present in summary or JSON output

Note:

- tiny inputs may report `estimated_token_direction = expanded`
- if `tiktoken` is not installed, requesting `--tokenizer-backend tiktoken` should fall back cleanly or report the fallback state explicitly
- larger repos or long-form text should usually report `reduced`

### D3b. Compress one incremental git change surface

```bash
python3 -m cli context compress --input-dir /absolute/path/to/project --incremental --base-commit HEAD~1 --output-dir /absolute/path/to/context-incremental-bundle --json
```

Expected:

- `compression_mode = directory_incremental`
- `incremental_mode = true`
- `incremental_scope = base_commit_diff | working_tree`
- `incremental_changed_paths`, `incremental_added_paths`, and `incremental_removed_paths` reflect the git delta
- `source_summary.changed_file_count`, `source_summary.added_file_count`, and `source_summary.removed_path_count` are present

### D3c. Restore one incremental git change surface

```bash
python3 -m cli context restore --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json --output-dir /absolute/path/to/restore-root --json
```

Expected:

- `restore_mode = directory_incremental`
- restore writes the changed and added files into one root directory
- restore writes `.ail_incremental_manifest.json`
- the incremental manifest includes `removed_paths`

### D3d. Bundle one incremental git change surface

```bash
python3 -m cli context bundle --input-dir /absolute/path/to/project --incremental --base-commit HEAD~1 --output-dir /absolute/path/to/context-incremental-bundle --json
```

Expected:

- `compression_mode = directory_incremental`
- `incremental_mode = true`
- `apply_check_included = false`
- bundle files exist:
  - `context_manifest.json`
  - `context_skeleton.mcp`
  - `context_restore.json`
  - `inspect.json`
  - `inspect_summary.txt`
  - `bundle_manifest.json`

### D4. Directory apply-check aligned

```bash
python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/aligned-project --json
```

Expected:

- `status = ok`
- `apply_check_passed = true`

### D5. Directory apply-check drifting

```bash
python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/drifting-project --json
```

Expected:

- `status = warning`
- `apply_check_passed = false`
- `drift_findings` includes dropped files, kind shifts, or reduced structure

### D6. Directory bundle export

```bash
python3 -m cli context bundle --preset website --input-dir /absolute/path/to/project --zip --output-dir /absolute/path/to/context-bundle --json
```

Expected bundle contents:

- `context_manifest.json`
- `context_skeleton.mcp`
- `context_restore.json`
- `README.txt`
- `inspect.json`
- `inspect_summary.txt`
- `bundle_manifest.json`
- optional `apply_check.json`
- optional `apply_check_summary.txt`
- optional `.zip`

Check:

- `entrypoint = context-bundle`
- `zip_enabled = true`
- `archive_path` exists

### D7. Directory patch export

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --zip --output-dir /absolute/path/to/context-patch --json
```

Expected patch contents:

- `patch_manifest.json`
- `patch_summary.txt`
- `apply_check.json`
- `apply_check_summary.txt`
- `patch_preview.diff` or one diff artifact tree
- candidate snapshot directory
- optional `.zip`

Check:

- `entrypoint = context-patch`
- `patch_mode = directory_structural_patch`
- `change_counts.changed_paths >= 0`
- `change_counts.added_paths >= 0`
- `change_counts.removed_paths >= 0`

### D8. Directory patch replay

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --output-dir /absolute/path/to/replayed-project --json
```

Expected:

- `entrypoint = context-patch-apply`
- `apply_mode = directory_restore_plus_overlay`
- changed files are replayed into the rebuilt output tree
- added files appear in the rebuilt output tree
- removed files are absent from the rebuilt output tree

### D8b. Directory patch replay dry-run

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --dry-run --output-dir /absolute/path/to/replayed-project --json
```

Expected:

- `entrypoint = context-patch-apply`
- `apply_mode = directory_restore_plus_overlay_preview`
- `dry_run = true`
- output tree is not materialized yet
- `applied_paths` still reports the predicted replay root

### D8c. Directory patch replay dry-run report

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --dry-run --output-dir /absolute/path/to/replayed-project --write-dry-run-report /absolute/path/to/dry-run-report.json --json
```

Expected:

- `dry-run-report.json` is written
- `entrypoint = context-patch-apply-dry-run-report`
- `change_counts` is populated
- `surface_size` is populated
- `risk_band` is one of `small`, `medium`, or `large`
- `first_changed_path` / `first_added_path` / `first_removed_path` are populated when applicable
- `first_write_target` / `first_remove_target` are populated when applicable
- `preview_manifest.changed_paths` is populated
- `preview_manifest.added_paths` is populated when the patch adds files
- `preview_manifest.removed_paths` is populated when the patch removes files
- `preview_manifest.write_targets` and `preview_manifest.remove_targets` point at predicted replay paths

### D8d. Invalid relative path restore guard

Prepare one malformed manifest by changing one stored directory `relative_path` to `../escape.py`, then run:

```bash
python3 -m cli context restore --package-file /absolute/path/to/invalid-context-manifest.json --output-dir /absolute/path/to/restore-root --json
```

Expected:

- process exits with usage status
- `status = error`
- `error.code = invalid_usage`
- `error.message` explains that upward traversal is not allowed

### D8e. Mixed directory patch regression

Use one directory candidate that changes one file, adds one file, and removes one file before running:

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/mixed-candidate --output-dir /absolute/path/to/context-patch --json
```

Expected:

- `patch_mode = directory_structural_patch`
- `change_counts.changed_paths >= 1`
- `change_counts.added_paths >= 1`
- `change_counts.removed_paths >= 1`
- `changed_paths`, `added_paths`, and `removed_paths` are all populated

### M1. Quick scale benchmark harness

```bash
python3 /Users/carwynmac/ai-cl/testing/context_scale_benchmark.py --quick --output-json /absolute/path/to/context_scale_benchmark.json --output-md /absolute/path/to/context_scale_benchmark.md
```

Expected:

- process exits successfully
- benchmark JSON is written
- benchmark Markdown report is written
- `summaries.directory_cases` is populated
- `summaries.directory_incremental_cases` is populated
- `summaries.incremental_comparison` is populated
- `summaries.text_cases` is populated
- all quick benchmark `restore_verified` fields are `true`

### D8b. Incremental directory patch export

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-incremental-bundle/context_manifest.json --input-dir /absolute/path/to/edited-incremental-surface --output-dir /absolute/path/to/context-incremental-patch --json
```

Expected:

- `compression_mode = directory_incremental`
- `incremental_mode = true`
- `incremental_changed_paths` is populated
- `incremental_added_paths` is populated
- `incremental_removed_paths` reflects the effective removed-path surface after any revived files are accounted for
- `patch_mode = directory_structural_patch`
- `apply_check.apply_check_passed` is present

### D8c. Incremental patch replay

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json --output-dir /absolute/path/to/replayed-project --json
```

Expected:

- `status = ok`
- `incremental_mode = true`
- `apply_mode = directory_incremental_restore_plus_overlay`
- replayed output includes changed and added files from the incremental surface
- revived removed paths are restored when present in the candidate snapshot
- `.ail_incremental_manifest.json` reflects the effective `removed_paths` after replay

### D8d. Incremental patch dry-run report

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-incremental-patch/patch_manifest.json --source-package-file /absolute/path/to/context-incremental-bundle/context_manifest.json --dry-run --write-dry-run-report /absolute/path/to/incremental-dry-run-report.json --output-dir /absolute/path/to/replayed-project --json
```

Expected:

- `dry_run = true`
- `incremental_mode = true`
- report includes `incremental_scope`
- report includes `incremental_change_counts`
- report includes `first_incremental_changed_path` and `first_incremental_added_path`
- dry-run target is not materialized

### D9. Policy-aware directory patch replay

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --policy-mode safe --output-dir /absolute/path/to/replayed-project --json
```

Expected when the patch removes files:

- process exits with validation status
- `status = warning`
- `apply_mode = policy_blocked`
- `policy_mode = safe`
- `policy_passed = false`
- `policy_findings` explains why replay was blocked

### T6. Text patch replay

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --output-file /absolute/path/to/replayed.txt --json
```

Expected:

- `entrypoint = context-patch-apply`
- `apply_mode = text_snapshot_replay`
- replayed output exactly matches the edited text used to create the patch

### T6b. Text patch replay dry-run

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --dry-run --output-file /absolute/path/to/replayed.txt --json
```

Expected:

- `entrypoint = context-patch-apply`
- `apply_mode = text_snapshot_replay_preview`
- `dry_run = true`
- target file is not written yet
- `applied_paths` still reports the predicted replay file
- `preview_manifest.write_targets` reports the predicted replay file

### T7. Policy-aware text patch replay

```bash
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --policy-mode safe --output-file /absolute/path/to/replayed.txt --json
```

Expected:

- `status = ok`
- `policy_mode = safe`
- `policy_passed = true`
- replayed output still matches the edited text used to create the patch

## Bundle / Patch Summary Tests

### B1. Bundle compact summary

```bash
python3 -m cli context bundle --preset website --input-dir /absolute/path/to/project --zip --output-dir /absolute/path/to/context-bundle --emit-summary
```

Expected summary fields:

- `status`
- `preset_id`
- `compression_mode`
- `bundle_root`
- `zip_enabled`
- `file_count`

### B2. Patch compact summary

```bash
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --zip --output-dir /absolute/path/to/context-patch --emit-summary
```

Expected summary fields:

- `status`
- `patch_mode`
- `patch_root`
- `zip_enabled`
- `apply_check_passed`
- `changed_paths`
- `added_lines` / `removed_lines` when applicable

## Cross-platform Notes

### Windows + PowerShell

Prefer:

```powershell
$env:PYTHONPATH = "D:\path\to\ail-builder"
python -m cli context bundle --preset website --input-dir D:\path\to\project --zip --output-dir D:\path\to\context-bundle --json
```

Watch for:

- quoting of Chinese or multi-line text inputs
- path escaping under `--output-dir` and `--output-file`
- stdout buffering on large JSON output

### macOS + zsh

Useful for clipboard and zip-adjacent manual review.

```bash
PYTHONPATH="/Users/carwynmac/ai-cl" python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --emit-summary
```

## Failure Cases To Record

If something fails, capture:

1. exact command
2. shell and OS
3. whether JSON, summary, or file-output mode was used
4. exit code
5. stderr or traceback
6. whether the failure is deterministic

## Recommended Minimum Regression Set

If you only run a short pass, run these 8 commands:

```bash
python3 -m cli context preset website --json
python3 -m cli context compress --preset writing --text-file /absolute/path/to/long-text.md --json
python3 -m cli context restore --package-file /absolute/path/to/context-bundle/context_manifest.json --output-file /absolute/path/to/restored.txt --json
python3 -m cli context inspect --package-file /absolute/path/to/context-bundle/context_manifest.json --emit-summary
python3 -m cli context apply-check --package-file /absolute/path/to/context-bundle/context_manifest.json --text-file /absolute/path/to/aligned-text.md --json
python3 -m cli context bundle --preset website --input-dir /absolute/path/to/project --zip --output-dir /absolute/path/to/context-bundle --emit-summary
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --json
python3 -m cli context patch --package-file /absolute/path/to/context-bundle/context_manifest.json --input-dir /absolute/path/to/edited-project --zip --emit-summary
python3 -m cli context patch-apply --patch-file /absolute/path/to/context-patch/patch_manifest.json --source-package-file /absolute/path/to/context-bundle/context_manifest.json --output-dir /absolute/path/to/replayed-project --json
```

## Current Maturity Judgment

Current maturity for the `context` line is:

- `alpha test-ready`

That means:

- the core workflow is stable enough for external testing
- restore is exact
- AI-facing skeletons are compact and structured
- bundle and patch exports are usable for collaboration
- deeper semantic patch application is still a later-stage capability
