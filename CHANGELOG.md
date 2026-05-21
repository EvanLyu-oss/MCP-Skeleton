# Changelog

## Unreleased

- added `context config --recommend` to generate project defaults from real compression analysis
- added `context config` to emit and validate `.mcp-skeleton.json` templates with structured JSON output
- added `.mcp-skeleton.json` config defaults for `context compress` and `context bundle`, with CLI flags still taking precedence
- added smart compression warnings and recommended config hints to `context compress` JSON and summary output
- documented the final Windows v0.1.3 quick smoke and stress benchmark validation results

## 0.1.3

- added a public cross-platform testing guide with quick smoke, stress benchmark, and test-machine result templates
- expanded benchmark stdout executive summaries with scale profile, case count, monorepo fixture size, token-ratio guardrails, and best savings signals for test-machine handoff
- added named benchmark scale profiles for quick, standard, and stress coverage, while preserving the existing `--quick` shortcut
- added scale-health guardrails that ensure best verified monorepo and realistic-directory skeletons stay compact versus full+standard baselines
- enriched benchmark recommendations with per-source grouping, candidate counts, token savings percentages, token-ratio span, and compression-time comparisons for large-directory and long-text tuning
- preserved text-density budgets under the writing preset so adaptive and compact long-text skeletons can produce meaningful token savings without changing restore fidelity

## 0.1.2

- validated v0.1.2 with the Python-native smoke runner passing `25/25` checks on both macOS and Windows
- added and expanded a Python-native cross-platform smoke runner for Windows and other environments without Bash
- fixed text patch snapshots and replay to preserve candidate bytes exactly across platforms
- documented the Windows Python smoke runner 11/11 validation result in the cross-platform validation report
- expanded the Python smoke runner with merge-conflict, directory patch-apply, dry-run report, and policy-block replay coverage
- expanded the Python smoke runner with incremental patch replay, incremental dry-run report, policy-template, and invalid restore path coverage
- expanded the Python smoke runner with bundle, clean incremental diagnostics, and apply-check drift coverage
- expanded the Python smoke runner with writing-outline, text-density, directory-symbols, directory-aggregation, text-patch, and incremental-patch coverage

## 0.1.1

- validated v0.1.1 as a cross-platform `ready` candidate on macOS and Windows quick benchmark paths
- documented the macOS and Windows validation results in `CONTEXT_CROSS_PLATFORM_VALIDATION_REPORT_20260520.md`
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
- added BOM-aware UTF-16LE/BE, UTF-8 BOM, GB2312, and EUC-JP text decoding for skeleton extraction while preserving byte-exact restore
- added a synthetic monorepo benchmark fixture so large multi-package directory behavior is measured in the scale harness
- added scale-health benchmark checks for large-directory restore fidelity, monorepo fixture size, and token-ratio guardrails
- expanded monorepo benchmark coverage across full, tree, imports, and symbols focus modes
- made scale-health benchmark thresholds configurable from the benchmark CLI
- added large-directory benchmark recommendations that pick the lowest-token verified focus/density option per backend and sample type
- added long-text benchmark recommendations for manuscript-scale focus/density selection
- added release-readiness benchmark summaries and next-action guidance that distinguish blocking restore failures from watch-level scale signals
- added optional baseline benchmark comparison output for restore, token-ratio, and compression-time regression trends
- added executive benchmark summaries for quick test-machine handoff of readiness, regression, restore, and recommended modes
- expanded benchmark stdout JSON with executive summary, release-readiness, and regression-trend snapshots for CI and test-machine logs
- fixed text benchmark restore verification to use byte-exact output-file restore instead of stdout text emission, avoiding Windows newline translation false failures
- bounded `standard` density directory skeletons for large repositories so monorepo-style inputs keep more complete structure without expanding past the source token footprint

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
