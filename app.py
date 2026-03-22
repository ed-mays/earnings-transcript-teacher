import logging
import os

import streamlit as st

from db.repositories import SchemaRepository
from ui.data_loaders import load_analyst_view, load_metadata, load_qa_evasion, load_speakers, load_strategic_shifts, load_transcript_spans
from ui.feynman import render_chat_interface
from ui.metadata_panel import render_metadata_panel
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

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

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


selected_ticker, chat_mode = render_sidebar(CONN_STR, on_ticker_change=_reset_chat)
st.session_state.active_ticker = selected_ticker

# ------------- Load Data -------------

themes, takeaways, synthesis, keywords, industry_terms, financial_terms = load_metadata(
    CONN_STR, st.session_state.active_ticker
)
evasion, misconceptions = load_analyst_view(CONN_STR, st.session_state.active_ticker)
speakers = load_speakers(CONN_STR, st.session_state.active_ticker)
spans = load_transcript_spans(CONN_STR, st.session_state.active_ticker)
strategic_shifts = load_strategic_shifts(CONN_STR, st.session_state.active_ticker)
qa_evasion = load_qa_evasion(CONN_STR, st.session_state.active_ticker)

# ------------- Layout -------------

left_col, right_col = st.columns([5, 5])

jargon: dict[str, str] = {
    term.lower(): definition
    for term, definition, _ in (*financial_terms, *industry_terms)
    if definition
}

with left_col:
    render_transcript_browser(spans, jargon=jargon)
    st.divider()
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
    )

with right_col:
    render_chat_interface(
        conn_str=CONN_STR,
        ticker=st.session_state.active_ticker,
        chat_mode=chat_mode,
        themes=themes,
        takeaways=takeaways,
        financial_terms=financial_terms,
        industry_terms=industry_terms,
        on_reset=_reset_chat,
    )
