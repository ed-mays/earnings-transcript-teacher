import threading

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from core.models import Competitor, NewsItem
from db.repositories import CallRepository, CompetitorRepository
from db.persistence import get_spans_for_ticker
from services.competitors import fetch_competitors
from services.llm import stream_chat
from services.recent_news import fetch_recent_news
from ui.term_actions import handle_define_click, handle_explain_click


def _handle_relevance_click(
    article_key: str,
    headline: str,
    summary: str,
    themes: list[str],
) -> None:
    """Generate and cache a relevance explanation for a news article."""
    if st.session_state.get(f"relevance_{article_key}"):
        st.session_state[f"show_relevance_{article_key}"] = True
        return

    themes_str = ", ".join(themes[:5]) if themes else "the earnings call results"
    system_prompt = (
        "You are a financial analyst. In 2-3 sentences explain why the given news article "
        "is relevant to the provided earnings call themes. Be specific and concise."
    )
    messages = [
        {
            "role": "user",
            "content": (
                f"Earnings call themes: {themes_str}\n\n"
                f"News headline: {headline}\n"
                f"Article summary: {summary}"
            ),
        }
    ]

    explanation = ""
    for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
        if isinstance(chunk, str):
            explanation += chunk

    if explanation:
        st.session_state[f"relevance_{article_key}"] = explanation.strip()
        st.session_state[f"show_relevance_{article_key}"] = True


@st.fragment(run_every="1s")
def _render_news_fragment(conn_str: str, ticker: str, themes: list[str]) -> None:
    """Render the Recent News section. Fetches data in a background thread so the
    main script (and the right-hand pane) are never blocked."""
    data_key = f"news_data_{ticker}"
    thread_key = f"news_thread_{ticker}"

    news_items = st.session_state.get(data_key)

    if news_items is not None:
        # Data ready — render it. run_every keeps firing but this branch is fast.
        with st.expander("Step 4 · Recent News"):
            if news_items:
                st.caption("Top news from around the earnings call, ranked by relevance to transcript themes.")
                for i, item in enumerate(news_items):
                    article_key = f"{ticker}_news_{i}"
                    if item.url:
                        st.markdown(f"**[{item.headline}]({item.url})**")
                    else:
                        st.markdown(f"**{item.headline}**")
                    meta_parts = [p for p in (item.source, item.date) if p]
                    if meta_parts:
                        st.caption(" · ".join(meta_parts))
                    if item.summary:
                        st.markdown(item.summary)
                    st.button(
                        "Explain relevance",
                        key=f"relevance_btn_{article_key}",
                        on_click=_handle_relevance_click,
                        args=(article_key, item.headline, item.summary, themes),
                    )
                    if st.session_state.get(f"show_relevance_{article_key}"):
                        explanation = st.session_state.get(f"relevance_{article_key}", "")
                        st.markdown(f"💡 **Relevance:** {explanation}")
                    if i < len(news_items) - 1:
                        st.divider()
            else:
                st.info("No recent news found.")
        return

    # Still loading — show placeholder and start the background thread once.
    with st.expander("Step 4 · Recent News  ·  ⏳ Loading…"):
        st.caption("Fetching recent news in the background…")

    if not st.session_state.get(thread_key):
        st.session_state[thread_key] = True
        ctx = get_script_run_ctx()

        def _fetch() -> None:
            add_script_run_ctx(threading.current_thread(), ctx)
            call_repo = CallRepository(conn_str)
            call_date = call_repo.get_call_date(ticker)
            company_name, _ = call_repo.get_company_info(ticker)
            if call_date:
                result = fetch_recent_news(
                    ticker=ticker,
                    company_name=company_name,
                    call_date=call_date,
                    themes=list(themes),
                )
            else:
                result = []
            st.session_state[data_key] = result

        threading.Thread(target=_fetch, daemon=True).start()


