"""Screen 4: the recorded decision, timings, audit trail and downloads."""
import html
import json
from datetime import datetime
from pathlib import Path
import streamlit as st

from report import build_markdown

CSS = """
/* ---------- Decision banner ---------- */
.nb-banner { display: flex; gap: 18px; align-items: center; border-radius: 20px; padding: 20px 24px; margin: 24px 0 14px; }
.nb-banner.green { background: var(--green-soft); }
.nb-banner.amber { background: var(--amber-soft); }
.nb-banner.red { background: var(--red-soft); }
.nb-banner-icon { width: 54px; height: 54px; border-radius: 50%; background: #FFFFFF; display: flex;
  align-items: center; justify-content: center; font-size: 24px; font-weight: 700; flex-shrink: 0; }
.nb-banner-title { font-size: 24px; font-weight: 700; }
.nb-banner.green .nb-banner-icon, .nb-banner.green .nb-banner-title { color: var(--green); }
.nb-banner.amber .nb-banner-icon, .nb-banner.amber .nb-banner-title { color: var(--amber); }
.nb-banner.red .nb-banner-icon, .nb-banner.red .nb-banner-title { color: var(--red); }
.nb-banner-sub { font-size: 13px; color: var(--navy); opacity: 0.8; margin-top: 3px; }

/* ---------- Override reason ---------- */
.nb-reason { background: #FFFFFF; border-radius: 16px; padding: 14px 18px; margin-bottom: 4px;
  border-left: 4px solid var(--amber); box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }
.nb-reason-k { font-size: 12px; color: var(--text-muted); font-weight: 600; margin-bottom: 4px; }
.nb-reason-v { font-size: 14px; color: var(--navy); line-height: 1.5; }

/* ---------- Deliverables panel and download buttons ---------- */
.st-key-deliverables_panel { background: #FFFFFF; border-radius: 20px; padding: 20px 22px;
  box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }
.stDownloadButton > button { border-radius: 999px; min-height: 46px; font-weight: 600;
  border: 1px solid #D5DBE3; background: #FFFFFF; color: var(--navy); }
.stDownloadButton > button:hover { border-color: var(--navy); color: var(--navy); }
"""

# Colour and icon for each final decision
OUTCOME = {"Approve": ("green", "✓"), "Refer": ("amber", "↗"), "Decline": ("red", "✕")}
NOT_AGENTS = {"Orchestrator", "Credit officer", "Policy guardrail"}


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def _duration(start: str, end: str) -> str:
    """Time between two 'HH:MM:SS' audit log timestamps, in friendly words."""
    seconds = int((datetime.strptime(end, "%H:%M:%S") - datetime.strptime(start, "%H:%M:%S")).total_seconds())
    seconds = max(seconds, 0)
    return f"{seconds} sec" if seconds < 60 else f"{seconds // 60} min {seconds % 60} sec"


def timings(log: list) -> tuple[str, str]:
    """AI analysis time (first entry until the hand-off) and officer review time (hand-off until decision)."""
    officer_at = next((i for i, entry in enumerate(log) if entry["agent"] == "Credit officer"), None)
    if not officer_at:
        return "—", "—"
    handoff = log[officer_at - 1]["time"]
    return _duration(log[0]["time"], handoff), _duration(handoff, log[officer_at]["time"])


def decision_banner(state: dict):
    d = state["human_decision"]
    tone, icon = OUTCOME[d["final_decision"]]
    when = datetime.strptime(d["decided_at"], "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %H:%M")
    st.html(f"""
<div class="nb-banner {tone}">
  <div class="nb-banner-icon">{icon}</div>
  <div>
    <div class="nb-banner-title">Final decision: {d['final_decision']}</div>
    <div class="nb-banner-sub">AI recommended {d['ai_recommendation']} · {d['action']} by
      {html.escape(d['officer'])} (credit officer) · {when}</div>
  </div>
</div>""")

    if d.get("reason"):
        st.html(f"""
<div class="nb-reason">
  <div class="nb-reason-k">Override reason</div>
  <div class="nb-reason-v">{html.escape(d['reason'])}</div>
</div>""")


def summary_metrics(state: dict):
    """Four headline figures, reusing the metric card style from Screen 3."""
    log = state["audit_log"]
    ai_time, officer_time = timings(log)
    agents_used = len({entry["agent"] for entry in log} - NOT_AGENTS)
    results = state.get("compliance_results")
    if results:
        failed = sum(1 for r in results if r["status"] != "PASS")
        exceptions, tone = f"{failed} of {len(results)}", ("red" if failed else "green")
    else:
        exceptions, tone = "Not checked", "amber"

    cards = [
        ("AI analysis time", ai_time, "green"),
        ("Officer review time", officer_time, ""),
        ("AI agents used", f"{agents_used} of 4", ""),
        ("Policy exceptions", exceptions, tone),
    ]
    st.html('<div class="nb-metrics">' + "".join(
        f'<div class="nb-metric"><div class="nb-metric-k">{label}</div>'
        f'<div class="nb-metric-v {cls}">{value}</div></div>' for label, value, cls in cards) + "</div>")


def download_buttons(state: dict, deal_id: str):
    """The deliverables: the credit report and the machine-readable decision record."""
    stem = Path(deal_id).stem
    report = build_markdown(state, deal_id)
    record = json.dumps({k: v for k, v in state.items() if k not in ("document", "policy")}, indent=2)

    st.download_button(":material/description: Download credit report (.md)", report,
                       file_name=f"{stem}_review.md", mime="text/markdown", use_container_width=True)
    st.download_button(":material/data_object: Download decision record (.json)", record,
                       file_name=f"{stem}_decision.json", mime="application/json", use_container_width=True)