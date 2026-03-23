import logging
import os

import streamlit as st

from db.repositories import LearningRepository, SchemaRepository
from ui.data_loaders import load_analyst_view, load_call_summary, load_metadata, load_qa_evasion, load_speaker_dynamics, load_speakers, load_strategic_shifts, load_transcript_spans
from ui.feynman import render_chat_interface
from ui.library import render_library
from ui.metadata_panel import build_feynman_suggestions, render_metadata_panel
from ui.sidebar import render_sidebar
from ui.transcript_browser import render_transcript_browser

logger = logging.getLogger(__name__)

# ------------- Configuration -------------

st.set_page_config(
    page_title="Earnings Transcript Teacher",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CONN_STR = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")

# ------------- State Initialisation -------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None

if "feynman_stage" not in st.session_state:
    st.session_state.feynman_stage = 1

if "feynman_topic" not in st.session_state:
    st.session_state.feynman_topic = ""

if "feynman_session_id" not in st.session_state:
    st.session_state.feynman_session_id = ""

if "feynman_is_synthesis" not in st.session_state:
    st.session_state.feynman_is_synthesis = False

if "feynman_synthesis_notes" not in st.session_state:
    st.session_state.feynman_synthesis_notes = []

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

if "transcript_search_term" not in st.session_state:
    st.session_state.transcript_search_term = ""

# ------------- Schema Health Check -------------

def _auto_migrate() -> bool:
    """Check that the database schema is up to date."""
    try:
        schema_repo = SchemaRepository(CONN_STR)
        is_ok, error_msg = schema_repo.check_health()
        if not is_ok:
            st.error(f"⚠️ {error_msg}")
            return False
        return True
    except Exception as e:
        st.warning(f"Schema health check failed: {e}")
        return False


if "schema_checked" not in st.session_state:
    st.session_state["schema_checked"] = _auto_migrate()

# ------------- Sidebar -------------

def _reset_chat() -> None:
    """Clear the chat history and Feynman state, saving in-progress session first."""
    if st.session_state.get("feynman_topic") and st.session_state.get("feynman_session_id"):
        from ui.feynman import _save_feynman_session
        _save_feynman_session(CONN_STR, st.session_state.active_ticker or "", completed=False)
    st.session_state.messages = []
    st.session_state.feynman_stage = 1
    st.session_state.feynman_topic = ""
    st.session_state.feynman_session_id = ""
    st.session_state.feynman_is_synthesis = False
    st.session_state.feynman_synthesis_notes = []


selected_ticker, chat_mode = render_sidebar(CONN_STR, on_ticker_change=_reset_chat)
st.session_state.active_ticker = selected_ticker

# ------------- Library / Zero State -------------

def _select_ticker_from_library(ticker: str) -> None:
    """Navigate from the library view to studying a specific transcript."""
    st.session_state.active_ticker = ticker
    st.session_state.show_library = False
    _reset_chat()


if selected_ticker is None or st.session_state.get("show_library"):
    render_library(CONN_STR, on_select=_select_ticker_from_library)
    st.stop()

# ------------- Load Data -------------

themes, takeaways, synthesis, keywords, industry_terms, financial_terms = load_metadata(
    CONN_STR, st.session_state.active_ticker
)
evasion, misconceptions = load_analyst_view(CONN_STR, st.session_state.active_ticker)
speakers = load_speakers(CONN_STR, st.session_state.active_ticker)
spans = load_transcript_spans(CONN_STR, st.session_state.active_ticker)
strategic_shifts = load_strategic_shifts(CONN_STR, st.session_state.active_ticker)
qa_evasion = load_qa_evasion(CONN_STR, st.session_state.active_ticker)
call_summary = load_call_summary(CONN_STR, st.session_state.active_ticker)
speaker_dynamics = load_speaker_dynamics(CONN_STR, st.session_state.active_ticker)
suggested_topics = build_feynman_suggestions(strategic_shifts, evasion, qa_evasion)

# ------------- Layout -------------

left_col, right_col = st.columns([5, 5])

jargon: dict[str, str] = {
    term.lower(): definition
    for term, definition, _ in (*financial_terms, *industry_terms)
    if definition
}

with left_col:
    # Start prompt (#66): shown once per transcript per session, adapts to learning history.
    start_prompt_key = f"start_prompt_dismissed_{selected_ticker}"
    if not st.session_state.get(start_prompt_key):
        learning_repo = LearningRepository(CONN_STR)
        sessions = learning_repo.get_sessions_for_ticker(selected_ticker)
        completed_sessions = [s for s in sessions if s["completed"]]
        if not completed_sessions:
            suggestion = "New here? **Start with Step 1 · Overview** to get oriented, then read the transcript."
        else:
            suggestion = (
                f"Welcome back — you have **{len(completed_sessions)} completed session(s)** on this call. "
                "Pick up where you left off, or try the **Feynman Loop** to test your retention."
            )
        prompt_col, dismiss_col = st.columns([9, 1])
        with prompt_col:
            st.success(f"💡 {suggestion}")
        with dismiss_col:
            if st.button("✕", key=f"dismiss_start_prompt_{selected_ticker}", help="Dismiss"):
                st.session_state[start_prompt_key] = True
                st.rerun()

    render_metadata_panel(
        conn_str=CONN_STR,
        ticker=st.session_state.active_ticker,
        themes=themes,
        takeaways=takeaways,
        synthesis=synthesis,
        keywords=keywords,
        industry_terms=industry_terms,
        financial_terms=financial_terms,
        speakers=speakers,
        evasion=evasion,
        misconceptions=misconceptions,
        strategic_shifts=strategic_shifts,
        qa_evasion=qa_evasion,
        call_summary=call_summary,
        speaker_dynamics=speaker_dynamics,
    )
    st.divider()

    # Jargon discovery banner (#67): show once per ticker until dismissed.
    jargon_count = len(financial_terms) + len(industry_terms)
    banner_dismissed_key = f"jargon_banner_dismissed_{selected_ticker}"
    if selected_ticker and jargon_count > 0 and not st.session_state.get(banner_dismissed_key):
        banner_col, dismiss_col = st.columns([9, 1])
        with banner_col:
            st.info(
                f"This transcript contains **{jargon_count} industry & financial terms** worth knowing — "
                "review them in **Step 6 · Language Lab** above before reading."
            )
        with dismiss_col:
            if st.button("✕", key=f"dismiss_jargon_banner_{selected_ticker}", help="Dismiss"):
                st.session_state[banner_dismissed_key] = True
                st.rerun()

    render_transcript_browser(
        spans,
        jargon=jargon,
        initial_search=st.session_state.get("transcript_search_term", ""),
    )

with right_col:
    render_chat_interface(
        conn_str=CONN_STR,
        ticker=st.session_state.active_ticker,
        chat_mode=chat_mode,
        suggested_topics=suggested_topics,
        financial_terms=financial_terms,
        industry_terms=industry_terms,
        on_reset=_reset_chat,
    )
