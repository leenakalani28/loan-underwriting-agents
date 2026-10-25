import streamlit as st

# ================= NORTHBRIDGE PALETTE =================
# Change these values to re-theme the whole app.
NAVY = "#0B1A2B"            # hero, headings, main buttons
NAVY_2 = "#1D2E42"          # tags and chips on navy
APRICOT = "#FFB25B"         # signature colour: logo, selected deal
APRICOT_SOFT = "#FFF1DE"    # soft apricot backgrounds
APRICOT_TEXT = "#FFCB8E"    # apricot text on navy
CANVAS = "#F6F7FB"          # page background
TEXT_MUTED = "#5D6B7A"      # secondary text
TEXT_ON_NAVY = "#B7C0CC"    # body text on navy

# Status colours: kept separate from the brand so pass/fail is never confused
GREEN, GREEN_SOFT = "#1E8A5A", "#E7F6EE"    # pass, approve, done
RED, RED_SOFT = "#D23F3F", "#FDECEC"        # fail, decline
AMBER, AMBER_SOFT = "#B86A12", "#FFF4E0"    # refer, waiting
# =======================================================

FONT = "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');"

CSS = """
html, body, .stApp, .stMarkdown, button, input, textarea, label {
  font-family: 'Plus Jakarta Sans', sans-serif;
}
.stApp { background: var(--canvas); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.stAppDeployButton { display: none; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1120px; }

/* ---------- Hero and deal header (navy band) ---------- */
.nb-hero { background: var(--navy); border-radius: 24px; overflow: hidden; }
.nb-nav { display: flex; justify-content: space-between; align-items: center; padding: 18px 28px; }
.nb-logo { display: flex; align-items: center; gap: 10px; color: #FFFFFF; font-weight: 700; font-size: 18px; }
.nb-crumb { color: var(--text-on-navy); font-weight: 400; font-size: 13px; margin-left: 6px; }
.nb-user { display: flex; align-items: center; gap: 10px; color: var(--text-on-navy); font-size: 13px; }
.nb-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--navy-2); color: var(--apricot);
  display: flex; align-items: center; justify-content: center; font-weight: 700; }
.nb-hero-grid { display: grid; grid-template-columns: 1.05fr 1fr; align-items: center; }
.nb-hero-text { padding: 8px 28px 40px; }
.nb-hero-art { padding: 0 28px 24px 0; }
.nb-tag { display: inline-flex; gap: 6px; align-items: center; font-size: 12px; padding: 5px 12px;
  border-radius: 999px; background: var(--navy-2); color: var(--apricot-text); }
.nb-h1 { color: #FFFFFF; font-size: 36px; font-weight: 700; line-height: 1.15; margin: 14px 0 10px; }
.nb-lead { color: var(--text-on-navy); font-size: 15px; line-height: 1.6; max-width: 480px; }

.nb-deal-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 4px 28px 28px; }
.nb-deal-name { color: #FFFFFF; font-size: 28px; font-weight: 700; line-height: 1.2; }
.nb-deal-meta { color: var(--text-on-navy); font-size: 14px; margin-top: 6px; }
.nb-pill { font-size: 12px; padding: 7px 14px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.nb-pill.progress { background: var(--navy-2); color: var(--apricot-text); }
.nb-pill.waiting { background: var(--amber-soft); color: var(--amber); }
.nb-pill.complete { background: var(--green-soft); color: var(--green); }

/* ---------- Application queue ---------- */
.nb-queue-head { display: flex; justify-content: space-between; align-items: flex-end; margin: 30px 0 14px; }
.nb-section-title { font-size: 21px; font-weight: 700; color: var(--navy); }
.nb-section-sub { font-size: 13px; color: var(--text-muted); }
.nb-count { font-size: 12px; padding: 5px 12px; border-radius: 999px; background: #FFFFFF; color: var(--text-muted); }

/* ---------- Deal cards: the picture, details and button form one card ---------- */
[class*="st-key-card_"], [class*="st-key-cardsel_"] {
  background: #FFFFFF; border-radius: 22px; overflow: hidden; gap: 0.6rem; padding-bottom: 18px;
  box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07);
}
[class*="st-key-cardsel_"] { box-shadow: 0 0 0 2px var(--apricot), 0 8px 22px rgba(11, 26, 43, 0.12); }
[class*="st-key-card_"] .stButton, [class*="st-key-cardsel_"] .stButton { padding: 0 18px; }
.nb-tile-body { padding: 14px 18px 0; }
.nb-borrower { font-weight: 700; color: var(--navy); font-size: 16px; line-height: 1.3; }
.nb-ref { font-size: 12px; color: #8A96A3; }
.nb-amount { font-size: 30px; font-weight: 700; color: var(--navy); margin: 10px 0 4px; }
.nb-meta { font-size: 13px; color: var(--text-muted); line-height: 1.5; min-height: 39px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* ---------- Agent step board ---------- */
.nb-steps { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 24px; }
.nb-step { background: #FFFFFF; border-radius: 20px; padding: 16px; border: 2px solid transparent;
  box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); transition: all 0.3s; }
.nb-step-num { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; background: var(--canvas); color: var(--text-muted); }
.nb-step-name { font-weight: 700; color: var(--navy); font-size: 14px; margin-top: 12px; }
.nb-step-detail { font-size: 12px; color: var(--text-muted); margin-top: 4px; min-height: 34px; line-height: 1.4; }
.nb-step.running { border-color: var(--apricot); }
.nb-step.running .nb-step-num { background: var(--apricot); color: var(--navy); animation: nb-pulse 1.2s infinite; }
.nb-step.done .nb-step-num { background: var(--green-soft); color: var(--green); }
.nb-step.warn .nb-step-num { background: var(--amber-soft); color: var(--amber); }
.nb-step.fail .nb-step-num { background: var(--red-soft); color: var(--red); }
.nb-step.awaiting { border-color: var(--amber); }
.nb-step.awaiting .nb-step-num { background: var(--amber-soft); color: var(--amber); }
.nb-step.skipped { opacity: 0.45; }
@keyframes nb-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 178, 91, 0.6); }
  50% { box-shadow: 0 0 0 8px rgba(255, 178, 91, 0); }
}

/* ---------- Orchestrator activity feed ---------- */
.nb-feed-title { font-size: 17px; font-weight: 700; color: var(--navy); margin: 28px 0 10px; }
.nb-feed { background: #FFFFFF; border-radius: 20px; padding: 6px 22px; box-shadow: 0 2px 12px rgba(11, 26, 43, 0.07); }
.nb-feed-row { display: grid; grid-template-columns: 76px 150px 1fr; gap: 12px; padding: 11px 0;
  border-top: 1px solid #EEF1F5; font-size: 13px; color: var(--navy); }
.nb-feed-row:first-child { border-top: none; }
.nb-feed-time { color: #8A96A3; font-family: ui-monospace, Consolas, monospace; }
.nb-feed-agent { font-weight: 600; }
.nb-feed-agent.orch { color: var(--amber); }
.nb-feed-agent.guard { color: var(--red); }
.nb-feed-agent.officer { color: var(--green); }
.nb-feed-empty { padding: 14px 0; color: var(--text-muted); font-size: 13px; }

/* ---------- Buttons: Monzo-style pills ---------- */
.stButton > button, [data-testid="stPopover"] button {
  border-radius: 999px; padding: 0.55rem 1.4rem; font-weight: 600; min-height: 46px;
  border: 1px solid #D5DBE3; background: #FFFFFF; color: var(--navy);
}
.stButton > button:hover, [data-testid="stPopover"] button:hover { border-color: var(--navy); color: var(--navy); }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: var(--navy); color: #FFFFFF; border: none; }
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  background: var(--navy-2); color: #FFFFFF; }
"""


def inject_theme():
    """Adds the palette and styling to the page. Called once at the top of app.py."""
    variables = f"""
    :root {{
      --navy: {NAVY}; --navy-2: {NAVY_2};
      --apricot: {APRICOT}; --apricot-soft: {APRICOT_SOFT}; --apricot-text: {APRICOT_TEXT};
      --canvas: {CANVAS}; --text-muted: {TEXT_MUTED}; --text-on-navy: {TEXT_ON_NAVY};
      --green: {GREEN}; --green-soft: {GREEN_SOFT};
      --red: {RED}; --red-soft: {RED_SOFT};
      --amber: {AMBER}; --amber-soft: {AMBER_SOFT};
    }}
    """
    st.markdown(f"<style>{FONT}{variables}{CSS}</style>", unsafe_allow_html=True)