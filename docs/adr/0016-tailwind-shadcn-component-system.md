# Tailwind + shadcn/ui Component System

**Status:** Accepted
**Date:** 2026-04-02

## Context

The Next.js frontend (ADR 0001) needed a styling and component strategy. The application has a moderate number of UI components — cards for transcript summaries, forms for search, data tables for analytics, dialogs for confirmations, and a chat interface for Feynman learning. The component library needed to support accessibility, dark mode, and customization without fighting library abstractions.

## Decision

Use Tailwind CSS for utility-first styling and shadcn/ui (with Base UI primitives from `@base-ui/react`) for the component library. shadcn copies component source code directly into the project (`web/components/ui/`), allowing full customization.

Key implementation details:
- Components use the `cn()` utility (clsx + tailwind-merge) for conditional class composition
- Icons from `lucide-react`
- Button component uses `@base-ui/react/button` (not Radix — no `asChild` prop; use `buttonVariants()` on Link className instead)

## Alternatives considered

1. **Material UI (MUI)** — The most popular React component library. Rejected because: (a) MUI's design language is strongly opinionated (Material Design) and difficult to customize beyond surface-level theming, (b) MUI's CSS-in-JS approach (Emotion) adds runtime overhead and conflicts with Tailwind's utility approach, and (c) MUI components are large and would significantly increase bundle size for a small application.

2. **Chakra UI** — A well-designed component library with good accessibility. Not chosen because: (a) Chakra uses its own styling system (style props) that doesn't compose cleanly with Tailwind utilities, (b) Chakra v3 was in transition during the decision period, creating stability concerns, and (c) shadcn's source-code-in-project model provides more flexibility for an evolving UI.

3. **Radix UI primitives + custom styling (no shadcn)** — Using Radix primitives directly with Tailwind. A viable approach, but rejected because shadcn provides pre-built compositions of Radix/Base UI primitives with Tailwind that accelerate development. Building the same components from raw primitives would take significantly longer with no quality advantage.

4. **CSS Modules or vanilla CSS** — Scoped CSS without a utility framework. Rejected because: (a) CSS Modules require creating separate `.module.css` files for each component, slowing iteration, (b) vanilla CSS has specificity management issues at scale, and (c) Tailwind's utility approach enables rapid prototyping during the compressed delivery window.

5. **No component library (raw HTML + Tailwind)** — Building all components from scratch with Tailwind utilities. Rejected because accessibility (keyboard navigation, ARIA attributes, focus management) requires significant effort to implement correctly — shadcn and Base UI provide this out of the box.

## Consequences

**Easier:**
- Components are source code in the project — no version-pinning issues or upstream breaking changes
- Tailwind utilities enable rapid styling iteration without context-switching to CSS files
- Accessible by default — Base UI primitives handle keyboard navigation and ARIA
- Customization is editing a local file, not overriding library internals

**Harder:**
- shadcn components are not auto-updated — upstream improvements must be manually merged
- Tailwind class strings can become long and hard to read for complex components
- The team must understand both Tailwind utilities and Base UI primitive APIs
- No design system consistency enforcement — it's possible to drift from shadcn patterns when building custom components
