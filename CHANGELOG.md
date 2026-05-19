# Changelog

## Unreleased

- added a directory restore completeness audit to the CLI smoke suite, explicitly comparing original included paths, restore-package paths, restored paths, and default skipped directories
- exposed directory compression skip metadata in `source_summary` so operators can distinguish true restore gaps from the default `.git`, `__pycache__`, and `.pytest_cache` skip contract
- documented that incremental restore reconstructs the git change surface rather than pretending to rebuild the full repository tree
- added best-effort non-UTF-8 text decode fallback for skeleton extraction while preserving original bytes for exact restore
- added smoke coverage for GBK text-file restore fidelity and non-UTF-8 directory text classification
- added directory filtering via `.mcp-skeletonignore` and repeated `--exclude` patterns for `context compress` and `context bundle`
- added filter metadata to directory `source_summary` and smoke coverage proving filtered paths stay out of the restore package
- added preset-specific skeleton strategies and suggested exclude hints so `codebase`, `writing`, `website`, and `ecommerce` produce more differentiated AI-facing context surfaces
- tuned preset-aware skeleton budgets and directory entry ordering, with smoke coverage proving codebase prefers code entries while writing prefers prose entries on mixed large directories
- validated input files and directories before compression so missing paths return invalid-usage errors instead of empty successful bundles
- added incremental diagnostics for clean or filtered git change surfaces and smoke coverage for zero-change incremental runs
- documented a safe dogfood workflow using ignored result directories and sandbox restores
- added `testing/dogfood_self_check.sh` to compress, inspect, sandbox-restore, and hash-check this repository during active development
- added a focused roadmap for encoding robustness, large-repo stability, semantic skeleton quality, CI/dogfood integration, and skeleton-layer secret awareness

## 0.1.0

- split `context` compression, restore, patch, replay, and benchmark workflows into the dedicated `MCP-Skeleton` repository
- switched the standalone repository license to MIT
- preserved the context-specific commit history from the original private parent repository
- included full and incremental compression flows, dry-run replay previews, policy-aware replay gates, merge-aware replay checks, and scale benchmark tooling
- promoted incremental `context apply-check` into the public surface, including top-level incremental metadata, summary fields, and dedicated smoke coverage
- enabled incremental `context patch-apply`, including incremental replay manifest updates and standalone smoke coverage
- enriched incremental patch dry-run reports with scope, per-lane counts, and first-path summary fields
- added a formal full-vs-incremental benchmark report for the standalone `MCP-Skeleton` repository
- added `context` skeleton focus modes for full, tree, imports, symbols, and writing-outline views
- extended the benchmark harness to compare focus-mode skeleton variants against the full baseline
- added a formal focus-mode benchmark report for directory and long-text skeleton views
- added adaptive and compact skeleton-density modes so large repos and long-form text can ship smaller AI-facing skeletons without changing restore fidelity
- extended the benchmark harness to compare skeleton-density variants against the standard full skeleton baseline
- added grouped directory and extension overviews so large directory skeletons can omit more per-file detail without losing top-level continuity
- added hot-subtree expansion and cold-subtree folding so large directory skeletons spend entry budget where structural signal is densest
- added chapter-fold outlines so long-form text can preserve chapter continuity while spending fewer skeleton tokens
- extended the benchmark harness with realistic repo-directory and repo-document corpora so synthetic results can be checked against repeatable real samples
- tightened directory apply-check drift detection for large added surfaces and added edge-case smoke coverage for missing files, kind changes, and bulk additions
- documented the `0.1.x` stability contract, experimental boundaries, exit-code semantics, and repeatable benchmark signals in the README
- added a `v0.1` release checklist covering scope, required validation commands, documentation review, artifact review, commit shape, and tag steps

## Selected history carried into this repo

- incremental context patches
- context compression principles documentation
- incremental context benchmarks
- incremental context bundles
- incremental context compression
- benchmark restore verification stabilization
- repo-scale benchmark harness
- dry-run report enrichment and risk bands
- merge-aware and policy-aware patch replay
- tokenizer-backed metrics and cross-platform benchmark reporting
