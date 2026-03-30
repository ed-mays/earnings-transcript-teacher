# Issue #249: Technical Documentation Maturity Audit

*Persona: Senior Technical Writer / Developer Experience Engineer*
*Date: 2026-03-29*

## Summary

The documentation corpus is functionally split between a legacy Python/Streamlit stack and the active FastAPI/Next.js/Supabase/Modal stack, with no deprecation guidance to help a new contributor choose between them. Operational documentation (runbooks, disaster recovery, data retention) is the strongest area — specific, actionable, and largely current. Architecture specifications are comprehensive but frozen in "Draft" status despite the described systems being built, making it impossible to know what has been implemented versus what is still aspirational. Three specific factual errors exist that would block a contributor from successfully running the system: a missing required environment variable, a pipeline reference document pointing to modules that no longer exist, and a web README that is unmodified Next.js boilerplate.

---

## Documentation Inventory

| Document | Apparent Audience | Accuracy | Maturity |
|---|---|---|---|
| `README.md` | New developers | Partial — dual-stack, no deprecation signal | Stale |
| `CLAUDE.md` | Claude Code sessions | Partial — legacy stack conventions only | Stale |
| `web/README.md` | Web frontend contributors | None — unmodified Next.js boilerplate | Stale |
| `web/CLAUDE.md` | Claude Code sessions (web) | Cryptic single line | Incomplete |
| `web/AGENTS.md` | Claude/AI agents | Accurate critical warning, no inbound links | Orphaned |
| `analysis_pipeline.md` | Developers / maintainers | Incorrect — references non-existent modules | Stale |
| `docs/database.md` | Developers | Accurate | Current |
| `docs/llm_usage.md` | Developers | Accurate | Current |
| `docs/data-retention-policy.md` | Operators / compliance | Accurate | Current |
| `docs/disaster-recovery.md` | On-call engineers | Mostly accurate; Firebase/Supabase mix | Current |
| `docs/future-roadmap.md` | Product stakeholders | No completion status | Stale |
| `docs/mvp-features.md` | Product stakeholders | No completion status | Stale |
| `docs/runbooks/migration-rollback.md` | Operators | Accurate | Current |
| `docs/runbooks/rls-verification.md` | Operators | Accurate | Current |
| `docs/architecture-review/00-index.md` | Architects / contributors | Accurate | Current |
| `docs/architecture-review/01-current-system-audit.md` | Architects | Accurate at time of writing | Draft |
| `docs/architecture-review/02-target-architecture.md` | Architects | Target defined; open questions unanswered | Draft |
| `docs/architecture-review/specs/[001]–[005]` | Implementation teams | Well-designed; implementation status unknown | Draft |
| `docs/ux-improvement-suggestions.md` | Product / UX | Duplicated elsewhere | Stale |
| `docs/ux-improvements-brainstorm.md` | Product / UX | Duplicated elsewhere | Stale |
| `docs/feature-ideation/ux-improvement-opportunities.md` | Product / UX | Overlaps above two files | Stale |
| `docs/feature-ideation/spike-49-flashcard-review-mode.md` | Developers | Accurate design; no implementation status | Orphaned |
| `docs/learning-path-redesign.md` | Developers | Accurate design; no implementation status | Orphaned |
| `ideation/feature-parity-audit.md` | Product / developers | Accurate; not linked to GitHub issues | Current |
| `ideation/feature-parity-items.md` | Developers | Accurate; no completion status | Current |
| `prompts/feynman-learning-strategy.md` | Unclear | Generic Feynman template; purpose unstated | Orphaned |
| `prompts/feynman/*.md` (9 files) | Developers | Accurate content; loading mechanism undocumented | Orphaned |

---

## Findings

---

**[HIGH] README.md presents two incompatible stacks without a deprecation signal**

File(s): `README.md`

Finding: The README documents both the legacy stack (Python `main.py` CLI + Streamlit `app.py`) and the new stack (FastAPI `api/` + Next.js `web/`) as active setups, in separate sections with no guidance on which applies to new contributors. The "Local development (new stack)" section begins at line 248 but is visually equivalent to the legacy setup instructions above it. Neither section is marked deprecated, recommended, or primary.

Impact: A new contributor following the README has a roughly 50% chance of setting up the wrong stack. The legacy setup will run successfully but targets a pipeline the project is migrating away from; wasted time and a confusing first experience are the predictable outcomes.

---

**[HIGH] `MODAL_TOKEN_ID` is a required environment variable with no documentation**

File(s): `api/settings.py`, `README.md`, `CLAUDE.md`

Finding: `api/settings.py` defines a `REQUIRED_ENV_VARS` list that includes `MODAL_TOKEN_ID`. The FastAPI app validates this list at startup and returns HTTP 503 for all requests if any variable is absent. `MODAL_TOKEN_ID` does not appear in the README environment variable table, `CLAUDE.md`, or any other setup guide. `api/.env.example` includes it, but `api/.env.example` is not referenced from any documentation.

Impact: A developer who follows the README setup instructions exactly will have a non-functional API with no clear diagnostic. The 503 response and startup log are the only clues, both requiring the developer to know to look at `api/settings.py`.

