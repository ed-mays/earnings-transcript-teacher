# UI/UX Visual Consistency Audit

**Issue:** #363
**Date:** 2026-04-04
**Scope:** All pages and components (7 pages, 23 components, admin included)
**Method:** Full code read + targeted grep for anti-patterns

---

## Summary

The app has a well-constructed design system — OKLCH tokens, a shadcn base-nova Card with `ring-1 ring-foreground/10`, and a Geist font stack — but adherence is uneven across the three surface areas built at different times. The most severe issue is the admin loading skeleton, which renders as a blank white grid in dark mode. The second most impactful problem is that card surfaces use at least six different border/shadow treatments, none of which match the canonical shadcn Card ring. The highest-leverage fix categories are: (1) replace hardcoded colors in loading skeletons, (2) adopt shadcn `Card` universally, and (3) consolidate the ~10 raw `<button>` instances that bypass the `Button` component.

---

## Findings

---

**[P1] Admin loading skeleton is broken in dark mode**

- Dimension: 2 (Design Token Usage), 10 (Dark Mode Parity)
- Pages/Components: `web/app/admin/loading.tsx`
- Symptom: In dark mode the loading skeleton renders as a white grid on a white background — the skeleton cards (`bg-white`, `border-zinc-200`) are invisible and the title shimmer (`bg-zinc-200`) blends into the page background.
- Root cause: Every color class in the file is a hardcoded Tailwind palette class (`bg-zinc-200`, `bg-zinc-100`, `bg-white`, `border-zinc-200`) instead of semantic tokens. Compare with `web/app/admin/health/loading.tsx` (written later) which correctly uses `bg-muted`, `border-border`, `bg-card`.
- Recommendation: Replace all `bg-zinc-*`, `bg-white`, `border-zinc-200` with `bg-muted`, `bg-card`, `border-border` to match the health skeleton.
- Effort: LOW
- Dark-mode impact: YES

---

**[P1] Hardcoded violet badge bypasses token system**

- Dimension: 2 (Design Token Usage), 10 (Dark Mode Parity)
- Pages/Components: `web/components/transcript/CallBriefPanel.tsx:116`
- Symptom: "Strategic shift flagged" badge uses hardcoded `bg-violet-50 text-violet-700` in light mode and `dark:bg-violet-900/30 dark:text-violet-400` in dark mode. The dark mode overrides exist but are hand-written palette values, not connected to the OKLCH token system. If the theme palette changes, this badge will diverge.
- Root cause: The badge was added without a corresponding semantic token. The design system has no "info-violet" or "shift" token — so this was wired directly to Tailwind palette classes.
- Recommendation: Map this to an existing semantic token (closest is `bg-info/10 text-info-foreground`) or add a `--shift` token to `globals.css`. Either way, remove the hardcoded palette classes.
- Effort: LOW
- Dark-mode impact: YES (partial — dark overrides exist but bypass the token system)

---

**[P2] Card surface treatment: six competing patterns**

- Dimension: 3 (Card Surface Treatment)
- Pages/Components: `admin/page.tsx`, `admin/health/page.tsx`, `admin/health/loading.tsx`, `admin/ingest/page.tsx`, `auth/sign-in/page.tsx`, `components/transcript/EvasionCard.tsx`, `components/transcript/NewsCard.tsx`, `components/transcript/TranscriptBrowser.tsx`, `components/CallList.tsx`
- Symptom: Card-like surfaces look visually different across the app. Some are slightly elevated (ring), some are bordered, some are shadow-only, some are none of the above. The result is a fragmented visual hierarchy where the user cannot intuit what is "a card."
- Root cause: The canonical shadcn Card uses `rounded-xl bg-card ring-1 ring-foreground/10` (no explicit border). But all hand-rolled card surfaces use `rounded-lg border border-border bg-card` — a different radius, a different border mechanism, and no ring. The six patterns observed:
  1. **Canonical Card (ring):** `ThemeCard`, `StrategicShiftCard`, `MetadataPanel`, `CallBriefPanel`, `TranscriptPage` (Feynman link card) — uses shadcn `<Card>`
  2. **Border, no ring:** `AnalyticsCard` in admin, `StatusCard` in admin health, `admin/ingest` form wrapper, `admin/health/loading.tsx` skeleton — `rounded-lg border border-border bg-card`
  3. **Border + shadow:** sign-in page — `rounded-xl border border-border bg-card shadow-sm`
  4. **Border only (no bg-card):** `EvasionCard` — `rounded-lg border overflow-hidden bg-card` (no `border-border`)
  5. **Border (no border-border):** `NewsCard` — `rounded-lg border bg-card`
  6. **Dashed border:** `CallList` empty state, `TranscriptBrowser` empty transcript state
