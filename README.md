# HAR AI Analyzer

A Gen-AI powered analysis tool that takes pre-processed HAR analysis JSON files and produces deep, actionable insights using AWS Bedrock (Claude Sonnet 4.6).

---

## What it does

Standard HAR analysis tools output structured JSON with metrics, severity flags, and generic recommendations. This tool takes that output one step further — feeding it into Claude to produce:

- Plain-English explanation of what the numbers mean for real users
- Root cause analysis behind each issue (not just surface symptoms)
- False positive detection (e.g. long-lived tracking connections flagged as slow page loads)
- Industry benchmark comparisons (Core Web Vitals, payload budgets)
- Prioritized, specific fixes — not generic advice

---

## Input

The tool accepts the structured JSON output files produced by a HAR analysis pipeline. These files follow a 4-section schema:

```
{
  "functionality": { ... },   ← API calls, JS errors, session info, form analysis
  "performance":   { ... },   ← page load metrics, resource types, timing breakdown
  "reliability":   { ... },   ← error rates, failed requests, CORS, security headers
  "third_party":   { ... }    ← third-party request counts, sizes, load times
}
```

Files are typically named `light_*.json` (simple flows, few requests) or `heavy_*.json` (full user journeys, hundreds of requests with analytics/chat/trackers).

---

## Project structure

```
har_analysis/
├── app.py                    ← Streamlit web UI
├── main.py                   ← CLI entry point
├── requirements.txt
├── .env.example              ← config template
└── analyzer/
    ├── __init__.py
    ├── loader.py             ← reads and classifies JSON files
    ├── context_builder.py    ← passes raw file data to Claude unchanged
    ├── bedrock_client.py     ← AWS Bedrock boto3 wrapper with streaming
    ├── prompts.py            ← system prompt + single file analysis prompt
    └── reporter.py           ← coloured terminal output formatter (CLI)
```

---

## How it works

```
Upload JSON
    ↓
loader.py        → load file, classify as light/heavy
    ↓
context_builder  → pass raw data unchanged
    ↓
prompts.py       → wrap raw data into structured prompt
    ↓
bedrock_client   → stream response from Claude Sonnet 4.6 via Bedrock
    ↓
app.py           → render structured report with severity cards
```

### Key design decisions

- **Raw data sent as-is** — `context_builder.py` does zero stripping or filtering. The full JSON from the user's file goes directly to Claude so no signal is lost.
- **Streaming** — uses `invoke_model_with_response_stream` so the user sees live output instead of waiting for the full response.
- **Strict JSON output** — Claude is instructed to return a fixed schema, making the response reliably parseable and renderable as structured UI components.

---

## Setup

### 1. Clone and create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in your credentials in `.env`:

```env
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

---

## Usage

### Streamlit web app (recommended)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

1. Upload one or more `light_*.json` or `heavy_*.json` files via the sidebar
2. Click **Run Analysis**
3. View the streamed analysis rendered as a structured report
4. Download the full report as JSON using the button at the bottom

### CLI

```bash
# single file
python main.py light_0.json

# multiple files
python main.py light_0.json light_1.json heavy_1.json

# all JSON files in current directory
python main.py --all

# save output to JSON
python main.py --all --output report.json
```

---

## Output structure

Each file analysis produces:

| Section | What it contains |
|---|---|
| **Executive Summary** | 2-3 sentence plain-English health overview |
| **Pages Analyzed** | Each page URL with load time and RED/AMBER/GREEN verdict |
| **Findings** | Individual issues with dimension, severity, explanation, root cause, fix |
| **False Positives** | Issues flagged by the tool that are actually noise, with explanation |
| **Data Gaps** | What couldn't be analyzed due to missing data in the input file |
| **Top 3 Priorities** | The most impactful fixes, ordered by user impact |

### Severity definitions

| Severity | Meaning |
|---|---|
| 🔴 RED | Critical — affects most users, needs immediate attention |
| 🟡 AMBER | Moderate — degrades experience, should be fixed soon |
| 🟢 GREEN | Acceptable — monitor only, no action required |

---

## Dependencies

| Package | Purpose |
|---|---|
| `boto3` | AWS Bedrock API client |
| `python-dotenv` | Load credentials from `.env` |
| `streamlit` | Web UI |

---

## Notes

- The `.env` file is never committed — add it to `.gitignore`
- The `venv/` directory should also be in `.gitignore`
- AWS credentials require Bedrock access enabled in your AWS account for the `ap-south-1` region
- The Bedrock client has a 120s read timeout — large heavy files may approach this on slow connections
