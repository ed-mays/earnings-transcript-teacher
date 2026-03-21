import streamlit as st

from db.repositories import LearningRepository
from ui.data_loaders import load_transcripts


def render_sidebar(conn_str: str, on_ticker_change) -> tuple[str, str]:
    """Render the settings sidebar and return (selected_ticker, chat_mode)."""
    with st.sidebar:
        st.markdown("### 📄 Transcript")

        available_tickers = load_transcripts(conn_str)

        if not available_tickers:
            st.warning("No transcripts found in database. Run `python main.py [TICKER]` first.")
            st.stop()

        selected_ticker = st.selectbox(
            "Select Transcript",
            available_tickers,
            on_change=on_ticker_change,
        )

        chat_mode = st.radio(
            "Mode",
            ["Feynman Loop", "General Q&A"],
            help=(
                "Feynman Loop guides you through teaching the material to test your understanding. "
                "General Q&A lets you explore the transcript freely."
            ),
        )

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
