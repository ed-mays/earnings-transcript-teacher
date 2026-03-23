import streamlit as st

from db.repositories import LearningRepository
from ui.data_loaders import load_transcripts


def render_library(conn_str: str, on_select: callable) -> None:
    """Render the transcript library landing page with study progress per transcript."""
    st.markdown("## 📚 Transcript Library")

    available_calls = load_transcripts(conn_str)

    if not available_calls:
        _render_zero_state()
        return

    learning_repo = LearningRepository(conn_str)
    ticker_counts: dict[str, tuple[int, int]] = {
        ticker: (total, completed)
        for ticker, total, completed in learning_repo.get_ticker_session_counts()
    }

    _render_filter_bar(available_calls)
    _render_transcript_table(available_calls, ticker_counts, on_select)


def _render_zero_state() -> None:
    """Render the empty-library state with getting-started instructions."""
    st.markdown("---")
    col_left, col_center, col_right = st.columns([1, 3, 1])
    with col_center:
        st.markdown(
            """
            ### Welcome to Earnings Transcript Teacher 🎓

            This app helps you deeply understand earnings calls by guiding you through:

            - **Step 1 · Overview** — key themes and strategic takeaways
            - **Step 2 · Tone & Speakers** — who said what and how they said it
            - **Step 3 · Said vs. Avoided** — what analysts asked and what executives dodged
            - **Step 4 · What Changed** — strategic shifts vs. prior quarters
            - **Step 5 · The Bigger Picture** — synthesis across the whole call
            - **Step 6 · Language Lab** — industry and financial jargon
            - **Feynman Loop** — test your understanding by teaching it back

            ---

            #### How to ingest your first transcript

            Run the following command in your terminal, replacing `AAPL` with any ticker:

            ```
            python3 main.py AAPL --save
            ```

            The app will download the transcript, analyse it, and store it in your database.
            Refresh this page once ingestion is complete.
            """
        )


def _render_filter_bar(available_calls: list[tuple]) -> None:
    """Render sort and filter controls above the library table."""
    col_search, col_sort = st.columns([3, 1])
    with col_search:
        st.text_input(
            "Filter by ticker or company",
            key="library_filter",
            placeholder="e.g. AAPL or Apple",
            label_visibility="collapsed",
        )
    with col_sort:
        st.selectbox(
            "Sort by",
            ["Date (newest)", "Date (oldest)", "Ticker (A–Z)", "Study progress"],
            key="library_sort",
            label_visibility="collapsed",
        )


def _render_transcript_table(
    available_calls: list[tuple],
    ticker_counts: dict[str, tuple[int, int]],
    on_select: callable,
) -> None:
    """Render the filterable, sortable transcript cards."""
    filter_text = st.session_state.get("library_filter", "").strip().lower()
    sort_order = st.session_state.get("library_sort", "Date (newest)")

    rows = []
    for ticker, fiscal_quarter, company_name, call_date in available_calls:
        if filter_text:
            searchable = f"{ticker} {company_name or ''}".lower()
            if filter_text not in searchable:
                continue
        total, completed = ticker_counts.get(ticker, (0, 0))
        rows.append((ticker, fiscal_quarter, company_name, call_date, total, completed))

    if sort_order == "Date (oldest)":
        rows.sort(key=lambda r: r[3] or "", reverse=False)
    elif sort_order == "Ticker (A–Z)":
        rows.sort(key=lambda r: r[0])
    elif sort_order == "Study progress":
        rows.sort(key=lambda r: r[4], reverse=True)
    # Default: Date (newest) — already newest-first from DB

    if not rows:
        st.info("No transcripts match your filter.")
        return

    st.markdown("---")
    header_cols = st.columns([2, 3, 2, 2, 2])
    for col, label in zip(header_cols, ["Ticker", "Company", "Quarter", "Date", "Sessions"]):
        col.markdown(f"**{label}**")
    st.markdown("---")

    for ticker, fiscal_quarter, company_name, call_date, total, completed in rows:
        row_cols = st.columns([2, 3, 2, 2, 2])
        row_cols[0].markdown(f"**{ticker}**")
        row_cols[1].markdown(company_name or "—")
        row_cols[2].markdown(fiscal_quarter or "—")
        date_str = _format_date(call_date)
        row_cols[3].markdown(date_str)
        if total > 0:
            row_cols[4].markdown(f"{completed}/{total} ✓")
        else:
            row_cols[4].markdown("Not started")

        if row_cols[4].button("Study →", key=f"lib_study_{ticker}"):
            on_select(ticker)


def _format_date(call_date) -> str:
    """Format a call date for display."""
    if not call_date:
        return "—"
    try:
        return call_date.strftime("%b %-d, %Y")
    except AttributeError:
        return str(call_date)
