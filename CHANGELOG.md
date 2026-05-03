# Changelog

All notable changes to AIL Builder will be documented in this file.

This changelog is intentionally lightweight for now. The repository already has a long internal phase history, but this file starts from the current open-source alpha packaging point and tracks outward-facing changes from there.

## Unreleased

### Added

- initial public `CHANGELOG.md` for tracking outward-facing updates
- added `/Users/carwynmac/ai-cl/OPENCODE_TEST_REPORT_20260423.md` to capture external opencode testing results
- added `project serve` for launching or dry-running a generated project's local frontend dev server, including an `--install-if-needed` path
- added `/Users/carwynmac/ai-cl/COMMERCIAL_LICENSE.md` to clarify commercial and enterprise use
- added `context patch-apply --dry-run` so replay targets can be previewed without writing files
- added `context patch-apply --write-dry-run-report` so replay previews can be exported as one structured manifest JSON
- added one mixed directory patch regression and one invalid-relative-path restore regression to the local `context` smoke coverage

### Changed

- clarified public positioning around static presentation-site generation
- updated context compression docs and smoke coverage to include dry-run patch replay previews
- expanded dry-run replay coverage with one explicit preview manifest export for changed, added, removed, and predicted target paths
- enriched dry-run preview reports with `change_counts` and `first_*` helper fields for faster operator-side inspection
- added `surface_size` and `risk_band` to dry-run preview outputs so replay scope is easier to judge from summaries and reports
- hardened directory restore and replay by rejecting absolute paths, drive-qualified paths, and `..` traversal before any files are written
- reduced large-directory metric amplification by reusing internal source-token hints during the initial `context compress` metrics pass instead of rebuilding one giant source-text surface
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
- added `writing apply-check` so externally expanded drafts can be checked for scaffold drift with an explicit pass or warning result instead of relying on raw review scores alone
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
- added `/Users/carwynmac/ai-cl/WRITING_TEST_MATRIX_20260428.md` so writing regressions can be run against one stable matrix across copy, story, book, out-of-scope, review, and bundle flows
- added a universal `context` CLI surface with `context compress` and `context restore`, so long raw text, one source file, or one project tree can be turned into an AI-facing `MCP-SKL.v1` skeleton plus an exact restore bundle
- added `context inspect`, so a context bundle can now be summarized or inspected as JSON without restoring the original content first
- added `context apply-check`, so edited text, files, or directory trees can now be checked against the original compressed skeleton boundary before handoff
- added `context preset` plus `context compress --preset`, so operators can choose a declared compression emphasis such as `generic`, `codebase`, `writing`, `website`, or `ecommerce` without changing restore accuracy
- added `context bundle`, so compression, inspection, optional apply-check results, and optional zip packaging can now be exported as one formal context handoff artifact set
- added `context patch`, so edited text, files, or project trees can now be compared against the original bundle and exported as one diff-plus-snapshot patch handoff package
- added `context patch-apply`, so text, file, and directory patch bundles can now be replayed into a safe output target without mutating the original working tree in place
- expanded `context patch-apply` with optional policy-aware replay controls, including `open`, `safe`, and `strict` modes plus custom allow/forbid path roots and changed-path caps
- added `/Users/carwynmac/ai-cl/examples/context_patch_policy.safe.json` and `/Users/carwynmac/ai-cl/CONTEXT_PATCH_POLICY_TEMPLATE_20260429.md` so operators now have one reusable JSON policy example plus a clear merge/override explanation for `context patch-apply`
- added `context patch-apply --emit-policy-template`, so operators can now print the resolved replay policy as reusable JSON without first preparing a patch bundle
- added `context patch-apply --write-policy-template`, so operators can now save the resolved replay policy JSON directly to disk without needing shell redirection
- added `context patch-apply --sample-policy`, so operators can now start from one built-in `safe` or `strict` project-oriented sample before layering additional replay restrictions
- added `context patch-apply --merge-mode reject-conflicts`, so replay can now compare the current output target against the original source-package base and block one overwrite when the target already diverged on a touched path
- added `context patch-apply --write-merge-report`, so merge-aware replay can now export one structured JSON report with per-conflict path details and conflict kinds
- added `/Users/carwynmac/ai-cl/CONTEXT_REPO_SCALE_PERFORMANCE_REPORT_20260429.md`, recording one repo-scale benchmark of the full `context` flow against `/Users/carwynmac/ai-cl/cli`, including compress, bundle, patch, apply-check, and patch-apply timings
- added `/Users/carwynmac/ai-cl/CONTEXT_TOKENIZER_REPO_SCALE_REPORT_20260429.md`, comparing heuristic token estimates against `tiktoken` on the same repo-scale `/Users/carwynmac/ai-cl/cli` benchmark and documenting how `auto` now resolves to tokenizer-backed metrics when available
- documented one GitHub transport workaround in `/Users/carwynmac/ai-cl/README.md` and `/Users/carwynmac/ai-cl/QUICKSTART_OPEN_SOURCE.md`, noting that some macOS environments may require `git -c http.version=HTTP/1.1` for reliable `pull` and `push`
- clarified in `/Users/carwynmac/ai-cl/README.md` and `/Users/carwynmac/ai-cl/QUICKSTART_OPEN_SOURCE.md` that successful browser login to GitHub does not guarantee `git` transport stability on the same machine
- added formal `context` metrics on `compress` and `inspect`, including source characters, skeleton characters, heuristic token estimates, token direction, and estimated size ratios
- expanded `context` metrics so `compress`, `inspect`, and `bundle` can now prefer tokenizer-backed counts via optional `tiktoken` support while still falling back cleanly to heuristic estimates
- added `/Users/carwynmac/ai-cl/CONTEXT_TEST_MATRIX_20260428.md` so context compression, restore, inspect, apply-check, bundle, and patch regressions can be run against one stable matrix
- added `/Users/carwynmac/ai-cl/CONTEXT_TEST_REPORT_20260428.md` to capture one external validation pass over presets, inspect, apply-check, bundle, and patch behavior
- added `/Users/carwynmac/ai-cl/CONTEXT_METRICS_REPORT_20260428.md` to capture one metrics-focused validation pass and clarify that current token figures are heuristic estimates rather than billing-grade measurements
- expanded the public docs with one Windows `tiktoken` validation note so tokenizer-backed `context` metrics now document the recommended `py -3 -m pip install tiktoken` path for interpreter-safe setup
- added `/Users/carwynmac/ai-cl/PATCH_APPLY_REGRESSION_REPORT_20260429.md` to capture one Windows regression pass over `context bundle`, `context patch`, `context patch-apply`, and tokenizer-backed metrics
- added `/Users/carwynmac/ai-cl/WRITING_CONTEXT_WORKFLOW_20260429.md` to document the combined long-form workflow across `writing` scaffolds, `context` compression, AI handoff, apply-check, bundle, and patch replay
- added `/Users/carwynmac/ai-cl/WEBSITE_CONTEXT_WORKFLOW_20260429.md` to document the combined website workflow across generation, style handoff, `context` compression, apply-check, patch export, and safe patch replay
- added `/Users/carwynmac/ai-cl/CROSS_WORKFLOW_MAP_20260429.md` to give one high-level map across the `website`, `style`, `writing`, and `context` workflow lines and show when those surfaces should be combined
- added `/Users/carwynmac/ai-cl/CONTEXT_COMPRESSION_SPEC_20260428.md` to document the new context-compression bundle shape, restore strategy, and MCP skeleton positioning
- added smoke coverage for text, code, and directory context compression, exact directory restore, context bundle inspection, context apply-check drift/pass cases, preset catalog selection, context bundle export/zip/apply-check cases, context patch export cases for text and directory candidates, and patch replay cases for text and directory bundles

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
