import streamlit as st

from ui.term_actions import handle_define_click, handle_explain_click


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
) -> None:
    """Render the left-column analysis panel: sentiment, jargon, speakers, takeaways, themes."""
    st.subheader(f"📊 {ticker} Analysis")

    with st.expander("🎭 Sentiment Analysis", expanded=False):
        if synthesis:
            overall, exec_tone, analyst_sent = synthesis
            st.markdown(f"**Overall Sentiment:** {overall}")
            st.markdown(f"**Executive Tone:** {exec_tone}")
            st.markdown(f"**Analyst Sentiment:** {analyst_sent}")
        else:
            st.info("No sentiment analysis available for this call.")

    with st.expander("🏦 Financial Jargon", expanded=False):
        if financial_terms:
            _render_term_list(conn_str, ticker, financial_terms, key_prefix=f"fin_{ticker}")
        else:
            st.info("No financial terms found in this transcript.")

    with st.expander("🏭 Industry Jargon", expanded=False):
        if industry_terms:
            _render_term_list(conn_str, ticker, industry_terms, key_prefix=f"ind_{ticker}")
        else:
            st.info("No industry-specific terms extracted.")

        if keywords:
            st.markdown("**Top Keywords (TF-IDF):**")
            st.markdown(", ".join([f"`{k}`" for k in keywords[:15]]))

    with st.expander("🎙️ Speakers", expanded=False):
        if speakers:
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

    with st.expander("💡 Key Takeaways", expanded=False):
        if takeaways:
            for t, why in takeaways:
                st.markdown(f"- **{t}**\n  - *{why}*")
        else:
            st.info("No key takeaways extracted.")

    with st.expander("🧩 Extracted Themes", expanded=False):
        if themes:
            for idx, t in enumerate(themes, 1):
                st.markdown(f"**Theme {idx}:** {t}")
        else:
            st.info("No themes extracted.")


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