@st.fragment(run_every="1s")
def _render_competitors_fragment(conn_str: str, ticker: str) -> None:
    """Render the Competitors section. Fetches data in a background thread so the
    main script (and the right-hand pane) are never blocked."""
    data_key = f"competitors_data_{ticker}"
    thread_key = f"competitors_thread_{ticker}"

    competitors = st.session_state.get(data_key)

    if competitors is not None:
        # Data ready — render it.
        with st.expander("Step 5 · Competitors"):
            if competitors:
                st.caption("Direct competitors identified for this company and industry.")
                for c in competitors:
                    name_line = f"**{c.name}**"
                    if c.ticker:
                        name_line += f" `{c.ticker}`"
                    if c.mentioned_in_transcript:
                        name_line += " 🔖 *mentioned in transcript*"
                    st.markdown(name_line)
                    if c.description:
                        st.markdown(f"_{c.description}_")
                    st.divider()
            else:
                st.info("No competitor data available.")

            if st.button("Refresh competitors", key=f"refresh_competitors_{ticker}"):
                CompetitorRepository(conn_str).delete(ticker)
                del st.session_state[data_key]
                if thread_key in st.session_state:
                    del st.session_state[thread_key]
                st.rerun()
        return

    # Still loading — show placeholder and start the background thread once.
    with st.expander("Step 5 · Competitors  ·  ⏳ Loading…"):
        st.caption("Fetching competitors in the background…")

    if not st.session_state.get(thread_key):
        st.session_state[thread_key] = True
        ctx = get_script_run_ctx()

        def _fetch() -> None:
            add_script_run_ctx(threading.current_thread(), ctx)
            repo = CompetitorRepository(conn_str)
            cached = repo.get(ticker)
            if cached:
                st.session_state[data_key] = cached
                return
            call_repo = CallRepository(conn_str)
            company_name, industry = call_repo.get_company_info(ticker)
            spans = get_spans_for_ticker(conn_str, ticker)
            transcript_text = " ".join(text for _, _, text in spans)
            result = fetch_competitors(
                ticker=ticker,
                company_name=company_name,
                industry=industry,
                transcript_text=transcript_text,
            )
            if result:
                repo.save(ticker, result)
            st.session_state[data_key] = result

        threading.Thread(target=_fetch, daemon=True).start()


def _handle_feynman_shift_click(shift_text: str) -> None:
    """Set the Feynman topic to the strategic shift text when the button is clicked."""
    st.session_state.feynman_topic = shift_text


