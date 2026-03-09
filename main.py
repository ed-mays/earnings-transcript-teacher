import sys

from transcript.loader import read_text_file, extract_transcript_text
from transcript.analysis import clean_text, tokenize, count_word_frequency
from transcript.keywords import extract_keywords
from transcript.themes import extract_themes
from transcript.takeaways import extract_takeaways
from transcript.sections import (
    extract_transcript_sections,
    extract_qa_exchanges,
    extract_spans,
    enrich_speakers,
)
from transcript.models import (
    CallAnalysis,
    CallRecord,
    SpanRecord,
    KeywordRecord,
    TopicRecord,
    QAPairRecord,
)
from transcript.embedder import get_embeddings
import os
import subprocess

try:
    from db.persistence import fetch_existing_embeddings, get_all_calls, search_spans, get_topics_for_ticker, get_takeaways_for_ticker, get_keywords_for_ticker
except ImportError:
    # If psycopg isn't installed or db module fails, stub it
    def fetch_existing_embeddings(conn_str, ticker, quarter):
        return {}
    def get_all_calls(conn_str):
        return []
    def search_spans(conn_str, ticker, query_vector, top_k=5):
        return []
    def get_topics_for_ticker(conn_str, ticker, limit=5):
        return []
    def get_takeaways_for_ticker(conn_str, ticker, limit=3):
        return []
    def get_keywords_for_ticker(conn_str, ticker, limit=15):
        return []

try:
    from transcript.chat_client import stream_chat
