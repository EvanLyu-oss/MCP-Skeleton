# Changelog

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
