# Structured Logging with JSON/Text Mode

**Status:** Accepted
**Date:** 2026-03-29

## Context

The architecture review's observability gap analysis (`docs/architecture-review/findings/issue-220-observability-logging.md`) found that the application used unstructured `print()` statements and inconsistent `logging.info()` calls, making it difficult to search, filter, or aggregate logs in Railway's log viewer. Production debugging required manual log scanning. The application needed a logging strategy that supported both machine-parseable output for production and human-readable output for development.

## Decision

Implement structured logging with two output modes:

- **JSON format** (production) — Machine-parseable JSON lines that integrate with log aggregation tools and Railway's log viewer. Each log entry includes timestamp, level, module, message, and structured context fields.
- **Plain text format** (local development) — Human-readable format with colors and simplified output for terminal viewing.

The format is controlled by the `LOG_FORMAT` environment variable (default: `text`). A slow query threshold (`LOG_SLOW_QUERY_THRESHOLD_MS = 500`) triggers warning-level log entries for database operations, enabling performance monitoring without external APM.

Sentry integration (`SENTRY_DSN`) captures errors and exceptions for alerting.

## Alternatives considered

1. **Unstructured logging (print/logging.info with f-strings)** — The pre-rewrite approach. Rejected because: (a) unstructured logs are impossible to filter or aggregate without regex parsing, (b) context fields (user_id, request_id, ticker) are lost in string formatting, and (c) Railway's log viewer can parse JSON fields but not arbitrary text patterns.

2. **structlog** — A popular Python structured logging library. A strong alternative with excellent integration and processors. Not chosen because: (a) the logging requirements are simple enough (JSON vs. text mode, a few context fields) that Python's built-in `logging` with a custom formatter suffices, and (b) structlog adds a dependency and its processor pipeline pattern has a learning curve for contributors.

3. **Third-party observability platform (Datadog, New Relic)** — Full APM with tracing, metrics, and log management. Rejected because: (a) the application is early-stage and doesn't generate enough traffic to justify APM costs, (b) Sentry covers error alerting, and (c) Railway's built-in log viewer handles basic log viewing. A full APM platform should be reconsidered as traffic grows.

4. **Python logging with RotatingFileHandler** — Writing logs to files with rotation. Rejected because: (a) Railway's container filesystem is ephemeral — log files are lost on deploy, (b) file-based logging requires a log shipper (Fluentd, Filebeat) to get logs into a central system, and (c) stdout logging is the standard for container-based deployments.

## Consequences

**Easier:**
- JSON logs are directly searchable in Railway's log viewer (filter by level, module, or custom fields)
- Slow query warnings surface database performance issues without external APM
- Sentry integration provides error alerting with stack traces and context
- Developers see human-readable logs locally while production gets machine-parseable output

**Harder:**
- Two log format code paths must be maintained and tested
- Structured logging requires discipline — every log call should include context fields, not just a message string
- No request tracing (correlation IDs) across services — logs from API and pipeline are not linked
- Sentry is the only alerting mechanism — no custom metric-based alerts
