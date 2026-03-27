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

---

## Sub-command: Daily Entry (default)

Create or update today's diary entry.

### Steps

1. **Get today's date** in `YYYY-MM-DD` format.

2. **Fetch merged PRs for today:**
   ```bash
   gh pr list --state merged --json number,title,createdAt,mergedAt --limit 100
   ```
   Filter to PRs where `mergedAt` date matches today. For each, calculate implementation time:
   - `days = (mergedAt date - createdAt date)` rounded to nearest whole day
   - Format: `N day` (singular) or `N days` (plural)
   - Format dates as `Mon DD` (e.g. `Mar 22`)

3. **Fetch open PRs (WIP):**
   ```bash
   gh pr list --state open --json number,title,createdAt
   ```
   For each open PR, calculate days open so far from `createdAt` to today.

4. **Check for existing branches without PRs:**
   ```bash
   git branch -r | grep -v HEAD | grep -v main
   ```
   Note any remote branches that don't correspond to an open PR (they may be WIP not yet raised as PR).

5. **Draft the entry** using this template:

   ```markdown
   # YYYY-MM-DD

   ## Completed
   - **#NNN** title — N days (Mon DD → Mon DD)

   ## In Progress
   - **#NNN** title — N days open

   ## Observations
   <!-- added below -->
   ```

   If no PRs were merged today, write `- none` under Completed.
   If no open PRs, write `- none` under In Progress.

6. **Ask the user for observations:**
   > "Any observations to record for today? (press Enter to skip)"

   Append each observation as a `> blockquote` line under the Observations section. If skipped, leave the section with just the HTML comment.

7. **Check if the diary entry file already exists:**
   - If it does not exist: write the full entry.
   - If it does exist: show the user the existing content and ask whether to overwrite or append the new sections below a `---` divider.

8. **Write the file** to `~/src/earnings-transcript-teacher-diary/YYYY-MM-DD.md`.

9. **Remind the user** to commit and push the diary repo:
   ```
   cd ~/src/earnings-transcript-teacher-diary && git add . && git commit -m "diary: YYYY-MM-DD" && git push
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

Generate retrospective bullet-summary entries for all merged PRs, grouped by merge date.

### Steps

1. **Fetch all merged PRs:**
   ```bash
   gh pr list --state merged --json number,title,createdAt,mergedAt,labels --limit 500
   ```

2. **Group PRs by merge date** (`mergedAt` date, `YYYY-MM-DD`).

3. **For each date, generate an entry** using the Daily Entry template:
   - Completed: PRs merged on that date with implementation time
   - In Progress: PRs that were open (created before, not yet merged) on that date — omit this section for historical entries to keep it simple
   - Observations: leave the section present but empty (HTML comment only)

4. **Check for existing files** — skip dates that already have a diary file (do not overwrite).

5. **Write all new files** to `~/src/earnings-transcript-teacher-diary/`.

6. **Report a summary:** "Generated N new entries from YYYY-MM-DD to YYYY-MM-DD. Skipped M existing entries."

7. **Remind the user** to review the generated entries before committing, then:
   ```
   cd ~/src/earnings-transcript-teacher-diary && git add . && git commit -m "diary: rebuild from PR history" && git push
   ```
