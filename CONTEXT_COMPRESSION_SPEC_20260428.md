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
PYTHONPATH="$PWD" python3 -m cli context compress --text-file /absolute/path/to/long-text.md --json
PYTHONPATH="$PWD" python3 -m cli context compress --input-file /absolute/path/to/app.py --emit-skeleton
PYTHONPATH="$PWD" python3 -m cli context compress --input-dir /absolute/path/to/project --output-dir /absolute/path/to/context-bundle --json
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

## Bundle Shape

When `context compress` is run with `--output-dir`, it writes:

- `context_manifest.json`
- `context_skeleton.mcp`
- `context_restore.json`
- `README.txt`

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
