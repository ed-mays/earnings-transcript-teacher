import streamlit as st

from db.persistence import update_term_definition, update_term_explanation
from db.repositories import CallRepository
from nlp.embedder import get_embeddings
from db.persistence import search_spans
from services.llm import stream_chat
from services.company_info import build_company_context
from ui.data_loaders import load_metadata


def handle_define_click(conn_str: str, ticker: str, term: str, current_def: str) -> None:
    """Show or generate a definition for a term when the Define button is clicked."""
    if not current_def or not current_def.strip():
        success = _generate_definition(conn_str, ticker, term)
        st.session_state[f"show_def_{ticker}_{term}"] = success
    else:
        st.session_state[f"show_def_{ticker}_{term}"] = True


def handle_explain_click(conn_str: str, ticker: str, term: str, current_exp: str) -> None:
    """Show or generate a contextual explanation for a term when the Explain button is clicked."""
    if not current_exp or not current_exp.strip():
        success = _generate_explanation(conn_str, ticker, term)
        st.session_state[f"show_exp_{ticker}_{term}"] = success
    else:
        st.session_state[f"show_exp_{ticker}_{term}"] = True


def _generate_definition(conn_str: str, ticker: str, term: str) -> bool:
    """Call the LLM to generate a company-grounded definition, then save it."""
    with st.spinner(f"Defining {term}..."):
        try:
            repo = CallRepository(conn_str)
            company_name, industry = repo.get_company_info(ticker)
            context = build_company_context(ticker, company_name, industry)
            system_prompt = (
                f"You are a precise financial analyst. Define the provided term in the context of "
                f"{context}. Return ONLY the definition, 1-2 sentences."
            )
            messages = [{"role": "user", "content": f"Company: {context}\nTerm: {term}"}]

            definition = ""
            for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
                if isinstance(chunk, str):
                    definition += chunk

            if definition:
                update_term_definition(conn_str, ticker, term, definition.strip())
                load_metadata.clear()
                return True
            return False
        except Exception as e:
            st.error(f"Error defining term: {e}")
            return False


def _generate_explanation(conn_str: str, ticker: str, term: str) -> bool:
    """Call the LLM to generate a contextual explanation using RAG, then save it."""
    with st.spinner(f"Explaining {term}..."):
        try:
            query_embs = get_embeddings([term])
            context_spans = []
            if query_embs and query_embs[0]:
                context_spans = search_spans(conn_str, ticker, query_embs[0], top_k=4)

            context_str = "\n".join(f"- {span}" for span in context_spans)

            system_prompt = (
                "You are an expert financial explainer. Explain why the given term is relevant "
                "in the context of the provided transcript snippets. "
                "Return ONLY the explanation, 1-2 sentences maximum."
            )
            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Company: {ticker}\nTerm: {term}\n\n"
                        f"<transcript_context>\n{context_str}\n</transcript_context>"
                    ),
                }
            ]

            explanation = ""
            for chunk in stream_chat(messages, system_prompt, model="sonar-pro"):
                if isinstance(chunk, str):
                    explanation += chunk

            if explanation:
                update_term_explanation(conn_str, ticker, term, explanation.strip())
                load_metadata.clear()
                return True
            return False
        except Exception as e:
            st.error(f"Error explaining term: {e}")
            return False
