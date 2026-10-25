import json
import time
import uuid
import streamlit as st
from langgraph.types import Command

from graph import build_graph
from report import save_report
from ui.theme import inject_theme
from ui.components import hero, queue_header, deal_card, deal_header, step_board, activity_feed
from ui.deals import load_sample_deals, parse_deal
from ui.progress import new_steps, apply_update
from ui import officer_review, decision

# Pause (in seconds) after each agent update, so the demo is easy to follow.
# Set to 0 for full speed.
DEMO_PACING = 0.6

st.set_page_config(page_title="Northbridge · SME loan assessment", page_icon="🏦",
                   layout="wide", initial_sidebar_state="collapsed")
inject_theme()
officer_review.inject_css()
decision.inject_css()

# ---------- Session memory ----------
# Streamlit re-runs this whole file on every click. st.session_state is the
# small memory that survives those re-runs (like MemorySaver does for the graph).
defaults = {
    "screen": "home",          # which screen to show: home, review, officer or decision
    "selected_id": None,       # which tile is selected on the home screen
    "uploaded_deal": None,     # an uploaded application, if any
    "current_deal": None,      # the deal being reviewed
    "thread_id": None,         # the graph's thread ID for this review
    "steps": None,             # what the five step cards show
    "log": [],                 # the audit log so far
    "pipeline_done": False,    # have the agents finished?
    "final_state": None,       # the completed case folder, after the officer decides
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# The graph (and its MemorySaver) must survive re-runs, so Screen 3 can resume the paused review
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

with open("data/lending_policy.json", encoding="utf-8") as f:
    POLICY = json.load(f)

with st.sidebar:
    st.markdown("### Demo settings")
    officer = st.text_input("Credit officer name", value="Leena")


# ======================= Helpers =======================

def initial_state(document: str) -> dict:
    """A fresh case folder, exactly as in run_pipeline.py."""
    return {
        "document": document, "policy": POLICY,
        "completeness": None, "terms": None, "compliance_results": None, "risk": None,
        "human_decision": None, "next_step": None, "extraction_retries": 0, "audit_log": [],
    }


def graph_config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def start_review(deal: dict):
    st.session_state.current_deal = deal
    # A new thread ID per review, so reviewing the same deal twice starts fresh
    st.session_state.thread_id = f"{deal['id']}-{uuid.uuid4().hex[:8]}"
    st.session_state.steps = new_steps()
    st.session_state.log = []
    st.session_state.pipeline_done = False
    st.session_state.final_state = None
    st.session_state.screen = "review"


def run_agents_live(deal: dict, board, feed):
    """Streams the graph and redraws the step cards and feed after every agent update."""
    steps, log = st.session_state.steps, st.session_state.log
    board.html(step_board(steps))
    feed.html(activity_feed(log))

    for update in st.session_state.graph.stream(initial_state(deal["document"]), graph_config(),
                                                stream_mode="updates"):
        for node, data in update.items():
            if node == "__interrupt__" or not data:
                continue   # the graph has paused for the credit officer
            log.extend(data.get("audit_log", []))
            apply_update(steps, node, data)
        board.html(step_board(steps))
        feed.html(activity_feed(log))
        time.sleep(DEMO_PACING)


# ======================= Screen 1: home =======================

def render_home():
    hero(officer)

    deals = load_sample_deals()
    if st.session_state.uploaded_deal:
        deals.append(st.session_state.uploaded_deal)

    queue_header(len(deals))

    columns = st.columns(3)
    for i, deal in enumerate(deals):
        with columns[i % 3]:
            is_selected = deal["id"] == st.session_state.selected_id
            if deal_card(deal, is_selected):
                st.session_state.selected_id = deal["id"]
                st.rerun()

    st.write("")
    left, right = st.columns(2)

    with left:
        with st.popover(":material/upload: Upload new application", use_container_width=True):
            file = st.file_uploader("Deal document (.txt, same format as the sample deals)", type=["txt"])
            if file:
                deal_id = f"upload_{file.name}"
                current = st.session_state.uploaded_deal
                if current is None or current["id"] != deal_id:
                    st.session_state.uploaded_deal = parse_deal(deal_id, file.read().decode("utf-8"))
                    st.session_state.selected_id = deal_id
                    st.rerun()

    with right:
        selected = next((d for d in deals if d["id"] == st.session_state.selected_id), None)
        if st.button(":material/play_arrow: Start AI-assisted review", type="primary",
                     use_container_width=True, key="start_review"):
            if selected is None:
                st.warning("Select an application first.")
            else:
                start_review(selected)
                st.rerun()


# ======================= Screen 2: agents at work =======================

def render_review():
    deal = st.session_state.current_deal
    done = st.session_state.pipeline_done

    if done:
        deal_header(officer, deal, "Awaiting credit officer decision", "waiting")
    else:
        deal_header(officer, deal, "AI review in progress", "progress")

    board = st.empty()
    st.html('<div class="nb-feed-title">Orchestrator activity</div>')
    feed = st.empty()

    if not done:
        run_agents_live(deal, board, feed)
        st.session_state.pipeline_done = True
        st.rerun()   # redraw with the "awaiting decision" status and the buttons

    board.html(step_board(st.session_state.steps))
    feed.html(activity_feed(st.session_state.log))

    st.write("")
    left, right = st.columns(2)
    with left:
        if st.button(":material/arrow_back: Back to queue", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()
    with right:
        if st.button("Review AI findings :material/arrow_forward:", type="primary", use_container_width=True):
            st.session_state.screen = "officer"
            st.rerun()


# ======================= Screen 3: credit officer review =======================

def render_officer():
    deal = st.session_state.current_deal

    # Open the paused review from MemorySaver, exactly as run_pipeline.py did
    snapshot = st.session_state.graph.get_state(graph_config())
    if not snapshot.next:
        # Already decided (e.g. the page was refreshed): go to the decision screen
        st.session_state.screen = "decision"
        st.rerun()

    pack = snapshot.tasks[0].interrupts[0].value   # the review pack from human_review_node
    state = snapshot.values                       # the full case folder

    deal_header(officer, deal, "Awaiting credit officer decision", "waiting")
    officer_review.metric_row(state, pack)

    left, right = st.columns([3, 2], gap="medium")

    # ---- The credit paper ----
    with left:
        officer_review.exceptions_panel(state)
        officer_review.assessment_panel(state)
        officer_review.detail_expanders(state)

    # ---- The decision ----
    with right:
        recommendation = pack["ai_recommendation"]
        thread = st.session_state.thread_id   # unique widget keys per review

        with st.container(key="decision_panel"):
            st.html(f'<div class="nb-panel-title">Credit officer decision</div>'
                    f'<div class="nb-panel-sub">AI recommendation: <b>{recommendation}</b></div>')

            choice = st.radio("Your decision", [f"Accept AI recommendation ({recommendation})", "Override"],
                              key=f"choice_{thread}", label_visibility="collapsed")
            overriding = choice == "Override"

            final_decision, reason = recommendation, ""
            if overriding:
                options = [o for o in ["Approve", "Refer", "Decline"] if o != recommendation]
                final_decision = st.selectbox("Your decision", options, key=f"final_{thread}")
                reason = st.text_area("Reason for override (required)", key=f"reason_{thread}",
                                      placeholder="e.g. Strong sponsor relationship; refer to committee "
                                                  "to explore restructuring with additional security")

            if st.button(":material/gavel: Record decision", type="primary",
                         use_container_width=True, key="record_decision"):
                if overriding and not reason.strip():
                    st.error("Please give a reason for the override.")
                else:
                    officer_decision = {
                        "action": "overridden" if overriding else "accepted",
                        "final_decision": final_decision,
                        "reason": reason.strip(),
                        "officer": officer,
                    }
                    # Resume the paused graph with the officer's decision
                    final_state = st.session_state.graph.invoke(Command(resume=officer_decision), graph_config())
                    save_report(final_state, deal["id"])
                    st.session_state.final_state = final_state
                    st.session_state.screen = "decision"
                    st.rerun()

            st.html('<div class="nb-panel-note">Your decision, the AI recommendation and any override '
                    'reason are recorded in the audit trail.</div>')

        st.write("")
        if st.button(":material/arrow_back: Agent activity", use_container_width=True):
            st.session_state.screen = "review"
            st.rerun()


# ======================= Screen 4: decision recorded =======================

def render_decision():
    deal = st.session_state.current_deal
    state = st.session_state.final_state
    if state is None:
        # e.g. a page refresh lost the session: read the finished review back from the graph
        state = st.session_state.graph.get_state(graph_config()).values

    deal_header(officer, deal, "Review complete", "complete")
    decision.decision_banner(state)
    decision.summary_metrics(state)

    left, right = st.columns([3, 2], gap="medium")

    # ---- Full audit trail ----
    with left:
        st.html('<div class="nb-feed-title" style="margin-top:6px">Full audit trail</div>')
        st.html(activity_feed(state["audit_log"]))

    # ---- Deliverables ----
    with right:
        st.html('<div class="nb-feed-title" style="margin-top:6px">Deliverables</div>')
        with st.container(key="deliverables_panel"):
            st.html('<div class="nb-panel-sub">The credit report and decision record have also been '
                    'saved to the <b>outputs</b> folder.</div>')
            decision.download_buttons(state, deal["id"])

        st.write("")
        if st.button(":material/refresh: Review another application", type="primary",
                     use_container_width=True, key="review_another"):
            st.session_state.selected_id = None
            st.session_state.screen = "home"
            st.rerun()


# ======================= Which screen to show =======================

screens = {"home": render_home, "review": render_review,
           "officer": render_officer, "decision": render_decision}
screens[st.session_state.screen]()