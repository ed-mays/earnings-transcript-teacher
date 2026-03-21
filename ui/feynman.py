import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from db.persistence import search_spans
from nlp.embedder import get_embeddings
from services.llm import stream_chat

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_STAGE_NAMES = {
    1: "Initial Explanation",
    2: "Gap Analysis",
    3: "Guided Refinement",
    4: "Understanding Test",
    5: "Teaching Note",
}

_STAGE_HINTS = {
    1: "📖 **Read the explanation below.** The AI will ask you to explain it back — give it a try in your own words!",
    2: "✏️ **Answer the AI's questions.** Try to explain the concept or fill in the gaps it identifies — no need to be perfect.",
    3: "💬 **Keep the conversation going.** Refine your explanation turn by turn. When you feel confident, click the button below to advance.",
    4: "🎯 **Apply what you've learned.** The AI will give you a new scenario — explain how the concept applies to it.",
    5: "🎉 **Session complete!** Your teaching note is below — a concise summary you can keep.",
}

_FEYNMAN_PROMPT_FILES = {
    1: "feynman/01_initial_explanation.md",
    2: "feynman/02_gap_analysis.md",
    3: "feynman/03_guided_refinement.md",
    4: "feynman/04_understanding_test.md",
    5: "feynman/05_teaching_note.md",
}


def _save_feynman_session(conn_str: str, ticker: str, completed: bool) -> None:
    """Write current Feynman session state to DB. Silently skips if session_id not set."""
    session_id = st.session_state.get("feynman_session_id")
    topic = st.session_state.get("feynman_topic", "")
    stage = st.session_state.get("feynman_stage", 1)
    messages = st.session_state.get("messages", [])
    if not session_id or not topic:
        return
    from db.repositories import LearningRepository
    repo = LearningRepository(conn_str)
    repo.save_session(
        ticker=ticker,
        session_id=session_id,
        topic=topic,
        stage=stage,
        messages=messages,
        completed=completed,
    )


def render_chat_interface(
    conn_str: str,
    ticker: str,
    chat_mode: str,
    themes: list,
    takeaways: list,
    financial_terms: list,
    industry_terms: list,
    on_reset=None,
) -> None:
    """Render the full chat area: topic picker, stage UI, message history, and input."""
    header_col, reset_col = st.columns([5, 1])
    with header_col:
        st.subheader("💬 Chat Interface")
    with reset_col:
        if st.button("Reset", help="Reset session", use_container_width=True):
            st.session_state.confirm_reset = True

    if st.session_state.get("confirm_reset"):
        st.warning("This will clear the chat and reset the Feynman loop.")
        yes_col, cancel_col = st.columns(2)
        with yes_col:
            if st.button("Yes, reset", type="primary", use_container_width=True):
                if on_reset:
                    on_reset()
                st.session_state.confirm_reset = False
                st.rerun()
        with cancel_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()
        return

    if chat_mode == "Feynman Loop" and not st.session_state.feynman_topic:
        from db.repositories import LearningRepository
        past_sessions = LearningRepository(conn_str).get_sessions_for_ticker(ticker)
        _render_topic_picker(themes, takeaways, past_sessions=past_sessions)
        return

    if chat_mode == "Feynman Loop":
        _render_stage_header(ticker)

    _render_message_history()
    _render_stage_advance_buttons(chat_mode)
    _handle_auto_fire_stage5(chat_mode)
    _render_chat_input(conn_str, ticker, chat_mode, financial_terms, industry_terms)


# ---------------------------------------------------------------------------
# Topic picker (shown before Feynman loop starts)
# ---------------------------------------------------------------------------