- Recommendation: Migrate `AnalyticsCard`, `StatusCard`, the admin ingest wrapper, `NewsCard`, and `EvasionCard` to use the shadcn `<Card>` component. This unifies the visual treatment to `ring-1 ring-foreground/10` with `rounded-xl`. Dashed-border empty states are intentionally distinct and should remain.
- Effort: MEDIUM
- Dark-mode impact: YES (ring vs border renders differently in dark mode)

---

**[P2] Admin ingest page bypasses component library throughout**

- Dimension: 1 (Component Library Adherence), 4 (Navigation/Wayfinding), 5 (Form Patterns)
- Pages/Components: `web/app/admin/ingest/page.tsx`
- Symptom: The ingest form looks visually inconsistent with the rest of the app: the input field has a different focus ring, the button has a different hover treatment, and the card container doesn't match other admin cards.
- Root cause: The page uses raw HTML `<button>` (line 94), raw `<input>` (line 83), and a hand-rolled `<div>` card wrapper (line 74). The focus style on the raw `<input>` (`focus:ring-1 focus:ring-ring`) differs from the shadcn `Input` component's focus treatment. The submit `<button>` uses `disabled:bg-muted` which doesn't visually match the shadcn `Button`'s `disabled:opacity-50`.
- Recommendation: Replace raw `<input>` with shadcn `Input`, raw `<button>` with shadcn `Button`, and the wrapper `<div>` with shadcn `Card`.
- Effort: LOW
- Dark-mode impact: NO (tokens are used; just wrong components)

---

**[P2] Raw `<a>` tags throughout — bypasses Next.js client navigation**

- Dimension: 4 (Navigation/Wayfinding)
- Pages/Components: `web/app/layout.tsx:66,76-93,117-131`, `web/app/admin/page.tsx:176,179`, `web/app/admin/health/page.tsx:82`, `web/app/admin/ingest/page.tsx:61,64`
- Symptom: Admin nav links trigger full-page reloads instead of client-side navigation. The brand link in the nav bar also causes a full reload. This introduces a visible flash on navigation between admin pages.
- Root cause: All navigation links in the root layout and all three admin pages use `<a href>` instead of Next.js `<Link>`. The main app pages (`/calls/[ticker]`, `/calls/[ticker]/learn`) correctly use `<Link>`.
- Recommendation: Replace every `<a href="...">` in `layout.tsx` and all admin pages with `import Link from "next/link"` and `<Link href="...">`. The root layout brand link (`<a href="/">`) should also become `<Link href="/">`.
- Effort: LOW
- Dark-mode impact: NO

---

**[P2] Admin pages have no breadcrumb or consistent nav component**

- Dimension: 4 (Navigation/Wayfinding)
- Pages/Components: `web/app/admin/page.tsx`, `web/app/admin/health/page.tsx`, `web/app/admin/ingest/page.tsx`, `web/components/BreadcrumbBar.tsx`
- Symptom: Admin pages show an inline link strip (`<div className="mb-6 flex gap-4 text-sm">`) for inter-admin navigation rather than the breadcrumb pattern used in the main app. Each page implements the strip differently: `/admin` links to Health and Ingest; `/admin/health` only links to Ingest; `/admin/ingest` links to both. No admin page shows breadcrumb context.
- Root cause: `BreadcrumbBar` only handles `/calls/[ticker]/learn` and `/calls/[ticker]` paths and returns `null` for everything else. Admin nav was implemented inline as a quick solution, with no extension of `BreadcrumbBar`.
- Recommendation: Extend `BreadcrumbBar` to handle `/admin`, `/admin/health`, and `/admin/ingest` patterns — or create a dedicated `AdminNav` component that wraps the shadcn `Breadcrumb` for admin routes. Remove the inline link strips from each admin page.
- Effort: MEDIUM
- Dark-mode impact: NO

---

**[P2] Raw `<button>` elements across signal cards and chat UI**

