# I Built a Local Codebase Map for AI Agents Instead of Another Chat UI

*Private draft — do not publish until the token and citation measurements are complete.*

Coding agents are getting better quickly. The bottleneck I keep seeing is less exciting:
they spend too much of every session figuring out where things are.

They grep. They open one file. They follow an import. They grep again. They reconstruct a
mental map, use it once, and pay to reconstruct it again in the next session.

I built Glob to make that exploration a small, local tool call instead.

## The idea

Glob is a local-first codebase index exposed as an MCP server. An agent can ask:

- where is provenance recorded?
- what fits elasticity, and when does it refuse?
- who calls `solve()`?
- where are resource capacities enforced?

The answer is not a generated explanation pretending to know the repository. It is a ranked
set of evidence with explicit `file:line` citations.

That distinction matters. A symbol definition found by the parser is not the same kind of
evidence as a fuzzy text match. Glob labels the difference.

## Why local?

The first version has no hosted backend, account system, telemetry, or embeddings API. The
index is SQLite in the target repository's `.glob/` directory. Python symbols are extracted
with tree-sitter WASM, and file contents are searched with SQLite FTS5.

This makes the privacy story simple: the repository does not leave the machine. It also keeps
the operating cost near zero while the product is still being tested.

A hosted API may eventually make sense for CI reports, shared team indexes, or agent
orchestrators. It is not the foundation. The local MCP tool is the wedge.

## The implementation

The MVP has four MCP tools:

- `glob_overview`
- `glob_search`
- `glob_find_symbol`
- `glob_trace`

The CLI can incrementally index a gitignore-aware repository:

```bash
bun run src/index.ts index /path/to/repo
bun run src/index.ts search /path/to/repo "calibrate_elasticity"
```

The response is deliberately mechanical:

```text
citation=engine/src/scrcae/calibration/elasticity.py:404
source=symbol
kind=def
name=calibrate_elasticity
score=3
```

The agent does not need to guess whether a result came from a definition or a text match.

## Dogfooding on a real repository

I used a supply-chain resilience optimizer as the first corpus. It has two layers — a
headless Python optimization engine and a Streamlit application — plus tests, documentation,
and an audit/provenance model.

The first indexing run produced these results:

- 80 Python files parsed
- 848 KB of Python source
- 1,131 symbols indexed
- approximately 240 ms to parse the corpus during the initial spike
- approximately 19 ms for a subsequent unchanged incremental index
- zero parser errors in the spike
- 9 automated tests passing in Glob itself after the hardening pass

The four discovery questions surfaced useful paths immediately:

- provenance: `app/services/macro.py:44`, `app/storage/models.py:45`, and engine provenance definitions
- elasticity calibration: `engine/src/scrcae/calibration/elasticity.py:404`
- refusal behavior: `engine/src/scrcae/calibration/elasticity.py:431` and refusal tests
- `solve()` references: `app/engine_client.py:47`, `app/adapters.py:725`, and `app/copilot.py:340`
- resource capacity logic: `engine/src/scrcae/domain/network.py:157` and
  `engine/src/scrcae/optimization/optimizer.py:471`

These are candidate citations, not a claim that the agent can skip reading source. The next
measurement is to compare how many tokens an agent needs to reach a correct answer with Glob
against a grep-and-read baseline.

## What is not proven yet

I am not claiming a 40% token reduction or 95% citation accuracy yet. Those are explicit exit
criteria, and the current CLI does not instrument model-token usage.

That is an intentional product rule: a useful-looking search result is not the same thing as
a measured improvement. If Glob cannot hit the quality bar, the search wedge should be
changed or dropped rather than hidden behind a hosted API.

## The market placement

The individual product is free, local, and compatible with the agents developers already use.
The paid opportunity is not charging for a grep replacement. It is the team layer around
context:

- shared query packs
- CI pull-request context reports
- organization policy and usage controls
- optional hosted indexing when a team explicitly needs it

The order matters. Build the shovel people can install in a minute. Add the mine only when
customers ask for collaboration.

## Current status

Glob is MIT-licensed, packaged for Bun distribution, and has a working stdio MCP server. It
is not a hosted SaaS, and that is currently a feature rather than unfinished infrastructure.

The next honest step is measurement: run the same four questions through an agent with and
without Glob, record tokens and citation correctness, then decide whether this is a product
or just a neat tool.
