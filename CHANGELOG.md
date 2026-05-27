# Changelog

## Unreleased

- renamed the public product surface to Ailoom Context, with `ailoom` as the primary CLI and `mcp-skeleton` retained as a compatibility alias
- prepared the benchmark guardrails and cross-platform validation report for a future GitHub slug migration to `ailoom-context`
- updated new bundle metadata to `ailoom_context_bundle.v1` and `AILOOM-SKL.v1` while keeping restore workflows compatible through the same package reader
- updated install scripts, README, SECURITY, beta trial docs, and smoke expectations to use the Ailoom Context brand for new-user paths
- added a Windows PowerShell installer (`install.ps1`) with install/update/uninstall/setup-shell flows and install-readiness manifest generation
- made quick/handoff/recent open and clipboard command text platform-aware so Windows users see `Start-Process` and `Set-Clipboard` instead of macOS-only `open`/`pbcopy`
- expanded README quickstart/install guidance with a Windows PowerShell path and tokenizer-backed metrics install option
- added `SECURITY.md` with the local-only/no-telemetry safety model, share-vs-keep-local boundary, artifact cleanup guidance, and MCP-SKL project identity notes
- added default AI-facing skeleton redaction for common secret shapes while preserving byte-exact local restore packages
- added `context clean` / `mcp-skeleton clean` to preview or remove known local MCP-Skeleton generated artifacts such as `.workspace_ail/`
- added a public beta trial guide and feedback template for early users testing MCP-Skeleton before formal v1.0
- made the Python smoke reuse restore-command assertion parse quoted command arguments so Windows paths wrapped by shell quoting pass correctly
- made Windows regression runs skip macOS `sh install.sh` quickstart/installer lifecycle checks instead of failing when `sh` is unavailable, while preserving macOS coverage
- improved Python smoke failure reporting with full tracebacks so cross-platform assertion failures identify the exact failing line
- added `mcp-skeleton doctor --install` for first-run install diagnostics, PATH/Python/readiness checks, and copy/paste repair commands
- added `install_doctor_command_text` to the installer readiness manifest and installer completion output
- expanded `handoff.json` with a stable AI/IDE handoff contract covering ready-to-share status, share-with-AI file, keep-local restore files, and safety boundary metadata
- added stable `performance_summary.speed_diagnostic` fields so wrappers can show why a quick/handoff run felt slow and which command to use next
- expanded `mcp-skeleton safety` with common questions and emergency recovery guidance for lost manifests, changed projects, and dry-run-first patch replay
- added `v1_beta_readiness` to release readiness summaries so macOS beta install/use readiness is visible without reading every check
- added `context safety` / `mcp-skeleton safety` to explain the restore-package sharing boundary, dry-run-first patch replay, and default noise protection in both human and JSON output
- added stable `user_outcome` fields to quick, handoff, and recent JSON so IDEs can tell users exactly which skeleton file is ready to share, whether the bundle was reused, and what command to run next
- expanded default-noise explanations with estimated skipped file and byte counts so large-project users can see why compression is faster and smaller before disabling the defaults
- added an installer readiness manifest at `~/.mcp-skeleton/install-readiness.json`, and exposed it through `mcp-skeleton version --json` for IDEs, test machines, and first-run automation
- added a stable `performance_summary` to `context quick` / `mcp-skeleton handoff` JSON and human output, with speed status, slowest phase, token impact, noise-protection impact, and the recommended next run
- expanded dogfood self-check output with a real performance record covering elapsed time, bundle size, included files, source/skeleton tokens, estimated savings, and exact-restore status
- fixed reused quick/handoff restore command text so it keeps the full manifest path instead of falling back to `context_manifest.json`
- added AI/IDE handoff prompt and `handoff.json` metadata files beside generated bundles, with `mcp-skeleton recent` reprinting the latest prompt
- improved installer and `mcp-skeleton version` guidance with explicit PATH fix, temporary export, self-check, and first-run handoff commands
- added a daily handoff summary to `mcp-skeleton handoff` that explains whether the bundle was created or reused, why that happened, and how clipboard copy was handled
- expanded default noise protection to skip common generated test results, restore outputs, and Python package metadata such as `testing/results`, `test-results`, `mcp-skeleton-restore`, and `*.egg-info`
- added bundle lifecycle fields to `mcp-skeleton recent`, including created time, bundle size, restore package path, and file-existence checks
- added `mcp-skeleton recent --list` and `mcp-skeleton recent --clean-stale --dry-run` for safe recent-bundle discovery and cleanup previews
- added zero-learning defaults so `mcp-skeleton handoff`, `quick`, `doctor`, and `recent` use the current directory when no input source is provided
- made `mcp-skeleton handoff` automatically reuse the last fresh bundle for unchanged projects, with `--force-refresh` available when a new bundle is required
- simplified the README and quickstart check around the two-command macOS path: `sh install.sh --setup-shell` then `mcp-skeleton handoff`
- added `context start` as a zero-friction onboarding command that writes config/report files, runs doctor, and prints the next compression command
- added a README Quickstart that gets new macOS users from install to demo, quick bundle, and fresh-bundle reuse in four commands
- added `testing/quickstart_check.py` to verify the README install/demo/handoff/quick/reuse path stays executable
- added a compact `executive_summary` to the release readiness runner so humans and test machines can read pass/fail, dogfood, doctor, and benchmark status without parsing full logs
- added consistent `At a glance` status cards to `context quick`, `context quick --preview`, `context doctor`, and `context recent` human output
- added `context quick` performance breakdown guidance that names the slowest visible phase and the best next command for large or slower runs
- added a `context quick` performance profile that reports phase timing, default noise protection, and next-run reuse/fast commands
- added install readiness fields to `mcp-skeleton version` and a first-run self-check panel to `install.sh`
- added `install.sh --setup-shell` to safely append one managed PATH block to `~/.zshrc` for future macOS terminals
- added first-run guidance to `context quick` so tiny projects explain token expansion as expected behavior instead of looking like a failed compression
- added clearer `context quick` AI handoff guidance that separates the skeleton file to share from bundle/manifest/restore files to keep locally
- added `mcp-skeleton handoff` as a short top-level alias for the restore-safe quick AI/IDE handoff workflow
- added `AI_HANDOFF.md` bundle guides plus `--copy` as a shorter macOS clipboard alias for first-run AI/IDE handoff
- updated installer and version guidance to recommend `mcp-skeleton handoff` as the first real project command
- improved fresh-bundle reuse guidance so `handoff` users see `mcp-skeleton handoff --reuse-if-fresh` and an explicit saved-work summary
- added default directory noise protection for common dependency, build, virtualenv, VCS, and cache folders, with visible compression explanations
- added `--include-default-skips` and `include_default_skips` config support for intentionally including default-skipped directories
- added `context quick` as a one-command start + restore-safety check + bundle workflow for zero-learning bundle creation
- added `context explain` to translate an existing bundle into plain-language safety, compression, and next-step guidance
- added direct `mcp-skeleton quick/start/doctor/...` top-level aliases and a macOS `install.sh` for lower-friction local installation
- improved `install.sh` completion output with command verification, PATH status, and copy/paste next-step commands
- added quick/start/doctor timing breakdowns and clearer token-impact summaries so users can judge speed and savings immediately
- added quick/preview performance advice with fast/ok/slow status plus copy/paste `--fast` and `--reuse-if-fresh` commands
- made `context quick` reuse the restore-safety compression payload when writing the final bundle, avoiding one repeated compression pass on large inputs
- added `context quick --preview` to show restore safety, token estimates, output paths, and the real run command without writing a bundle
- added `context quick --fast` for large inputs that need the fastest safe bundle path without config recommendation/onboarding generation
- added standard `context quick` speed tips that suggest a copy/paste `--fast` command for large or noticeably slow inputs
- added `context demo` / `mcp-skeleton demo` so new users can run a complete sample compression and restore-safety flow without preparing a project
- added `mcp-skeleton version`, doctor install-path hints, and `install.sh --update/--uninstall` for simpler install lifecycle management
- improved `context quick` human output with a first-screen result panel, token impact, timing, and copy/paste next command
- improved `context quick` first-screen handoff with the skeleton file, estimated savings, restore command, and inspect command
- added explicit `context quick` AI/IDE handoff guidance for the skeleton file, bundle folder, and restore manifest
- added `context quick --open` plus copy/paste `open <bundle>` guidance for locating generated bundles on macOS
- added `context quick --copy-command` plus copy/paste `cat context_skeleton.mcp | pbcopy` guidance for handing skeletons to AI/IDE tools
- added `context quick` experience guidance for speed status, token-savings health, and when to prefer `--fast`
- added `context recent` / `mcp-skeleton recent` to rediscover the last quick bundle, skeleton, restore manifest, and handoff commands for a project
- added `context recent` freshness detection so stale quick bundles show a copy/paste refresh command
- added `context quick --reuse-if-fresh` to reuse unchanged recent bundles without recompressing large projects
- hardened dogfood expectations against nested MCP-Skeleton onboarding artifacts created during local self-use
- added `context doctor --write-report` for Markdown readiness reports
- added automatic preset/focus/density defaults for common directory, code-file, and prose-file inputs
- hardened dogfood, smoke, and release readiness checks against local `context start` onboarding artifacts in the repository root
- excluded generated `.workspace_ail/` work artifacts from default directory compression, recommendations, dogfood, and release readiness checks
- hardened realistic-directory benchmark inputs against generated workspace, result, onboarding, and tarball-sync artifacts on test machines
- added copy/paste-ready command text and plain action plans to `context start` and `context doctor` for lower-learning-curve onboarding
- added recovery steps and fix command hints to CLI errors, plus non-empty output directory protection for `context quick`
- updated dogfood self-check to use `context start` before recommended trial compression and byte-exact restore verification