- Dimension: 1 (Component Library Adherence), 9 (Interactive State Consistency)
- Pages/Components: `ThemeCard.tsx:87`, `EvasionCard.tsx:117`, `StrategicShiftCard.tsx:125`, `NewsCard.tsx:94`, `ChatThread.tsx:98`, `ChatThread.tsx:66-78`, `KeywordList.tsx:53`, `CallBriefPanel.tsx:131`
- Symptom: Interactive buttons across signal cards and chat have inconsistent hover, focus, and disabled states because each one manually reimplements hover and disabled styling. None of the raw `<button>` elements have a visible focus ring — this is an accessibility regression.
- Root cause: All eight raw button instances bypass the shadcn `Button` component (which has built-in `focus-visible:ring-3 focus-visible:ring-ring/50`). Each applies its own ad hoc classes:
  - Signal cards: `hover:bg-warning/20 transition-colors disabled:opacity-50` (OK) — but no focus-visible ring
  - "Scroll to new messages" float: `hover:bg-primary/90 transition-colors` — no focus ring
  - Suggestion chips: `hover:bg-accent hover:text-accent-foreground active:scale-[0.98] transition-all` — closest to `Button variant="ghost"`
  - "Define with AI" in KeywordList: just `underline` link — could be `Button variant="link"`
  - "Expand all / Collapse all" in CallBriefPanel: `hover:text-foreground hover:underline` — should be `Button variant="ghost" size="xs"` or `variant="link"`
- Recommendation: Replace all raw `<button>` elements with the shadcn `Button` component using appropriate variants:
  - Signal cards "What this signals": `Button variant="outline" size="sm"` (or a custom `warning` variant if one is added)
  - Suggestion chips: `Button variant="outline"`
  - "Define with AI": `Button variant="link" size="xs"`
  - "Expand all / Collapse all": `Button variant="ghost" size="xs"`
  - "Scroll to new messages": `Button size="sm"` (already uses primary colors)
- Effort: MEDIUM
- Dark-mode impact: NO (tokens used; gap is focus rings and interactive state consistency)

---

**[P2] Sentiment and evasion badges hand-rolled throughout instead of using `Badge`**

- Dimension: 1 (Component Library Adherence)
- Pages/Components: `CallCard.tsx:51-68`, `CallBriefPanel.tsx:24-45`, `EvasionCard.tsx:78-81`, `MetadataPanel.tsx:428-431`, `CompetitorList.tsx:16`
- Symptom: The same visual concept (a small label chip) is implemented six different ways: inline IIFE spans in `CallCard`, named helper components (`SignalBadge`, `EvasionBadge`) in `CallBriefPanel`, inline spans in `EvasionCard` and `MetadataPanel`, and a manually constructed chip in `CompetitorList`. The `Badge` component is already imported and used for the industry tag in `CallCard` (line 44) — creating an inconsistency on the same component.
- Root cause: `signal-colors.ts` returns raw Tailwind class strings (`bg` and `text`), which cannot be passed directly to the shadcn `Badge` component. The path of least resistance was to construct `<span>` elements. The `Badge` component uses `cva` variants, so custom domain-specific styling requires either variant extension or `className` override.
- Recommendation: Extend the `Badge` component with a `className` override approach. `signal-colors.ts` returns bg+text classes that can be passed as `className` to `<Badge>`. Consolidate all inline sentiment/evasion/ticker chip patterns to use `<Badge>`.
- Effort: MEDIUM
- Dark-mode impact: NO (tokens used; this is component library adherence)

---

**[P2] Page heading typography is inconsistent**

- Dimension: 7 (Typography Scale and Hierarchy)
- Pages/Components: All `page.tsx` files
- Symptom: Page `<h1>` elements use three different font-weight and tracking combinations, making pages feel authored by different people.
- Root cause: No shared page heading component or convention. Observed variations:
  - Home, Admin Analytics, Admin Health, Admin Ingest: `text-3xl font-semibold text-foreground` (no tracking)
  - Learn page: `text-2xl font-bold tracking-tight text-foreground` (smaller, bolder, tight)
  - Transcript page: `text-3xl font-bold tracking-tight text-foreground uppercase` (uppercase, bolder)
- Recommendation: Establish a single page heading style — `text-3xl font-semibold text-foreground` is the most common and appropriate for non-specialized pages. The transcript page uppercase ticker treatment is intentional and should remain. The learn page heading (`text-2xl`) should be bumped to `text-3xl` to match; `font-bold` vs `font-semibold` should be aligned.
- Effort: LOW
- Dark-mode impact: NO

---

**[P2] Sign-in button is a raw `<button>` with a hand-rolled card container**

