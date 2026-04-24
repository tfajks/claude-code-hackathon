# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is a hackathon specification framework — not a runnable application. It contains five enterprise engineering scenario briefs. Teams pick one scenario, build their own solution alongside these documents, and submit three files: `README.md`, `CLAUDE.md`, and `presentation.html`.

There are no build, test, or lint commands at the repo level. Each team defines their own stack and tooling per scenario.

## Scenarios

| # | File | Challenge |
|---|------|-----------|
| 1 | [01-code-modernization.md](01-code-modernization.md) | Extract services from a monolith nobody understands |
| 2 | [02-cloud-migration.md](02-cloud-migration.md) | On-prem to cloud; CFO and CTO disagree on how |
| 3 | [03-data-engineering.md](03-data-engineering.md) | Seven systems, zero agreement on what a "customer" is |
| 4 | [04-data-analytics.md](04-data-analytics.md) | 40 dashboards, one metric, four conflicting answers |
| 5 | [05-agentic-solution.md](05-agentic-solution.md) | 200 requests/day triaged by hand — build the agent |

**Scenario 5 is the only one with a required tech constraint**: it must use the Claude Agent SDK (Python or TypeScript).

## Submission Requirements

Judges read these three files first — assume they carry the full weight:

1. **`README.md`** — fills the template in the main README: participants, scenario, what was built, challenges attempted, key decisions, how to run it, what's next, how Claude Code was used.
2. **`CLAUDE.md`** — shows how the team taught Claude Code their conventions.
3. **`presentation.html`** — an HTML deck built with Claude Code, ready to deliver live.

Submit as `Table#_TeamName/` folder or `Table#_TeamName.zip`. No client or internal data in any submission.

## Three-Level CLAUDE.md Pattern

The hackathon encourages this hierarchy, which teams should implement as they build:

- **User-level** (`~/.claude/CLAUDE.md`): personal preferences, not committed
- **Project-level** (root `CLAUDE.md`): shared conventions, committed to VCS
- **Directory-level** (e.g. `src/agents/CLAUDE.md`): per-module specifics

## Techniques Worth Reaching For

These patterns appear in the certification domains the scenarios stress. Use them deliberately, not just because they're available.

**Agentic Architecture (Scenario 5 especially)**
- Coordinator + specialist subagents via the Task tool. Task subagents do *not* inherit coordinator context — pass everything explicitly in each Task prompt.
- `stop_reason` handling in the agent loop (not just an iteration cap).
- `fork_session` to run two paths on the same input and compare.

**Tool Design**
- Tool descriptions state what the tool does *and* what it does not — input formats, edge cases, example queries.
- Structured error responses: `isError: true` with a reason code and recovery guidance so the agent can retry rather than parse a string.
- Cap specialist tool sets at ~4–5 tools; reliability drops past that range.
- Expose built systems via an MCP server so a fresh Claude session picks the right tool on first try.

**Claude Code Config**
- `PreToolUse` hooks for deterministic hard stops (PII exfil, known-bad routes). Use prompts for probabilistic preferences. Write an ADR explaining why each guardrail is a hook versus a prompt — the distinction is cert-testable.
- Custom slash commands run a playbook; skills capture reusable guidance. Use them distinctly.
- Plan Mode for reversible-dangerous operations; direct execution for safe paths.
- Non-interactive Claude Code in CI: scoped tools, no write access to production paths.

**Prompt Engineering**
- Replace vague modifiers ("significant," "recent") with explicit thresholds.
- Two sharp few-shot examples (including a negative and a boundary case) outperform eight fuzzy ones.
- Use `tool_use` with JSON Schema for structured output. Don't prompt-for-JSON.
- Validation-retry loop: validator checks output against schema, feeds specific errors back, retries up to N times. Log retry count and error type.

**Context Management / Escalation**
- Escalation rules = category + confidence threshold + impact bucket. Vague rules ("when the agent isn't sure") produce inconsistent behavior.
- Stratified sampling in eval sets so easy categories don't dominate the score.
- Log the reasoning chain, not just the answer, so every decision is replayable from the log alone.

## Judging Priorities

- **Depth beats breadth** — finish fewer challenges well rather than sketching all of them.
- **Commit history is evidence** — judges read the journey, not just the final state.
- ADRs and architecture diagrams carry significant weight under "best architecture thinking."
- Adversarial eval sets (prompt injection, mis-escalation, false confidence) carry weight under "best testing."
