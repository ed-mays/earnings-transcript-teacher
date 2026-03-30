"""Request-scoped context variables for correlation ID propagation."""

import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
