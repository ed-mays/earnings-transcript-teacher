import streamlit as st

from ui.data_loaders import load_transcripts


def render_sidebar(conn_str: str, on_ticker_change) -> tuple[str, str]:
    """Render the settings sidebar and return (selected_ticker, chat_mode)."""
    with st.sidebar:
        st.title("🎓 Settings")

        available_tickers = load_transcripts(conn_str)

        if not available_tickers:
            st.warning("No transcripts found in database. Run `python main.py [TICKER]` first.")
            st.stop()

        selected_ticker = st.selectbox(
            "Select Transcript",
            available_tickers,
            on_change=on_ticker_change,
        )

        st.divider()

        chat_mode = st.radio(
            "Learning Mode",
            ["General Q&A", "Feynman Loop"],
            help=(
                "General Q&A lets you explore the transcript freely. "
                "Feynman Loop guides you through teaching the material to test your understanding."
            ),
        )

        if st.button("Clear Chat", on_click=on_ticker_change, use_container_width=True):
            pass

    return selected_ticker, chat_mode
