# Context Patch-Apply Regression Report 2026-04-29

## Goal

Capture one concrete external regression pass that validates the full `context` replay lane after:

- `context patch-apply`
- tokenizer-backed `context` metrics

This report is intentionally narrower than the broader context test matrix.
Its job is to confirm that one edited candidate can move all the way through:

1. bundle creation
2. patch creation
3. patch replay
4. replay-result verification
5. tokenizer-backed metrics inspection

## Environment

- platform: Windows + PowerShell
- Python entrypoint: `py -3`
- tokenizer backend under test: `tiktoken`
- tokenizer model / encoding under test: `cl100k_base`

Important setup note confirmed during the run:

- on Windows, `py -3 -m pip install tiktoken` is the safer install path
- this avoids the common mismatch where `pip` installs into a different interpreter than the one used by `py -3 -m cli`

## Commands Under Test

Bundle creation:

```powershell
py -3 -m cli context bundle --text-file "test_patch_original.txt" --zip --output-dir "patch_test_original" --tokenizer-backend tiktoken --tokenizer-model cl100k_base --json
```

Patch creation:

```powershell
py -3 -m cli context patch --package-file "patch_test_original/context_manifest.json" --text-file "test_patch_edited.txt" --output-dir "patch_test_patch" --json
```

Patch replay:

```powershell
py -3 -m cli context patch-apply --patch-file "patch_test_patch/patch_manifest.json" --output-dir "patch_test_output" --json
```

Tokenizer-backed metrics check:

```powershell
py -3 -m cli context compress --text-file "test_large_context.txt" --preset website --tokenizer-backend tiktoken --tokenizer-model cl100k_base --json
```

## Regression Results

| Stage | Result | Notes |
|------|------|------|
| bundle creation | pass | bundle exported successfully |
| patch creation | pass | diff and candidate snapshot exported successfully |
| patch-apply replay | pass | replay completed into a safe output target |
| replay verification | pass | replayed file matched the edited candidate |
| tokenizer-backed metrics | pass | `tiktoken` metrics emitted successfully |
| apply-check continuity | pass | aligned candidate reported `strong` |

## Observed Patch-Apply Flow

Observed working sequence:

1. compress original text into a context bundle
2. generate a patch bundle from the edited text
3. replay the patch bundle into a fresh output target
4. verify that the replayed file equals the edited candidate

This confirms that `context patch-apply` is not only exporting metadata correctly, but is also able to reconstruct the edited result in a controlled replay target.

## Observed Tokenizer Metrics Result

Tokenizer-backed sample:

- source characters: `8,119`
- skeleton characters: `2,652`
- tokenizer-counted source tokens: `1,346`
- tokenizer-counted skeleton tokens: `572`
- tokenizer-counted tokens saved: `774`

Equivalent reading:

- the skeleton retained about `42.5%` of the original token footprint in this sample
- the compression pass saved about `57.5%` of source tokens in this sample

This wording is important.
It should not be shortened to "saved 42.5%" because that would invert the meaning of the ratio.

## Apply-Check Result

Observed continuity result:

- alignment score: `92`
- alignment band: `strong`

This matters because it shows the patch/export/replay path did not destabilize the existing structural-alignment checks.

## Interpretation

This regression pass confirms three important things:

1. `context patch-apply` is operational, not just specified
2. tokenizer-backed metrics can run in real Windows environments when `tiktoken` is installed into the same interpreter used by `py -3 -m cli`
3. patch replay and structural continuity checks coexist cleanly in the same workflow

## Recommended Positioning

Safe wording:

- `context patch-apply has passed an external replay regression on Windows`
- `tokenizer-backed metrics have been validated with tiktoken on Windows`
- `patch replay plus continuity checking now forms a complete external-testable context workflow`

Avoid:

- `production-ready patch engine`
- `exact API billing`
- `universal token savings guarantee`

## Final Judgment

Recommended label for this specific lane:

- `context replay and tokenizer-metrics workflow: externally validated alpha`

That is the right level of confidence:

- stronger than a local-only implementation claim
- still honest about the fact that broader cross-environment validation should continue