def _render_topic_picker(themes: list, takeaways: list, past_sessions: list[dict] | None = None) -> None:
    """Show the Feynman topic selection UI."""
    st.markdown("#### 🧠 Feynman Loop")
    st.caption("Choose a topic. The AI will guide you to explain it back, expose gaps, and deepen your understanding.")

    if past_sessions:
        in_progress = [s for s in past_sessions if not s["completed"]]
        completed = [s for s in past_sessions if s["completed"]]

        if in_progress or completed:
            with st.expander("📚 Previous Sessions", expanded=True):
                if in_progress:
                    st.markdown("**In Progress**")
                    for session in in_progress[:3]:
                        label = session["topic"]
                        if len(label) > 50:
                            label = label[:47] + "…"
                        stage_label = _STAGE_NAMES.get(session["stage"], f"Stage {session['stage']}")
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"*{label}* — {stage_label}")
                        with col2:
                            if st.button("Continue →", key=f"resume_{session['id']}", use_container_width=True):
                                st.session_state.feynman_session_id = session["id"]
                                st.session_state.feynman_topic = session["topic"]
                                st.session_state.feynman_stage = session["stage"]
                                st.session_state.messages = session["messages"]
                                st.rerun()

                if completed:
                    st.markdown("**Completed**")
                    for session in completed[:3]:
                        label = session["topic"]
                        if len(label) > 50:
                            label = label[:47] + "…"
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"*{label}*")
                        with col2:
                            if st.button("Review ↗", key=f"review_{session['id']}", use_container_width=True):
                                st.session_state.feynman_session_id = session["id"]
                                st.session_state.feynman_topic = session["topic"]
                                st.session_state.feynman_stage = 5
                                st.session_state.messages = session["messages"]
                                st.rerun()
            st.markdown("---")

    suggestions: list[str] = []
    for t in themes[:3]:
        suggestions.append(t)
    for t, _ in takeaways[:2]:
        if len(suggestions) < 5 and t not in suggestions:
            suggestions.append(t)

    if suggestions:
        st.markdown("**Practice Topics**")
        num_cols = min(3, len(suggestions))
        rows = [suggestions[i:i + num_cols] for i in range(0, len(suggestions), num_cols)]
        for row in rows:
            chip_cols = st.columns(num_cols)
            for col, suggestion in zip(chip_cols, row):
                label = suggestion if len(suggestion) <= 55 else suggestion[:52] + "…"
                if col.button(label, use_container_width=True):
                    st.session_state.feynman_session_id = str(uuid.uuid4())
                    st.session_state.feynman_topic = suggestion
                    st.rerun()

    st.markdown("---")
    st.markdown("**Or enter your own topic:**")
    custom_topic = st.text_input(
        "Topic",
        placeholder="e.g. revenue guidance, FX headwinds, gross margin drivers",
        label_visibility="collapsed",
    )
    if st.button("Start Feynman Loop ▶", disabled=not custom_topic.strip(), type="primary"):
        st.session_state.feynman_session_id = str(uuid.uuid4())
        st.session_state.feynman_topic = custom_topic.strip()
        st.rerun()


# ---------------------------------------------------------------------------
# Stage header and progress indicator
# ---------------------------------------------------------------------------

def _build_feynman_markdown(ticker: str, topic: str, messages: list[dict]) -> str:
    """Build a markdown string from a completed Feynman session chat history."""
    lines: list[str] = [
        f"# Feynman Session — {ticker}",
        "",
        f"**Topic:** {topic}  ",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    for msg in messages:
        if msg.get("feynman_auto") or msg.get("display") is False:
            continue
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"**You:** {content}")
        elif role == "assistant":
            lines.append(f"**Teacher:** {content}")
        lines.append("")
    return "\n".join(lines)


