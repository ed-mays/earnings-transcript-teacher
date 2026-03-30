---
name: diary
description: Maintain a daily engineering diary in the companion earnings-transcript-teacher-diary repo. Supports /diary, /diary reset, and /diary rebuild.
---

# Engineering Diary Skill

Maintain a daily engineering diary for the `earnings-transcript-teacher` project.

**Diary repo path:** `~/src/earnings-transcript-teacher-diary/`
**Entry path pattern:** `~/src/earnings-transcript-teacher-diary/YYYY-MM-DD.md`
**Archive path:** `~/src/earnings-transcript-teacher-diary/archive/`

---

## Sub-commands

Detect the sub-command from the args following `/diary`:
- No args → run **Daily Entry**
- `reset` → run **Reset**
- `rebuild` → run **Rebuild**
- Any other args → run **Daily Entry**, treating the args as a pre-supplied observation (skip the observation prompt)

---

## Sub-command: Daily Entry (default)

Every invocation produces exactly one `## Session: [Topic]` block. The daily file is a sequence of such blocks separated by `---` dividers. There is no structural difference between the first run of the day and subsequent runs.

### Steps

1. **Get today's date** in `YYYY-MM-DD` format.

2. **Parse the existing diary file** (if it exists) at `~/src/earnings-transcript-teacher-diary/YYYY-MM-DD.md`:
   - **Existing PR numbers** — collect every `#NNN` from `[**#NNN**]` markdown links anywhere in the file. Build a set: `existing_prs`.
   - **Existing skill names** — collect every `**name**` entry that appears under any `### Learnings` block. Build a set: `existing_skills`.
   - If the file does not exist, both sets are empty.

3. **Fetch merged PRs for today:**
   ```bash
   gh pr list --state merged --json number,title,createdAt,mergedAt --limit 100
   ```
   Filter to PRs where `mergedAt` date matches today (convert UTC to GMT-5). For each, calculate implementation time:
   - `days = (mergedAt date - createdAt date)` rounded to nearest whole day
   - Same-day merges: `same day (Mon DD → Mon DD)`
   - Multi-day: `N day` / `N days (Mon DD → Mon DD)`

   Partition: `new_prs` = today's merged PRs whose number is **not** in `existing_prs`.

4. **Fetch open PRs (WIP):**
   ```bash
   gh pr list --state open --json number,title,createdAt
   ```
   For each, calculate days open from `createdAt` to today. Also check:
   ```bash
   git branch -r | grep -v HEAD | grep -v main
   ```
   Note remote branches without a corresponding open PR.

5. **Find today's new learnings** from `~/.claude/skills/learned/`:
   ```bash
   grep -rl "Extracted: YYYY-MM-DD" ~/.claude/skills/learned/
   ```
   For each matching file, read the `name` and `description` frontmatter fields. Exclude any whose `name` is already in `existing_skills`. These are skills saved or updated today via `/learn` or `/learn-eval`.

6. **Derive the session topic.**

   **When `new_prs` is non-empty:**
   - Look at the conventional-commit types (`feat`, `fix`, `refactor`, `docs`, `chore`) and title keywords across `new_prs`
   - Generate a short (2–4 word) title-case topic that captures the dominant theme: e.g. `Production Hardening`, `Observability Foundation`, `CI Pipeline`, `Data Retention`, `Security Fixes`
   - If a single PR: derive directly from its title, dropping the type prefix

   **When `new_prs` is empty (tooling/analysis/ideation sessions):**
   - Infer from WIP branches or the nature of work being wrapped up
   - Fall back to `General Session` if nothing is determinable

   **Ask the user:**
   > "Suggested session topic: **[Topic]**. Press Enter to accept, or type a new name:"

   Use the confirmed topic verbatim (capitalise as a title if the user typed one).

