# AIL Builder

![Status](https://img.shields.io/badge/status-alpha%20builder%20preview-cf6f2e)
![CLI Checks](https://img.shields.io/badge/cli%20checks-207%2F207%20passing-2f855a)
![License](https://img.shields.io/badge/license-MIT-1f6feb)

**CLI-first website generation, durable customization, and structured handoff workflows for AIL.**

AIL Builder is the current AIL platform mainline. It is best understood today as an **alpha / builder preview** for:

- structured website generation workflows
- CLI-first website evaluation and handoff
- durable managed / unmanaged customization
- skill-ready agent / IDE workflow packaging
- sample-level brand distinction experiments

This repository is already strong enough for external testers to run, inspect, and give feedback on.
It is **not** yet packaged as a stable end-user product.

**Start here:** [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md) · [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md) · [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) · [`SKILL_PACKAGING_PLAN_20260418.md`](SKILL_PACKAGING_PLAN_20260418.md) · [`SKILL.md`](SKILL.md) · [`MCP_TOOL_SURFACE_SPEC_20260418.md`](MCP_TOOL_SURFACE_SPEC_20260418.md)

Windows testers are supported too: see [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md) for PowerShell equivalents and current cross-platform notes.

## Current Status

Current high-level state:

- website-first: complete for the current scope
- customization UX: closed for the current scope
- brand distinction: active, roughly `52%` to `62%` complete

Current validation anchor:

- `testing/results/cli_smoke_results.json`
  - `status = ok`
  - `207 / 207` checks passing

Current strongest proof baselines:

- `output_projects/CompanyProductSiteBrandPostureReview`
- `output_projects/PersonalIndependentSiteSignatureReview`

## Who This Is For

AIL Builder is a good fit today for:

- builders who are comfortable using a CLI
- contributors who want to inspect and extend generation workflows
- testers evaluating website generation, customization, and handoff surfaces
- agent / IDE users who want to load a structured workflow surface as a skill
- collaborators interested in structured product-building workflows rather than one-shot site scaffolds

It is not yet optimized for:

- casual users expecting a 5-minute no-context setup
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

## What Already Works Well

The repository already has real product truth in these areas:

- website-oriented CLI checks, previews, summaries, and handoff flows
- managed / unmanaged customization via `hook-guide`, `hook-init`, and `hook-continue`
- durable override workflows without editing managed files directly
- dual-line brand-distinction sample work on company and personal baselines

## Main Documents

Current open-source / packaging docs:

- [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md)
- [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md)
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
- [`SKILL_PACKAGING_PLAN_20260418.md`](SKILL_PACKAGING_PLAN_20260418.md)
- [`SKILL.md`](SKILL.md)
- [`MCP_TOOL_SURFACE_SPEC_20260418.md`](MCP_TOOL_SURFACE_SPEC_20260418.md)

Current phase and review docs:

- [`BRAND_DISTINCTION_PHASE_REVIEW_20260417.md`](BRAND_DISTINCTION_PHASE_REVIEW_20260417.md)
- [`CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md`](CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md)
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- [`REPO_MAP.md`](REPO_MAP.md)

More detailed implementation docs remain in:

- `docs/`
- `testing/`
- `archive/`

## License

AIL Builder is now released under the **MIT License**.

See:

- `LICENSE`