def _render_stage_header(ticker: str) -> None:
    """Render the Feynman stage caption, hint, and completion banner."""
    stage = st.session_state.feynman_stage
    topic_label = st.session_state.feynman_topic
    if len(topic_label) > 50:
        topic_label = topic_label[:47] + "…"

    st.caption(
        f"🧠 **Feynman Loop** · Topic: *{topic_label}* · "
        f"Step {stage} of 5: {_STAGE_NAMES.get(stage, 'Complete')}"
    )

    hint = _STAGE_HINTS.get(stage)
    if hint:
        st.info(hint)

    if stage == 5 and st.session_state.messages:
        last_msg = next(
            (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None
        )
        if last_msg and last_msg.get("feynman_stage") == 5:
            st.success("🎉 **Feynman Session Complete!** Review your teaching note above.")
            new_cycle_col, export_col = st.columns(2)
            with new_cycle_col:
                if st.button("🔄 Start a new Feynman cycle", type="secondary", use_container_width=True):
                    st.session_state.feynman_topic = ""
                    st.session_state.feynman_stage = 1
                    st.session_state.messages = []
                    st.rerun()
            with export_col:
                topic = st.session_state.feynman_topic
                topic_slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:40]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{ticker}_{topic_slug}_{timestamp}.md"
                markdown = _build_feynman_markdown(ticker, topic, st.session_state.messages)
                st.download_button(
                    label="⬇️ Export session",
                    data=markdown,
                    file_name=filename,
                    mime="text/markdown",
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# Message history display
# ---------------------------------------------------------------------------

def _render_message_history() -> None:
    """Display all visible chat messages with optional token stats."""
    for msg in st.session_state.messages:
        if (
            msg["role"] != "system"
            and not msg["content"].startswith("*[Proceeding to")
            and not msg.get("feynman_auto")
        ):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "stats" in msg:
                    st.caption(
                        f"Model: {msg['stats'].get('model')} "
                        f"• Tokens: In {msg['stats'].get('prompt_tokens', 0)} "
                        f"/ Out {msg['stats'].get('completion_tokens', 0)}"
                    )


# ---------------------------------------------------------------------------
# Manual stage-advance buttons (stages 3 and 4)
# ---------------------------------------------------------------------------

def _render_stage_advance_buttons(chat_mode: str) -> None:
    """Render the manual advance buttons for Feynman stages 3 and 4."""
    if chat_mode != "Feynman Loop":
        return

    stage = st.session_state.feynman_stage
    last_assistant = next(
        (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None
    )

    if stage == 3 and last_assistant:
        if st.button("✅ I'm ready to be tested", type="primary"):
            st.session_state.feynman_stage = 4
            st.session_state.messages.append(
                {"role": "user", "content": "I'm ready for the understanding test.", "display": False}
            )
            st.rerun()

    if stage == 4 and last_assistant and last_assistant.get("feynman_stage") == 4:
        if st.button("🎓 I'm done — give me my teaching note", type="primary"):
            st.session_state.feynman_stage = 5
            st.session_state.messages.append(
                {"role": "user", "content": "I am ready for the ultimate teaching note.", "display": False}
            )
            st.rerun()


# ---------------------------------------------------------------------------
# Stage 5 auto-fire safety net
# ---------------------------------------------------------------------------

def _handle_auto_fire_stage5(chat_mode: str) -> None:
    """Inject the stage 5 trigger if it's missing (fallback for page refresh)."""
    if chat_mode != "Feynman Loop" or st.session_state.feynman_stage != 5:
        return

    last_assistant = next(
        (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None
    )
    has_pending_trigger = any(
        m.get("display") is False and m["role"] == "user"
        for m in st.session_state.messages
    )
    teaching_note_done = last_assistant and last_assistant.get("feynman_stage") == 5

    if not teaching_note_done and not has_pending_trigger:
        st.session_state.messages.append(
            {"role": "user", "content": "I am ready for the ultimate teaching note.", "display": False}
        )
        st.rerun()


# ---------------------------------------------------------------------------
# Chat input + LLM response
# ---------------------------------------------------------------------------

def _render_chat_input(
    conn_str: str,
    ticker: str,
    chat_mode: str,
    financial_terms: list,
    industry_terms: list,
) -> None:
    """Handle user input (typed or auto-fired), RAG retrieval, and LLM streaming."""
    feynman_active = chat_mode == "Feynman Loop" and bool(st.session_state.feynman_topic)
    stage_complete = chat_mode == "Feynman Loop" and st.session_state.feynman_stage == 5
    placeholder_text = (
        f"Ask about {ticker}..."
        if chat_mode == "General Q&A"
        else "Type your response..."
    )

    # Auto-fire stage 1 initial explanation when topic is freshly set
    if feynman_active and st.session_state.feynman_stage == 1 and not st.session_state.messages:
        st.session_state.messages.append(
            {"role": "user", "content": f"I want to learn about: {st.session_state.feynman_topic}", "display": False}
        )
        st.rerun()

    # Detect any pending auto-fired prompt
    auto_prompt = None
    for m in list(st.session_state.messages):
        if m.get("display") is False and m["role"] == "user":
            auto_prompt = m["content"]
            break

    prompt = st.chat_input(placeholder_text, disabled=stage_complete) or auto_prompt
    if not prompt:
        return

    is_auto = prompt == auto_prompt

    if is_auto:
        # Mark the hidden message as sent (keeps it in history for the API but hides it from UI)
        st.session_state.messages = [
            {**m, "display": True, "feynman_auto": True}
            if (m.get("display") is False and m["role"] == "user" and m["content"] == prompt)
            else m
            for m in st.session_state.messages
        ]
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt, "display": True})

    # RAG retrieval
    context_spans = _retrieve_context(conn_str, ticker, prompt)

    # LLM response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response, usage_stats = _stream_response(
            chat_mode=chat_mode,
            ticker=ticker,
            prompt=prompt,
            context_spans=context_spans,
            financial_terms=financial_terms,
            industry_terms=industry_terms,
            response_placeholder=response_placeholder,
        )

    # Auto-advance stages 1 & 2
    if chat_mode == "Feynman Loop" and full_response:
        stage = st.session_state.feynman_stage
        if stage in (1, 2):
            st.session_state.feynman_stage += 1

    if full_response:
        stats_dict = {"model": usage_stats.get("model", "Unknown")}
        if "usage" in usage_stats:
            stats_dict["prompt_tokens"] = usage_stats["usage"].get("prompt_tokens", 0)
            stats_dict["completion_tokens"] = usage_stats["usage"].get("completion_tokens", 0)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "stats": stats_dict,
            "display": True,
            "feynman_stage": st.session_state.feynman_stage,
        })
        if chat_mode == "Feynman Loop" and st.session_state.feynman_stage == 5:
            last_appended = st.session_state.messages[-1]
            if last_appended.get("feynman_stage") == 5:
                _save_feynman_session(conn_str, ticker, completed=True)
        st.rerun()


