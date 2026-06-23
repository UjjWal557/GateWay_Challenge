# AI Decisions — Signal

## Model + tools used
- **Model**: gemini-3.1-flash-lite (Google Gemini API, free tier)
- **SDK**: google-generativeai Python SDK
- **UI**: Streamlit dashboard
- **No** vector DB, embeddings, fine-tuning, or external tools
- Zero-shot classification — pure prompt engineering

## Prompt strategy
Strict system prompt with 10 explicit named rules enforced in priority order.
Output contract: first character must be `{`, last must be `}` — no prose, 
no markdown, no explanation before or after the JSON.
Schema is fully defined in the prompt with all valid enum values listed.
Edge cases handled by name: injection → Rule 1, garbage → Rule 2, 
non-English → Rule 3, sarcasm → Rule 4, multi-issue → Rule 5.
Retry logic: on JSON parse failure, clean markdown fences and retry once.
On 429 rate limit, extract wait time from error message and sleep exactly 
that long — no fixed delays, no wasted time.

## How we handle uncertainty and bad input
| Scenario | Handling |
|---|---|
| confidence < 0.6 | auto needs_human = True |
| Prompt injection | Rule 1 → abuse + needs_human, confidence 1.0 |
| Empty / garbage input | preprocess → __EMPTY_MESSAGE__ → skip API |
| HTML input | strip tags + decode entities before API call |
| JSON/code input | extract string values, send clean text |
| Non-English | classify + note language in summary |
| PII (card/email/phone) | detected pre-API, priority escalated, human flagged |
| P0 priority | always needs_human = True |
| 429 rate limit | auto-retry with exact backoff from error response |
| JSON parse failure | clean → retry → safe fallback dict, never crashes |

## How we know it works
- **9/9 guardrail tests** pass on live API — injection, garbage, empty, 
  non-English, sarcasm, multi-issue, PII, angry, vague all handled correctly
- **10/10 category accuracy, 10/10 priority accuracy** on 10 hand-labeled 
  ground truth messages. Full pipeline tested on 20 real-world messages 
  with 0 fallbacks.
- **0 retries, 0 fallbacks** on 20 real-world messages including HTML, JSON 
  dumps, SQL injection, XSS, multi-language, and PII inputs
- **Avg confidence: 0.93** — model is honest about uncertainty
- **validate.py** runs 6/6 system health checks including live API test, 
  preprocessing, PII detection, and output file validation

## Cost + performance
| Metric | Value |
|---|---|
| Avg latency per message | 1909ms |
| Total cost (20 messages) | $0.0020 |
| Est. cost per 1000 messages | ~$0.10 |
| Guardrail score | 9/9 |
| Accuracy on ground truth | 100% |

## What we'd fix with more time
1. **Confidence calibration** — threshold of 0.6 is fixed; would tune 
   per-category using larger labeled dataset
2. **Async processing** — current sequential processing with rate limit 
   backoff adds latency; parallel batching with queue would be faster
3. **Embedding pre-filter** — route obvious cases (exact keyword match) 
   without an LLM call to reduce cost at scale
4. **Streaming responses** — lower perceived latency for the dashboard
5. **Webhook ingestion** — real-time message intake instead of file upload
