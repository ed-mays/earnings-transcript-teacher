# Unrefined Feature Ideas

Raw ideas captured as they come up. Reviewed periodically to generate GitHub issues.

Identifier format: `TYPE-slug` where TYPE is one of: `FEAT`, `BUG`, `SPIKE`, `UX`, `INFRA`, `PERF`

---

## 2026-03-27

### FEAT-user-roles *(→ promoted to GitHub issues)*
The app doesn't have any kind of user roles — the ADMIN_SECRET_TOKEN approach feels like a clunky workaround. Need a way to distinguish between administrative and "regular" users.

### UX-navigation
The app doesn't have any navigation, it's all just one big screen. The screen is starting to get dense with information — investigate ways to make it cleaner.

### FEAT-gamification
Maybe consider some kind of optional gamification for the app.

### FEAT-user-profiles
Users might want to set up a profile.

### FEAT-payments
Payment integration.

### UX-themes
User-selectable UI themes.

### INFRA-progressive-environments
Configure progressive environments for external services. The app doesn't currently follow a dev → stage → prod promotion flow. The intent is to define a clear path to production: what environments exist, how each external service (Supabase, Vercel, Railway, Modal) is configured per environment, and how changes are promoted between them.

### SPIKE-storybook
Evaluate using Storybook to develop a component library for the app.

### FEAT-feature-flags
The app has no feature flag system. We want one for production control, A/B testing, and blast-radius reduction during deployments. At current scale, prefer a low/no-cost provider but build behind an abstraction layer so we can port to another provider later.

### BUG-vercel-preview-cors
Vercel preview URLs don't work — appears to be a CORS issue. The app was updated to dynamically generate allowed origins at deployment/runtime, but that hasn't worked for preview environments. Production is unaffected. Need to investigate root cause and find a fix that makes preview URLs functional.

### BUG-speaker-attribution
Speaker attribution in Q&A is sometimes off by one sentence. The operator's closing line ("We'll go ahead and take our first question from X") introduces the next speaker but gets attributed to that speaker instead. In the AAPL transcript, "We'll go ahead and take our first question from Amit Daryanani of Evercore." appears in Amit's speech bubble rather than the operator's. Each speaker's text block needs to be trimmed of any leading sentence that belongs to the prior speaker.
