import html
import re
import streamlit as st

from ui.illustrations import logo_svg, hero_svg, sector_svg, as_img


def _user(officer: str) -> str:
    initial = officer[:1].upper() or "?"
    return f'<div class="nb-user"><div class="nb-avatar">{initial}</div>{html.escape(officer)} · Credit officer</div>'


# ======================= Screen 1: home =======================

def hero(officer: str):
    logo = as_img(logo_svg(), "width:34px;height:34px;display:block")
    picture = as_img(hero_svg(), "width:100%;display:block")
    st.html(f"""
<div class="nb-hero">
  <div class="nb-nav">
    <div class="nb-logo">{logo}Northbridge</div>
    {_user(officer)}
  </div>
  <div class="nb-hero-grid">
    <div class="nb-hero-text">
      <span class="nb-tag">✦ AI-assisted underwriting</span>
      <div class="nb-h1">SME commercial loan assessment</div>
      <div class="nb-lead">Specialist AI agents check completeness, extract terms, test lending policy
        and assess risk. The credit officer makes the final decision.</div>
    </div>
    <div class="nb-hero-art">{picture}</div>
  </div>
</div>""")


def queue_header(count: int):
    st.html(f"""
<div class="nb-queue-head">
  <div>
    <div class="nb-section-title">Applications awaiting assessment</div>
    <div class="nb-section-sub">Select an application to start the AI-assisted review</div>
  </div>
  <span class="nb-count">{count} in queue</span>
</div>""")


def deal_card(deal: dict, selected: bool) -> bool:
    """Draws one application card (picture, details and Select button). Returns True if clicked."""
    safe_id = re.sub(r"\W", "_", deal["id"])
    # The key becomes a CSS class, which is how theme.py styles the container as one card
    key = f"cardsel_{safe_id}" if selected else f"card_{safe_id}"
    picture = as_img(sector_svg(deal["sector"], selected),
                     "width:100%;height:110px;object-fit:cover;display:block")

    with st.container(key=key):
        st.html(f"""
{picture}
<div class="nb-tile-body">
  <div class="nb-borrower">{html.escape(deal['borrower'])}</div>
  <div class="nb-ref">{html.escape(deal['reference'])}</div>
  <div class="nb-amount">{html.escape(deal['amount'])}</div>
  <div class="nb-meta">{html.escape(deal['sector'])} · {html.escape(deal['purpose'])}</div>
</div>""")
        return st.button(
            "Selected" if selected else "Select",
            key=f"btn_{safe_id}",
            type="primary" if selected else "secondary",
            use_container_width=True,
        )


# ======================= Screens 2-4: deal pages =======================

def deal_header(officer: str, deal: dict, status_label: str, status_kind: str):
    """The navy band at the top of every deal screen. status_kind: progress, waiting or complete."""
    logo = as_img(logo_svg(), "width:30px;height:30px;display:block")
    st.html(f"""
<div class="nb-hero">
  <div class="nb-nav">
    <div class="nb-logo">{logo}Northbridge<span class="nb-crumb">/ Applications / {html.escape(deal['reference'])}</span></div>
    {_user(officer)}
  </div>
  <div class="nb-deal-head">
    <div>
      <div class="nb-deal-name">{html.escape(deal['borrower'])}</div>
      <div class="nb-deal-meta">{html.escape(deal['amount'])} · {html.escape(deal['sector'])} · {html.escape(deal['purpose'])}</div>
    </div>
    <span class="nb-pill {status_kind}">{html.escape(status_label)}</span>
  </div>
</div>""")


STEP_SYMBOLS = {"done": "✓", "warn": "!", "fail": "✕", "skipped": "–", "awaiting": "…"}


def step_board(steps: dict) -> str:
    """Returns the HTML for the five agent step cards."""
    cards = []
    for number, step in enumerate(steps.values(), start=1):
        symbol = STEP_SYMBOLS.get(step["status"], str(number))
        cards.append(f"""
<div class="nb-step {step['status']}">
  <div class="nb-step-num">{symbol}</div>
  <div class="nb-step-name">{step['label']}</div>
  <div class="nb-step-detail">{html.escape(step['detail'])}</div>
</div>""")
    return f'<div class="nb-steps">{"".join(cards)}</div>'


AGENT_STYLES = {"Orchestrator": "orch", "Policy guardrail": "guard", "Credit officer": "officer"}


def activity_feed(log: list) -> str:
    """Returns the HTML for the orchestrator activity feed (the audit log)."""
    if not log:
        rows = '<div class="nb-feed-empty">Starting the review…</div>'
    else:
        rows = "".join(f"""
<div class="nb-feed-row">
  <span class="nb-feed-time">{entry['time']}</span>
  <span class="nb-feed-agent {AGENT_STYLES.get(entry['agent'], '')}">{html.escape(entry['agent'])}</span>
  <span>{html.escape(entry['message'])}</span>
</div>""" for entry in log)
    return f'<div class="nb-feed">{rows}</div>'