except ImportError:
    def stream_chat(messages, system_prompt, model="sonar-pro"):
        yield "Error: LLM client not available."


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def analyze(ticker: str = "MSFT") -> CallAnalysis:
    """Run the full analysis pipeline and return structured results."""
    ticker = ticker.upper()
    file_path = f"./transcripts/{ticker}.json"
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    # Basic stats
    tokens = tokenize(clean_text(raw_text))

    # Sections
    prepared_remarks, qa = extract_transcript_sections(raw_text)

    # Call record
    call = CallRecord(
        ticker=ticker,
        transcript_json=content,
        transcript_text=raw_text,
        token_count=len(tokens),
        prepared_len=len(prepared_remarks),
        qa_len=len(qa),
    )

    # Speakers
    speakers = enrich_speakers(raw_text, prepared_remarks, qa)

    # Spans
    raw_spans = extract_spans(raw_text, prepared_remarks, qa)
    span_records = [
        SpanRecord(
            call_id=call.id,
            speaker_name=speaker,
            section=section,
            span_type="turn",
            sequence_order=order,
            text=text,
        )
        for speaker, section, text, order in raw_spans
    ]

    # Embeddings
    # 1. Try to load cached embeddings from Postgres
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    # Using the same placeholder quarter as persistence.py for now
    fiscal_quarter = f"Q? {ticker}"
    embedding_cache = fetch_existing_embeddings(conn_str, ticker, fiscal_quarter)

    # 2. Separate spans into cache hits and cache misses
    spans_to_embed = []
    for span in span_records:
        if span.text in embedding_cache:
            span.embedding = embedding_cache[span.text]
        else:
            spans_to_embed.append(span)

    # 3. Call Voyage API only for the misses
    new_embeddings = None
    if spans_to_embed:
        texts_to_embed = [s.text for s in spans_to_embed]
        new_embeddings = get_embeddings(texts_to_embed)
        if new_embeddings and len(new_embeddings) == len(spans_to_embed):
            for span, emb in zip(spans_to_embed, new_embeddings):
                span.embedding = emb

    api_count = len(spans_to_embed) if new_embeddings else 0
    cached_count = len(span_records) - len(spans_to_embed)
    
    # Store these counts temporarily on the call object so display() can show them
    call.cached_embeddings_count = cached_count
    call.api_embeddings_count = api_count

    # Build a lookup: (speaker_name, text_prefix) -> SpanRecord for linking

    span_lookup: dict[tuple[str, str], SpanRecord] = {}
    for s in span_records:
        key = (s.speaker_name, s.text[:80])
        span_lookup[key] = s

    # Keywords
    keyword_results = extract_keywords(raw_text)
    keywords = [
        KeywordRecord(term=term, score=score)
        for term, score in keyword_results
    ]

    # Topics
    theme_results = extract_themes(raw_text)
    topics = [
        TopicRecord(
            label=t.label,
            terms=t.terms,
            weight=t.weight,
            rank_order=rank,
        )
        for rank, t in enumerate(theme_results, 1)
    ]

    # Takeaways — link back to span records
    takeaway_results = extract_takeaways(raw_text)
    takeaway_spans: list[SpanRecord] = []
    for t in takeaway_results:
        key = (t.speaker, t.text[:80])
        if key in span_lookup:
            span = span_lookup[key]
            span.textrank_score = t.score
            takeaway_spans.append(span)
        else:
            # Takeaway didn't match a span (e.g. sentence-level split);
            # create a standalone span for it.
            takeaway_span = SpanRecord(
                call_id=call.id,
                speaker_name=t.speaker,
                section="qa",
                span_type="turn",
                sequence_order=-1,
                text=t.text,
                textrank_score=t.score,
            )
            takeaway_spans.append(takeaway_span)

    # Q&A pairs — link exchanges to span IDs
    exchanges = extract_qa_exchanges(qa, prepared_remarks=prepared_remarks)
    qa_pairs: list[QAPairRecord] = []

    # Build a set of known executive names for classifying Q&A turns.
    exec_names = {
        p.name for p in speakers if p.role == "executive"
    }

    for exchange_idx, exchange in enumerate(exchanges, 1):
        q_ids = []
        a_ids = []
        for speaker, text in exchange:
            key = (speaker, text[:80])
            span = span_lookup.get(key)
            if span:
                if speaker.lower() == "operator" or speaker in exec_names:
                    a_ids.append(span.id)
                else:
                    q_ids.append(span.id)

        if q_ids or a_ids:
            qa_pairs.append(QAPairRecord(
                exchange_order=exchange_idx,
                question_span_ids=q_ids,
                answer_span_ids=a_ids,
            ))

    return CallAnalysis(
        call=call,
        speakers=speakers,
        spans=span_records,
        keywords=keywords,
        topics=topics,
        takeaways=takeaway_spans,
        qa_pairs=qa_pairs,
    )


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display(result: CallAnalysis) -> None:
    """Print the analysis results to console."""
    call = result.call

    print(f"Analysing {call.ticker}")
    print("=" * 40)

    print("\nBasic stats:")
    print(f"Token count: {call.token_count}")

    print("\nSection Extraction")
    print(f"Prepared Remarks: {call.prepared_len} chars")
    print(f"Q&A: {call.qa_len} chars")

    print("\nSpeaker Identification")
    print(f"Speakers ({len(result.speakers)} unique):")
    for p in result.speakers:
        detail = p.title or p.firm or ""
        detail_str = f", {detail}" if detail else ""
        print(f"  [{p.role:<10}] {p.name}{detail_str} ({p.turn_count} turn{'s' if p.turn_count != 1 else ''})")

    print("\nQ&A Exchange Extraction")
    print(f"\nQ&A exchanges found: {len(result.qa_pairs)}")
    # Show first 3 exchanges using span data
    exec_names = {p.name for p in result.speakers if p.role == "executive"}
    span_by_id = {s.id: s for s in result.spans}
    for pair in result.qa_pairs[:3]:
        all_ids = pair.question_span_ids + pair.answer_span_ids
        turns = [(span_by_id[sid].speaker_name, span_by_id[sid].text)
                 for sid in all_ids if sid in span_by_id]
        print(f"\n--- Exchange {pair.exchange_order} ({len(turns)} turns) ---")
        for speaker, text in turns:
            print(f"  {speaker}: {text}")

    print("\nKeyword Extraction (TF-IDF)")
    for kw in result.keywords:
        print(f"  {kw.score:.4f}  {kw.term}")

    print("\nTheme Extraction (NMF)")
    for topic in result.topics:
        print(f"  Topic {topic.label + 1}: {', '.join(topic.terms)}")

    print("\nKey Takeaways (TextRank)")
    for i, t in enumerate(result.takeaways, 1):
        print(f"  {i}. [{t.speaker_name}] {t.text}")
        
    print("\nSemantic Search")
    num_embeddings = sum(1 for s in result.spans if s.embedding is not None)
    if num_embeddings > 0:
        cached = getattr(call, "cached_embeddings_count", 0)
        api = getattr(call, "api_embeddings_count", 0)
        print(f"  {num_embeddings} span embeddings available")
        print(f"    - {cached} loaded from Postgres cache")
        print(f"    - {api} generated via Voyage AI API")
    else:
        print("  Skipped (VOYAGE_API_KEY not set)")


# ---------------------------------------------------------------------------
# Interactive Menu
# ---------------------------------------------------------------------------

