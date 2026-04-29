# Context Metrics Report 2026-04-28

## Goal

Capture one concrete metrics-focused validation pass for the `context` workflow after formal metrics output was added to:

- `context compress`
- `context inspect`

This report exists to separate:

- machine-emitted metrics
- heuristic token estimation
- illustrative cost reasoning

That separation matters because the metrics are useful, but they are not billing-grade tokenizer results.

## Scope

Validated surface:

- `/Users/carwynmac/ai-cl/cli/context_compression.py`
- `/Users/carwynmac/ai-cl/cli/ail_cli.py`

Relevant commit under test:

- `33783d0 feat: add context metrics output`

## Metrics Fields

The current `context` metrics surface includes:

- `source_char_count`
- `skeleton_char_count`
- `estimated_token_count_source`
- `estimated_token_count_skeleton`
- `estimated_tokens_saved`
- `estimated_token_delta_from_source`
- `estimated_token_direction`
- `estimated_token_reduction_ratio`
- `estimated_token_size_ratio`
- `char_reduction_ratio`
- `token_estimate_basis`
- `token_estimate_backend`
- `token_estimate_model`
- `token_estimate_requested_backend`
- `token_estimate_fallback_used`
- `heuristic_token_count_source`
- `heuristic_token_count_skeleton`
- `tokenizer_available`

Current estimation modes:

- default fallback: `heuristic_chars_div_4`
- optional tokenizer-backed mode: `tiktoken:<encoding>`

This means:

- token counts are estimated unless a tokenizer-backed mode is explicitly requested and available
- the results are good enough for operator reporting and regression comparison
- the results are not exact tokenizer measurements for any specific production model

## Sample Validation Result

One external repo-scale sample reported:

- raw characters: `900,809`
- skeleton characters: `19,569`
- observed char reduction ratio: `0.0217`
- estimated source tokens: `225,203`
- estimated skeleton tokens: `4,893`
- estimated tokens saved: `220,310`

Equivalent reading:

- observed raw-to-skeleton char reduction was about `97.83%`
- estimated token footprint fell to roughly `2.17%` of the raw source in that sample

One later Windows validation pass also confirmed the optional tokenizer-backed path with:

- tokenizer backend: `tiktoken`
- tokenizer model / encoding: `cl100k_base`
- raw characters: `8,119`
- skeleton characters: `2,652`
- tokenizer-counted source tokens: `1,346`
- tokenizer-counted skeleton tokens: `569`
- tokenizer-counted tokens saved: `777`

Equivalent reading:

- observed raw-to-skeleton char reduction was about `67%`
- tokenizer-counted token footprint fell to about `42.27%` of the raw source in that sample

That Windows pass also surfaced one practical setup note:

- on Windows, `pip install tiktoken` may target a different interpreter than `py -3 -m cli`
- the safer install path is:
  - `py -3 -m pip install tiktoken`

That note matters because the CLI feature itself was fine; the real issue was environment mismatch.

## How To Read These Numbers

The sample above is meaningful, but only inside its scope.

It should be read as:

- one repo-scale observed result
- one illustration of why structured skeletons can dramatically reduce context pressure

It should **not** be read as:

- a guarantee that every file or project compresses to `2%`
- an exact token bill for any one model provider
- a universal cost-savings promise

## Important Boundary

Very small inputs may show:

- `estimated_token_direction = expanded`

That is expected.

Reason:

- the MCP skeleton header and structural markers can outweigh the original source when the source is already tiny

This is a feature, not a failure:

- the metrics surface now reports that honestly instead of pretending every input always shrinks

The intended primary targets are still:

- large code directories
- long-form writing
- multi-file project context

## Cost Framing

Any cost calculation based on the current metrics must be labeled as an example.

Safe wording:

- `illustrative cost estimate under a simple per-1K-token assumption`
- `example savings estimate based on heuristic token counts`

Unsafe wording:

- `actual API cost`
- `guaranteed savings`

Why:

- model pricing changes
- cached-token pricing differs from fresh-token pricing
- providers count tokens differently
- input and output pricing are usually separate

## Practical Use

The metrics surface is already useful for:

- comparing raw source size against skeleton size
- deciding whether compression is worth using for a given input
- writing test reports without hand-counting characters
- tracking regressions if skeleton output unexpectedly grows

## Recommended Operator Language

Recommended:

- `estimated token reduction`
- `observed reduction in this sample`
- `heuristic token estimate`
- `repo-scale sample`

Avoid:

- `exact token cost`
- `guaranteed 97% reduction`
- `all inputs shrink dramatically`

## Suggested Next Step

If deeper precision becomes important later, the next natural enhancement would be:

- broader tokenizer coverage beyond the initial optional `tiktoken` path

The current heuristic metrics are already appropriate for:

- alpha testing
- operator reporting
- external validation summaries

## Final Judgment

The current metrics surface is strong enough for public alpha documentation.

Recommended label:

- `operator-grade metrics, not billing-grade metrics`

That is the right balance:

- useful enough to guide decisions
- honest enough to avoid overclaiming precision
