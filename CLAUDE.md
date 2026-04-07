# CLAUDE.md

## Project

Gen-AI powered HAR analysis tool. Takes pre-processed HAR analysis JSON files (light/heavy) and produces deep insights via AWS Bedrock (Claude Sonnet 4.6). Built with Python + Streamlit.

## Commands

```bash
# activate venv first
source venv/bin/activate

# run Streamlit app
streamlit run app.py

# run CLI
python main.py light_0.json
python main.py --all
python main.py --all --output report.json
```

## Architecture

```
loader.py → context_builder.py → prompts.py → bedrock_client.py → app.py / reporter.py
```

- `loader.py` — reads JSON files, classifies as light/heavy
- `context_builder.py` — passes raw file data to Claude unchanged, zero stripping
- `prompts.py` — `SYSTEM_PROMPT` + `single_file_prompt` only, nothing else
- `bedrock_client.py` — boto3 wrapper, uses streaming (`invoke_model_with_response_stream`)
- `app.py` — Streamlit UI, renders structured findings cards
- `reporter.py` — CLI terminal output only (ANSI colours)

## Environment

Credentials live in `.env` (never commit):
```
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## Key decisions

- **Raw data sent as-is** — `context_builder.py` does zero stripping, the full JSON from the user's file goes directly to Claude
- **Streaming** — `invoke_model_with_response_stream` used everywhere, never `invoke_model`
- **Single prompt** — `single_file_prompt` covers all 4 dimensions (performance, reliability, third_party, functionality) in one call
- **Strict JSON schema** — Claude always returns a fixed structure: `file`, `classification`, `executive_summary`, `pages_analyzed`, `findings`, `false_positives`, `data_gaps`, `top_3_priorities`
- **No cross-file comparison** — removed, each file analyzed independently
- **No deep-dive prompt** — removed, `single_file_prompt` already covers full context

## Input file schema

```json
{
  "functionality": {},
  "performance": {},
  "reliability": {},
  "third_party": {}
}
```

Files named `light_*.json` (3-5 requests, simple flows) or `heavy_*.json` (700+ requests, full user journeys with analytics/trackers).

## Bedrock client

- `read_timeout=120s`, `connect_timeout=10s`
- Retries: max 2, standard mode
- `analyze_stream()` — yields `{"chunk": str}` during streaming, then `{"final_json": dict}` when done
- `analyze()` — non-streaming fallback, not used in app but kept for testing
- JSON parsed from response with markdown fence stripping

## What not to do

- Do not add any stripping or filtering to `context_builder.py` — raw data goes to Claude as-is
- Do not remove `analyze()` from `bedrock_client.py` — used for CLI testing
- Do not add cross-file comparison back — intentionally removed
- Do not commit `.env` or `venv/`
