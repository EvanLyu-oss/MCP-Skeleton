# AI-CL

## Purpose

This repository contains the current AIL platform mainline, including:

- AIL engine and server code
- CLI v1 implementation
- testing and benchmark infrastructure
- cloud sync and API specifications
- archived legacy material

AIL is the single source of truth.

## Start Here

If you are new to this repo, read these in order:

1. `/Users/carwynmac/ai-cl/REPO_MAP.md`
2. `/Users/carwynmac/ai-cl/PROJECT_CONTEXT.md`
3. `/Users/carwynmac/ai-cl/docs/AIL_CLOUD_SYNC_PROTOCOL_V1.md`
4. `/Users/carwynmac/ai-cl/docs/AIL_CLI_IMPLEMENTATION_GUIDE.md`
5. `/Users/carwynmac/ai-cl/testing/raw_lane_baseline_v50.md`
6. `/Users/carwynmac/ai-cl/archive/ARCHIVE_INDEX.md`

For current website-oriented product packaging, also see:

- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_PHASE_REVIEW_20260417.md`
- `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260409.md`
- `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260408.md`
- `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260406.md`
- `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260403.md`
- `/Users/carwynmac/ai-cl/WEBSITE_PRIORITY_REVIEW_20260403.md`
- `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260402.md`
- `/Users/carwynmac/ai-cl/WEBSITE_PRIORITY_REVIEW_20260402.md`
- `/Users/carwynmac/ai-cl/WEBSITE_PHASE_MILESTONE_20260403.md`
- `/Users/carwynmac/ai-cl/WEBSITE_PHASE_CLOSEOUT_20260403.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_PHASE_REVIEW_20260416.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_PHASE_REVIEW_20260409.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_PERSONAL_SLICE_EVALUATION_20260409.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_COMPANY_SLICE_EVALUATION_20260409.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_REVIEW_20260409.md`
- `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_IMPLEMENTATION_PLAN_20260409.md`
- `/Users/carwynmac/ai-cl/NEXT_PHASE_RECOMMENDATION_20260409.md`
- `/Users/carwynmac/ai-cl/NEXT_PHASE_OPTIONS_RFC_20260403.md`
- `/Users/carwynmac/ai-cl/MANAGED_UNMANAGED_PHASE1_20260331.md`
- `/Users/carwynmac/ai-cl/MANAGED_UNMANAGED_PHASE2_COMPONENT_HOOKS_20260331.md`
- `/Users/carwynmac/ai-cl/MANAGED_UNMANAGED_PHASE3_HOOK_CATALOG_20260402.md`
- `/Users/carwynmac/ai-cl/MANAGED_UNMANAGED_MILESTONE_20260403.md`
- `/Users/carwynmac/ai-cl/CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md`
- phase-2 hooks now also carry lightweight page / section context into Vue hooks and HTML partial wrappers
- phase-2 hook coverage now also includes the first ecom discovery / purchase section hooks
- phase-2 hook coverage now also includes the first landing / company-homepage child-slot hooks for selected hero / FAQ / CTA / footer subareas
- phase-2 hook coverage now also includes the first ecom child-slot hooks for selected product / checkout subareas
- phase-2 hook coverage now also includes the first after-sales child-slot hooks for selected tracked-case subareas
- selected landing, after-sales, and ecom hooks now also carry small runtime summaries through `context.runtime`
- the managed / unmanaged + hook workflow is now strong enough to treat as a stable customization milestone
- local rebuild protection for managed frontend files now also lands summaries under:
  - `/.ail/local_rebuild_backups/<timestamp>/summary.md`
- `/Users/carwynmac/ai-cl/output/playwright/personal_signature_review_runtime.png`
- `/Users/carwynmac/ai-cl/output/playwright/personal_story_review_submit_runtime.png`
- `/Users/carwynmac/ai-cl/SAFE_SPLIT_REVIEW_20260328.md`
- `/Users/carwynmac/ai-cl/SYSTEM_VS_TEST_HELPER_BOUNDARY_20260322.md`
- `/Users/carwynmac/ai-cl/SYSTEM_VS_TEST_HELPER_DETAILED_MATRIX_20260322.md`
- `/Users/carwynmac/ai-cl/WEBSITE_SUPPORT_MATRIX_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_FRONTIER_SUMMARY_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_PRODUCT_PACK_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_DEMO_PACK_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_DELIVERY_CHECKLIST_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_REQUIREMENT_TEMPLATES_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_SALES_POSITIONING_20260319.md`
- `/Users/carwynmac/ai-cl/WEBSITE_NEXT_TASKS_20260319.md`
- `/Users/carwynmac/ai-cl/testing/results/website_delivery_assets_20260319.md`

Safe split status:

- phase-1 extraction is already implemented
- `/Users/carwynmac/ai-cl/ail_engine_v5_ecom.py` now contains the ecom / after-sales view generators
- `/Users/carwynmac/ai-cl/ail_engine_v5.py` remains the main orchestrator and delegates through `AILEcomGeneratorMixin`
- this is the current recommended pause point before any second-stage `landing` extraction

Run the website demo pack directly:

```bash
bash /Users/carwynmac/ai-cl/testing/run_website_demo_pack.sh
```

Build reusable delivery assets for each website pack:

```bash
bash /Users/carwynmac/ai-cl/testing/build_website_delivery_assets.sh
```

Read the latest project state review:

```bash
cat /Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260409.md
```

Check whether a requirement fits the current website delivery surface:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website check '做一个企业产品官网，包含首页、功能介绍、FAQ、联系我们。' --base-url embedded://local --json
```

