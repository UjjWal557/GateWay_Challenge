# Signal — AI Triage Engine
> Turn unstructured customer messages into structured decisions.

## What it does
Reads raw customer messages and outputs structured JSON triage decisions:
{ category, priority, summary, suggested_action, needs_human, confidence }
Handles garbage input, prompt injection, non-English, sarcasm, and 
multi-issue messages without crashing.

## Stack
- Python 3.x + Google Gemini API (gemini-2.5-flash)
- Streamlit dashboard UI

## Setup
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Add to .env:
```env
GEMINI_API_KEY=your-key-here
```

## Commands
| Command                          | What it does                        |
|----------------------------------|-------------------------------------|
| python src/run.py                | Triage all messages                 |
| python src/test_guardrails.py    | Run 8 edge case tests               |
| python src/evaluate.py           | Evaluate against ground truth       |
| streamlit run src/app.py         | Launch dashboard                    |

## Output files
- output/results.json    → all triage decisions
- output/eval_report.json → accuracy, latency, cost metrics

## See also
AI_DECISIONS.md — prompt strategy, uncertainty handling, where it breaks.
