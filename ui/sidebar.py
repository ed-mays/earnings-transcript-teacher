import streamlit as st

from db.repositories import LearningRepository
from ui.data_loaders import load_transcripts


def _format_call_label(ticker: str, fiscal_quarter: str, company_name: str | None, call_date) -> str:
    """Format a transcript selector label from available call metadata."""
    parts = [ticker]
    if company_name:
        parts.append(company_name)
    if fiscal_quarter:
        parts.append(fiscal_quarter)
    if call_date:
        try:
            parts.append(call_date.strftime("%b %-d, %Y"))
        except AttributeError:
            parts.append(str(call_date))
    return " — ".join(parts)


def render_sidebar(conn_str: str, on_ticker_change) -> tuple[str | None, str]:
    """Render the settings sidebar and return (selected_ticker, chat_mode).

    Returns (None, chat_mode) when no transcripts are available or the Library view is active.
    """
    if "show_library" not in st.session_state:
        st.session_state.show_library = False

    with st.sidebar:
        available_calls = load_transcripts(conn_str)

        if not available_calls:
            st.info("No transcripts yet. See the main panel for setup instructions.")
            return None, "Feynman Loop"

        st.markdown("### 📄 Transcript")

        if st.button("📚 Library", use_container_width=True, help="Browse all transcripts"):
            st.session_state.show_library = True
            st.rerun()

        tickers = [c[0] for c in available_calls]
        label_by_ticker = {
            c[0]: _format_call_label(c[0], c[1], c[2], c[3])
            for c in available_calls
        }

        selected_ticker = st.selectbox(
            "Select Transcript",
            tickers,
            format_func=lambda t: label_by_ticker.get(t, t),
            on_change=on_ticker_change,
        )

        chat_mode = st.radio(
            "Mode",
            ["Feynman Loop", "Ask the Transcript"],
            key="chat_mode",
            help=(
                "Feynman Loop guides you through teaching the material to test your understanding. "
                "Ask the Transcript lets you explore the transcript freely."
            ),
        )

        st.markdown("---")
        if st.button("🔄 Reload data", help="Clear cached data and reload from the database. Use this after re-ingesting a transcript."):
            st.cache_data.clear()
            st.rerun()

        learning_repo = LearningRepository(conn_str)
        stats = learning_repo.get_learning_stats()
        if stats["total_sessions"] > 0:
            st.markdown("---")
            with st.expander("📊 My Learning", expanded=False):
                st.markdown(
                    f"**{stats['total_sessions']}** sessions · "
                    f"**{stats['completed_sessions']}** completed · "
                    f"**{stats['tickers_studied']}** tickers"
                )
                ticker_counts = learning_repo.get_ticker_session_counts()
                for ticker, total, completed in ticker_counts[:5]:
                    st.markdown(f"- **{ticker}**: {total} sessions ({completed} complete)")

    return selected_ticker, chat_mode