- Dimension: 1 (Component Library Adherence), 5 (Form Patterns)
- Pages/Components: `web/app/auth/sign-in/page.tsx:23,37-60`
- Symptom: The sign-in page uses a hand-rolled `<div className="...rounded-xl border border-border bg-card p-8 shadow-sm">` card and a raw `<button>` for the Google sign-in action. The focus ring (`focus:ring-2 focus:ring-ring focus:ring-offset-2`) works, but it's reimplemented from scratch rather than inheriting from the shadcn `Button` component.
- Root cause: Early implementation without design system. The card uses `shadow-sm` which doesn't match the canonical `ring-1 ring-foreground/10`.
- Recommendation: Wrap the sign-in card in shadcn `<Card>` and replace the raw `<button>` with `<Button variant="outline">`. The `<Button>` already handles focus rings and disabled states.
- Effort: LOW
- Dark-mode impact: NO (tokens used; visual treatment difference is ring vs border+shadow)

---

**[P3] Missing `loading.tsx` for home, learn, and ingest routes**

- Dimension: 6 (Loading and Error State Coverage)
- Pages/Components: `web/app/`, `web/app/calls/[ticker]/learn/`, `web/app/admin/ingest/`
- Symptom: Three routes have no Next.js `loading.tsx`. For `/` (home), `CallList` handles its own loading state with an inline skeleton, so there's no visible gap — but the pattern is inconsistent with the route-level skeleton used for `/calls/[ticker]`. For `/calls/[ticker]/learn`, the page renders instantly (client component), so no skeleton is needed. For `/admin/ingest`, the page is also a client component with no initial data fetch, so no skeleton is needed.
- Root cause: `CallList` was built as a client component managing its own loading state rather than being a server component behind a `loading.tsx`. This means there's no route-level skeleton for `/` even though the page blocks on data.
- Recommendation: Add a `web/app/loading.tsx` (the home route skeleton) — a grid of `CallCardSkeleton`-style placeholders. For `/calls/[ticker]/learn` and `/admin/ingest`, no action is needed as they are client-only pages.
- Effort: LOW
- Dark-mode impact: NO

---

**[P3] No `error.tsx` boundary anywhere in the app**

- Dimension: 6 (Loading and Error State Coverage)
- Pages/Components: All routes
- Symptom: If a server component throws (e.g., the transcript fetch on `/calls/[ticker]` throws a non-404 API error), Next.js will render its default error page which is unstyled and exposes implementation details in development mode.
- Root cause: No `error.tsx` files have been created. The transcript page (`/calls/[ticker]/page.tsx`) explicitly throws on API errors (line 33: `throw new Error(...)`) to trigger Next.js error handling — but there is no boundary to catch it.
- Recommendation: Add at minimum a root-level `web/app/error.tsx` that shows a styled error message using design tokens. A per-route `error.tsx` for `/calls/[ticker]` would also be appropriate given the intentional throw pattern.
- Effort: LOW
- Dark-mode impact: NO

---

**[P3] Signals section ReactMarkdown block duplicated across three components**

- Dimension: (Code hygiene — not a user-visible inconsistency today, but a maintenance risk)
- Pages/Components: `ThemeCard.tsx:66-94`, `EvasionCard.tsx:96-124`, `StrategicShiftCard.tsx:103-133`
- Symptom: The same JSX block — a warning-styled `ReactMarkdown` renderer with custom `p`, `ul`, `ol`, `li`, `strong` component overrides and the "📈 What this signals for investors" heading — is copy-pasted identically across three components. If the styling changes (e.g., the warning color is updated), all three must be updated in sync.
- Root cause: The `signals` UI was added iteratively to each card type rather than extracted into a shared component.
- Recommendation: Extract a `SignalsSection` component (or `WhatThisSignals`) that accepts the `signals` string, `loadingSignals`, `signalsError`, and `onFetch` callback as props. All three signal cards adopt this component. `NewsCard` has a similar-but-distinct pattern (`Why does this matter for this call?`) with neutral colors — it can adopt the same structural component with different color props.
- Effort: MEDIUM
- Dark-mode impact: NO

---

**[P3] `ThemePicker` trigger not using `Button`**