def render_metadata_panel(
    conn_str: str,
    ticker: str,
    themes: list,
    takeaways: list,
    synthesis,
    keywords: list[str],
    industry_terms: list,
    financial_terms: list,
    speakers: list,
    evasion: list | None = None,
    misconceptions: list | None = None,
    strategic_shifts: list[str] | None = None,
) -> None:
    """Render the left-column analysis panel as a numbered learning path."""
    st.markdown(f"### 📊 {ticker} — Learning Path")

    with st.expander("Step 1 · Overview"):
        if takeaways:
            st.markdown("**Key Takeaways**")
            for t, why in takeaways:
                st.markdown(f"- **{t}**\n  - *{why}*")
        else:
            st.info("No key takeaways extracted.")

        st.markdown("---")

        if themes:
            st.markdown("**Extracted Themes**")
            for idx, t in enumerate(themes, 1):
                st.markdown(f"**Theme {idx}:** {t}")
        else:
            st.info("No themes extracted.")

    with st.expander("Step 2 · Tone & Speakers"):
        if synthesis:
            overall, exec_tone, analyst_sent = synthesis
            st.markdown("**Sentiment Analysis**")
            st.markdown(f"**Overall Sentiment:** {overall}")
            st.markdown(f"**Executive Tone:** {exec_tone}")
            st.markdown(f"**Analyst Sentiment:** {analyst_sent}")
        else:
            st.info("No sentiment analysis available for this call.")

        st.markdown("---")

        if speakers:
            st.markdown("**Speakers**")
            executives = [(n, r, t, f) for n, r, t, f in speakers if r == "executive"]
            analysts = [(n, r, t, f) for n, r, t, f in speakers if r == "analyst"]
            if executives:
                st.markdown("**Executives**")
                for name, _, title, _ in executives:
                    subtitle = f"*{title}*" if title else ""
                    st.markdown(f"- {name}{' — ' + subtitle if subtitle else ''}")
            if analysts:
                st.markdown("**Analysts**")
                for name, _, _, firm in analysts:
                    subtitle = f"*{firm}*" if firm else ""
                    st.markdown(f"- {name}{' — ' + subtitle if subtitle else ''}")
        else:
            st.info("No speaker data available.")

    if evasion:
        with st.expander("Step 3 · What management avoided"):
            for analyst_concern, defensiveness_score, evasion_explanation in evasion:
                st.markdown(f"**Concern:** {analyst_concern}")
                st.markdown(f"*Defensiveness score: {defensiveness_score}/10*")
                st.markdown(f"**Why it was flagged:** {evasion_explanation}")
                st.divider()

    if misconceptions:
        with st.expander("Step 3 · Learning Opportunities"):
            for fact, misinterpretation, correction in misconceptions:
                st.markdown(f"*Context: {fact}*")
                st.markdown(f"**Misconception:** {misinterpretation}")
                st.markdown(f"**Correction:** {correction}")
                st.divider()

    if ticker:
        _render_news_fragment(conn_str, ticker, themes)
        _render_competitors_fragment(conn_str, ticker)

    with st.expander("Step 6 · Strategic Shifts"):
        if strategic_shifts:
            for i, shift in enumerate(strategic_shifts):
                st.markdown(shift)
                st.button(
                    "Explain via Feynman",
                    key=f"feynman_shift_{ticker}_{i}",
                    on_click=_handle_feynman_shift_click,
                    args=(shift,),
                )
                if i < len(strategic_shifts) - 1:
                    st.divider()
        else:
            st.info("No surprises or insights")

    st.checkbox("Show advanced analysis", key="show_advanced_analysis")

    if st.session_state.show_advanced_analysis:
        with st.expander("Step 3 · Financial Jargon"):
            if financial_terms:
                _render_term_list(conn_str, ticker, financial_terms, key_prefix=f"fin_{ticker}")
            else:
                st.info("No financial terms found in this transcript.")

        with st.expander("Step 3 · Industry Jargon"):
            if industry_terms:
                _render_term_list(conn_str, ticker, industry_terms, key_prefix=f"ind_{ticker}")
            else:
                st.info("No industry-specific terms extracted.")

            if keywords:
                st.markdown("**Top Keywords (TF-IDF):**")
                st.markdown(", ".join([f"`{k}`" for k in keywords[:15]]))


def _render_term_list(conn_str: str, ticker: str, terms: list, key_prefix: str) -> None:
    """Render a list of (term, definition, explanation) rows with Define/Explain buttons."""
    for i, (term, definition, explanation) in enumerate(terms):
        st.markdown(f"**{term.title()}**")
        btn_col1, btn_col2, _ = st.columns([0.5, 0.5, 0.1])
        with btn_col1:
            st.button(
                "Define",
                key=f"{key_prefix}_def_{i}_{term}",
                on_click=handle_define_click,
                args=(conn_str, ticker, term, definition),
            )
        with btn_col2:
            st.button(
                "Explain",
                key=f"{key_prefix}_exp_{i}_{term}",
                on_click=handle_explain_click,
                args=(conn_str, ticker, term, explanation),
            )
        show_def = st.session_state.get(f"show_def_{ticker}_{term}", False)
        show_exp = st.session_state.get(f"show_exp_{ticker}_{term}", False)
        if show_def:
            st.markdown(f"📘 **Definition:** {definition if definition else '*(Generating...)*'}")
        if show_exp:
            st.markdown(f"💡 **Context:** {explanation if explanation else '*(Generating...)*'}")
        st.divider()
