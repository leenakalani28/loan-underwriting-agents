"""Screen 3: the credit officer's review pack. Styles and display pieces in one place."""
import html
import streamlit as st

from report import TERM_LABELS, format_value

CSS = """
/* ---------- Key metrics ---------- */
.nb-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 24px 0 18px; }
.nb-metric { background: #FFFFFF; border-radius: 18px; padding: 14px 16px; box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }
.nb-metric-k { font-size: 12px; color: var(--text-muted); }
.nb-metric-v { font-size: 24px; font-weight: 700; color: var(--navy); margin-top: 4px; }
.nb-metric-v.green { color: var(--green); }
.nb-metric-v.amber { color: var(--amber); }
.nb-metric-v.red { color: var(--red); }

/* ---------- Panels ---------- */
.nb-panel { background: #FFFFFF; border-radius: 20px; padding: 18px 22px; margin-bottom: 14px;
  box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }
.nb-panel-title { font-size: 16px; font-weight: 700; color: var(--navy); margin-bottom: 10px; }
.nb-panel-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 4px; }
.nb-panel-note { font-size: 12px; color: var(--text-muted); line-height: 1.5; }

/* ---------- Policy exceptions ---------- */
.nb-exc { display: grid; grid-template-columns: 28px 1fr auto; gap: 10px; align-items: start; padding: 10px 0; }
.nb-exc + .nb-exc { border-top: 1px solid #EEF1F5; }
.nb-exc-icon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 12px; font-weight: 700; }
.nb-exc-icon.red { background: var(--red-soft); color: var(--red); }
.nb-exc-icon.amber { background: var(--amber-soft); color: var(--amber); }
.nb-exc-text { font-size: 13px; color: var(--navy); font-weight: 600; line-height: 1.4; }
.nb-exc-actual { font-size: 12px; color: var(--text-muted); font-weight: 400; margin-top: 2px; }
.nb-sev { font-size: 11px; padding: 3px 10px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.nb-sev.high { background: var(--red-soft); color: var(--red); }
.nb-sev.medium { background: var(--amber-soft); color: var(--amber); }
.nb-ok { background: var(--green-soft); color: var(--green); border-radius: 12px; padding: 12px 14px;
  font-size: 13px; font-weight: 600; }
.nb-warn { background: var(--amber-soft); color: var(--amber); border-radius: 12px; padding: 12px 14px;
  font-size: 13px; font-weight: 600; }

/* ---------- AI assessment ---------- */
.nb-summary { font-size: 14px; line-height: 1.65; color: var(--navy); }
.nb-two { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 14px; }
.nb-list-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.nb-list-title.red { color: var(--red); }
.nb-list-title.green { color: var(--green); }
.nb-list { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.55; color: var(--navy); }
.nb-list li { margin-bottom: 6px; }

/* ---------- Detail tables ---------- */
.nb-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.nb-table th, .nb-table td { padding: 8px 6px; border-top: 1px solid #EEF1F5; text-align: left;
  vertical-align: top; color: var(--navy); }
.nb-table th { color: var(--text-muted); font-weight: 600; border-top: none; }
.nb-status { font-size: 11px; padding: 2px 9px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.nb-status.PASS { background: var(--green-soft); color: var(--green); }
.nb-status.FAIL { background: var(--red-soft); color: var(--red); }
.nb-status.UNABLE_TO_VERIFY { background: var(--amber-soft); color: var(--amber); }
[data-testid="stExpander"] details { background: #FFFFFF; border-radius: 16px; border: none;
  box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }

/* ---------- Decision panel ---------- */
.st-key-decision_panel { background: #FFFFFF; border-radius: 20px; padding: 20px 22px;
  box-shadow: 0 0 0 2px var(--amber-soft), 0 2px 12px rgba(11, 26, 43, 0.07); }
"""

# Which colour each outcome or rating gets
TONE = {"Approve": "green", "Refer": "amber", "Decline": "red",
        "Low": "green", "Medium": "amber", "High": "red"}
STATUS_LABEL = {"PASS": "Pass", "FAIL": "Fail", "UNABLE_TO_VERIFY": "Unverified"}


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def _metric(label: str, value: str, tone: str = "") -> str:
    return (f'<div class="nb-metric"><div class="nb-metric-k">{label}</div>'
            f'<div class="nb-metric-v {tone}">{html.escape(value)}</div></div>')