7. **Collect observations.**

   If args were passed to `/diary` (and they aren't `reset` or `rebuild`), treat them as a pre-supplied observation — skip the prompt and use the args text directly.

   Otherwise ask:
   > "Any observations for this session? (press Enter to skip)"

   Collect each observation as a `> blockquote` line. If skipped, leave the `### Observations` section with just the HTML comment placeholder.

8. **Draft the session block** using this template:

   ```markdown
   ## Session: [Topic]

   ### Completed
   - [**#NNN**](https://github.com/ed-mays/earnings-transcript-teacher/pull/NNN) title — same day (Mon DD → Mon DD)

   ### Value Delivered
   <!-- Business-facing narrative. 2–4 sentences max. -->

   ### Learnings
   <!-- Patterns and knowledge captured this session. Omit section if none. -->
   - **skill-name** — one-line description of what was learned

   ### In Progress
   - [**#NNN**](https://github.com/ed-mays/earnings-transcript-teacher/pull/NNN) title — N days open

   ### Observations
   <!-- added below -->
   > observation text
   ```

   Apply these rules:

   **`### Completed`** — list only `new_prs`. If none, write `- none`.

   **`### Value Delivered`** — fetch each new PR's body (`gh pr view NNN --json body`) and write ONE narrative paragraph answering:
   - What can users or the business now do that they couldn't before?
   - What risk, limitation, or problem has been removed?
   - How does this advance a strategic goal (production readiness, UX, observability, cost, etc.)?

   Write for a technical product manager — no file names, test counts, LOC, or library names. Synthesise multiple PRs into a single coherent narrative. PR references in prose are hyperlinks: `[#NNN](https://github.com/ed-mays/earnings-transcript-teacher/pull/NNN)`. Omit this section entirely if no new PRs.

   **`### Learnings`** — list each new skill (not already in the file). One bullet: `- **name** — short plain-English description`. Omit the section entirely if there are no new learnings.

   **`### In Progress`** — include this section **only** in the session block being written now (it reflects current state). Before appending, strip any `### In Progress` block from the previous last session in the file — it is now stale. If no open PRs and no WIP branches, write `- none`.

   **`### Observations`** — blockquote lines. If none, leave the HTML comment.

   **No-PR sessions** (tooling, analysis, ideation): replace `### Completed`, `### Value Delivered`, and `### Learnings` with a single italic context line at the top of the block:
   ```markdown
   ## Session: [Topic]

   *No PRs — work was [brief description of what was done].*

   ### Observations
   ```
   Still include `### Learnings` if there are new skills to record, and still include `### In Progress`.

9. **Write the file.**
   - **File does not exist:** Write the full entry:
     ```
     # YYYY-MM-DD

     ## Session: [Topic]
     ...
     ```
   - **File exists:** Append `\n---\n\n` followed by the new session block. Also remove the stale `### In Progress` block from the end of the existing content (the block ending just before the new `---`).

10. **Remind the user** to commit and push the diary repo:
    ```
    cd ~/src/earnings-transcript-teacher-diary && git add YYYY-MM-DD.md && git commit -m "diary: YYYY-MM-DD" && git push
    ```

---

## Sub-command: Reset

Archive all existing diary entries and start fresh.

### Steps

1. **Get today's date** in `YYYY-MM-DD` format.

2. **Create the archive folder:**
   ```bash
   mkdir -p ~/src/earnings-transcript-teacher-diary/archive/YYYY-MM-DD-reset
   ```

3. **Move all `.md` files** (except `README.md`) from the diary root into the archive folder:
   ```bash
   find ~/src/earnings-transcript-teacher-diary -maxdepth 1 -name "*.md" ! -name "README.md" \
     -exec mv {} ~/src/earnings-transcript-teacher-diary/archive/YYYY-MM-DD-reset/ \;
   ```

4. **Confirm** to the user: "Archived N entries to `archive/YYYY-MM-DD-reset/`. Diary is now empty."

5. **Remind the user** to commit and push:
   ```
   cd ~/src/earnings-transcript-teacher-diary && git add . && git commit -m "diary: reset YYYY-MM-DD" && git push
   ```

---

## Sub-command: Rebuild

Generate retrospective entries for all merged PRs, grouped by merge date.

### Steps

1. **Fetch all merged PRs:**
   ```bash
   gh pr list --state merged --json number,title,createdAt,mergedAt,labels --limit 500
   ```

2. **Group PRs by merge date** (`mergedAt` date, `YYYY-MM-DD`, converted to GMT-5).

3. **For each date, generate an entry** using a single session block:

   ```markdown
   # YYYY-MM-DD

   ## Session: [Topic]

   ### Completed
   - [**#NNN**](https://github.com/ed-mays/earnings-transcript-teacher/pull/NNN) title — N days (Mon DD → Mon DD)

   ### Value Delivered
   <!-- narrative -->

   ### Observations
   <!-- -->
   ```

   - **Topic**: derive from the dominant PR type and theme for that date using the same logic as Daily Entry step 6 Case A.
   - **Value Delivered**: fetch each PR's body (`gh pr view NNN --json body,title`) and write a single narrative — what capability was added and why it mattered. No metrics. No implementation detail. PR references as hyperlinks.
   - **Learnings**: omit for historical entries (no skills data available retrospectively).
   - **In Progress**: omit for historical entries.
   - **Observations**: leave the section with just the HTML comment.

4. **Check for existing files** — skip dates that already have a diary file (do not overwrite).

5. **Write all new files** to `~/src/earnings-transcript-teacher-diary/`.

6. **Report a summary:** "Generated N new entries from YYYY-MM-DD to YYYY-MM-DD. Skipped M existing entries."

7. **Remind the user** to review the generated entries before committing, then:
   ```
   cd ~/src/earnings-transcript-teacher-diary && git add . && git commit -m "diary: rebuild from PR history" && git push
   ```
