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
- refined the experimental ecommerce `/account` member shell so it now separates order, address, wishlist, and security blocks more explicitly instead of presenting a single coarse placeholder panel
- expanded the experimental ecommerce `/account` order area with a status filter strip, order-card skeletons, and an explicit order empty-state block so future account/order work can attach to a clearer UI contract
- expanded the experimental ecommerce `/account` address area with a default-address card, reusable address-item skeletons, explicit address actions, and an address empty-state block aligned with checkout reuse
- expanded the experimental ecommerce `/account` wishlist area with saved-item skeletons, recent-view strips, and explicit return-entry markers for product, search, category, and shop continuity
- expanded the experimental ecommerce `/account` security area with sign-in method chips, device cards, privacy/export controls, and explicit high-risk action placeholders for account freeze/logout/delete flows
- updated the open-source quickstart and repository docs so external testers can follow a verified `trial-run --scenario ecom_min` plus `project serve` path for the experimental ecommerce preview
- added `/Users/carwynmac/ai-cl/DESIGN_HANDOFF_SPEC_20260426.md` to define the architecture-first AIL Core plus external model styling contract and the proposed `project style-brief` / `project style-apply-check` direction
- added `project style-brief` so operators and external design models can export one architecture-first styling brief with override-safe write roots, managed-boundary rules, preview context, and recommended validation commands
- added `project style-apply-check` so styled projects can locally verify managed mirror integrity, route/runtime continuity, and preview dry-run readiness without depending on a cloud project record
- added `project style-intent` so operators can save reusable audience, tone, brand-keyword, localization, and visual-constraint intent into `.ail/style_intent.json`, and wired `project style-brief` to include that saved intent automatically
- expanded `project style-brief` with a prompt-ready `--emit-prompt` mode and a `model_prompt` field so operators can paste one compact styling task directly into external models
- expanded `project style-apply-check` with a compact `--emit-summary` mode and a `summary_text` field so operators can quickly review pass/fail boundary results without reading the full JSON payload
- added a first `writing` CLI branch with `writing packs`, `writing check`, and `writing intent` so the repo can start classifying low-token copy, story-outline, and book-blueprint requests without pretending to be a full prose generation platform
- expanded the first `writing` CLI branch with `writing scaffold`, which now emits structured low-token scaffolds for copy hierarchies, story outlines, and book blueprints instead of jumping straight to long-form prose
- expanded the first `writing` CLI branch with `writing brief` and `--emit-prompt`, so writing scaffolds and saved writing intent can now be handed to external models as one prompt-ready continuation task
- expanded the first `writing` CLI branch with `writing expand` and `--emit-text`, so copy, story, and book scaffolds can now be turned into one controlled first-draft pass before deeper rewriting
- widened `copy_min` writing detection so announcement and launch-style requests such as product release notices are classified into the copy lane more reliably
- added deterministic variation modes inside `writing expand` so first-draft outputs can differ in voice while staying stable for the same requirement and pack
- added `writing expand --deep` so the existing first-draft pass can be pushed one layer further into a second-pass draft without pretending to generate a finished manuscript
- added `writing review`, so draft text can now be checked against the current low-token scaffold for alignment, drift findings, revision targets, and a next-pass rewrite prompt
- added `writing review --emit-summary` plus a `summary_text` field so review results can be scanned quickly without reading the full JSON payload
- added `writing review --output-file` so summary or JSON review results can be written directly to disk for testing and external-editor handoff
- added `writing expand --output-file` so first-draft prose can be saved directly as text or JSON during testing and external-editor handoff
- added `writing brief --output-file` so prompt handoffs and JSON brief payloads can be written directly to disk for testing and external-model workflows
- added `writing bundle`, so one command can now export check, scaffold, brief, expand, and review outputs into a reusable bundle directory
- added `writing bundle --zip` so the full writing bundle can also be exported as a shareable zip archive
- added `writing bundle --emit-summary` plus a `summary_text` field so bundle results can be scanned quickly without opening the full JSON manifest
- added `writing bundle --output-file` so the compact bundle summary or full bundle manifest can be written directly to disk
- added `README.txt` inside each writing bundle so the exported directory explains file purpose and suggested reading order
- added `manifest_version` and `bundle_created_at` to writing bundles so exported artifacts carry lightweight versioning and creation metadata
- added `writing bundle --copy-archive-path` so zipped bundles can copy their archive path directly into the macOS clipboard for faster handoff
- added `writing bundle --copy-summary` so compact bundle summaries can be copied straight into a handoff note or test report
- tightened `writing check` so requests for one-shot finished long-form novels or publication-ready full books are classified as out of scope instead of being accepted into scaffold-first lanes
- stopped `writing bundle` from passively reading stdin when no review text was requested, which avoids hangs in wrapped shell environments such as PowerShell-based test runners

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
