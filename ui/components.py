import html
import re
import streamlit as st

from ui.illustrations import logo_svg, hero_svg, sector_svg, as_img


def hero(officer: str):
    initial = officer[:1].upper() or "?"
    logo = as_img(logo_svg(), "width:34px;height:34px;display:block")
    picture = as_img(hero_svg(), "width:100%;display:block")
    st.html(f"""
<div class="nb-hero">
  <div class="nb-nav">
    <div class="nb-logo">{logo}Northbridge</div>
    <div class="nb-user"><div class="nb-avatar">{initial}</div>{html.escape(officer)} · Credit officer</div>
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