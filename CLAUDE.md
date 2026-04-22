# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Gen-AI powered HAR analysis tool. Takes pre-processed HAR analysis JSON files (light/heavy) and produces deep insights via AWS Bedrock (Claude Sonnet 4.6). Built with Python + Streamlit.

## Commands

```bash
# activate venv first
source venv/bin/activate

# run Streamlit app
streamlit run app.py
```

There is no test suite. Sample JSON files for manual testing live in `input_files/`.

## Architecture

```
loader.py → context_builder.py → prompts.py → bedrock_client.py → app.py
```

All core modules live in the `analyzer/` package:

- `analyzer/loader.py` — reads JSON files
- `analyzer/context_builder.py` — passes raw file data to Claude unchanged, zero stripping
- `analyzer/prompts.py` — `SYSTEM_PROMPT` + `single_file_prompt` only, nothing else
- `analyzer/bedrock_client.py` — boto3 wrapper, uses streaming (`invoke_model_with_response_stream`); `temperature=0.2`, `max_tokens=8192`
- `app.py` — Streamlit UI, renders structured findings cards; uses `analyze_stream()` with a live placeholder that swaps to the structured report on completion

## Environment

Credentials live in `.env` (never commit). See `.env.example` for the template:
```
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

`load_dotenv()` is called at the top of `app.py` before any env var reads.

## Key decisions

- **Raw data sent as-is** — `context_builder.py` does zero stripping; the full JSON from the user's file goes directly to Claude
- **Streaming** — `invoke_model_with_response_stream` used everywhere in the web app, never `invoke_model`
- **Single prompt** — `single_file_prompt` covers all 4 dimensions (performance, reliability, third_party, functionality) in one call
- **Strict JSON schema** — Claude always returns a fixed structure: `file`, `executive_summary`, `pages_analyzed`, `findings`, `false_positives`, `data_gaps`, `top_3_priorities`
- **No cross-file comparison** — removed; each file analyzed independently
- **No deep-dive prompt** — removed; `single_file_prompt` already covers full context

## Input file schema

```json
{
  "functionality": {},
  "performance": {},
  "reliability": {},
  "third_party": {}
}
```

## Bedrock client

- `read_timeout=120s`, `connect_timeout=10s`
- Retries: max 2, standard mode
- `analyze_stream()` — yields `{"chunk": str}` during streaming, then `{"final_json": dict}` when done
- `analyze()` — non-streaming fallback; kept for testing
- JSON parsed from response with markdown fence stripping; parse failures return `{"raw_response": text, "parse_error": True}` rather than crashing

## What not to do

- Do not add any stripping or filtering to `context_builder.py` — raw data goes to Claude as-is
- Do not remove `analyze()` from `bedrock_client.py` — kept for testing
- Do not add cross-file comparison back — intentionally removed
- Do not commit `.env` or `venv/`
