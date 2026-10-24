import streamlit as st

from ui.theme import inject_theme
from ui.components import hero, queue_header, deal_card
from ui.deals import load_sample_deals, parse_deal

st.set_page_config(page_title="Northbridge · SME loan assessment", page_icon="🏦", layout="wide")
inject_theme()

# ---------- Session memory ----------
# Streamlit re-runs this whole file on every click. st.session_state is the
# small memory that survives those re-runs (like MemorySaver does for the graph).
for key, value in {"screen": "home", "selected_id": None, "uploaded_deal": None, "current_deal": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.sidebar:
    st.markdown("### Demo settings")
    officer = st.text_input("Credit officer name", value="Leena")


def render_home():
    hero(officer)

    deals = load_sample_deals()
    if st.session_state.uploaded_deal:
        deals.append(st.session_state.uploaded_deal)

    queue_header(len(deals))

    # ---- Application cards ----
    columns = st.columns(3)
    for i, deal in enumerate(deals):
        with columns[i % 3]:
            is_selected = deal["id"] == st.session_state.selected_id
            if deal_card(deal, is_selected):
                st.session_state.selected_id = deal["id"]
                st.rerun()

    st.write("")
    left, right = st.columns(2)

    # ---- Upload a new application ----
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

    # ---- Start the review ----
    with right:
        selected = next((d for d in deals if d["id"] == st.session_state.selected_id), None)
        if st.button(":material/play_arrow: Start AI-assisted review", type="primary",
                     use_container_width=True, key="start_review"):
            if selected is None:
                st.warning("Select an application first.")
            else:
                st.session_state.current_deal = selected
                st.session_state.screen = "review"
                st.rerun()


def render_review():
    # Placeholder: Screen 2 (live agents) is built in the next step
    deal = st.session_state.current_deal
    st.success(f"Ready to review {deal['borrower']} ({deal['reference']}). Screen 2 comes next.")
    if st.button("← Back to queue"):
        st.session_state.screen = "home"
        st.rerun()


# ---------- Which screen to show ----------
if st.session_state.screen == "home":
    render_home()
else:
    render_review()