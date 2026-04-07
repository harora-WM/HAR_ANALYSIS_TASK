import json
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from analyzer.loader import load_file
from analyzer.context_builder import build_context
from analyzer.bedrock_client import BedrockClient
from analyzer.prompts import SYSTEM_PROMPT, single_file_prompt

load_dotenv()

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HAR AI Analyzer",
    page_icon="🔍",
    layout="wide",
)

# ── styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.severity-red    { background:#ff4b4b22; color:#ff4b4b; border:1px solid #ff4b4b;
                   border-radius:6px; padding:2px 10px; font-weight:700; font-size:13px; }
.severity-amber  { background:#ffa50022; color:#ffa500; border:1px solid #ffa500;
                   border-radius:6px; padding:2px 10px; font-weight:700; font-size:13px; }
.severity-green  { background:#00c85322; color:#00c853; border:1px solid #00c853;
                   border-radius:6px; padding:2px 10px; font-weight:700; font-size:13px; }
.finding-card    { background:#1e1e2e; border-radius:10px; padding:16px 20px;
                   margin-bottom:12px; border-left:4px solid #555; }
.finding-card.red    { border-left-color:#ff4b4b; }
.finding-card.amber  { border-left-color:#ffa500; }
.finding-card.green  { border-left-color:#00c853; }
.metric-box      { background:#1e1e2e; border-radius:10px; padding:14px;
                   text-align:center; }
.section-header  { font-size:18px; font-weight:700; margin:24px 0 8px 0;
                   border-bottom:1px solid #333; padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def severity_badge(sev: str) -> str:
    cls = {"RED": "severity-red", "AMBER": "severity-amber", "GREEN": "severity-green"}.get(sev, "severity-green")
    return f'<span class="{cls}">{sev}</span>'


def card_class(sev: str) -> str:
    return {"RED": "red", "AMBER": "amber", "GREEN": "green"}.get(sev, "green")


def get_client() -> BedrockClient:
    return BedrockClient(
        region=os.getenv("AWS_REGION", "ap-south-1"),
        model_id=os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"),
    )


def load_uploaded(uploaded_file) -> dict:
    """Save uploaded file to a temp path and load it via loader."""
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    loaded = load_file(tmp_path)
    loaded["filename"] = uploaded_file.name
    os.unlink(tmp_path)
    return loaded


# ── render ────────────────────────────────────────────────────────────────────

def render_single_analysis(analysis: dict):
    if analysis.get("parse_error"):
        st.error("Claude returned an unparseable response.")
        st.code(analysis.get("raw_response", ""), language="text")
        return

    # header row
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📄 {analysis.get('file', 'Unknown')}")
    with col2:
        cls = analysis.get("classification", "").upper()
        badge_col = "🔵" if cls == "LIGHT" else "🟠"
        st.markdown(f"**{badge_col} {cls}**")

    # ── severity scorecard ────────────────────────────────────────────────────
    findings = analysis.get("findings", [])
    red_count   = sum(1 for f in findings if f.get("severity") == "RED")
    amber_count = sum(1 for f in findings if f.get("severity") == "AMBER")
    green_count = sum(1 for f in findings if f.get("severity") == "GREEN")

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"""
        <div style="background:#ff4b4b22;border:1px solid #ff4b4b;border-radius:10px;
                    padding:16px;text-align:center;">
            <div style="font-size:36px;font-weight:800;color:#ff4b4b">{red_count}</div>
            <div style="color:#ff4b4b;font-weight:600">🔴 RED</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""
        <div style="background:#ffa50022;border:1px solid #ffa500;border-radius:10px;
                    padding:16px;text-align:center;">
            <div style="font-size:36px;font-weight:800;color:#ffa500">{amber_count}</div>
            <div style="color:#ffa500;font-weight:600">🟡 AMBER</div>
        </div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""
        <div style="background:#00c85322;border:1px solid #00c853;border-radius:10px;
                    padding:16px;text-align:center;">
            <div style="font-size:36px;font-weight:800;color:#00c853">{green_count}</div>
            <div style="color:#00c853;font-weight:600">🟢 GREEN</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── metrics scorecard ─────────────────────────────────────────────────────
    pages_analyzed = analysis.get("pages_analyzed", [])
    fastest_page = min((p.get("total_load_ms", 0) for p in pages_analyzed), default=0)
    real_pages = [p for p in pages_analyzed if p.get("verdict") in ("RED", "AMBER", "GREEN")]

    # pull key metrics from findings text (best effort from titles/explanations)
    perf_findings = [f for f in findings if f.get("dimension") == "performance"]
    rel_finding   = next((f for f in findings if f.get("dimension") == "reliability"), None)
    tp_finding    = next((f for f in findings if f.get("dimension") == "third_party"), None)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Pages Recorded", len(pages_analyzed))
    with m2:
        st.metric("Performance Issues", len(perf_findings))
    with m3:
        err_label = "0%" if not rel_finding or "Zero" in rel_finding.get("title","") else "See findings"
        st.metric("Error Rate", err_label)
    with m4:
        st.metric("3P Issues", 1 if tp_finding else 0)

    st.divider()

    # executive summary
    st.info(analysis.get("executive_summary", ""))

    # pages analyzed
    pages = analysis.get("pages_analyzed", [])
    if pages:
        st.markdown('<div class="section-header">Pages Analyzed</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(pages), 3))
        for i, page in enumerate(pages):
            with cols[i % 3]:
                sev = page.get("verdict", "GREEN")
                st.markdown(f"""
                <div class="metric-box">
                    <div style="font-size:11px;color:#888;margin-bottom:4px">{page.get('url','unknown')[:50]}</div>
                    <div style="font-size:22px;font-weight:700">{page.get('total_load_ms',0):,}ms</div>
                    <div style="margin-top:6px">{severity_badge(sev)}</div>
                    <div style="font-size:12px;color:#aaa;margin-top:6px">{page.get('one_liner','')}</div>
                </div>
                """, unsafe_allow_html=True)

    # findings
    if findings:
        st.markdown('<div class="section-header">Findings</div>', unsafe_allow_html=True)
        for f in findings:
            sev = f.get("severity", "GREEN")
            cc = card_class(sev)
            st.markdown(f"""
            <div class="finding-card {cc}">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                    {severity_badge(sev)}
                    <span style="font-weight:700;font-size:15px">{f.get('title','')}</span>
                    <span style="color:#888;font-size:12px;margin-left:auto">{f.get('dimension','').upper()}</span>
                </div>
                <div style="margin-bottom:6px"><span style="color:#888">What it means: </span>{f.get('explanation','')}</div>
                <div style="margin-bottom:6px"><span style="color:#888">Root cause: </span>{f.get('root_cause','')}</div>
                <div><span style="color:#00c853">Fix: </span><strong>{f.get('recommendation','')}</strong></div>
            </div>
            """, unsafe_allow_html=True)

    # two-column: false positives + data gaps
    fp = analysis.get("false_positives", [])
    gaps = analysis.get("data_gaps", [])
    if fp or gaps:
        left, right = st.columns(2)
        if fp:
            with left:
                st.markdown('<div class="section-header">⚠️ False Positives / Noise</div>', unsafe_allow_html=True)
                for item in fp:
                    with st.expander(item.get("flagged_issue", "")[:60]):
                        st.write(item.get("reason", ""))
        if gaps:
            with right:
                st.markdown('<div class="section-header">🕳️ Data Gaps</div>', unsafe_allow_html=True)
                for g in gaps:
                    st.markdown(f"- {g}")

    # top 3 priorities
    priorities = analysis.get("top_3_priorities", [])
    if priorities:
        st.markdown('<div class="section-header">🎯 Top 3 Priorities</div>', unsafe_allow_html=True)
        for i, p in enumerate(priorities, 1):
            st.markdown(f"**{i}.** {p}")


# ── main app ──────────────────────────────────────────────────────────────────

def main():
    st.title("🔍 HAR AI Analyzer")
    st.caption("Upload your HAR analysis JSON files and get Gen-AI powered insights via AWS Bedrock.")

    st.divider()

    # ── sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("📂 Upload Files")
        uploaded = st.file_uploader(
            "Upload one or more analysis JSON files",
            type=["json"],
            accept_multiple_files=True,
            help="Upload light_*.json or heavy_*.json files",
        )

        st.divider()
        analyze_btn = st.button(
            "🚀 Run Analysis",
            type="primary",
            disabled=not uploaded,
            use_container_width=True,
        )

        if uploaded:
            st.divider()
            st.caption(f"**{len(uploaded)} file(s) loaded:**")
            for f in uploaded:
                icon = "🔵" if f.name.startswith("light") else "🟠"
                st.caption(f"{icon} {f.name}")

    # ── main area ─────────────────────────────────────────────────────────────
    if not uploaded:
        st.markdown("""
        ### How to use
        1. Upload your `light_*.json` or `heavy_*.json` analysis files using the sidebar
        2. Click **Run Analysis**

        ### What you'll get
        - Plain-English explanation of what the metrics mean for real users
        - Root cause analysis behind each issue
        - False positive detection (e.g., tracking pixel connections flagged as slow pages)
        - Prioritized, actionable recommendations
        """)
        return

    if not analyze_btn:
        st.info(f"**{len(uploaded)} file(s) ready.** Click **Run Analysis** in the sidebar to proceed.")
        return

    # ── run analysis ──────────────────────────────────────────────────────────
    client = get_client()
    loaded_files = []

    with st.spinner("Loading and preprocessing files..."):
        for uf in uploaded:
            try:
                loaded_files.append(load_uploaded(uf))
            except Exception as e:
                st.error(f"Failed to load {uf.name}: {e}")
                return

    individual_results = []
    progress = st.progress(0, text="Analyzing files...")

    for i, loaded in enumerate(loaded_files):
        progress.progress(
            i / len(loaded_files),
            text=f"Analyzing {loaded['filename']} ({i+1}/{len(loaded_files)})...",
        )
        try:
            context = build_context(loaded)
            prompt = single_file_prompt(context)

            # stream live tokens into a code block, swap for structured report when done
            stream_placeholder = st.empty()
            streamed_text = ""
            result = None

            for event in client.analyze_stream(prompt, SYSTEM_PROMPT):
                if "chunk" in event:
                    streamed_text += event["chunk"]
                    stream_placeholder.code(streamed_text, language="json")
                elif "final_json" in event:
                    result = event["final_json"]

            stream_placeholder.empty()
            individual_results.append(result)

        except Exception as e:
            st.error(f"Analysis failed for {loaded['filename']}: {e}")
            individual_results.append({"file": loaded["filename"], "parse_error": True, "raw_response": str(e)})

    progress.progress(1.0, text="Done!")
    progress.empty()

    # render results
    if len(individual_results) == 1:
        render_single_analysis(individual_results[0])
    else:
        tabs = st.tabs([r.get("file", f"File {i+1}") for i, r in enumerate(individual_results)])
        for tab, result in zip(tabs, individual_results):
            with tab:
                render_single_analysis(result)

    # download
    st.divider()
    st.download_button(
        label="⬇️ Download Full Report (JSON)",
        data=json.dumps({"individual": individual_results}, indent=2),
        file_name="har_analysis_report.json",
        mime="application/json",
    )


if __name__ == "__main__":
    main()