## 0.1.5

- validated the v0.1.5 release-readiness workflow on macOS and Windows
- added a Python release readiness runner that combines syntax checks, smoke checks, dogfood, doctor, quick benchmark, baseline save, and optional Bash smoke
- updated release and cross-platform test guidance for v0.1.5 doctor/readiness/baseline validation
- added `context doctor` readiness checks for config resolution, compression advice, sandbox restore, and byte/hash parity
- added structured compression explanations so large-directory recommendations describe scale, hot groups, excludes, and focus/density rationale
- added benchmark `--save-baseline-json` to copy a run into a reusable regression baseline file
- expanded dogfood self-check to trial-run recommended compression args before bundle/restore verification
- added `recommended_command_args` to `context config --recommend` JSON and Markdown reports for direct trial compression
- added machine-readable `recommended_command_args` to `context compress --json` so scripts can apply recommended focus, density, and exclude settings
- added scale class and compression advice counts to benchmark summaries and recommendation previews
- added current-vs-recommended token estimate comparison to `context config --recommend`
- added source scale details to `context config --recommend` JSON and onboarding reports
- added source scale profiling and large-directory filter/focus recommendations to `context compress`
- added `.mcp-skeleton.yaml` and `.mcp-skeleton.yml` config discovery and validation
- added `context config init`, `context init`, and YAML config template output by file suffix
- added `context install-hook` for a lightweight pre-commit config validation and CLI syntax hook

## 0.1.4

- validated v0.1.4 on macOS and Windows, including Python smoke, dogfood self-check, and quick benchmark release readiness
- documented the post-v0.1.3 macOS and Windows dogfood/config-onboarding validation baseline
- added a cross-platform Python dogfood self-check that validates config recommendation, onboarding report, bundle, inspect, restore, and SHA256 parity
- added optional Markdown onboarding reports for `context config --recommend`
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