def metric_row(state: dict, pack: dict):
    """The four headline figures across the top of the review."""
    recommendation = pack["ai_recommendation"]
    rating = pack["risk_rating"]
    results = state.get("compliance_results")
    terms = state.get("terms") or {}

    cards = [
        _metric("AI recommendation", recommendation, TONE.get(recommendation, "")),
        _metric("Risk rating", rating, TONE.get(rating, "")),
    ]

    if results:
        passed = sum(1 for r in results if r["status"] == "PASS")
        cards.append(_metric("Policy rules", f"{passed} of {len(results)} pass",
                             "green" if passed == len(results) else "red"))
        ltv = terms.get("ltv_percent")
        ltv_rule = next((r for r in results if r["rule_id"] == "R1"), None)
        ltv_tone = "red" if ltv_rule and ltv_rule["status"] == "FAIL" else ""
        cards.append(_metric("Loan-to-value", f"{ltv:g}%" if ltv is not None else "—", ltv_tone))
    else:
        missing = len((state.get("completeness") or {}).get("missing_sections", []))
        cards.append(_metric("Policy rules", "Not checked"))
        cards.append(_metric("Missing sections", str(missing), "amber"))

    st.html(f'<div class="nb-metrics">{"".join(cards)}</div>')


def exceptions_panel(state: dict):
    """Policy exceptions first: what the credit officer most needs to see."""
    completeness = state.get("completeness") or {}
    results = state.get("compliance_results")

    if not completeness.get("is_complete", True):
        missing = ", ".join(completeness.get("missing_sections", []))
        body = (f'<div class="nb-warn">Application incomplete. Missing sections: {html.escape(missing)}. '
                'The AI agents did not assess this application.</div>')
        title = "Application status"
    else:
        exceptions = [r for r in results if r["status"] != "PASS"]
        title = f"Policy exceptions ({len(exceptions)})"
        if not exceptions:
            body = f'<div class="nb-ok">✓ All {len(results)} policy rules passed</div>'
        else:
            rows = []
            for r in exceptions:
                icon, tone = ("✕", "red") if r["status"] == "FAIL" else ("!", "amber")
                rows.append(f"""
<div class="nb-exc">
  <div class="nb-exc-icon {tone}">{icon}</div>
  <div class="nb-exc-text">{r['rule_id']} · {html.escape(r['description'])}
    <div class="nb-exc-actual">Actual: {html.escape(r['actual_value'])}</div></div>
  <span class="nb-sev {r['severity']}">{r['severity'].capitalize()}</span>
</div>""")
            body = "".join(rows)

    st.html(f'<div class="nb-panel"><div class="nb-panel-title">{title}</div>{body}</div>')


def assessment_panel(state: dict):
    """The AI's summary, key risks and mitigants."""
    risk = state.get("risk")
    if not risk:
        st.html('<div class="nb-panel"><div class="nb-panel-title">AI assessment</div>'
                '<div class="nb-panel-sub">Not assessed: the application was incomplete.</div></div>')
        return

    risks = "".join(f"<li>{html.escape(item)}</li>" for item in risk["key_risks"]) or "<li>None identified</li>"
    mitigants = "".join(f"<li>{html.escape(item)}</li>" for item in risk["mitigants"]) or "<li>None identified</li>"
    st.html(f"""
<div class="nb-panel">
  <div class="nb-panel-title">AI assessment</div>
  <div class="nb-summary">{html.escape(risk['summary'])}</div>
  <div class="nb-two">
    <div><div class="nb-list-title red">Key risks</div><ul class="nb-list">{risks}</ul></div>
    <div><div class="nb-list-title green">Mitigants</div><ul class="nb-list">{mitigants}</ul></div>
  </div>
</div>""")


def detail_expanders(state: dict):
    """The full rule results and extracted terms, available but out of the way."""
    results = state.get("compliance_results")
    terms = state.get("terms")

    if results:
        with st.expander(f"All {len(results)} policy rules"):
            rows = "".join(f"""
<tr><td>{r['rule_id']}</td><td>{html.escape(r['description'])}</td>
<td><span class="nb-status {r['status']}">{STATUS_LABEL[r['status']]}</span></td>
<td>{html.escape(r['actual_value'])}</td></tr>""" for r in results)
            st.html(f'<table class="nb-table"><tr><th>Rule</th><th>Requirement</th>'
                    f'<th>Result</th><th>Actual</th></tr>{rows}</table>')

    if terms:
        with st.expander("Extracted loan terms"):
            rows = "".join(f"<tr><td>{label}</td><td>{html.escape(format_value(key, terms.get(key)))}</td></tr>"
                           for key, label in TERM_LABELS.items())
            st.html(f'<table class="nb-table"><tr><th>Term</th><th>Value</th></tr>{rows}</table>')