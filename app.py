import os
import streamlit as st

from db.persistence import (
    get_all_calls,
    get_topics_for_ticker,
    get_takeaways_for_ticker,
    get_keywords_for_ticker,
    get_extracted_terms_for_ticker,
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
def load_metadata(ticker):
    """Fetch metadata for a given transcript."""
    topics = get_topics_for_ticker(CONN_STR, ticker)
    takeaways = get_takeaways_for_ticker(CONN_STR, ticker)
    keywords = get_keywords_for_ticker(CONN_STR, ticker)
    terms = get_extracted_terms_for_ticker(CONN_STR, ticker, limit=10)
    
    # Deduplicate keywords for cleaner display
    unique_keywords = []
    seen = set()
    for kw in keywords:
        if kw.lower() not in seen:
            unique_keywords.append(kw)
            seen.add(kw.lower())
            
    return topics, takeaways, unique_keywords, terms

def reset_chat():
    """Clear the chat history."""
    st.session_state.messages = []

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
topics, takeaways, keywords, jargon = load_metadata(st.session_state.active_ticker)

# Layout: 35% left column (Metadata), 65% right column (Chat)
left_col, right_col = st.columns([3.5, 6.5])

with left_col:
    st.subheader(f"📊 {st.session_state.active_ticker} Analysis")
    
    with st.expander("📚 Vocabulary & Jargon", expanded=True):
        if jargon:
            for term, definition in jargon:
                st.markdown(f"**{term.title()}**: {definition}")
        else:
            st.info("No specific jargon extracted for this transcript.")
            
        if keywords:
            st.markdown("**Top Keywords (TF-IDF):**")
            st.markdown(", ".join([f"`{k}`" for k in keywords[:15]]))
            
    with st.expander("💡 Key Takeaways", expanded=True):
        if takeaways:
            for t in takeaways:
                st.markdown(f"- {t}")
        else:
            st.info("No key takeaways extracted.")
            
    with st.expander("🧩 Extracted Themes", expanded=True):
        if topics:
            for idx, t in enumerate(topics, 1):
                st.markdown(f"**Theme {idx}:** {', '.join(t)}")
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
                    if jargon:
                        jargon_str = "Extracted Jargon:\n" + "\n".join([f"- {t}: {d}" for t, d in jargon])
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