- Dimension: 1 (Component Library Adherence), 9 (Interactive State Consistency)
- Pages/Components: `web/components/ThemePicker.tsx:20-25`
- Symptom: The theme toggle in the nav bar uses a raw `DropdownMenuTrigger` with manually applied `hover:bg-accent hover:text-accent-foreground transition-colors` instead of composing it with `Button variant="ghost" size="icon"`. The focus style is absent — the trigger has no `focus-visible:ring`.
- Root cause: The `DropdownMenuTrigger` in this codebase is a `@base-ui/react/menu` primitive that accepts a `render` prop or wraps children. The correct pattern (as used in `layout.tsx` for the mobile sheet trigger) is `<SheetTrigger render={<Button ... />}>`.
- Recommendation: Wrap the `DropdownMenuTrigger` with `Button variant="ghost" size="icon"` as the render target, following the pattern used in the mobile sheet trigger in `layout.tsx`.
- Effort: LOW
- Dark-mode impact: NO

---

**[P3] `CallCardSkeleton` in `CallList` is a hand-rolled card skeleton**

- Dimension: 3 (Card Surface Treatment), 6 (Loading State Coverage)
- Pages/Components: `web/components/CallList.tsx:8-19`
- Symptom: `CallCardSkeleton` uses `rounded-xl border p-6 shadow-sm bg-card` — which is a third variant (border + shadow) that doesn't match either the canonical shadcn Card (ring) or the admin hand-rolled cards (border + no shadow). It also lacks `border-border`, so the border color is the global border color from `@layer base`.
- Root cause: Written independently from the `CallCard` it stands in for.
- Recommendation: Update `CallCardSkeleton` to match the visual treatment of `CallCard` (which uses shadcn `<Card>`). The easiest fix is to render a skeleton `<Card className="p-6 h-full ...">` with muted shimmer children, mirroring the actual card layout.
- Effort: LOW
- Dark-mode impact: NO (minor — `border` without `border-border` inherits the global border color via `@layer base`, which is token-based)

---

## Categorized Action Plan

### 1. Token and dark-mode fixes
Fix hardcoded colors that break or risk breaking theming.

**Files:**
- `web/app/admin/loading.tsx` — replace `bg-zinc-*`, `bg-white`, `border-zinc-200` with tokens
- `web/components/transcript/CallBriefPanel.tsx:116` — replace `bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400` with token-based equivalent

**Effort:** LOW (2 files, <15 lines total)

---

### 2. Component library migration
Replace raw HTML elements with their shadcn equivalents.

**Files:**
- `web/app/admin/ingest/page.tsx` — `<input>` → `Input`, `<button>` → `Button`, `<div>` card → `Card`
- `web/app/auth/sign-in/page.tsx` — `<button>` → `Button`, `<div>` card → `Card`
- `web/components/ThemePicker.tsx` — wrap `DropdownMenuTrigger` with `Button variant="ghost" size="icon"`

**Effort:** LOW (3 files, targeted replacements)

---

### 3. Shared pattern extraction
Deduplicate the signals section and consolidate badge rendering.

**Files (signals extraction):**
- New: `web/components/transcript/SignalsSection.tsx` — extract the repeated ReactMarkdown + warning-styled block
- `web/components/transcript/ThemeCard.tsx` — adopt `SignalsSection`
- `web/components/transcript/EvasionCard.tsx` — adopt `SignalsSection`
- `web/components/transcript/StrategicShiftCard.tsx` — adopt `SignalsSection`
- `web/components/transcript/NewsCard.tsx` — adopt or extend `SignalsSection` with neutral variant

**Files (badge consolidation):**
- `web/components/CallCard.tsx` — replace inline `<span>` with `<Badge className={...}>`
- `web/components/transcript/CallBriefPanel.tsx` — replace `SignalBadge` and `EvasionBadge` helpers with `Badge`
- `web/components/transcript/EvasionCard.tsx` — replace inline severity badge span with `Badge`
- `web/components/transcript/MetadataPanel.tsx` — replace evasion index inline span with `Badge`
- `web/components/CompetitorList.tsx` — replace ticker chip with `Badge`

**Effort:** MEDIUM (1 new file, 8 files modified)

---

### 4. Navigation unification
Migrate all `<a>` tags to `<Link>` and extend `BreadcrumbBar` to cover admin routes.

**Files:**
- `web/app/layout.tsx` — replace brand link and all admin nav `<a>` tags with `<Link>`
- `web/app/admin/page.tsx` — replace `<a>` nav strip with `<Link>`, remove inline strip
- `web/app/admin/health/page.tsx` — replace `<a>` nav with `<Link>`, remove inline strip
- `web/app/admin/ingest/page.tsx` — replace `<a>` nav with `<Link>`, remove inline strip
- `web/components/BreadcrumbBar.tsx` — add admin route patterns, or extract to a shared `AdminBreadcrumb`

