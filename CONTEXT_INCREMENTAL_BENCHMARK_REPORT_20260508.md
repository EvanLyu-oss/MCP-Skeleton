# Context Incremental Benchmark Report

This report captures one formal `full vs incremental` benchmark run from the dedicated `MCP-Skeleton` repository.

The goal is not to claim that every tiny incremental surface will always beat the raw changed files in absolute token count.
The goal is to show that, for large repositories, **incremental context transport avoids repeatedly shipping the full repository surface**.

## Benchmark Setup

- generated_at: `2026-05-07T16:09:43Z`
- repo_root: `/Users/carwynmac/MCP-Skeleton`
- directory target: `/Users/carwynmac/MCP-Skeleton/cli`
- python: `3.9.6`
- platform: `macOS-26.4.1-arm64-arm-64bit`
- tokenizer model when available: `cl100k_base`
- iterations: `1`

## Full Directory Baseline

| Backend | Source chars | Skeleton chars | Source tokens | Skeleton tokens | Tokens saved | Token ratio | Compress ms | Restore ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heuristic | 193,297 | 7,056 | 48,325 | 1,764 | 46,561 | 0.0365 | 136.28 | True |
| auto | 193,297 | 7,056 | 42,134 | 1,926 | 40,208 | 0.0457 | 146.74 | True |
| tiktoken | 193,297 | 7,056 | 42,134 | 1,926 | 40,208 | 0.0457 | 146.92 | True |

Interpretation:

- the full repository-scale surface already compresses well
- skeleton token footprint lands at roughly `3.65%` to `4.57%` of the raw directory surface
- restore verification remained `True` for every backend

## Incremental Directory Surface

This benchmark captured one incremental change surface with:

- `change_surface_count = 3`
- changed paths: one file
- added paths: one file
- removed paths: one file

| Backend | Change surface | Source chars | Skeleton chars | Source tokens | Skeleton tokens | Token ratio | Compress ms | Restore ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heuristic | 3 | 127 | 1,836 | 32 | 459 | 14.3438 | 153.93 | True |
| auto | 3 | 127 | 1,836 | 23 | 601 | 26.1304 | 154.97 | True |
| tiktoken | 3 | 127 | 1,836 | 23 | 601 | 26.1304 | 154.20 | True |

Interpretation:

- on a very small incremental surface, skeleton metadata dominates
- that is expected and does **not** invalidate the incremental strategy
- incremental bundles are not designed to outperform a tiny raw diff in isolation
- they are designed to avoid rebundling the entire repository on every small change

## Full vs Incremental Comparison

| Backend | Change surface | Full source tokens | Incremental source tokens | Source token ratio | Full skeleton tokens | Incremental skeleton tokens | Skeleton token ratio | Full compress ms | Incremental compress ms | Compress ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| auto | 3 | 42,134 | 23 | 0.0005 | 1,926 | 601 | 0.3120 | 146.74 | 154.97 | 1.0561 |
| heuristic | 3 | 48,325 | 32 | 0.0007 | 1,764 | 459 | 0.2602 | 136.28 | 153.93 | 1.1295 |
| tiktoken | 3 | 42,134 | 23 | 0.0005 | 1,926 | 601 | 0.3120 | 146.92 | 154.20 | 1.0496 |

Interpretation:

- incremental **source** transport shrank to roughly `0.05%` to `0.07%` of the full directory source surface
- incremental skeleton transport shrank to roughly `26.02%` to `31.20%` of the full directory skeleton surface
- compress time did not materially improve in this tiny benchmark because:
  - git diff discovery still runs
  - skeleton framing still runs
  - the repository is not large enough to make traversal cost dominant

## Why This Still Matters

The main win is not "tiny incremental bundle vs tiny raw diff."

The main win is:

1. large repository stays large
2. small change surface stays small
3. AI no longer needs the full repository skeleton every time
4. replay, apply-check, dry-run, policy, and merge workflows still remain available on the incremental surface

This is the core scaling behavior we want:

- as repository size grows, full context cost grows
- incremental change surfaces usually stay comparatively small
- the gap between `full source tokens` and `incremental source tokens` becomes more meaningful over time

## Long-Text Baseline Reminder

The same benchmark run also kept the long-text cases healthy:

- `book_20,000`: token ratio around `0.1302` heuristic / `0.1908` tokenizer-backed
- `book_100,000`: token ratio around `0.0267` heuristic / `0.0391` tokenizer-backed
- `book_400,000`: token ratio around `0.0067` heuristic / `0.0099` tokenizer-backed

That supports the same core principle:

- the larger the source, the more compelling the structural skeleton becomes

## Conclusion

This benchmark supports a precise product claim:

- `MCP-Skeleton` does **not** guarantee that every tiny incremental bundle is smaller than the raw changed files
- it **does** provide a strong repository-scale advantage by letting teams send only the git-scoped change surface instead of repeatedly sending the full repository context

For large engineering projects, that is the important scaling property.
