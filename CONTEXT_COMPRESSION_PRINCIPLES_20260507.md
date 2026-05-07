# Context Compression Principles 2026-05-07

## Purpose

This document explains the engineering model behind AIL Builder's `context` surface.

The goal is not "summarize a large input."
The goal is to make oversized codebases, books, project trees, and long-form drafts usable inside AI context windows **without losing structural continuity or exact machine recovery**.

In practical terms, the system is designed to:

- reduce prompt weight for large inputs
- preserve the logic-carrying structure another AI needs first
- keep an exact restore package next to the compressed view
- support safe downstream workflows such as inspect, apply-check, patch, and replay

## Core Model

The system splits one original source into two coordinated layers:

1. AI-facing skeleton
2. Machine-facing restore package

### AI-facing skeleton

The skeleton is a compact structural representation written in `MCP-SKL.v1`.

It is optimized for:

- low token footprint
- fast first-pass understanding
- structural navigation
- cross-agent handoff

It keeps the parts of the source that matter most for interpretation:

- file trees
- headings and section order
- imports
- symbols
- relationship hints
- theme terms
- route or component roles
- incremental change surfaces when requested

### Machine-facing restore package

The restore package keeps the exact payload needed to reconstruct the source.

It is optimized for:

- exact recovery
- stable handoff
- patch and replay workflows
- operator trust

This package is currently stored as a structured encoded blob:

- `zlib + base64 + json`

That lets the system preserve:

- full text
- exact file bytes
- exact directory tree contents
- incremental removed-path manifests where applicable

## Why This Is Not Ordinary Summarization

Ordinary summarization throws detail away and asks the model to work from an abstraction alone.

This system does something different:

- it **re-encodes** the source for AI consumption
- it does **not** rely on the summary to hold the whole original
- it keeps exact restoration outside the model context

That is why the system can support:

- compressed review
- exact restore
- safe patch export
- replay with dry-run, policy, and merge gates

## Compression Strategy

The main compression principle is:

**preserve logic-bearing structure, strip first-pass reading overhead**

The system separates information into two broad categories.

### Category A: structure an AI needs first

Examples:

- directory trees
- class and function symbols
- import graphs
- section headings
- chapter flow
- route boundaries
- component roles
- changed / added / removed path sets

This information is promoted into the skeleton.

### Category B: full surface detail a machine must keep

Examples:

- full prose paragraphs
- complete source code bodies
- repeated boilerplate
- exact formatting details
- all file bytes in a directory tree

This information stays in the restore package.

The result is not "the source, but shorter."
It is "the source, split into a structural AI view and an exact recovery view."

## Input Shapes

The current design supports three primary input shapes:

1. long text
2. one file
3. one directory tree

### Long text

Typical examples:

- books
- manuscripts
- long briefs
- technical notes

The skeleton preserves:

- heading hierarchy
- section flow
- repeated themes
- core structure terms

### One file

Typical examples:

- Python source
- Markdown
- config files

The skeleton preserves:

- imports
- symbol boundaries
- dominant terms
- file role hints

### One directory tree

Typical examples:

- repos
- websites
- ecommerce projects
- content bundles

The skeleton preserves:

- file tree
- per-file code or text summaries
- symbol and import structure
- route / component / section roles when relevant

## Why Token Savings Grow With Scale

The project is intentionally strongest on large inputs.

For small inputs, metadata overhead can outweigh the benefit.
For large inputs, the structural view grows much more slowly than the raw content surface.

This produces the key scaling effect:

- raw source tokens usually grow roughly with total input volume
- skeleton tokens grow more slowly because they represent structure, not full surface detail

That is why:

- a short single file may expand
- a repo-sized directory often compresses dramatically
- a long book-length text usually compresses far more aggressively than a short article

This is also why the metrics surface reports direction honestly:

- `reduced`
- `expanded`
- `flat`

The system does not pretend every input always shrinks.

## Metrics Philosophy

The metrics layer exists to make compression behavior observable and comparable.

It reports:

- source characters
- skeleton characters
- estimated source tokens
- estimated skeleton tokens
- token direction
- reduction ratios

Two token-estimation paths exist:

1. heuristic estimates
2. tokenizer-backed estimates

The heuristic path is useful as a fallback and for deterministic smoke coverage.
The tokenizer-backed path is better for closer model-aligned reporting.

Neither path is described as billing-grade cost accounting.

## Exact Restore Principle

The exact restore principle is simple:

**the skeleton is never the only copy of meaning**

Meaning is split:

- interpretation-critical structure goes into the skeleton
- exact reconstruction data stays in the restore package

This is what allows the system to claim:

- low-token AI transport
- exact machine recovery

without cheating by truncating the original and hoping the model "remembers enough."

## Incremental Compression Principle

Incremental compression is the next major scaling lever.

For large repos, the useful AI surface is often not the full tree.
It is the current change surface.

Current incremental behavior:

- reads git-backed change state
- identifies changed paths
- identifies added paths
- records removed paths
- builds the AI-facing skeleton only from the incremental surface

This means the incremental package is exact for:

- changed files
- added files
- removed-path metadata

It does not claim to reconstruct untouched repository content.

That is an intentional boundary, not a bug.

This is the mechanism that will keep making the token advantage stronger as projects grow:

- full repository size keeps increasing
- actual active change surface often stays small

## From Compression To Workflow

`context` is not just a compressor.
It is a workflow surface built around the compressed representation.

Current workflow layers include:

1. `context compress`
2. `context inspect`
3. `context restore`
4. `context apply-check`
5. `context patch`
6. `context patch-apply`
7. `context patch-apply --dry-run`
8. policy-aware replay
9. merge-aware replay
10. incremental bundle and benchmark paths

That makes the system useful for:

- long-context transport
- cross-agent handoff
- controlled replay
- diff export
- safe operator review

## Safety Model

The safety model matters because compressed context is not useful if replay is unsafe.

Current safety principles include:

- no blind overwrite without explicit replay mode
- dry-run preview before mutation
- policy gating for allowed and forbidden roots
- merge gating for conflict-aware replay
- path validation to reject absolute paths, drive-qualified paths, and `..` traversal

These controls are part of the compression system, not separate extras, because the point is not just to shrink context.
The point is to make compressed context usable in real engineering workflows.

## What The System Is

This system is best thought of as:

- a low-token context transport layer
- a structured AI handoff protocol
- an exact restore mechanism
- a replay-safe patch workflow

## What The System Is Not

It is not primarily:

- a generic summarizer
- a vector database
- a full code knowledge graph
- a substitute for all IDE-native repo intelligence

Those can be complementary systems.
The `context` line is strongest when it stays focused on:

- compressing oversized input surfaces
- preserving exact recoverability
- making downstream AI collaboration cheaper and safer

## Design Implication For Future Work

If the long-term objective is:

- larger repos
- longer books
- more files
- lower effective token spend

then the best next-stage work stays on this axis:

1. stronger incremental workflows
2. more stable large-scale benchmarks
3. better structure-focused skeleton views
4. safer and more precise replay surfaces

That is the path most aligned with the current architecture and its strongest product advantage.
