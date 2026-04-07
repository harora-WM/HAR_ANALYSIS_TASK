import json

SYSTEM_PROMPT = """You are an expert web performance and network analyst specializing in HAR (HTTP Archive) analysis.

You receive pre-processed analysis data extracted from HAR files. This data has already been parsed and structured into four dimensions: performance, reliability, third_party, and functionality.

Your job is to:
1. Interpret the numbers — don't just restate them, explain what they mean for real users
2. Identify the actual root causes behind issues, not just surface symptoms
3. Distinguish real problems from noise (e.g., long-lived tracking connections flagged as slow page loads)
4. Prioritize findings by user impact
5. Give specific, actionable recommendations — not generic advice

Severity definitions:
- RED: Critical issue affecting most users, needs immediate attention
- AMBER: Moderate issue affecting some users or degrading experience, should be fixed soon
- GREEN: Within acceptable range, monitor only

Always structure your response as valid JSON matching the schema provided in the prompt.
"""


def single_file_prompt(context: dict) -> str:
    return f"""Analyze this HAR analysis data for file: {context['filename']} (classification: {context['classification']})

DATA:
{json.dumps(context['data'], indent=2)}

Return a JSON response with this exact structure:
{{
  "file": "<filename>",
  "classification": "<light|heavy>",
  "executive_summary": "<2-3 sentence plain English summary of the overall health of this recording>",
  "pages_analyzed": [
    {{
      "url": "<page url>",
      "total_load_ms": <number>,
      "verdict": "<GREEN|AMBER|RED>",
      "one_liner": "<what's happening on this page in one sentence>"
    }}
  ],
  "findings": [
    {{
      "dimension": "<performance|reliability|third_party|functionality>",
      "severity": "<RED|AMBER|GREEN>",
      "title": "<short issue title>",
      "explanation": "<explain what this means for actual users — not just the metric>",
      "root_cause": "<likely technical reason behind this issue>",
      "recommendation": "<specific actionable fix>"
    }}
  ],
  "false_positives": [
    {{
      "flagged_issue": "<what the tool flagged>",
      "reason": "<why this is likely a false positive or misleading>"
    }}
  ],
  "data_gaps": [
    "<any important analysis that couldn't be done due to missing data in this file>"
  ],
  "top_3_priorities": [
    "<most impactful thing to fix first>",
    "<second priority>",
    "<third priority>"
  ]
}}

Be precise with numbers. If you see a VerySlowPageLoad for a tracking/analytics domain, flag it as a false positive and explain why.
"""