**Effort:** MEDIUM (5 files; BreadcrumbBar extension requires new route patterns)

---

### 5. Loading and error state gaps
Add missing Next.js route boundaries.

**Files:**
- New: `web/app/loading.tsx` — home route skeleton (grid of CallCardSkeleton-style placeholders)
- New: `web/app/error.tsx` — root-level styled error boundary
- New: `web/app/calls/[ticker]/error.tsx` — per-route error boundary for the explicit throw

**Effort:** LOW (3 new files, straightforward)

---

### 6. Surface treatment normalization
Unify all card-like surfaces to the canonical shadcn `Card` treatment (`ring-1 ring-foreground/10`, `rounded-xl`).

**Files (high-impact):**
- `web/app/admin/page.tsx` — `AnalyticsCard` → shadcn `<Card>`
- `web/app/admin/health/page.tsx` — `StatusCard` → shadcn `<Card>`
- `web/app/admin/health/loading.tsx` — skeleton cards → align with canonical Card shape (`rounded-xl`)
- `web/components/transcript/NewsCard.tsx` — outer div → `<Card>`
- `web/components/transcript/EvasionCard.tsx` — `Collapsible` outer → wrap in `<Card>` or align border treatment

**Files (lower-impact):**
- `web/components/CallList.tsx` — `CallCardSkeleton` — align rounded/border to match `CallCard`
- `web/components/transcript/TranscriptBrowser.tsx` — `SpanBlock` and search result divs (intentionally semantic-colored; document as deliberate exceptions)

**Effort:** MEDIUM (7 files; admin page requires replacing the local `AnalyticsCard`/`StatusCard` components)

---

### 7. Raw button accessibility and interactive state fixes
Ensure all interactive elements have keyboard-accessible focus rings.

**Files:**
- `web/components/transcript/ThemeCard.tsx`
- `web/components/transcript/EvasionCard.tsx`
- `web/components/transcript/StrategicShiftCard.tsx`
- `web/components/transcript/NewsCard.tsx`
- `web/components/chat/ChatThread.tsx`
- `web/components/transcript/KeywordList.tsx`
- `web/components/transcript/CallBriefPanel.tsx`

**Effort:** MEDIUM (7 files; depends on signals extraction in Work Package 3 for the overlapping signal card buttons)

---

## Dependency Map

```
WP 1 (token fixes)          → Independent; do first
WP 2 (component migration)  → Independent; do second
WP 5 (loading/error)        → Independent; low-risk
WP 4 (navigation)           → Independent; do after WP 2 (Link is used in admin pages)
WP 3 (shared patterns)      → WP 7 depends on WP 3 (signal card buttons are part of SignalsSection)
WP 6 (surface treatment)    → WP 2 should be complete first (Card in admin pages)
WP 7 (button a11y)          → WP 3 should be complete first for signal cards
```

Recommended sequence: WP 1 → WP 2 → WP 5 → WP 4 → WP 3 → WP 6 → WP 7

---

## Seed Observation Cross-Reference

| Seed | Status | Finding |
|------|--------|---------|
| S1 — Admin ingest bypasses component library | Verified | P2 "Admin ingest page bypasses component library throughout" |
| S2 — Badge duplication in CallCard | Verified | P2 "Sentiment and evasion badges hand-rolled throughout" |
| S3 — Admin nav fragmentation | Verified, expanded (layout.tsx also uses `<a>`) | P2 "Admin pages have no breadcrumb or consistent nav component" + P2 "Raw `<a>` tags throughout" |
| S4 — Inconsistent form patterns | Verified | P2 "Sign-in button is a raw `<button>` with a hand-rolled card container" + P2 "Admin ingest page bypasses component library" |
| S5 — Admin loading skeleton breaks dark mode | Verified | P1 "Admin loading skeleton is broken in dark mode" |
| S6 — Card surface treatment variance | Verified, expanded (6 patterns vs 4 stated) | P2 "Card surface treatment: six competing patterns" |
| S7 — Missing loading/error boundaries | Verified, scoped | P3 "Missing `loading.tsx`..." + P3 "No `error.tsx` boundary" |
| S8 — Raw buttons in transcript signal components | Verified, expanded (8 instances vs 3) | P2 "Raw `<button>` elements across signal cards and chat UI" |
| S9 — Signals section markup duplication | Verified | P3 "Signals section ReactMarkdown block duplicated across three components" |