---

**[HIGH] `analysis_pipeline.md` describes modules that do not exist**

File(s): `analysis_pipeline.md`, `nlp/`

Finding: The pipeline reference document describes seven analysis steps and maps them to source modules: `analysis.py`, `sections.py`, `keywords.py`, `themes.py`, and `takeaways.py`. Of these, `keywords.py`, `themes.py`, and `takeaways.py` do not exist in `nlp/`. The keyword extraction, theme clustering, and takeaway generation described in the document are now handled by the ingestion-tier LLM pipeline defined in `ingestion/prompts.py` — which has no documentation at all.

Impact: A developer reading `analysis_pipeline.md` to understand how enrichment works will follow references to non-existent files. The actual ingestion prompt system (`ingestion/prompts.py`) remains entirely undiscovered. This is the most factually incorrect document in the corpus.

---

**[HIGH] `web/README.md` is unmodified Next.js boilerplate**

File(s): `web/README.md`, `web/AGENTS.md`

Finding: `web/README.md` contains only the default text generated by `create-next-app` ("This is a Next.js project bootstrapped with `create-next-app`"). It contains no project-specific content: no environment variables, no local dev steps, no explanation of how the frontend connects to the FastAPI backend, and no authentication setup. Additionally, `web/AGENTS.md` contains a critical warning about breaking changes in the project's Next.js version that is not referenced from `web/README.md`, `README.md`, or `CLAUDE.md`.

Impact: Web contributors have no onboarding path. `web/AGENTS.md`'s warning is effectively invisible to any contributor who doesn't discover it by browsing the directory.

---

**[MEDIUM] Architecture specifications are labeled "Draft" despite the systems being built**

File(s): `docs/architecture-review/specs/[001]–[005].spec.md`

Finding: All five architecture specs are stamped "Draft" (or "Planned" for spec [005]). The FastAPI backend, Next.js frontend, and Supabase data layer described in these specs are demonstrably implemented — the code exists. Specs have no "Implemented in PR #X" notes, no "Updated: date" field, and no implementation status tracker. Spec [002] describes connection pooling patterns that were implemented in PR #214; spec [005] describes a React frontend that is substantially built.

Impact: A reader cannot distinguish between the aspirational and the actual. An engineer scoping new work may unknowingly duplicate effort that has already been done, or assume a pattern is established when it was never implemented.

---

**[MEDIUM] Three overlapping UX improvement documents with no cross-references or issue links**

File(s): `docs/ux-improvement-suggestions.md`, `docs/ux-improvements-brainstorm.md`, `docs/feature-ideation/ux-improvement-opportunities.md`

Finding: These three files cover substantially the same ground — UX improvements for the learning experience. `ux-improvements-brainstorm.md` is a raw list of ~40 ideas with no prioritization. `ux-improvement-suggestions.md` and `ux-improvement-opportunities.md` both contain prioritized recommendations with ~70% overlapping content. None of the three files reference each other or link to GitHub issues.

Impact: Any engineer or PM looking for "what UX improvements are planned" will find three partial answers. It is unclear which file is canonical, whether the priorities differ intentionally, and whether any of the recommendations have been acted on.

---

**[MEDIUM] `docs/` directory is not surfaced in `README.md`**

File(s): `README.md`, `docs/`

Finding: `README.md` contains no mention of the `docs/` directory. The directory holds architecture review specs, runbooks, a disaster recovery guide, a data retention policy, and feature ideation spikes — substantial operational and architectural reference material. There is no table of contents, no index link, and no pointer from the README to this content.

Impact: New contributors and operators discover the `docs/` directory only by browsing the repository. The runbooks — which are specifically valuable under pressure — are effectively hidden from anyone who has not already found them.

---

**[MEDIUM] `CLAUDE.md` contains no conventions for the new stack**

File(s): `CLAUDE.md`

Finding: `CLAUDE.md` documents architecture rules, testing conventions, and code style exclusively in terms of the legacy Python pipeline. It references `main.py`, `app.py` (Streamlit), `cli/`, and `db/repositories.py`, but contains nothing about FastAPI route handler conventions, API response schema patterns, TypeScript / Next.js component structure, or Modal pipeline conventions.

Impact: AI-assisted development sessions targeting the new stack get legacy-stack guidance. Specifically: Claude Code receives no instruction to follow the repository pattern in FastAPI routes, maintain the error contract defined in the spec, or respect TypeScript strictness in the web layer.

---

**[MEDIUM] `prompts/feynman/` has no README and its loading mechanism is undocumented**

File(s): `prompts/feynman/`, `ui/feynman.py`, `ingestion/prompts.py`

Finding: Nine modular prompt files exist in `prompts/feynman/` but the directory has no README. The files are loaded at runtime by `ui/feynman.py` via a `_load_prompt_file()` function that maps stage names to file paths using a `_FEYNMAN_PROMPT_FILES` dict — this is not documented anywhere. Additionally, the ingestion-tier LLM prompts (`TIER_1`, `TIER_2`, `TIER_3_SYNTHESIS`, and NLP synthesis prompts) live in `ingestion/prompts.py` as Python string constants, creating a second prompt system that is architecturally separate from `prompts/feynman/` but entirely undocumented.