Read the reusable website delivery asset bundles:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website assets --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website assets company_product --json
```

Resolve one concrete website delivery asset target:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website open-asset --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website open-asset company_product --json
```

Inspect one concrete website delivery asset target directly:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website inspect-asset --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website inspect-asset company_product --json
```

Show the current website-level preview and handoff targets:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website preview --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website preview company_product --json
```

Export one consolidated website-oriented handoff bundle:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website export-handoff --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website export-handoff company_product --json
```

Execute the asset inspection step implied by the current website handoff:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website run-inspect-command --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website run-inspect-command company_product --json
```

Read the current website-oriented frontier, assets, validation, and demo state in one view:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website summary --json
```

Execute the current recommended website-oriented action directly:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli website go --json
```

## Fastest Trial Entry

If you want the shortest frozen-profile product path, run:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli trial-run --scenario landing --base-url embedded://local
```

Or use the thin wrapper:

```bash
bash /Users/carwynmac/ai-cl/demo_v1.sh --scenario landing
```

The CLI preview handoff is now consistent across:

- `trial-run --json`
- `cloud status --json`
- `build artifact <build_id> --json`
- `project summary --json`

Batch-check the full frozen-profile entry surface:

```bash
bash /Users/carwynmac/ai-cl/testing/run_trial_entry_checks.sh
```

If you want a repo-level or current-project workspace overview before deciding what to run next:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace status --base-url embedded://local
```

If you want a shorter workspace-level summary for operator or agent use:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace summary --base-url embedded://local
```

If you want the CLI to execute the current recommended workspace-level action directly:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace go --base-url embedded://local
```

If you want a workspace-level recovery diagnosis before choosing the next repo-level or project-level path:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace doctor --base-url embedded://local
```

If you want the default high-frequency workspace follow-up path:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace continue --base-url embedded://local
```

If you want a single CLI view of the current RC and readiness state:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli rc-check --base-url embedded://local
```

If you want the same view after refreshing readiness first:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli rc-check --refresh --base-url embedded://local
```

If you want the CLI to execute the current RC-level recommended action directly:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli rc-go --base-url embedded://local
```

If you are already inside an initialized AIL project and want a higher-level project view:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project summary --base-url embedded://local
```

If you want the shortest project-level preview handoff:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project preview --base-url embedded://local
```

If you want one concrete project preview target resolved for inspection:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project open-target --base-url embedded://local
```

If you want the CLI to inspect that resolved project target directly:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project inspect-target --base-url embedded://local
```

If you want the CLI to execute that project inspection step in one go:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project run-inspect-command --base-url embedded://local --json
```

If you want the shortest workspace-level preview handoff:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace preview --base-url embedded://local
```

If you want one concrete workspace preview target resolved for inspection:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace open-target --base-url embedded://local
```

If you want the CLI to execute that workspace inspection step in one go:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace run-inspect-command --base-url embedded://local --json
```

If you want one consolidated workspace handoff bundle for IDEs or agents:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace export-handoff --base-url embedded://local --json
```

The website-oriented handoff surface is now stronger as well:

- `project export-handoff --json` includes `website_delivery_summary`
- `workspace export-handoff --json` includes `website_surface_summary` at repo root and delegates to the same project-level `website_delivery_summary` inside initialized projects

If you want the CLI to execute the current recommended project workbench action:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project go --base-url embedded://local
```

If you want a non-destructive project health check before continuing work:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project check --base-url embedded://local
```

