#!/usr/bin/env bash
# PostToolUse hook — flag `rounded-full` usages in .tsx/.jsx writes.
#
# Why: the project convention (see ~/.claude/skills/learned/tailwind-rounded-full-multiline-badge.md)
# reserves `rounded-full` for guaranteed-short, fixed-size elements (icon buttons,
# avatar rings, switch primitives). Multi-line-capable text badges should use
# `rounded-md` so wrapped content keeps consistent corners.
#
# This hook is NON-BLOCKING: it emits a reminder to stderr and exits 0. The
# model sees the reminder in the tool-result context and can decide whether to
# fix or (if legitimate) move on. Heuristic is intentionally permissive — a
# false positive is cheap; a silent miss is what we're preventing.
#
# Exit codes:
#   0 — always. Never block the tool call.

set -uo pipefail

# Read hook event JSON from stdin.
payload="$(cat)"

# Extract file_path; bail if not a file-writing tool or path missing.
file_path="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
[[ -z "$file_path" ]] && exit 0

# Only .tsx / .jsx.
case "$file_path" in
  *.tsx|*.jsx) ;;
  *) exit 0 ;;
esac

# Whole-file exceptions — shadcn primitives the app doesn't own.
case "$file_path" in
  */components/ui/switch.tsx) exit 0 ;;
esac

# File may not exist yet (unlikely in PostToolUse, but be safe).
[[ -f "$file_path" ]] || exit 0

# Grep for rounded-full with line numbers.
matches="$(grep -n 'rounded-full' "$file_path" || true)"
[[ -z "$matches" ]] && exit 0

# Line-level exception filter. Drop lines that look like legitimate fixed-size
# circles, icon buttons, or the typing-indicator pattern. Over-inclusive is
# fine — the hook is a reminder, not a gate.
#
# Patterns excluded:
#   - min-h-[44px] or min-w-[44px]           → 44×44 touch target icon buttons
#   - size-N                                 → Tailwind size shorthand (fixed)
#   - h-N followed later by w-N (or vice)    → explicit fixed circle
#   - animate-pulse + bg-muted               → typing-indicator pattern
#   - absolute positioning                   → positioned icon/decorative button,
#                                              almost never dynamic text pill
flagged="$(printf '%s\n' "$matches" | grep -Ev 'min-h-\[44px\]|min-w-\[44px\]|size-[0-9]' \
  | grep -Ev 'h-[0-9]+(\.[0-9]+)?[^a-zA-Z].*w-[0-9]+(\.[0-9]+)?[^a-zA-Z]|w-[0-9]+(\.[0-9]+)?[^a-zA-Z].*h-[0-9]+(\.[0-9]+)?[^a-zA-Z]' \
  | grep -Ev 'animate-pulse.*bg-muted|bg-muted.*animate-pulse' \
  | grep -Ev '\babsolute\b' \
  || true)"

[[ -z "$flagged" ]] && exit 0

# Emit reminder to stderr — the model will see it in the tool result context.
{
  printf 'REMINDER: %s contains rounded-full on line(s) that may be multi-line-capable text pills.\n' "$file_path"
  printf '\n'
  printf '%s\n' "$flagged"
  printf '\n'
  printf 'The project convention (see ~/.claude/skills/learned/tailwind-rounded-full-multiline-badge.md) reserves rounded-full for guaranteed-short, fixed-size elements. Dynamic-length or wrap-capable text pills should use rounded-md instead.\n'
  printf '\n'
  printf 'Exceptions (ignore if any apply): icon buttons with min-h-[44px]/min-w-[44px], fixed h-N w-N or size-N circles, shadcn Switch track/thumb, avatar rings, numeric counters. If this file falls under an exception the heuristic did not catch, leave rounded-full and ignore this reminder.\n'
} >&2

exit 0