def _retrieve_context(conn_str: str, ticker: str, prompt: str) -> list[str]:
    """Run a vector similarity search and return the top transcript spans."""
    query_embs = get_embeddings([prompt])
    if query_embs and query_embs[0]:
        return search_spans(conn_str, ticker, query_embs[0], top_k=4)
    return []


def _load_prompt_file(relative_path: str) -> str:
    """Read a prompt file from the prompts/ directory."""
    try:
        return (_PROMPTS_DIR / relative_path).read_text()
    except FileNotFoundError:
        return "You are a helpful expert answering questions using the transcript context."


def _stream_response(
    chat_mode: str,
    ticker: str,
    prompt: str,
    context_spans: list[str],
    financial_terms: list,
    industry_terms: list,
    response_placeholder,
) -> tuple[str, dict]:
    """Build the API message list, call the LLM, and stream the response."""
    stage = st.session_state.feynman_stage

    if chat_mode == "General Q&A":
        sys_prompt = _load_prompt_file("feynman/00_general_qa.md")
        # Inject jargon when explicitly requested
        if any(w in prompt.lower() for w in ["jargon", "vocabulary", "terms"]):
            all_terms = financial_terms + industry_terms
            if all_terms:
                context_spans = list(context_spans) + [
                    "Extracted Jargon:\n" + "\n".join([f"- {t}: {d}" for t, d, _ in all_terms])
                ]
    else:
        sys_prompt = _load_prompt_file(_FEYNMAN_PROMPT_FILES[stage])
        if stage == 1 and ticker:
            sys_prompt += f"\n\n<CompanyContext>\nThe transcript being studied is from: {ticker}\n</CompanyContext>"

    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if m.get("display") is True
    ]

    if context_spans:
        context_str = "\n".join(f"- {span}" for span in context_spans)
        api_messages[-1]["content"] = (
            f"{prompt}\n\n<transcript_context>\n{context_str}\n</transcript_context>"
        )

    full_response = ""
    usage_stats: dict = {}
    try:
        for chunk in stream_chat(api_messages, sys_prompt):
            if isinstance(chunk, dict):
                usage_stats = chunk
                continue
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")
        response_placeholder.markdown(full_response)
    except Exception as e:
        response_placeholder.error(f"Error connecting to LLM: {e}")

    return full_response, usage_stats