If you want a recovery-oriented diagnosis for the current project:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project doctor --base-url embedded://local
```

For the full command-by-command path, see:

- `/Users/carwynmac/ai-cl/QUICKSTART_V1.md`
- `/Users/carwynmac/ai-cl/PROJECT_CONTEXT.md` for the current development phase snapshot

## Main Areas

| Path | Purpose |
| --- | --- |
| `/Users/carwynmac/ai-cl/cli/` | AIL CLI v1 |
| `/Users/carwynmac/ai-cl/docs/` | Protocol and implementation docs |
| `/Users/carwynmac/ai-cl/testing/` | Raw lane, repair smoke, CLI smoke, evolution loop |
| `/Users/carwynmac/ai-cl/benchmark/` | Frozen vs experimental benchmark harness |
| `/Users/carwynmac/ai-cl/skills/` | Generator, diagnostic, and repair skills |
| `/Users/carwynmac/ai-cl/archive/` | Archived legacy or generated material |

## Core Runtime Files

Current active mainline:

- `/Users/carwynmac/ai-cl/ail_engine_v4.py`
- `/Users/carwynmac/ai-cl/ail_engine_v5.py`
- `/Users/carwynmac/ai-cl/ail_server_v5.py`

## Useful Commands

### CLI checks

```bash
bash /Users/carwynmac/ai-cl/testing/run_cli_checks.sh
```

### Benchmark

```bash
bash /Users/carwynmac/ai-cl/benchmark/run_benchmark.sh
```

### Raw lane

```bash
bash /Users/carwynmac/ai-cl/testing/run_raw_model_outputs.sh
```

### Evolution loop

```bash
bash /Users/carwynmac/ai-cl/testing/run_evolution_loop.sh
```

## Cleanup Rule

Before moving or deleting top-level files:

1. audit references first
2. archive before delete
3. rerun CLI checks
4. rerun benchmark if workflow files were touched

Detailed cleanup records:

- `/Users/carwynmac/ai-cl/archive/CLEANUP_AUDIT_20260316.md`
- `/Users/carwynmac/ai-cl/archive/ARCHIVE_INDEX.md`

## Current Status

The repo is currently organized around:

- active mainline code
- stable testing and benchmark flows
- protocol and implementation documentation
- retained side workflows
- archived legacy material


If you want one consolidated project handoff bundle for IDEs or agents:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project export-handoff --base-url embedded://local --json
```

Shortest operator cheat sheet for the current durable-hook workflow:

- `/Users/carwynmac/ai-cl/CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md`

Managed / unmanaged customization quick start:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project hook-guide --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-guide --json
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-continue --dry-run --text-compact
```

If you want grouped operator help first:

```bash
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project hook-guide --help
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-guide --help
PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-continue --help
```

Customization UX is now strong enough that the README no longer needs to mirror every helper flag.

Use the current operator vocabulary across these entrypoints:

- `overview`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project hook-guide --json`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-guide --json`
- `discover`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project hooks --json`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hooks --json`
- `preview`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-continue --dry-run --text-compact`
- `handoff / execute`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli project hook-init ...`
  - `PYTHONPATH=/Users/carwynmac/ai-cl python3 -m cli workspace hook-init ...`

Use these documents instead of treating the README as the full command matrix:

- current brand-distinction validation review:
  - `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_REVIEW_20260409.md`
- current brand-distinction implementation plan:
  - `/Users/carwynmac/ai-cl/BRAND_DISTINCTION_IMPLEMENTATION_PLAN_20260409.md`
- current next-phase recommendation:
  - `/Users/carwynmac/ai-cl/NEXT_PHASE_RECOMMENDATION_20260409.md`
- current customization closeout:
  - `/Users/carwynmac/ai-cl/CUSTOMIZATION_UX_PHASE_CLOSEOUT_20260409.md`
- operator quick path:
  - `/Users/carwynmac/ai-cl/CUSTOMIZATION_UX_OPERATOR_CHEAT_SHEET_20260406.md`
- current phase truth:
  - `/Users/carwynmac/ai-cl/PROJECT_STATE_REVIEW_20260409.md`
- historical phase detail:
  - `/Users/carwynmac/ai-cl/MANAGED_UNMANAGED_PHASE3_HOOK_CATALOG_20260402.md`

Current validation anchor for the customization workflow remains:

- `/Users/carwynmac/ai-cl/testing/results/cli_smoke_results.json`
  - `status = ok`

Fresh validation note:

- after a temporary Codex exec/session-pool overload on 2026-04-03, Codex was restarted
- fresh compile passed again on 2026-04-04
- fresh `/Users/carwynmac/ai-cl/testing/cli_smoke.sh` passed again on 2026-04-04
- `/Users/carwynmac/ai-cl/testing/results/cli_smoke_results.json` remains the current green reference

Generated override examples:

```text
frontend/src/ail-overrides/components/examples/README.md
frontend/src/ail-overrides/components/examples/page.home.before.example.vue
frontend/src/ail-overrides/components/examples/page.home.section.hero.after.example.html
```

Copy one of these into `frontend/src/ail-overrides/components/`, rename it to a real hook name from `.ail/hook_catalog.md`, then edit it in place.
