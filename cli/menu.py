import os
import re
import sys
import subprocess
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "feynman"

from db.persistence import (
    save_analysis,
    get_all_calls,
    get_themes_for_ticker,
    get_takeaways_for_ticker,
    get_keywords_for_ticker,
    get_extracted_terms_for_ticker,
    search_spans
)
from nlp.embedder import get_embeddings
from services.llm import stream_chat
from services.orchestrator import analyze
from cli.display import display

def _validate_ticker(ticker: str) -> bool:
    """Return True if ticker is 1-5 uppercase alphabetical characters (e.g. AAPL, MSFT)."""
    return bool(re.match(r'^[A-Z]{1,5}$', ticker))


def interactive_menu() -> None:
    """Run the interactive CLI menu loop."""
    print("Welcome to the Earnings Transcript Teacher!")
    print("===========================================")
    
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    
    while True:
        print("\nMain Menu:")
        print("1. Download & Ingest a new transcript")
        print("2. List transcripts in Database")
        print("3. Interactive Q&A (Open Exploration)")
        print("4. Start a Feynman learning session")
        print("5. View saved transcript details (Themes/Takeaways)")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            ticker = input("Enter the ticker symbol (e.g. MSFT): ").strip().upper()
            if not _validate_ticker(ticker):
                print("Invalid ticker. Please enter 1-5 letters (e.g. MSFT, AAPL).")
                continue
                
            print(f"\nDownloading transcript for {ticker}...")
            # Call the download bash script
            result = subprocess.run(["./download_transcript.sh", ticker])
            
            if result.returncode != 0:
                print("Failed to download transcript. Check your API_NINJAS_KEY and ticker symbol.")
            else:
                print("\nIngesting and analyzing transcript...")
                try:
                    analysis = analyze(ticker)
                    display(analysis)
                    print(f"\nSaving analysis to database ({conn_str})...")
                    save_analysis(conn_str, analysis)
                    print("Successfully saved to database.")
                except Exception as e:
                    print(f"Error analyzing or saving transcript: {e}", file=sys.stderr)
                    
        elif choice == "2":
            calls = get_all_calls(conn_str)
            if not calls:
                print("\nNo transcripts found in the database. Try downloading one first!")
            else:
                print(f"\nFound {len(calls)} transcripts in database:")
                for ticker, quarter in calls:
                    print(f"  - {ticker} ({quarter})")
                    
        elif choice == "4":
            ticker = input("Enter the ticker symbol to study: ").strip().upper()
            if not _validate_ticker(ticker):
                print("Invalid ticker. Please enter 1-5 letters (e.g. MSFT, AAPL).")
            else:
                calls = get_all_calls(conn_str)
                saved_tickers = [c[0] for c in calls]
                
                if ticker not in saved_tickers:
                    print(f"\nTranscript for {ticker} not found in the database.")
                    print("Please use Option 1 to download and ingest it first.")
                else:
                    print(f"\nStarting Feynman session on {ticker}...")
                    
                    level = input("\nWhat is your current knowledge level? (Beginner/Intermediate/Advanced): ").strip().lower()
                    
                    if level == "beginner":
                        themes = get_themes_for_ticker(conn_str, ticker)
                        takeaways = get_takeaways_for_ticker(conn_str, ticker)
                        
                        while True:
                            print("\n--- Beginner Learning Options ---")
                            print("1. Explore vocabulary and jargon")
                            print("2. Analyze key takeaways")
                            print("3. Continue to Feynman learning loop (Select a specific topic)")
                            
                            sub_choice = input("\nEnter your choice (1-3): ").strip()
                            
                            if sub_choice == "1":
                                jargon_terms = get_extracted_terms_for_ticker(conn_str, ticker, limit=10)
                                if not jargon_terms:
                                    raw_keywords = get_keywords_for_ticker(conn_str, ticker, limit=10)
                                    jargon_terms = [(k, "A frequently used keyword in this call.", "") for k in raw_keywords]

                                if jargon_terms:
                                    print("\nExtracting key financial jargon for beginners...")
                                    terms_str = "\n".join(f"- {term}: {definition}" for term, definition, _ in jargon_terms)
                                    user_input = f"Here is a list of financial jargon and terms from the transcript:\n{terms_str}\n\nPlease explain the most important ones simply to a beginner."
                                    
                                    try:
                                        with open(_PROMPTS_DIR / "00_beginner_jargon.md", "r") as f:
                                            sys_prompt = f.read()
                                    except FileNotFoundError:
                                        sys_prompt = "You are a friendly mentor explaining financial jargon simply to a beginner. Explain these terms."
                                        
                                    print("\nTeacher: ", end="", flush=True)
                                    try:
                                        usage_stats = None
                                        for chunk in stream_chat([{"role": "user", "content": user_input}], sys_prompt):
                                            if isinstance(chunk, dict):
                                                usage_stats = chunk
                                                continue
                                            print(chunk, end="", flush=True)
                                        
                                        if usage_stats:
                                            print(f"\n\n[Stats | Model: {usage_stats.get('model', 'Unknown')} | Input Tokens: {usage_stats.get('usage', {}).get('prompt_tokens', 0)} | Output Tokens: {usage_stats.get('usage', {}).get('completion_tokens', 0)}]")
                                    except Exception as e:
                                        print(f"[Error: {e}]", end="")
                                    print("\n")
                                else:
                                    print("\nNo jargon found for this transcript.")
                            elif sub_choice == "2":
                                if takeaways:
                                    print("\nAnalyzing key takeaways and their significance based on the transcript...")
                                    
                                    takeaway_embs = get_embeddings([t[0] for t in takeaways])
                                    context_spans = []
                                    if takeaway_embs:
                                        for emb in takeaway_embs:
                                            if emb:
                                                spans = search_spans(conn_str, ticker, emb, top_k=2)
                                                context_spans.extend(spans)
                                    
                                    seen_spans = set()
                                    unique_context = []
                                    for span in context_spans:
                                        if span not in seen_spans:
                                            unique_context.append(span)
                                            seen_spans.add(span)
                                    
                                    context_str = "\n".join(f"- {span}" for span in unique_context)
                                    takeaways_str = "\n".join(f"- {t[0]}: {t[1]}" for t in takeaways)
                                    
                                    user_input = f"Here are the key takeaways:\n{takeaways_str}\n\n<transcript_context>\n{context_str}\n</transcript_context>\n\nPlease explain why these takeaways are significant."
                                    
                                    try:
                                        with open(_PROMPTS_DIR / "00_beginner_takeaways.md", "r") as f:
                                            sys_prompt = f.read()
                                    except FileNotFoundError:
                                        sys_prompt = "You are a helpful expert. Explain why the following key takeaways are significant based on the provided transcript context."

                                    print("\nTeacher: ", end="", flush=True)
                                    try:
                                        usage_stats = None
                                        for chunk in stream_chat([{"role": "user", "content": user_input}], sys_prompt):
                                            if isinstance(chunk, dict):
                                                usage_stats = chunk
                                                continue
                                            print(chunk, end="", flush=True)
                                        
                                        if usage_stats:
                                            print(f"\n\n[Stats | Model: {usage_stats.get('model', 'Unknown')} | Input Tokens: {usage_stats.get('usage', {}).get('prompt_tokens', 0)} | Output Tokens: {usage_stats.get('usage', {}).get('completion_tokens', 0)}]")
                                    except Exception as e:
                                        print(f"[Error: {e}]", end="")
                                    print("\n")
                                else:
                                    print("\nNo takeaways found for this transcript.")
                            elif sub_choice == "3":
                                if themes:
                                    print(f"\nHere are some key themes discussed in the {ticker} transcript:")
                                    for idx, t in enumerate(themes, 1):
                                        print(f"  {idx}. {t}")
                                topic = input("\nWhat specific topic would you like to master? ").strip()
                                break
                            else:
                                print("\nInvalid choice. Please enter 1, 2, or 3.")
                    else:
                        topic = input("\nWhat topic from the transcript would you like to master? ").strip()
                        
                    if not topic:
                        continue
                        
                    state = 1
                    messages = []
                    print("\nType your responses below. Type 'exit' to return to the main menu.")
                    
                    while state <= 5:
                        prompt_files = {
                            1: "prompts/feynman/01_initial_explanation.md",
                            2: "prompts/feynman/02_gap_analysis.md",
                            3: "prompts/feynman/03_guided_refinement.md",
                            4: "prompts/feynman/04_understanding_test.md",
                            5: "prompts/feynman/05_teaching_note.md",
                        }
                        
                        try:
                            with open(prompt_files[state], "r") as f:
                                system_prompt = f.read()
                        except FileNotFoundError:
                            print(f"\nError: Could not find {prompt_files[state]}")
                            break
                            
                        # 0. Get Input based on State
                        if state == 1:
                            user_input = f"I want to learn about: {topic}"
                        elif state == 5:
                            user_input = "I am ready for the ultimate teaching note."
                        else:
                            user_input = input("\nYou: ").strip()
                            if user_input.lower() in ["exit", "quit"]:
                                print("\nEnding session.")
                                break
                            if not user_input:
                                continue
                                
                        # 1. RAG Retrieve
                        query_embs = get_embeddings([user_input])
                        context_spans = []
                        if query_embs and query_embs[0]:
                            context_spans = search_spans(conn_str, ticker, query_embs[0], top_k=3)
                            
                        # 2. Inject Context (Ephemeral)
                        api_messages = list(messages)
                        augmented_input = user_input
                        if context_spans:
                            context_str = "\n".join(f"- {span}" for span in context_spans)
                            augmented_input = f"{user_input}\n\n<transcript_context>\n{context_str}\n</transcript_context>"
                            
                        api_messages.append({"role": "user", "content": augmented_input})
                        
                        # Add raw input to actual persistent history (only if it wasn't a hidden system prompt like state 1 or 5)
                        if state not in [1, 5]:
                            messages.append({"role": "user", "content": user_input})
                        else:
                             messages.append({"role": "user", "content": f"*[Proceeding to State {state}]*"})
                        
                        # 3. Stream Response
                        print("\nTeacher: ", end="", flush=True)
                        assistant_response = ""
                        usage_stats = None
                        try:
                            for chunk in stream_chat(api_messages, system_prompt):
                                if isinstance(chunk, dict):
                                    usage_stats = chunk
                                    continue
                                    
                                print(chunk, end="", flush=True)
                                assistant_response += chunk
                                
                            if usage_stats:
                                print(f"\n\n[Stats | Model: {usage_stats.get('model', 'Unknown')} | Input Tokens: {usage_stats.get('usage', {}).get('prompt_tokens', 0)} | Output Tokens: {usage_stats.get('usage', {}).get('completion_tokens', 0)}]")
                        except Exception as e:
                            print(f"[Error: {e}]", end="")
                        print()
                        
                        # Add the raw response to history
                        messages.append({"role": "assistant", "content": assistant_response})
                        
                        # 4. State Transitions
                        if state in [1, 2, 4]:
                            state += 1
                        elif state == 3:
                            advance = input("\n[System] Ready to test your understanding? (y/n): ").strip().lower()
                            if advance == 'y':
                                state += 1
                        elif state == 5:
                            print("\n[System] Feynman Session Complete!")
                            break
                        
        elif choice == "5":
            ticker = input("Enter the ticker symbol to view: ").strip().upper()
            if not _validate_ticker(ticker):
                print("Invalid ticker. Please enter 1-5 letters (e.g. MSFT, AAPL).")
            else:
                calls = get_all_calls(conn_str)
                saved_tickers = [c[0] for c in calls]
                
                if ticker not in saved_tickers:
                    print(f"\nTranscript for {ticker} not found in the database.")
                    print("Please use Option 1 to download and ingest it first.")
                else:
                    themes = get_themes_for_ticker(conn_str, ticker)
                    takeaways = get_takeaways_for_ticker(conn_str, ticker)
                    keywords = get_keywords_for_ticker(conn_str, ticker)
                    
                    print(f"\n--- Analysis Details for {ticker} ---")
                    
                    if themes:
                        print("\nAgentic Themes:")
                        for idx, t in enumerate(themes, 1):
                            print(f"  {idx}. {t}")
                            
                    if keywords:
                        # De-duplicate keywords by converting to lowercase set but keeping order
                        seen = set()
                        unique_kw = [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))]
                        print("\nTop TF-IDF Keywords:")
                        # Print as a nice comma-separated list
                        print(f"  {', '.join(unique_kw)}")
                            
                    if takeaways:
                        print("\nAgentic Key Takeaways:")
                        for text, why in takeaways:
                            print(f"  - {text}")
                            print(f"    Significance: {why}")
                            
                    if not any([themes, takeaways, keywords]):
                        print("\nNo detailed analysis found for this transcript.")
                        
        elif choice == "3":
            ticker = input("Enter the ticker symbol to study: ").strip().upper()
            if not _validate_ticker(ticker):
                print("Invalid ticker. Please enter 1-5 letters (e.g. MSFT, AAPL).")
            else:
                calls = get_all_calls(conn_str)
                saved_tickers = [c[0] for c in calls]
                
                if ticker not in saved_tickers:
                    print(f"\nTranscript for {ticker} not found in the database.")
                    print("Please use Option 1 to download and ingest it first.")
                else:
                    print(f"\nStarting Interactive Q&A on {ticker}...")
                    
                    # Generate some suggested questions
                    themes = get_themes_for_ticker(conn_str, ticker)
                    takeaways = get_takeaways_for_ticker(conn_str, ticker, limit=2)
                    
                    suggestions = []
                    if takeaways:
                        suggestions.append(f"Can you explain why '{takeaways[0][0][:50]}...' is a key takeaway?")
                        if len(takeaways) > 1:
                            suggestions.append(f"What does the transcript say regarding '{takeaways[1][0][:50]}...'?")
                    if themes:
                        top_theme = themes[0][:50]
                        suggestions.append(f"Can you summarize the discussion around '{top_theme}...'?")
                        
                    suggestions.append("What financial jargon is used in this transcript?")
                        
                    if suggestions:
                        print("\nHere are a few suggested questions to explore:")
                        for idx, s in enumerate(suggestions, 1):
                            print(f"  {idx}. {s}")
                            
                    try:
                        with open(_PROMPTS_DIR / "00_general_qa.md", "r") as f:
                            system_prompt = f.read()
                    except FileNotFoundError:
                        system_prompt = "You are a helpful expert answering questions using the transcript context."
                        
                    messages = []
                    print("\nType your questions below. Type 'exit' to return to the main menu.")
                    
                    while True:
                        user_input = input("\nYou: ").strip()
                        if user_input.lower() in ["exit", "quit"]:
                            print("\nEnding session.")
                            break
                        if not user_input:
                            continue
                            
                        # 1. RAG Retrieve
                        query_embs = get_embeddings([user_input])
                        context_spans = []
                        if query_embs and query_embs[0]:
                            context_spans = search_spans(conn_str, ticker, query_embs[0], top_k=4)
                            
                        # If user asks about jargon/vocabulary, explicitly inject it
                        lower_input = user_input.lower()
                        if any(w in lower_input for w in ["jargon", "vocabulary", "terms"]):
                            jargon = get_extracted_terms_for_ticker(conn_str, ticker, limit=10)
                            if jargon:
                                jargon_str = "Extracted Jargon:\n" + "\n".join([f"- {term}: {definition}" for term, definition in jargon])
                                context_spans.append(jargon_str)
                            
                        # 2. Inject Context (Ephemeral)
                        api_messages = list(messages)
                        augmented_input = user_input
                        if context_spans:
                            context_str = "\n".join(f"- {span}" for span in context_spans)
                            augmented_input = f"{user_input}\n\n<transcript_context>\n{context_str}\n</transcript_context>"
                            
                        api_messages.append({"role": "user", "content": augmented_input})
                        messages.append({"role": "user", "content": user_input})
                        
                        # 3. Stream Response
                        print("\nTeacher: ", end="", flush=True)
                        assistant_response = ""
                        usage_stats = None
                        try:
                            for chunk in stream_chat(api_messages, system_prompt):
                                if isinstance(chunk, dict):
                                    usage_stats = chunk
                                    continue
                                    
                                print(chunk, end="", flush=True)
                                assistant_response += chunk
                                
                            if usage_stats:
                                print(f"\n\n[Stats | Model: {usage_stats.get('model', 'Unknown')} | Input Tokens: {usage_stats.get('usage', {}).get('prompt_tokens', 0)} | Output Tokens: {usage_stats.get('usage', {}).get('completion_tokens', 0)}]")
                        except Exception as e:
                            print(f"[Error: {e}]", end="")
                        print()
                        
                        # Add the raw response to history
                        messages.append({"role": "assistant", "content": assistant_response})
                        
        elif choice == "6":
            print("\nGoodbye!")
            break
            
        else:
            print("\nInvalid choice. Please enter a number between 1 and 6.")
