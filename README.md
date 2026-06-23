# 📡 Signal — AI Triage Engine

> Turn messy customer messages into structured decisions — and know when to call a human.

Built for the **FRONTLINE One-Day AI Build Challenge**.

---

## What it does

Reads raw customer messages and outputs a structured JSON triage decision:

```json
{
  "category": "billing",
  "priority": "P1",
  "summary": "Customer was charged twice for their subscription.",
  "suggested_action": "Investigate duplicate charge and issue refund.",
  "needs_human": true,
  "confidence": 0.95
}
```

Handles garbage input, HTML, prompt injection, non-English, sarcasm, PII, and multi-issue messages without crashing.

---

## Setup

```bash
git clone https://github.com/UjjWal557/GateWay_Challenge.git
cd GateWay_Challenge
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:
GEMINI_API_KEY=your-key-here

Get a free key at: https://aistudio.google.com/apikey

---

## Commands

| Command | What it does |
|---|---|
| `python src/run.py` | Triage all messages in `data/messages.txt` |
| `python src/test_guardrails.py` | Run 9 edge case tests |
| `python src/evaluate.py` | Evaluate against 10 ground truth labels |
| `python src/validate.py` | Full system health check |
| `streamlit run src/app.py` | Launch visual dashboard |

---

## Stack

| Tool | Why |
|---|---|
| **gemini-3.1-flash-lite** | Free tier, 500 RPD, fast, reliable JSON output |
| **google-generativeai** | Official SDK, simple one-call API |
| **Streamlit** | Full dashboard in pure Python — no frontend needed |
| **python-dotenv** | API key never hardcoded in source |
| **No vector DB or LangChain** | Task is classification, not retrieval — prompt engineering is enough |

---

## Architecture

Raw message

│

├─► pii_check()

│       Scan raw text for credit cards, emails, phone numbers

│       If found: escalate priority, force needs_human = True

│

├─► preprocess()

│       Strip HTML tags and decode entities

│       Extract text from JSON dumps and code blocks

│       Truncate at 800 chars, normalize unicode and whitespace

│       If empty after cleaning: skip API, return unclear

│

├─► Gemini API

│       Strict system prompt — 10 named rules, priority order

│       Output contract: first char { last char } — JSON only

│       All 8 categories and 4 priorities listed explicitly

│       On parse failure: strip markdown fences, retry once

│       On 429 rate limit: read retry delay from error, sleep, retry

│

├─► post_process()

│       confidence < 0.6 → needs_human = True

│       P0 priority → needs_human = True

│       abuse category → needs_human = True, priority = P1

│       Strip any fields outside the defined schema

│

└─► Structured JSON decision

---

## AI Decisions

**Model:** `gemini-3.1-flash-lite` — zero-shot classification, no fine-tuning.
A well-structured prompt achieved 100% accuracy on ground truth.
Fine-tuning adds cost, complexity, and retraining overhead — only justified when zero-shot fails.

**Prompt strategy:** 10 named rules enforced in priority order.
Output contract forces raw JSON only — first char `{`, last char `}`.
All valid enum values listed explicitly so the model cannot invent new categories or priorities.

**Uncertainty:** Model self-reports confidence from 0.0 to 1.0.
Below 0.6 automatically sets `needs_human = True` — the system knows when it does not know.

**Bad input handling:**

| Scenario | What happens |
|---|---|
| Prompt injection | Classified as `abuse`, blocked, needs_human = True |
| Empty or garbage | API skipped entirely, returns `unclear` |
| HTML input | Tags stripped before API call |
| PII detected | Priority escalated one level, human flagged |
| JSON parse failure | Clean fences → retry once → safe fallback dict |
| 429 rate limit | Read exact retry delay from error, sleep, retry |
| Any exception | Safe fallback dict returned — never crashes |

**Results:**

| Metric | Value |
|---|---|
| Guardrail tests | 9/9 pass on live API |
| Category accuracy | 10/10 — 100% |
| Priority accuracy | 10/10 — 100% |
| Avg confidence | 0.93 |
| Avg latency | ~1900ms |
| Fallbacks used | 0 |
| Cost (20 messages) | $0.001 |

**What I'd fix with more time:**
- Confidence threshold calibrated per-category from a larger labeled dataset
- Async parallel processing to remove the rate limit bottleneck
- Embedding pre-filter for obvious cases to reduce API calls
- Webhook ingestion for real-time message intake instead of file upload

---

*Using AI tools to build was encouraged — and required understanding every decision made.*
*Signal was built with Google Antigravity and Claude.*
