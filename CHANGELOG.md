# Changelog

All notable changes to AIL Builder will be documented in this file.

This changelog is intentionally lightweight for now. The repository already has a long internal phase history, but this file starts from the current open-source alpha packaging point and tracks outward-facing changes from there.

## Unreleased

### Added

- initial public `CHANGELOG.md` for tracking outward-facing updates
- added `/Users/carwynmac/ai-cl/OPENCODE_TEST_REPORT_20260423.md` to capture external opencode testing results
- added `project serve` for launching or dry-running a generated project's local frontend dev server, including an `--install-if-needed` path
- added `/Users/carwynmac/ai-cl/COMMERCIAL_LICENSE.md` to clarify commercial and enterprise use

### Changed

- clarified public positioning around static presentation-site generation
- documented ecommerce, CMS, blog-publishing, routing, localization, managed-drift, and local-preview limitations more explicitly
- improved managed-file drift messaging so CLI output explains it as a sync safety guard, not necessarily a website generation failure
- changed the repository licensing posture from MIT to PolyForm Noncommercial 1.0.0 and updated public docs to describe the repo as source-available rather than OSI open source
- clarified `website check` output so landing-style requests now explicitly warn that multi-page asks are often realized as single-page sections
- narrowed the current public website surface to static presentation-style packs in `website check`, `website assets`, and `website summary`
- added an explicit `--experimental-dynamic` website lane so ecommerce and after-sales packs can be explored without reopening them as part of the stable public static-site surface
- expanded `website check` with delivery-contract guidance so the experimental ecommerce lane now reports supported capabilities, unsupported capabilities, and operator positioning more explicitly
- upgraded the experimental ecommerce storefront shell with a shared announcement bar, top navigation, floating tools, footer, storefront theme base, and reusable product-card styling across generated ecommerce pages
- expanded the experimental ecommerce home page with Phase 2 storefront modules, including a promo strip, category shortcut cards, new-arrival shelf, brand/factory story block, buyer testimonial strip, and payment/logistics trust cards
- expanded experimental ecommerce listing pages with stronger discovery modules, including price-band filtering, richer sort controls, paginated result grids, and clearer empty-state handling across category and search pages
- expanded the experimental ecommerce product page with a richer gallery flow, variant chips, quantity stepper, spec table, review strip, and after-sales assurance modules while keeping cart and discovery continuity intact
- expanded the experimental ecommerce transaction skeleton with cart-side delivery/payment prep cards, checkout-side address and payment selectors, and an inline success receipt that preserves order context after submit
- expanded the experimental ecommerce storefront with Phase 6 auxiliary pages and member-shell routing, adding generated `/about`, `/contact`, `/policy`, and `/account` views plus storefront navigation/footer links to reach them

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
