# AIL Builder

![Status](https://img.shields.io/badge/status-alpha%20builder%20preview-cf6f2e)
![CLI Checks](https://img.shields.io/badge/cli%20checks-207%2F207%20passing-2f855a)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-9c27b0)

**CLI-first static website generation, durable customization, and structured handoff workflows for AIL.**

## Use Notice

This repository is published as a **source-available community release**.

- free for learning, research, evaluation, and personal noncommercial use
- not an OSI-approved open-source release
- enterprise, team, client, hosted-service, and other commercial use require separate authorization from the author
- provided as-is, without warranty

See [`LICENSE`](LICENSE) and [`COMMERCIAL_LICENSE.md`](COMMERCIAL_LICENSE.md).

AIL Builder is the current AIL platform mainline. It is best understood today as an **alpha / builder preview** for:

- structured website generation workflows
- CLI-first website evaluation and handoff
- durable managed / unmanaged customization
- skill-ready agent / IDE workflow packaging
- sample-level brand distinction experiments
- low-token structured writing pack experiments for copy, fiction planning, and book blueprints

This repository is already strong enough for external testers to run, inspect, and give feedback on.
It is **not** yet packaged as a stable end-user product.

**Start here:** [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md) · [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md) · [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) · [`SKILL_PACKAGING_PLAN_20260418.md`](SKILL_PACKAGING_PLAN_20260418.md) · [`SKILL.md`](SKILL.md) · [`MCP_TOOL_SURFACE_SPEC_20260418.md`](MCP_TOOL_SURFACE_SPEC_20260418.md)

Architecture-first styling direction:

- [`DESIGN_HANDOFF_SPEC_20260426.md`](DESIGN_HANDOFF_SPEC_20260426.md)

Windows testers are supported too: see [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md) for PowerShell equivalents and current cross-platform notes.

Recent outward-facing changes are tracked in [`CHANGELOG.md`](CHANGELOG.md).

## Current Status

Current high-level state:

- website-first: complete for the current scope
- customization UX: closed for the current scope
- brand distinction: active, roughly `52%` to `62%` complete

Current validation anchor:

- `testing/results/cli_smoke_results.json`
  - `status = ok`
  - `207 / 207` checks passing
- Windows validation:
  - `workspace summary` confirmed working on Windows
  - `website check` confirmed working on Windows
  - successful output confirmed under `output_projects/`

Current strongest proof baselines:

- `output_projects/CompanyProductSiteBrandPostureReview`
- `output_projects/PersonalIndependentSiteSignatureReview`

Current tested generation scope:

- supported: static presentation-style sites such as personal portfolios, company product pages, and simple landing pages
- partial: blog-style presentation pages, without CMS or publishing-system behavior
- experimental: `ecom_min` storefront generation and preview behind `trial-run --scenario ecom_min`
- experimental: low-token `writing` pack detection and intent capture for copy, story, and book-planning requests
- out of scope for the stable public website promise: full ecommerce operations, production login systems, dashboards, CMS, back-office workflows, and database-backed applications

Current public website boundary:

- optimized for static presentation-style websites
- intentionally not positioned as ecommerce, account, order, after-sales workflow, or other dynamic product behavior

Architecture-first styling direction:

- use `python3 -m cli project style-brief --base-url embedded://local --json` from a generated project when you want one operator-safe brief for an external design model
- use `python3 -m cli project style-brief --base-url embedded://local --emit-prompt` when you want one prompt-ready text block you can paste directly into `opencode`, `minimax`, or another design model
- use `python3 -m cli project style-apply-check --base-url embedded://local --json` after a styling pass when you want one local boundary and runtime continuity check
- use `python3 -m cli project style-apply-check --base-url embedded://local --emit-summary` when you want one compact accept/reject summary instead of the full JSON payload
- use `python3 -m cli project style-intent --json` to read or save the current audience, brand, tone, localization, and visual constraints for later handoff
- this brief consolidates:
  - current preview and generated surface context
  - saved design intent from `.ail/style_intent.json`
  - allowed override-safe write roots
  - forbidden managed roots
  - recommended validation and preview commands
- the apply-check validates:
  - managed mirror integrity for router and view runtime copies
  - route wiring continuity
  - local preview dry-run readiness
- pair it with:
  - `python3 -m cli project export-handoff --base-url embedded://local --json`
  - `python3 -m cli project hook-guide --json`

Experimental dynamic lane:

- `website check --experimental-dynamic` can opt into the current experimental ecommerce / after-sales lane
- this lane is not part of the stable public website promise yet
- treat generated output there as exploratory, not productized
- current ecommerce experimental lane is best positioned as:
  - catalog / shop entry
  - product detail
  - cart
  - checkout skeleton / handoff
  - search, category, and shop continuity pages
  - account-center shell
  - supporting pages such as `about`, `contact`, and `policy`
- current verified ecom scenario entrypoint is:
  - `python3 -m cli trial-run --scenario ecom_min --base-url embedded://local --json`
- current verified local preview path is:
  - generate with `trial-run --scenario ecom_min`
  - then run `python3 -m cli project serve --install-if-needed` from the generated project directory
- do not position the ecommerce lane as:
  - production login / account system
  - payment capture stack
  - merchant backend
  - order-management platform
  - database-backed production commerce system

Current observed ecommerce preview shape:

- multi-page storefront skeleton rather than a single landing page
- product browse/search/cart/checkout continuity is present
- account-center shell is present and now includes:
  - order skeleton
  - address skeleton
  - wishlist skeleton
  - security skeleton
- login may appear as a shell page when auth APIs are present, but should not be marketed as a finished auth product

Current realization expectation for most landing-style website requests:

- asks for `about`, `features`, `pricing`, `FAQ`, or `blog` are often implemented as sections on one main page
- generated routes may remain minimal, often centered on `/` plus fallback routes such as `/403`
- do not promise independent multi-page routing unless the generated router actually shows it

## Who This Is For

AIL Builder is a good fit today for:

- builders who are comfortable using a CLI
- contributors who want to inspect and extend generation workflows
- testers evaluating website generation, customization, and handoff surfaces
- agent / IDE users who want to load a structured workflow surface as a skill
- collaborators interested in structured product-building workflows rather than one-shot site scaffolds

It is not yet optimized for:

- casual users expecting a 5-minute no-context setup
- production ecommerce, CMS, authentication, dashboard, or database-backed app generation
- automatic one-command generate-and-serve from a raw prompt
- production deployment with stability guarantees
- a frozen public API or stable plugin surface

## Fastest Start

Read these first:

1. [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md)
2. [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md)
3. [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)

Then use the shortest verified entry:

```bash
REPO_ROOT="$PWD"
PYTHONPATH="$REPO_ROOT" python3 -m cli website check 'Create a company product website with a home page, features, FAQ, and contact page.' --base-url embedded://local --json
```

If you want a higher-level repository view first:

```bash
REPO_ROOT="$PWD"
PYTHONPATH="$REPO_ROOT" python3 -m cli workspace summary --base-url embedded://local
```

If you want to inspect the current durable customization surface from a sample project:

```bash
REPO_ROOT="$PWD"
cd "$REPO_ROOT/output_projects/CompanyProductSiteBrandPostureReview"
PYTHONPATH="$REPO_ROOT" python3 -m cli project hook-guide --json
```

If you want to preview a generated project locally:

```bash
REPO_ROOT="$PWD"
cd "$REPO_ROOT/output_projects/CompanyProductSiteBrandPostureReview"
PYTHONPATH="$REPO_ROOT" python3 -m cli project serve --dry-run --json
PYTHONPATH="$REPO_ROOT" python3 -m cli project serve --install-if-needed
```

If you want to validate the current experimental ecommerce storefront lane:

```bash
REPO_ROOT="$PWD"
ecom_project_dir="$(mktemp -d /tmp/ail_ecom_preview.XXXXXX)"
PYTHONPATH="$REPO_ROOT" python3 -m cli trial-run --scenario ecom_min --base-url embedded://local --project-dir "$ecom_project_dir" --json
cd "$ecom_project_dir"
PYTHONPATH="$REPO_ROOT" python3 -m cli project serve --install-if-needed
```

If you want to test the new low-token writing branch:

```bash
REPO_ROOT="$PWD"
PYTHONPATH="$REPO_ROOT" python3 -m cli writing packs --json
PYTHONPATH="$REPO_ROOT" python3 -m cli writing check '写一个企业产品宣传文案，包含首页主标题、卖点和 CTA。' --json
PYTHONPATH="$REPO_ROOT" python3 -m cli writing scaffold '写一本非虚构商业书目录和章节目标，帮助创业者搭建销售系统。' --json
PYTHONPATH="$REPO_ROOT" python3 -m cli writing brief '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --emit-prompt
PYTHONPATH="$REPO_ROOT" python3 -m cli writing expand '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --emit-text
PYTHONPATH="$REPO_ROOT" python3 -m cli writing expand '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --deep --json
PYTHONPATH="$REPO_ROOT" python3 -m cli writing expand '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --emit-text --output-file /absolute/path/to/expand-draft.txt
PYTHONPATH="$REPO_ROOT" python3 -m cli writing review '写一个企业产品宣传文案，包含首页主标题、卖点和 CTA。' --text 'Help operators cut reporting time in half. Request pricing today.' --json
PYTHONPATH="$REPO_ROOT" python3 -m cli writing review '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --text-file /absolute/path/to/draft.txt --emit-summary
PYTHONPATH="$REPO_ROOT" python3 -m cli writing review '写一个长篇奇幻小说提纲和角色设定，包含主要冲突和章节结构。' --text-file /absolute/path/to/draft.txt --emit-summary --output-file /absolute/path/to/review-summary.txt
PYTHONPATH="$REPO_ROOT" python3 -m cli writing intent --audience 'indie founders' --format-mode copy --style-direction 'clear persuasive' --json
```

## What Already Works Well

The repository already has real product truth in these areas:

- website-oriented CLI checks, previews, summaries, and handoff flows
- static presentation-site generation for portfolio, company/product, and landing-style pages
- experimental ecommerce storefront generation and local preview through `trial-run --scenario ecom_min` plus `project serve`
- project-level local frontend serving via `project serve`
- managed / unmanaged customization via `hook-guide`, `hook-init`, and `hook-continue`
- durable override workflows without editing managed files directly
- repo-level low-token writing classification, scaffolding, prompt handoff, and first-draft expansion via `writing check`, `writing packs`, `writing scaffold`, `writing brief`, `writing expand`, and `writing intent`
- dual-line brand-distinction sample work on company and personal baselines

## Main Documents

Current public / packaging docs:

- [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md)
- [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md)
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`DESIGN_HANDOFF_SPEC_20260426.md`](DESIGN_HANDOFF_SPEC_20260426.md)
- [`SKILL_PACKAGING_PLAN_20260418.md`](SKILL_PACKAGING_PLAN_20260418.md)
- [`SKILL.md`](SKILL.md)
- [`MCP_TOOL_SURFACE_SPEC_20260418.md`](MCP_TOOL_SURFACE_SPEC_20260418.md)

Current phase and review docs:

- [`BRAND_DISTINCTION_PHASE_REVIEW_20260417.md`](BRAND_DISTINCTION_PHASE_REVIEW_20260417.md)
- [`OPENCODE_TEST_REPORT_20260423.md`](OPENCODE_TEST_REPORT_20260423.md)
- [`CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md`](CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md)
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- [`REPO_MAP.md`](REPO_MAP.md)

More detailed implementation docs remain in:

- `docs/`
- `testing/`
- `archive/`

## License

AIL Builder is released under **PolyForm Noncommercial 1.0.0**.

That means:

- personal and noncommercial use are allowed
- enterprise and commercial use require separate authorization
- this repository should be described as source-available, not OSI open source

See:

- `LICENSE`
- `COMMERCIAL_LICENSE.md`
