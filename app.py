import os
import streamlit as st

from db.persistence import (
    get_all_calls,
    get_themes_for_ticker,
    get_takeaways_for_ticker,
    get_keywords_for_ticker,
    get_industry_terms_for_ticker,
    get_financial_terms_for_ticker,
    get_speakers_for_ticker,
    get_spans_for_ticker,
    update_term_definition,
    update_term_explanation,
    search_spans
)
from nlp.embedder import get_embeddings
from services.llm import stream_chat

# ------------- Configuration -------------

st.set_page_config(
    page_title="Earnings Transcript Teacher",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CONN_STR = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")

# ------------- State Management -------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None

# ------------- Helper Functions -------------

@st.cache_data
def load_transcripts():
    """Fetch available transcripts from the database."""
    calls = get_all_calls(CONN_STR)
    return [c[0] for c in calls] if calls else []

@st.cache_data
def auto_migrate():
    """Ensure database schema is up to date."""
    try:
        import psycopg
        with psycopg.connect(CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';")
            conn.commit()
    except Exception as e:
        print(f"Auto-migrate failed: {e}")

# Run migration once per Streamlit session
auto_migrate()

@st.cache_data
def load_speakers(ticker: str) -> list[tuple[str, str, str | None, str | None]]:
    """Fetch enriched speaker profiles for a transcript from the database."""
    return get_speakers_for_ticker(CONN_STR, ticker)

@st.cache_data
def load_transcript_spans(ticker: str) -> list[tuple[str, str, str]]:
    """Fetch all speaker turns for a transcript from the database."""
    return get_spans_for_ticker(CONN_STR, ticker)

@st.cache_data
def load_metadata(ticker):
    """Fetch metadata for a given transcript."""
    try:
        themes = get_themes_for_ticker(CONN_STR, ticker)
        takeaways = get_takeaways_for_ticker(CONN_STR, ticker)
        keywords = get_keywords_for_ticker(CONN_STR, ticker)
        industry_terms = get_industry_terms_for_ticker(CONN_STR, ticker)
        financial_terms = get_financial_terms_for_ticker(CONN_STR, ticker)

        # Deduplicate keywords for cleaner display
        unique_keywords = []
        seen = set()
        for kw in keywords:
            if kw.lower() not in seen:
                unique_keywords.append(kw)
                seen.add(kw.lower())

        return themes, takeaways, unique_keywords, industry_terms, financial_terms
    except Exception as e:
        import traceback
        with open("streamlit_db_error.txt", "w") as f:
            f.write(traceback.format_exc())
            f.write(f"\nConn str: {CONN_STR}")
        raise e

def reset_chat():
    """Clear the chat history."""
    st.session_state.messages = []

def handle_define_click(ticker: str, term: str, current_def: str):
    if not current_def or not current_def.strip():
        success = generate_definition(ticker, term)
        if success:
            st.session_state[f"show_def_{ticker}_{term}"] = True
        else:
            st.session_state[f"show_def_{ticker}_{term}"] = False
    else:
        st.session_state[f"show_def_{ticker}_{term}"] = True

def handle_explain_click(ticker: str, term: str, current_exp: str):
    if not current_exp or not current_exp.strip():
        success = generate_explanation(ticker, term)
        if success:
            st.session_state[f"show_exp_{ticker}_{term}"] = True
        else:
            st.session_state[f"show_exp_{ticker}_{term}"] = False
    else:
        st.session_state[f"show_exp_{ticker}_{term}"] = True

def generate_definition(ticker: str, term: str) -> bool:
    """Call the LLM to generate a general dictionary definition, then save it."""
    with st.spinner(f"Defining {term}..."):
        try:
            system_prompt = "You are a precise financial dictionary. Define the provided term generally in 1-2 sentences. Return ONLY the definition text."
            messages = [{"role": "user", "content": f"Term: {term}"}]
            
            definition = ""
            for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
                if isinstance(chunk, str):
                    definition += chunk
            
            if definition:
                update_term_definition(CONN_STR, ticker, term, definition.strip())
                # Clear cache so next render shows the new definition
                load_metadata.clear()
                return True
            return False
        except Exception as e:
            st.error(f"Error defining term: {e}")
            return False

def generate_explanation(ticker: str, term: str) -> bool:
    """Call the LLM to generate a contextual explanation using RAG, then save it."""
    with st.spinner(f"Explaining {term}..."):
        try:
            # 1. Retrieve Context (RAG)
            query_embs = get_embeddings([term])
            context_spans = []
            if query_embs and query_embs[0]:
                context_spans = search_spans(CONN_STR, ticker, query_embs[0], top_k=4)
                
            context_str = "\n".join(f"- {span}" for span in context_spans)
            
            # 2. Call LLM
            system_prompt = "You are an expert financial explainer. Explain why the given term is relevant in the context of the provided transcript snippets. Return ONLY the explanation, 1-2 sentences maximum."
            messages = [{"role": "user", "content": f"Company: {ticker}\nTerm: {term}\n\n<transcript_context>\n{context_str}\n</transcript_context>"}]
            
            explanation = ""
            for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
                if isinstance(chunk, str):
                    explanation += chunk
            
            if explanation:
                update_term_explanation(CONN_STR, ticker, term, explanation.strip())
                load_metadata.clear()
                return True
            return False
        except Exception as e:
            st.error(f"Error explaining term: {e}")
            return False

# ------------- Sidebar -------------

with st.sidebar:
    st.title("🎓 Settings")
    
    available_tickers = load_transcripts()
    
    if not available_tickers:
        st.warning("No transcripts found in database. Run `python main.py [TICKER]` first.")
        st.stop()
        
    # Transcript Selection
    selected_ticker = st.selectbox(
        "Select Transcript", 
        available_tickers,
        on_change=reset_chat
    )
    st.session_state.active_ticker = selected_ticker
    
    st.divider()
    
    # Chat Mode Selection
    chat_mode = st.radio(
        "Learning Mode",
        ["General Q&A", "Feynman Loop"],
        help="General Q&A lets you explore the transcript freely. Feynman Loop guides you through teaching the material to test your understanding."
    )
    
    if st.button("Clear Chat", on_click=reset_chat, use_container_width=True):
        pass

# ------------- Main App -------------

# Load data for the active transcript
themes, takeaways, keywords, industry_terms, financial_terms = load_metadata(st.session_state.active_ticker)

# Layout: 35% left column (Metadata), 65% right column (Chat)
left_col, right_col = st.columns([3.5, 6.5])

with left_col:
    st.subheader(f"📊 {st.session_state.active_ticker} Analysis")
    
    def _render_term_list(terms, key_prefix):
        """Render a list of (term, definition, explanation) rows with Define/Explain buttons."""
        for i, (term, definition, explanation) in enumerate(terms):
            st.markdown(f"**{term.title()}**")
            btn_col1, btn_col2, _ = st.columns([0.5, 0.5, .1])
            with btn_col1:
                st.button(
                    "Define",
                    key=f"{key_prefix}_def_{i}_{term}",
                    on_click=handle_define_click,
                    args=(st.session_state.active_ticker, term, definition)
                )
            with btn_col2:
                st.button(
                    "Explain",
                    key=f"{key_prefix}_exp_{i}_{term}",
                    on_click=handle_explain_click,
                    args=(st.session_state.active_ticker, term, explanation)
                )
            show_def = st.session_state.get(f"show_def_{st.session_state.active_ticker}_{term}", False)
            show_exp = st.session_state.get(f"show_exp_{st.session_state.active_ticker}_{term}", False)
            if show_def:
                st.markdown(f"📘 **Definition:** {definition if definition else '*(Generating...)*'}")
            if show_exp:
                st.markdown(f"💡 **Context:** {explanation if explanation else '*(Generating...)*'}")
            st.divider()

    with st.expander("🏦 Financial Jargon", expanded=False):
        if financial_terms:
            _render_term_list(financial_terms, key_prefix=f"fin_{st.session_state.active_ticker}")
        else:
            st.info("No financial terms found in this transcript.")

    with st.expander("🏭 Industry Jargon", expanded=False):
        if industry_terms:
            _render_term_list(industry_terms, key_prefix=f"ind_{st.session_state.active_ticker}")
        else:
            st.info("No industry-specific terms extracted.")

        if keywords:
            st.markdown("**Top Keywords (TF-IDF):**")
            st.markdown(", ".join([f"`{k}`" for k in keywords[:15]]))
            
    with st.expander("🎙️ Speakers", expanded=False):
        speakers = load_speakers(st.session_state.active_ticker)
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

with right_col:
    st.subheader("💬 Chat Interface")
    
    # Display existing chat messages
    for msg in st.session_state.messages:
        # Don't show system/hidden messages in the UI
        if msg["role"] != "system" and not msg["content"].startswith("*[Proceeding to"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "stats" in msg:
                    st.caption(f"Model: {msg['stats'].get('model')} • Tokens: In {msg['stats'].get('prompt_tokens', 0)} / Out {msg['stats'].get('completion_tokens', 0)}")

    # Chat Input
    if prompt := st.chat_input(f"Ask about {st.session_state.active_ticker}..."):
        
        # 1. Display user message exactly as typed
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # 2. Add to session history
        st.session_state.messages.append({"role": "user", "content": prompt, "display": True})
        
        # 3. Retrieve Context (RAG)
        query_embs = get_embeddings([prompt])
        context_spans = []
        if query_embs and query_embs[0]:
            context_spans = search_spans(CONN_STR, st.session_state.active_ticker, query_embs[0], top_k=4)
            
        # 4. Handle System Prompts & Custom Logic based on mode
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            usage_stats = {}
            
            if chat_mode == "General Q&A":
                # Load prompt
                try:
                    with open("prompts/feynman/00_general_qa.md", "r") as f:
                        sys_prompt = f.read()
                except FileNotFoundError:
                    sys_prompt = "You are a helpful expert answering questions using the transcript context."
                    
                # Inject jargon if user asked about it
                if any(w in prompt.lower() for w in ["jargon", "vocabulary", "terms"]):
                    all_terms = financial_terms + industry_terms
                    if all_terms:
                        jargon_str = "Extracted Jargon:\n" + "\n".join([f"- {t}: {d}" for t, d, _ in all_terms])
                        context_spans.append(jargon_str)
                        
                # Format final API messages
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if "display" in m]
                
                # Augment the last user message with the RAG context
                if context_spans:
                    context_str = "\n".join(f"- {span}" for span in context_spans)
                    augmented_input = f"{prompt}\n\n<transcript_context>\n{context_str}\n</transcript_context>"
                    api_messages[-1]["content"] = augmented_input
                    
                # Stream Response
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
                    
            elif chat_mode == "Feynman Loop":
                # Basic Feynman implementation for GUI MVP
                try:
                    with open("prompts/feynman/01_initial_explanation.md", "r") as f:
                        sys_prompt = f.read()
                except FileNotFoundError:
                    sys_prompt = "You are a Feynman method tutor. Evaluate the user's understanding."
                    
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if "display" in m]
                
                if context_spans:
                    context_str = "\n".join(f"- {span}" for span in context_spans)
                    augmented_input = f"{prompt}\n\n<transcript_context>\n{context_str}\n</transcript_context>"
                    api_messages[-1]["content"] = augmented_input
                    
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

            # 5. Save the assistant response and stats to history
            if full_response:
                stats_dict = {'model': usage_stats.get('model', 'Unknown')}
                if 'usage' in usage_stats:
                    stats_dict['prompt_tokens'] = usage_stats['usage'].get('prompt_tokens', 0)
                    stats_dict['completion_tokens'] = usage_stats['usage'].get('completion_tokens', 0)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "stats": stats_dict,
                    "display": True
                })
                # Trigger a rerun so the final markdown renders cleanly without the cursor
                st.rerun()

    st.divider()

    with st.expander("📄 Transcript Browser", expanded=False):
        spans = load_transcript_spans(st.session_state.active_ticker)
        if spans:
            import re
            def _escape(t: str) -> str:
                return re.sub(r'([\\`*_{}[\]()#+\-!|~>$])', r'\\\1', t)
            lines = [f"**{speaker}:** {_escape(text)}" for speaker, _, text in spans]
            with st.container(height=500):
                st.markdown("\n\n".join(lines))
        else:
            st.info("No transcript data available.")
