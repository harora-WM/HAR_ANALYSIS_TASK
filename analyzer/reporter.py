import json
from pathlib import Path

# ANSI colours for terminal output
RED = "\033[91m"
AMBER = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

SEVERITY_COLOUR = {"RED": RED, "AMBER": AMBER, "GREEN": GREEN}


def print_single_report(analysis: dict) -> None:
    """Print a single-file analysis report to stdout."""
    _header(f"  {analysis.get('file', 'Unknown')}  |  {analysis.get('classification', '').upper()}  ")

    # Executive summary
    _section("Executive Summary")
    print(f"  {analysis.get('executive_summary', '')}\n")

    # Pages
    pages = analysis.get("pages_analyzed", [])
    if pages:
        _section("Pages Analyzed")
        for p in pages:
            sev = p.get("verdict", "GREEN")
            col = SEVERITY_COLOUR.get(sev, "")
            print(f"  {col}[{sev}]{RESET}  {p.get('url', 'unknown')}  —  {p.get('total_load_ms', 0)}ms")
            print(f"         {DIM}{p.get('one_liner', '')}{RESET}")
        print()

    # Findings
    findings = analysis.get("findings", [])
    if findings:
        _section("Findings")
        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "GREEN")
            col = SEVERITY_COLOUR.get(sev, "")
            print(f"  {BOLD}{i}. {col}[{sev}]{RESET}{BOLD} {f.get('title', '')}{RESET}")
            print(f"     {DIM}Dimension:{RESET} {f.get('dimension', '')}")
            print(f"     {DIM}What it means:{RESET} {f.get('explanation', '')}")
            print(f"     {DIM}Root cause:{RESET} {f.get('root_cause', '')}")
            print(f"     {DIM}Fix:{RESET} {GREEN}{f.get('recommendation', '')}{RESET}")
            print()

    # False positives
    fp = analysis.get("false_positives", [])
    if fp:
        _section("False Positives / Noise")
        for item in fp:
            print(f"  {DIM}⚠ Flagged:{RESET}  {item.get('flagged_issue', '')}")
            print(f"    {DIM}Why noise:{RESET} {item.get('reason', '')}")
        print()

    # Data gaps
    gaps = analysis.get("data_gaps", [])
    if gaps:
        _section("Data Gaps")
        for g in gaps:
            print(f"  {DIM}• {g}{RESET}")
        print()

    # Top 3 priorities
    priorities = analysis.get("top_3_priorities", [])
    if priorities:
        _section("Top 3 Priorities")
        for i, p in enumerate(priorities, 1):
            print(f"  {BOLD}{i}.{RESET} {p}")
        print()

    print("─" * 70 + "\n")



def save_report(analysis: dict, output_path: str) -> None:
    """Save analysis result as a JSON file."""
    Path(output_path).write_text(json.dumps(analysis, indent=2))
    print(f"{GREEN}Report saved to: {output_path}{RESET}")


# ── helpers ───────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    width = max(len(title) + 4, 70)
    print(f"\n{CYAN}{'═' * width}{RESET}")
    print(f"{CYAN}{BOLD}{title.center(width)}{RESET}")
    print(f"{CYAN}{'═' * width}{RESET}\n")


def _section(title: str) -> None:
    print(f"{BOLD}{CYAN}{title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