Impact: A developer modifying the Feynman chat experience cannot understand the prompt loading mechanism without reading `ui/feynman.py`. The existence of a second prompt system in `ingestion/prompts.py` is invisible. Any future prompt versioning or A/B testing work will start from a blank slate.

---

**[LOW] `disaster-recovery.md` mixes "Firebase" and "Supabase" terminology**

File(s): `docs/disaster-recovery.md`

Finding: The disaster recovery guide uses "Firebase projects" in several places where "Supabase projects" is correct. The project settled on Supabase (not Firebase) as its managed Postgres and auth provider. The Firebase references appear to be vestigial from an earlier version of the document.

Impact: Low operational risk (the procedural steps are correct), but introduces confusion during a high-stress incident where precise terminology matters.

---

**[LOW] `main.py --mode` flag is undocumented**

File(s): `README.md`, `main.py`

Finding: `main.py` supports a `--mode cli|gui` flag that launches either the console or Streamlit UI. The README shows only positional argument examples (`python3 main.py AAPL --save`) and the interactive menu invocation. The `--mode gui` shorthand for launching Streamlit from the CLI is not shown.

Impact: Minor — the legacy stack is being deprecated anyway. But the omission is a concrete example of the class of drift between implementation and documentation.

---

**[LOW] Feature spike files have no implementation status markers**

File(s): `docs/feature-ideation/spike-49-flashcard-review-mode.md`, `docs/learning-path-redesign.md`

Finding: Both spike documents contain detailed design work (Stage 1 / Stage 2 breakdowns, implementation notes, open questions) with no indication of whether the design has been implemented, is in progress, or is still pending. Neither file links to implementing PRs or GitHub issues.

Impact: A developer picking up this work cannot tell whether they are starting from scratch, building on a partial implementation, or reviewing a completed feature's historical design rationale.

---

## Structural Gaps

The following documentation types are absent but expected at this stage of the project:

**New Developer Onboarding Guide**
A single end-to-end walkthrough: clone the repo, configure environment variables for both legacy and new stack, run the FastAPI backend and Next.js frontend together, run the test suite, and make a minimal change. Currently, this path is reconstructed from four sources (README legacy section, README new stack section, `web/README.md` boilerplate, architecture specs) none of which are complete. Should live at `docs/getting-started.md` or as a top-level README restructure.

**API Reference**
FastAPI automatically generates an OpenAPI spec at `/docs` and `/redoc`, but neither endpoint is mentioned in any documentation. No static API reference exists. Should be linked from the README and/or exported as `docs/api-reference.md` for offline access.

**Database Schema Reference / Data Dictionary**
The `docs/database.md` file explains the migration system but does not document what the schema contains: table names, column descriptions, foreign key relationships, or the purpose of each table. With 13 migrations and 8 repository classes, the schema is non-trivial. Should live at `docs/database-schema.md`.

**Architecture Decision Records (ADR) Index**
Significant decisions were made during the rewrite (Supabase over Firebase, pgvector over Pinecone, Modal for ingestion, Voyage AI for embeddings). These decisions are buried in architecture spec prose and not queryable. An ADR index at `docs/decisions/` would make the reasoning discoverable and auditable.

**Changelog / Release Notes**
No document tracks what changed between deployments: new environment variables, schema migrations applied, API contract changes, or deprecated features. As the project transitions from legacy to new stack, a changelog would reduce the risk of operators running a mismatched combination of components.

---

## Recommended Next Steps

1. **Fix the three factual errors** (HIGH findings 2, 3, 4): Add `MODAL_TOKEN_ID` to the README env table, update or replace `analysis_pipeline.md` to describe the actual ingestion prompt system, and replace `web/README.md` with project-specific content. These are the only findings that would prevent a competent developer from successfully running the system.

2. **Add a "docs/" pointer to README.md** (MEDIUM finding 7): A single paragraph and a table of contents entry is enough to surface the existing runbooks and architecture documentation. This costs one paragraph and unlocks all the operational content that already exists.

3. **Mark specs with implementation status** (MEDIUM finding 5): Each spec should gain a one-line status note ("Implemented via PR #214, #213") and a "Last updated" date. No rewriting required — a brief annotation per spec is sufficient.

4. **Consolidate UX improvement files** (MEDIUM finding 6): Merge the three overlapping files into one canonical document with a priority-ordered table and a "Status" column linked to GitHub issues. Delete the redundant files.

5. **Add a README to `prompts/feynman/`** (MEDIUM finding 9): Document what each file does, which stage it maps to, how `ui/feynman.py` loads it, and note the separate existence of `ingestion/prompts.py`.

6. **Update `CLAUDE.md` with new-stack conventions** (MEDIUM finding 8): Add a section covering FastAPI route patterns, API response envelope, error handling contract, and a pointer to `web/AGENTS.md` for Next.js-specific guidance.

7. **Write a New Developer Onboarding guide** (structural gap): This is the highest-leverage missing document. It turns a multi-hour discovery process into a 20-minute setup.
