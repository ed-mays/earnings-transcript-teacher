# Vertical Slice Delivery Model

**Status:** Accepted
**Date:** 2026-03-26

## Context

The rewrite (ADR 0001) required building multiple layers simultaneously: database schema, repository classes, API routes, and frontend components. The project needed a delivery strategy that balanced incremental progress with integration risk. The compressed timeline (~11 days for the core rewrite) made it critical that each merged PR produced a demonstrably working feature.

## Decision

Each issue and PR delivers a complete vertical slice — data layer + API endpoint + UI component — rather than horizontal layers. Infrastructure (database migrations, auth setup, deployment configuration) is built as part of the first vertical slice that needs it, not as standalone foundation work.

Examples:
- "Add earnings call list" = migration + CallRepository + `/api/calls` route + CallList page component
- "Add semantic search" = embedding repository + `/api/search` route + SearchPage with results display

Issue titles describe the work outcome, not delivery units. Sequencing is expressed via dependency fields (Depends on / Blocks), not issue numbering.

## Alternatives considered

1. **Layer-by-layer delivery (horizontal slices)** — Build all repositories first, then all API routes, then all UI components. Rejected because: (a) layer-by-layer delivery means no user-visible progress until all layers are complete, preventing feedback until late in the cycle, (b) mismatches between layers (e.g., a repository method returning data the route doesn't need) aren't discovered until integration, and (c) motivation suffers when weeks of work produce no visible features.

2. **Feature flags with trunk-based development** — Merge incomplete features behind flags, enable them when the full stack is ready. Rejected because: (a) the project is pre-launch with no production users, so feature flags add complexity without protecting anyone, (b) flag cleanup is an ongoing maintenance burden, and (c) the team is a single developer, eliminating the coordination benefit that feature flags provide for multi-developer teams.

3. **Sprint-based batched delivery** — Group related slices into time-boxed sprints with batch integration at the end. Rejected because: (a) with a single developer, sprint ceremonies and planning overhead don't provide value, (b) the compressed timeline doesn't accommodate multi-week sprints, and (c) continuous integration of vertical slices provides the same quality assurance with less process.

4. **Prototype first, then rebuild** — Build a rough end-to-end prototype, then rewrite each layer properly. Rejected because: (a) the original Streamlit app *was* the prototype, and the goal is to avoid throwaway code, (b) "rebuild properly" tends to scope-creep, and (c) vertical slices with tests achieve production quality from the first PR.

## Consequences

**Easier:**
- Every merged PR produces a user-visible feature that can be demoed and tested
- Integration issues are caught immediately (the slice doesn't work if layers don't fit)
- Progress is visible and measurable (features shipped, not layers completed)
- Feedback loops are short — a broken UX is discovered in the same PR, not weeks later

**Harder:**
- Each slice touches multiple layers, making PRs larger and harder to review
- Some infrastructure must be built "just enough" for the first slice, then extended later (e.g., connection pooling was minimal for the first endpoint, then hardened later)
- Test coverage per slice must span all layers, increasing the test burden per PR
- Rework is possible if early slices make assumptions that later slices invalidate
