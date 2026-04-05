# Modal for Distributed Compute

**Status:** Accepted
**Date:** 2026-03-27

## Context

Transcript ingestion is a long-running operation (30–60 seconds per transcript) that makes multiple LLM API calls across three tiers (ADR 0011). Running this in the FastAPI API process would block request handling, and long-running HTTP requests are unreliable (client timeouts, proxy disconnections). The ingestion workload needed to run asynchronously, with its own resource limits and timeout configuration, independent of the API server.

## Decision

Use Modal's serverless compute platform for transcript ingestion. The pipeline is defined in `pipeline/ingest.py` using Modal's Python-native decorator interface:

- `@app.function` decorator with a 3600-second timeout
- Automatic container image building from `pipeline/requirements.txt`
- Secret injection via the `earnings-secrets` Modal secret (not from `api/.env`)
- The API triggers ingestion by calling the Modal function asynchronously

Key implementation detail: `add_local_dir` must be the last step in the Modal image chain; `ignore=` takes inline patterns, not a file path; module-level code runs in the container context (avoid side effects at import time).

## Alternatives considered

1. **Background tasks in FastAPI (BackgroundTasks)** — Running ingestion as a FastAPI background task after sending the HTTP response. Rejected because: (a) background tasks share the API process's resources, and a CPU/memory-intensive ingestion could degrade API responsiveness, (b) if the API process restarts (deploy, crash), in-flight background tasks are lost with no recovery, and (c) there's no visibility into background task progress or failures.

2. **Celery + Redis** — The standard Python task queue. Rejected because: (a) Celery requires a message broker (Redis/RabbitMQ) and a worker process, adding two infrastructure components, (b) Celery's configuration and serialization model is complex for what is essentially "run this function asynchronously," and (c) Modal provides the same capability with less infrastructure to manage.

3. **AWS Lambda / Google Cloud Functions** — Serverless functions on a major cloud provider. Rejected because: (a) the pipeline imports shared Python modules (`nlp/`, `services/`, `db/`) that require packaging as a deployment bundle, which is more complex than Modal's `add_local_dir`, (b) Lambda/Cloud Functions have lower default timeouts (15 min / 9 min) that would need configuration, and (c) Modal's Python-native interface is more developer-friendly than YAML/Terraform configuration.

4. **Google Cloud Run Jobs** — Container-based batch jobs. A viable alternative with good container support. Not chosen because: (a) Cloud Run Jobs require building and pushing a Docker image, while Modal builds the image automatically from a requirements file, and (b) Cloud Run Jobs require GCP project setup and IAM configuration that Modal abstracts away.

5. **Temporal / Inngest (durable workflow engines)** — Workflow orchestration with retry, state management, and observability. A strong alternative for production resilience. Not chosen because: (a) the ingestion pipeline is a single linear operation (not a complex workflow with branches and human-in-the-loop steps), and (b) Modal provides sufficient retry and timeout capabilities for the current use case. Workflow engines should be reconsidered if the pipeline becomes more complex.

## Consequences

**Easier:**
- Ingestion runs independently of the API process — no resource contention
- Modal handles container image building, scaling, and infrastructure management
- Python-native decorator interface — no YAML, Terraform, or Docker configuration
- 1-hour timeout accommodates large transcripts with many LLM calls
- Secret injection is separate from the API's environment variables

**Harder:**
- Modal is a less established platform than AWS/GCP — potential availability and longevity risk
- Debugging requires checking Modal's dashboard for function logs, separate from Railway API logs
- The `earnings-secrets` Modal secret must be kept in sync with the API's environment variables manually
- Modal's container build model has quirks (`add_local_dir` ordering, `ignore=` syntax) that differ from standard Docker patterns
- No built-in webhook or callback when ingestion completes — the API must poll or the client must refresh
