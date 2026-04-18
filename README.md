# AI-CL

![Status](https://img.shields.io/badge/status-alpha%20builder%20preview-cf6f2e)
![CLI Checks](https://img.shields.io/badge/cli%20checks-207%2F207%20passing-2f855a)
![License](https://img.shields.io/badge/license-MIT-1f6feb)

**CLI-first website generation, durable customization, and structured handoff workflows for AIL.**

AI-CL is the current AIL platform mainline. It is best understood today as an **alpha / builder preview** for:

- structured website generation workflows
- CLI-first website evaluation and handoff
- durable managed / unmanaged customization
- sample-level brand distinction experiments

This repository is already strong enough for external testers to run, inspect, and give feedback on.
It is **not** yet packaged as a stable end-user product.

**Start here:** [`OPEN_SOURCE_STATUS.md`](OPEN_SOURCE_STATUS.md) · [`QUICKSTART_OPEN_SOURCE.md`](QUICKSTART_OPEN_SOURCE.md) · [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)

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

AI-CL is a good fit today for:

- builders who are comfortable using a CLI
- contributors who want to inspect and extend generation workflows
- testers evaluating website generation, customization, and handoff surfaces
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
PYTHONPATH="$REPO_ROOT" python3 -m cli website check '做一个企业产品官网，包含首页、功能介绍、FAQ、联系我们。' --base-url embedded://local --json
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

AI-CL is now released under the **MIT License**.

See:

- `LICENSE`
