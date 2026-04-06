# Beta Cost Estimate (Napkin Math)

**Date:** 2026-04-06
**Scenario:** 20 beta users, 3 Feynman chat sessions/week each

---

## Feynman Chat (Perplexity `sonar-pro`)

### Assumptions
- Model: `sonar-pro` (configured in `services/llm.py:34`)
- A Feynman session = 5 stages, ~10 API calls (user turn + assistant response building up history)
- System prompt: ~850 words / ~1,100 tokens (stage 1, largest); stages 2-5 are ~100 words each
- Token growth per turn (accumulated chat history):
  - Turn 1: ~1,500 input + ~500 output
  - Turn 3: ~2,800 input + ~500 output
  - Turn 5: ~4,000 input + ~500 output
- **Total per session: ~15,000 input + ~3,000 output tokens**

### Pricing [VERIFY: check https://docs.perplexity.ai/guides/pricing for current rates]
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

### Monthly cost (20 users x 3 sessions/week x 4 weeks = 240 sessions)
| | Tokens | Cost |
|---|---|---|
| Input | 240 x 15,000 = 3.6M | $10.80 |
| Output | 240 x 3,000 = 720K | $10.80 |
| **Subtotal** | | **$21.60/month** |

---

## Transcript Ingestion (Anthropic Claude, one-time)

### Assumptions
- From `core/models.py` pricing table and `ingestion/pipeline.py` flow
- Average transcript: ~12,000 tokens, ~50 chunks
- ~30% of chunks score >= 6 (trigger Tier 2 deep enrichment)

### Per-transcript breakdown
| Phase | Model | Calls | Avg Input | Avg Output | Cost |
|---|---|---|---|---|---|
| Tier 1 (all chunks) | Sonnet 4.5 ($3/$15 per 1M) | ~50 | ~2,000 | ~500 | ~$0.35 |
| Tier 2 (high-value) | Sonnet 4.5 | ~15 | ~2,000 | ~1,500 | ~$0.15 |
| Tier 3 synthesis | Haiku ($0.80/$4 per 1M) | 1 | ~5,000 | ~1,000 | <$0.01 |
| NLP synthesis | Haiku | 1 | ~3,000 | ~800 | <$0.01 |
| Brief synthesis | Haiku | 1 | ~2,000 | ~200 | <$0.01 |
| **Per transcript** | | | | | **~$0.52** |

### Beta total (20 transcripts)
| | Cost |
|---|---|
| 20 transcripts x $0.52 | **~$10.40 one-time** |

---

## Runtime API Calls (Anthropic Claude, per user session)

### Per-session breakdown
- Term definitions (Haiku, 1-2 calls): ~$0.001
- Investor signals (Haiku, 6-8 calls): ~$0.005
- **Per session: ~$0.006**

### Monthly (240 sessions)
| | Cost |
|---|---|
| 240 x $0.006 | **~$1.44/month** |

---

## Total

| Category | Cost | Frequency |
|---|---|---|
| Feynman chat (Perplexity) | ~$21.60 | Monthly |
| Runtime API calls (Anthropic) | ~$1.44 | Monthly |
| Transcript ingestion (Anthropic) | ~$10.40 | One-time |
| **Monthly ongoing** | **~$23/month** | |
| **First month** | **~$33** | |

### Verdict

Monthly cost is ~$23 for 20 beta users — roughly at the $20/month "trivial" threshold from the issue. This removes cost as a blocking constraint on the timeline.

### Sensitivity

- If users average 5 sessions/week instead of 3: ~$38/month
- If we switch from `sonar-pro` to `sonar` (cheaper, lower quality): ~$6/month
- If beta grows to 50 users at 3 sessions/week: ~$58/month

### How to validate with real data

Token usage is already tracked in `analytics_events` (see `db/analytics.py`). After dogfooding:
```sql
SELECT
    properties->>'service' AS service,
    SUM((properties->>'input_tokens')::int) AS input_tokens,
    SUM((properties->>'output_tokens')::int) AS output_tokens
FROM analytics_events
WHERE event_name = 'api_call_completed'
    AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY service;
```
Or hit `GET /admin/analytics/costs` (requires admin auth).
