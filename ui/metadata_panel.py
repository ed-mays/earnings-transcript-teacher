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
        # Empty result — clear the cache so the next run retries the fetch.
        if not news_items:
            del st.session_state[data_key]
            if thread_key in st.session_state:
                del st.session_state[thread_key]
        else:
            # Data ready — render it. run_every keeps firing but this branch is fast.
            st.caption(
                "These articles provide context around the themes discussed in this call. "
                "Read them alongside the transcript to understand the market backdrop. "
                "Use **Explain relevance** on any article to see how it connects to this specific call."
            )
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

                already_explained = st.session_state.get(f"show_relevance_{article_key}")
                if already_explained:
                    explanation = st.session_state.get(f"relevance_{article_key}", "")
                    st.info(f"💡 **Why this matters for this call:** {explanation}")
                else:
                    st.button(
                        "💡 Explain relevance to this call",
                        key=f"relevance_btn_{article_key}",
                        on_click=_handle_relevance_click,
                        args=(article_key, item.headline, item.summary, themes),
                        use_container_width=True,
                    )
                if i < len(news_items) - 1:
                    st.divider()
            return

    # Still loading — show placeholder and start the background thread once.
    st.caption("Fetching recent news in the background… ⏳")

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
        if competitors:
            st.caption(
                "Understanding the competitive landscape helps you read between the lines. "
                "When a competitor is mentioned in an earnings call, ask: *Why now? Is management "
                "on the defensive, or signalling confidence? What does this reveal about market dynamics?*"
            )
            mentioned = [c for c in competitors if c.mentioned_in_transcript]
            not_mentioned = [c for c in competitors if not c.mentioned_in_transcript]

            if mentioned:
                st.markdown(f"**📌 Referenced in this call ({len(mentioned)})**")
                for c in mentioned:
                    name_line = f"**{c.name}**"
                    if c.ticker:
                        name_line += f" `{c.ticker}`"
                    st.markdown(name_line)
                    if c.description:
                        st.markdown(f"_{c.description}_")
                    st.divider()

            if not_mentioned:
                if mentioned:
                    st.markdown("**Other competitors**")
                for c in not_mentioned:
                    name_line = f"**{c.name}**"
                    if c.ticker:
                        name_line += f" `{c.ticker}`"
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
    st.caption("Fetching competitors in the background… ⏳")

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


def _handle_signals_click(
    card_key: str,
    concern: str,
    explanation: str,
    defensiveness_score: int,
) -> None:
    """Generate and cache an investor-implications framing for an evasion card."""
    if st.session_state.get(f"signals_{card_key}"):
        st.session_state[f"show_signals_{card_key}"] = True
        return

    level = _defensiveness_label(defensiveness_score)
    system_prompt = (
        "You are a financial analyst educator. In 2–3 sentences, explain the investor "
        "implications of the evasion pattern described. Focus on what a careful investor "
        "or analyst should infer from this behaviour — not just what happened, but why it matters."
    )
    messages = [
        {
            "role": "user",
            "content": (
                f"Evasion concern: {concern}\n"
                f"Defensiveness level: {level}\n"
                f"What the executive avoided: {explanation}"
            ),
        }
    ]

    framing = ""
    for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
        if isinstance(chunk, str):
            framing += chunk

    if framing:
        st.session_state[f"signals_{card_key}"] = framing.strip()
        st.session_state[f"show_signals_{card_key}"] = True


def _render_signals_button(card_key: str, concern: str, explanation: str, score: int) -> None:
    """Render the 'What this signals' button or its generated result."""
    if st.session_state.get(f"show_signals_{card_key}"):
        framing = st.session_state.get(f"signals_{card_key}", "")
        st.warning(f"📈 **What this signals for investors:** {framing}")
    else:
        st.button(
            "📈 What this signals for investors",
            key=f"signals_btn_{card_key}",
            on_click=_handle_signals_click,
            args=(card_key, concern, explanation, score),
            use_container_width=True,
        )


def _handle_feynman_shift_click(shift_text: str) -> None:
    """Set the Feynman topic to the strategic shift text when the button is clicked."""
    st.session_state.feynman_topic = shift_text


def build_feynman_suggestions(
    strategic_shifts: list[dict] | None,
    evasion: list | None,
    qa_evasion: list | None,
    max_suggestions: int = 3,
) -> list[str]:
    """Build an ordered list of suggested Feynman topics from the richest available sources."""
    suggested: list[str] = []

    if strategic_shifts:
        for shift in strategic_shifts[:2]:
            topic = shift.get("current_position", "") if isinstance(shift, dict) else str(shift)
            if topic:
                suggested.append(topic)

    if evasion:
        for analyst_concern, _, _ in evasion:
            if len(suggested) >= max_suggestions:
                break
            if analyst_concern not in suggested:
                suggested.append(analyst_concern)

    if qa_evasion:
        for _, question_topic, _, _, concern, _, _ in qa_evasion:
            if len(suggested) >= max_suggestions:
                break
            topic = question_topic or concern
            if topic and topic not in suggested:
                suggested.append(topic)

    return suggested



