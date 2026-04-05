# Environment-Driven Configuration

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application runs in three distinct environments that each inject configuration differently:

- **Local development** — `.env` files loaded by shell scripts
- **Railway** — Environment variables set in the Railway dashboard
- **Modal** — Secrets injected via the `earnings-secrets` Modal secret, not from `api/.env`

The configuration approach needed to work identically across all three without environment-specific code paths.

## Decision

All configuration is via environment variables with fail-fast startup validation. No config files (`.ini`, `.yaml`, `.toml`), no settings classes with defaults, no tiered config resolution.

The implementation in `api/settings.py` defines a `REQUIRED_ENV_VARS` list. At startup, the API validates that every required variable is present — if any are missing, the API returns 503 for all requests with a clear error message listing the missing variables.

The canonical reference for all environment variables is `api/.env.example` with inline comments.

## Alternatives considered

1. **Pydantic Settings (pydantic-settings)** — A typed settings class with validation, default values, and `.env` file loading. A strong alternative that would provide type safety and IDE support. Not chosen because: (a) the settings are simple key-value pairs that don't benefit from nested model validation, (b) Pydantic Settings encourages default values, which can mask missing configuration in new environments (the fail-fast approach catches this immediately), and (c) adding a dependency for what amounts to `os.environ.get()` with a validation loop felt over-engineered.

2. **Config files with environment overrides (YAML/TOML)** — A base config file with per-environment overrides. Rejected because: (a) config files must be deployed alongside the application, adding a deployment concern, (b) Railway and Modal don't have a natural place for config files (they inject env vars, not files), and (c) config file hierarchies (base → environment → local) add resolution complexity.

3. **Python-dotenv with multiple .env files** — Loading `.env.development`, `.env.production`, etc. Rejected because: (a) multiple `.env` files create confusion about which values are active, (b) `.env` files in production risk committing secrets to the repository, and (c) the three environments already have their own env var injection mechanisms.

4. **AWS SSM Parameter Store / HashiCorp Vault** — Centralized secret management. Rejected because: (a) adds infrastructure dependency (SSM requires AWS, Vault requires a server), (b) the application runs across three different platforms (Railway, Modal, Vercel) that would each need a different integration path, and (c) the current secret count (~10 variables) doesn't justify a dedicated secret management service.

## Consequences

**Easier:**
- Configuration works identically everywhere — `os.environ["KEY"]` is the universal access pattern
- Missing configuration fails loudly at startup, not silently at runtime when a feature is first used
- No config files to deploy, version, or template
- New environments are configured by setting env vars — no code changes

**Harder:**
- No type safety — all env vars are strings until parsed in application code
- No default values — every required variable must be explicitly set in every environment
- The `api/.env.example` file must be manually kept in sync with `REQUIRED_ENV_VARS`
- Complex configuration (e.g., feature flags, per-environment behavior) requires adding more env vars rather than structured config