def interactive_menu() -> None:
    """Run the interactive CLI menu loop."""
    print("Welcome to the Earnings Transcript Teacher!")
    print("===========================================")
    
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    from db.persistence import save_analysis, get_all_calls, get_topics_for_ticker, get_takeaways_for_ticker, get_keywords_for_ticker
    
    while True:
        print("\nMain Menu:")
        print("1. Download & Ingest a new transcript")
        print("2. List transcripts in Database")
        print("3. Start a Feynman learning session")
        print("4. View saved transcript details (Themes/Takeaways)")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            ticker = input("Enter the ticker symbol (e.g. MSFT): ").strip().upper()
            if not ticker:
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
                    from db.persistence import save_analysis
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
                    
        elif choice == "3":
            ticker = input("Enter the ticker symbol to study: ").strip().upper()
            if ticker:
                calls = get_all_calls(conn_str)
                saved_tickers = [c[0] for c in calls]
                
                if ticker not in saved_tickers:
                    print(f"\nTranscript for {ticker} not found in the database.")
                    print("Please use Option 1 to download and ingest it first.")
                else:
                    print(f"\nStarting Feynman session on {ticker}...")
                    
                    level = input("\nWhat is your current knowledge level? (Beginner/Intermediate/Advanced): ").strip().lower()
                    
                    if level == "beginner":
                        topics = get_topics_for_ticker(conn_str, ticker)
                        takeaways = get_takeaways_for_ticker(conn_str, ticker)
                        
                        if topics:
                            print(f"\nSince you are a beginner, here are some key themes discussed in the {ticker} transcript:")
                            for idx, t in enumerate(topics, 1):
                                print(f"  {idx}. {', '.join(t)}")
                                
                        if takeaways:
                            print("\nAnalyzing key takeaways and their significance based on the transcript...")
                            
                            takeaway_embs = get_embeddings(takeaways)
                            context_spans = []
                            for emb in takeaway_embs:
                                if emb:
                                    # Get top 2 spans per takeaway to build a comprehensive context
                                    spans = search_spans(conn_str, ticker, emb, top_k=2)
                                    context_spans.extend(spans)
                            
                            # Deduplicate spans while preserving order if possible
                            seen_spans = set()
                            unique_context = []
                            for span in context_spans:
                                if span not in seen_spans:
                                    unique_context.append(span)
                                    seen_spans.add(span)
                            
                            context_str = "\n".join(f"- {span}" for span in unique_context)
                            takeaways_str = "\n".join(f"- {t}" for t in takeaways)
                            
                            user_input = f"Here are the key takeaways:\n{takeaways_str}\n\n<transcript_context>\n{context_str}\n</transcript_context>\n\nPlease explain why these takeaways are significant."
                            
                            try:
                                with open("prompts/feynman/00_beginner_takeaways.md", "r") as f:
                                    sys_prompt = f.read()
                            except FileNotFoundError:
                                sys_prompt = "You are a helpful expert. Explain why the following key takeaways are significant based on the provided transcript context."

                            print("\nTeacher: ", end="", flush=True)
                            try:
                                for chunk in stream_chat([{"role": "user", "content": user_input}], sys_prompt):
                                    print(chunk, end="", flush=True)
                            except Exception as e:
                                print(f"[Error: {e}]", end="")
                            print("\n")
                                
                        topic = input("\nBased on these, what specific topic would you like to master? ").strip()
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
                        try:
                            for chunk in stream_chat(api_messages, system_prompt):
                                print(chunk, end="", flush=True)
                                assistant_response += chunk
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
                        
        elif choice == "4":
            ticker = input("Enter the ticker symbol to view: ").strip().upper()
            if ticker:
                calls = get_all_calls(conn_str)
                saved_tickers = [c[0] for c in calls]
                
                if ticker not in saved_tickers:
                    print(f"\nTranscript for {ticker} not found in the database.")
                    print("Please use Option 1 to download and ingest it first.")
                else:
                    topics = get_topics_for_ticker(conn_str, ticker)
                    takeaways = get_takeaways_for_ticker(conn_str, ticker)
                    keywords = get_keywords_for_ticker(conn_str, ticker)
                    
                    print(f"\n--- Analysis Details for {ticker} ---")
                    
                    if topics:
                        print("\nNMF Themes (Topic Clusters):")
                        for idx, t in enumerate(topics, 1):
                            print(f"  {idx}. {', '.join(t)}")
                            
                    if keywords:
                        # De-duplicate keywords by converting to lowercase set but keeping order
                        seen = set()
                        unique_kw = [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))]
                        print("\nTop TF-IDF Keywords:")
                        # Print as a nice comma-separated list
                        print(f"  {', '.join(unique_kw)}")
                            
                    if takeaways:
                        print("\nTextRank Key Takeaways:")
                        for text in takeaways:
                            print(f"  - {text}")
                            
                    if not any([topics, takeaways, keywords]):
                        print("\nNo detailed analysis found for this transcript.")
                        
        elif choice == "5":
            print("\nGoodbye!")
            break
            
        else:
            print("\nInvalid choice. Please enter a number between 1 and 5.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import os
    
    # If run without arguments, use interactive menu
    if len(sys.argv) == 1:
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
    else:
        # Legacy CLI mode
        parser = argparse.ArgumentParser(description="Analyze an earnings transcript.")
        parser.add_argument("ticker", help="Ticker symbol (e.g., AAPL)")
        parser.add_argument("--save", action="store_true", help="Save results to Postgres")
        args = parser.parse_args()
    
        result = analyze(args.ticker)
        display(result)
    
        if args.save:
            from db.persistence import save_analysis
            conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
            print(f"\nSaving analysis to database ({conn_str})...")
            try:
                save_analysis(conn_str, result)
                print("Successfully saved to database.")
            except Exception as e:
                print(f"Error saving to database: {e}", file=sys.stderr)
                sys.exit(1)