_AI_BADGE = '<abbr title="This analysis is AI-generated — verify against the transcript">🤖</abbr>'


def _defensiveness_label(score: int) -> str:
    """Convert a numeric defensiveness score to a qualitative label."""
    if score >= 8:
        return "High"
    elif score >= 5:
        return "Moderate"
    else:
        return "Low"


_TOTAL_STEPS = 6


def _mark_step_complete(conn_str: str, ticker: str, step_number: int) -> None:
    """Callback: persist a step completion and clear the step-progress cache."""
    from db.repositories import ProgressRepository
    from ui.data_loaders import load_step_progress, load_all_step_counts
    ProgressRepository(conn_str).mark_step_viewed(ticker, step_number)
    load_step_progress.clear()
    load_all_step_counts.clear()


def _step_label(title: str, step_number: int, completed_steps: set[int]) -> str:
    """Return a step expander label with a checkmark if the step is done."""
    suffix = " ✓" if step_number in completed_steps else ""
    return f"{title}{suffix}"


def _render_mark_read_button(conn_str: str, ticker: str, step_number: int, completed_steps: set[int]) -> None:
    """Render a 'Mark as read' button at the bottom of a step, or a completion note if already done."""
    if step_number in completed_steps:
        st.caption("✓ Marked as read")
    else:
        st.button(
            "Mark as read",
            key=f"mark_read_{ticker}_step{step_number}",
            on_click=_mark_step_complete,
            args=(conn_str, ticker, step_number),
        )


_PRE_READING_ITEMS = [
    ("Step 1 · Overview", "Read the key themes and takeaways before diving in"),
    ("Step 2 · Tone & Speakers", "Know who is presenting and what roles they play"),
    ("Step 3 · Said vs. Avoided", "Prime yourself to spot what management avoids"),
    ("Step 4 · What Changed", "Note the strategic shifts from prior quarters"),
    ("Step 5 · The Bigger Picture", "Understand the market and competitive context"),
    ("Step 6 · Language Lab", "Familiarise yourself with the jargon"),
]


def render_pre_reading_checklist(ticker: str) -> None:
    """Render a collapsible pre-reading checklist to structure engagement before the transcript."""
    done_count = sum(
        1
        for i in range(len(_PRE_READING_ITEMS))
        if st.session_state.get(f"prereading_{ticker}_{i}", False)
    )
    label = f"📋 Before you read — {done_count}/{len(_PRE_READING_ITEMS)} steps prepared"
    with st.expander(label):
        st.caption(
            "Work through the analysis steps below before reading the raw transcript. "
            "Each step builds the context you need to read the call critically."
        )
        for i, (step_name, description) in enumerate(_PRE_READING_ITEMS):
            st.checkbox(
                f"**{step_name}** — {description}",
                key=f"prereading_{ticker}_{i}",
            )


