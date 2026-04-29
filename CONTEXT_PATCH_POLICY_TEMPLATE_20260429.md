# Context Patch Policy Template

This repository now supports policy-aware replay for:

- `python3 -m cli context patch-apply --policy-file ...`

Use a policy file when you want replay rules that are:

- stricter than the default `open` mode
- more explicit than repeating many CLI flags
- easy to reuse across multiple bundles or operators

## Recommended Starter File

Example template:

Path:

- `/Users/carwynmac/ai-cl/examples/context_patch_policy.safe.json`

Contents:

```json
{
  "require_apply_check_passed": true,
  "block_removals": true,
  "block_additions": false,
  "max_changed_paths": 12,
  "allow_roots": [
    "src",
    "docs"
  ],
  "forbid_roots": [
    "src/generated",
    "secrets"
  ]
}
```

## Supported Fields

- `require_apply_check_passed`
  - `true` blocks replay unless the patch bundle recorded a passing apply-check result.

- `block_removals`
  - `true` blocks replay when the patch removes any path.

- `block_additions`
  - `true` blocks replay when the patch adds any path.

- `max_changed_paths`
  - Integer cap across `changed_paths + added_paths + removed_paths`.

- `allow_roots`
  - Relative path prefixes that replay is allowed to touch.
  - If present, every affected path must fall under at least one allowed root.

- `forbid_roots`
  - Relative path prefixes that replay must never touch.

## Merge Rules

Replay policy is resolved in this order:

1. built-in preset from `--policy-mode`
2. JSON overrides from `--policy-file`
3. explicit CLI flags such as:
   - `--allow-root`
   - `--forbid-root`
   - `--block-removals`
   - `--block-additions`
   - `--require-apply-check-pass`
   - `--max-changed-paths`

CLI flags win over the JSON file.

## Example Usage

Safe directory replay:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-patch/patch_manifest.json \
  --source-package-file /absolute/path/to/context-bundle/context_manifest.json \
  --policy-mode safe \
  --policy-file /Users/carwynmac/ai-cl/examples/context_patch_policy.safe.json \
  --output-dir /absolute/path/to/replayed-project \
  --emit-summary
```

Tighter text replay:

```bash
PYTHONPATH="$PWD" python3 -m cli context patch-apply \
  --patch-file /absolute/path/to/context-patch/patch_manifest.json \
  --policy-file /Users/carwynmac/ai-cl/examples/context_patch_policy.safe.json \
  --allow-root notes \
  --block-additions \
  --output-file /absolute/path/to/replayed.txt \
  --json
```

## Expected Failure Shape

When a replay is blocked by policy, the command returns:

- `status = warning`
- `apply_mode = policy_blocked`
- `policy_passed = false`
- `policy_findings`

and exits with the validation status instead of replaying the patch.
