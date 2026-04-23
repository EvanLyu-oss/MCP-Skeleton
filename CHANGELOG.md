# Changelog

All notable changes to AIL Builder will be documented in this file.

This changelog is intentionally lightweight for now. The repository already has a long internal phase history, but this file starts from the current open-source alpha packaging point and tracks outward-facing changes from there.

## Unreleased

### Added

- initial public `CHANGELOG.md` for tracking outward-facing updates
- added `/Users/carwynmac/ai-cl/OPENCODE_TEST_REPORT_20260423.md` to capture external opencode testing results

### Changed

- clarified public positioning around static presentation-site generation
- documented ecommerce, CMS, blog-publishing, routing, localization, managed-drift, and local-preview limitations more explicitly

## 2026-04-19

### Cross-platform improvements

- switched the main CLI runtime path to dynamic repository-root resolution
- removed the most important developer-specific macOS path dependency from the main execution path
- added `output_projects/ail_vue_base` to the tracked repository contents so fresh clones include the frontend template baseline
- updated `/Users/carwynmac/ai-cl/QUICKSTART_OPEN_SOURCE.md` with PowerShell equivalents for Windows testers
- updated `/Users/carwynmac/ai-cl/README.md` with a short Windows note at the repository entrypoint
- updated `/Users/carwynmac/ai-cl/KNOWN_LIMITATIONS.md` to clarify that cross-platform support is improving, but not fully normalized yet

### Why this matters

- Windows testers should no longer hit the original first-run failure caused by a hardcoded macOS repo path
- Windows validation has now confirmed successful `workspace summary` and `website check` runs
- the repository now describes its current cross-platform state more honestly
- the main setup path is easier to follow across Unix-like shells and PowerShell

## 2026-04-18

### Open-source alpha packaging

- added `/Users/carwynmac/ai-cl/LICENSE` with the MIT license
- rewrote `/Users/carwynmac/ai-cl/README.md` for a GitHub-friendly alpha landing page
- added `/Users/carwynmac/ai-cl/OPEN_SOURCE_STATUS.md`
- added `/Users/carwynmac/ai-cl/QUICKSTART_OPEN_SOURCE.md`
- added `/Users/carwynmac/ai-cl/KNOWN_LIMITATIONS.md`
- added GitHub issue templates under `/Users/carwynmac/ai-cl/.github/ISSUE_TEMPLATE/`
- renamed the public project identity to `AIL Builder`

### Skill and MCP packaging

- added `/Users/carwynmac/ai-cl/SKILL.md` as the repository-level skill entry
- added `/Users/carwynmac/ai-cl/SKILL_PACKAGING_PLAN_20260418.md`
- added `/Users/carwynmac/ai-cl/MCP_TOOL_SURFACE_SPEC_20260418.md`

## 2026-04-17

### Brand distinction review update

- added `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_PHASE_REVIEW_20260417.md`
- updated the project-wide phase judgment for Brand Distinction to roughly `52%` to `62%`
- captured dual-line strengthening, consolidation, and middle-section tightening as the current mid-phase checkpoint