def render_learning_objectives(themes: list, takeaways: list, call_summary: str | None) -> None:
    """Render a learning objectives section derived from synthesis data."""
    with st.expander("🎯 Learning objectives"):
        st.markdown(
            "Work through these 6 steps to build a complete picture of the earnings call:"
        )
        st.markdown(
            "- **Step 1 · Overview** — identify the headline themes and key strategic takeaways\n"
            "- **Step 2 · Tone & Speakers** — read the room: who drove the conversation and how\n"
            "- **Step 3 · Said vs. Avoided** — spot what executives dodged and why it matters\n"
            "- **Step 4 · What Changed** — track strategic shifts from prior quarters\n"
            "- **Step 5 · The Bigger Picture** — place the call in its market and competitive context\n"
            "- **Step 6 · Language Lab** — master the jargon before you read the transcript"
        )
        if themes:
            theme_list = ", ".join(f"*{t}*" for t in themes[:4])
            st.markdown(f"**Key themes to watch for in this call:** {theme_list}")


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
    strategic_shifts: list[dict] | None = None,
    qa_evasion: list[tuple] | None = None,
    call_summary: str | None = None,
    speaker_dynamics: list[dict] | None = None,
    completed_steps: set[int] | None = None,
) -> None:
    """Render the left-column analysis panel as a numbered learning path."""
    if completed_steps is None:
        completed_steps = set()

    st.markdown(f"### 📊 {ticker} — Learning Path")

    # Progress indicator (#70)
    steps_done = len(completed_steps)
    if steps_done > 0:
        st.progress(steps_done / _TOTAL_STEPS, text=f"{steps_done}/{_TOTAL_STEPS} steps read")
    else:
        st.progress(0.0, text=f"0/{_TOTAL_STEPS} steps read")

    render_pre_reading_checklist(ticker)
    render_learning_objectives(themes, takeaways, call_summary)

    with st.expander(_step_label("Step 1 · Overview", 1, completed_steps)):
        if call_summary:
            st.markdown(call_summary)
            st.markdown("---")

        if takeaways:
            st.markdown(f"**Key Takeaways** {_AI_BADGE}", unsafe_allow_html=True)
            st.caption("The 'so what' — narrative insights and implications from the call.")
            for t, why in takeaways:
                st.markdown(f"- **{t}**\n  - *{why}*")
        else:
            st.info("No key takeaways extracted.")

        st.markdown("---")

        if themes:
            st.markdown(f"**Extracted Themes** {_AI_BADGE}", unsafe_allow_html=True)
            st.caption("Recurring topics and subject clusters identified across the transcript.")
            for idx, t in enumerate(themes, 1):
                st.markdown(f"**Theme {idx}:** {t}")
        else:
            st.info("No themes extracted.")

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 1, completed_steps)

    with st.expander(_step_label("Step 2 · Tone & Speakers", 2, completed_steps)):
        if synthesis:
            overall, exec_tone, analyst_sent = synthesis
            st.markdown(f"**Sentiment Analysis** {_AI_BADGE}", unsafe_allow_html=True)
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

        if speaker_dynamics:
            st.markdown("---")
            st.markdown("**Call Dynamics**")
            # Most active executive: highest total turn count across all sections
            exec_rows = [r for r in speaker_dynamics if r["role"] == "executive"]
            if exec_rows:
                by_exec: dict[str, int] = {}
                for r in exec_rows:
                    by_exec[r["speaker"]] = by_exec.get(r["speaker"], 0) + r["turn_count"]
                top_exec, top_exec_turns = max(by_exec.items(), key=lambda x: x[1])
                st.markdown(f"Most active executive: **{top_exec}** — {top_exec_turns} turns")
            # Most active analyst: highest Q&A turn count
            analyst_qa_rows = [r for r in speaker_dynamics if r["role"] == "analyst" and r["section"] == "qa"]
            if analyst_qa_rows:
                top = max(analyst_qa_rows, key=lambda r: r["turn_count"])
                label = top["speaker"]
                if top["firm"]:
                    label += f", {top['firm']}"
                st.markdown(f"Most active analyst: **{label}** — {top['turn_count']} exchanges in Q&A")
            # Analyst firm diversity
            analyst_firms = {
                r["firm"]
                for r in speaker_dynamics
                if r["role"] == "analyst" and r.get("firm")
            }
            analyst_names = {r["speaker"] for r in speaker_dynamics if r["role"] == "analyst"}
            if analyst_firms:
                st.markdown(
                    f"Questions came from **{len(analyst_firms)} firm{'s' if len(analyst_firms) != 1 else ''}** "
                    f"({len(analyst_names)} analyst{'s' if len(analyst_names) != 1 else ''})"
                )
            # Exec vs analyst word share
            exec_words = sum(r["word_count"] for r in speaker_dynamics if r["role"] == "executive")
            analyst_words = sum(r["word_count"] for r in speaker_dynamics if r["role"] == "analyst")
            total_words = exec_words + analyst_words
            if total_words > 0:
                exec_pct = round(exec_words / total_words * 100)
                st.markdown(
                    f"Talk time: executives **{exec_pct}%**, analysts **{100 - exec_pct}%**"
                )

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 2, completed_steps)

    if evasion or qa_evasion:
        with st.expander(_step_label("Step 3 · Said vs. Avoided", 3, completed_steps)):
            if evasion:
                st.markdown(f"**📋 Prepared Remarks** {_AI_BADGE}", unsafe_allow_html=True)
                for idx, (analyst_concern, defensiveness_score, evasion_explanation) in enumerate(evasion):
                    st.markdown(f"**Concern:** {analyst_concern}")
                    st.markdown(f"*Defensiveness: {_defensiveness_label(defensiveness_score)}*")
                    st.markdown(f"**Why it was flagged:** {evasion_explanation}")
                    card_key = f"{ticker}_prepared_{idx}"
                    _render_signals_button(card_key, analyst_concern, evasion_explanation, defensiveness_score)
                    st.divider()

            if qa_evasion:
                st.markdown(f"**🎤 Q&A Session** {_AI_BADGE}", unsafe_allow_html=True)
                for i, (analyst_name, question_topic, question_text, answer_text, concern, score, explanation) in enumerate(qa_evasion):
                    badge = "🔴" if score >= 8 else "🟡" if score >= 5 else "🟢"
                    name = analyst_name or "The analyst"
                    topic = question_topic or concern
                    with st.expander(f"{badge} {name} asked about {topic}"):
                        if question_text:
                            st.markdown("**Question**")
                            st.markdown(question_text)
                        if answer_text:
                            st.markdown("**Response**")
                            st.markdown(answer_text)
                        with st.expander("What the executive avoided"):
                            st.markdown(explanation)
                        card_key = f"{ticker}_qa_{i}"
                        _render_signals_button(card_key, question_topic or concern, explanation, score)
                    if i < len(qa_evasion) - 1:
                        st.divider()

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 3, completed_steps)

    with st.expander(_step_label("Step 4 · What Changed", 4, completed_steps)):
        if strategic_shifts:
            for i, shift in enumerate(strategic_shifts):
                prior = shift.get("prior_position", "") if isinstance(shift, dict) else ""
                current = shift.get("current_position", str(shift)) if isinstance(shift, dict) else str(shift)
                significance = shift.get("investor_significance", "") if isinstance(shift, dict) else ""
                if prior:
                    st.markdown(f"**Prior:** {prior}")
                st.markdown(f"**Now:** {current}")
                if significance:
                    st.markdown(f"**Why it matters:** {significance}")
                st.button(
                    "Explain via Feynman",
                    key=f"feynman_shift_{ticker}_{i}",
                    on_click=_handle_feynman_shift_click,
                    args=(current,),
                )
                if i < len(strategic_shifts) - 1:
                    st.divider()
        else:
            st.info("No surprises or insights")

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 4, completed_steps)

    if ticker:
        with st.expander(_step_label("Step 5 · The Bigger Picture", 5, completed_steps)):
            st.markdown("#### Recent News")
            _render_news_fragment(conn_str, ticker, themes)
            st.divider()
            st.markdown("#### Competitors")
            _render_competitors_fragment(conn_str, ticker)

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 5, completed_steps)

    with st.expander(_step_label("Step 6 · Language Lab", 6, completed_steps)):
        if misconceptions:
            st.markdown(f"**Common Misconceptions** {_AI_BADGE}", unsafe_allow_html=True)
            reveal_all_key = f"reveal_all_misconceptions_{ticker}"
            if st.button("Expand all corrections", key=f"expand_all_misc_{ticker}"):
                st.session_state[reveal_all_key] = True
            reveal_all = st.session_state.get(reveal_all_key, False)
            for i, (fact, misinterpretation, correction) in enumerate(misconceptions):
                reveal_key = f"reveal_misconception_{ticker}_{i}"
                st.markdown(f"*Context: {fact}*")
                st.markdown(f"**Misconception:** {misinterpretation}")
                revealed = reveal_all or st.session_state.get(reveal_key, False)
                if revealed:
                    st.markdown(f"**Correction:** {correction}")
                else:
                    st.button(
                        "Reveal correction",
                        key=f"reveal_btn_misc_{ticker}_{i}",
                        on_click=lambda k=reveal_key: st.session_state.update({k: True}),
                    )
                st.divider()

        st.markdown("**Financial Jargon**")
        if financial_terms:
            _render_term_list(conn_str, ticker, financial_terms, key_prefix=f"fin_{ticker}")
        else:
            st.info("No financial terms found in this transcript.")

        st.markdown("**Industry Jargon**")
        if industry_terms:
            _render_term_list(conn_str, ticker, industry_terms, key_prefix=f"ind_{ticker}")
        else:
            st.info("No industry-specific terms extracted.")

        if keywords:
            st.markdown("**Top Keywords (TF-IDF):**")
            st.markdown(", ".join([f"`{k}`" for k in keywords[:15]]))

        st.markdown("---")
        _render_mark_read_button(conn_str, ticker, 6, completed_steps)



def _handle_find_in_transcript(term: str) -> None:
    """Set the transcript search term when Find in transcript is clicked."""
    st.session_state["transcript_search_term"] = term


def _render_term_list(conn_str: str, ticker: str, terms: list, key_prefix: str) -> None:
    """Render a list of (term, definition, explanation) rows with Define/Explain/Find buttons."""
    for i, (term, definition, explanation) in enumerate(terms):
        st.markdown(f"**{term.title()}**")
        btn_col1, btn_col2, btn_col3 = st.columns([0.4, 0.4, 0.4])
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
        with btn_col3:
            st.button(
                "Find in transcript",
                key=f"{key_prefix}_find_{i}_{term}",
                on_click=_handle_find_in_transcript,
                args=(term,),
            )
        show_def = st.session_state.get(f"show_def_{ticker}_{term}", False)
        show_exp = st.session_state.get(f"show_exp_{ticker}_{term}", False)
        if show_def:
            st.markdown(f"📘 **Definition:** {definition if definition else '*(Generating...)*'}")
        if show_exp:
            st.markdown(f"💡 **Context:** {explanation if explanation else '*(Generating...)*'}")
        st.divider()
