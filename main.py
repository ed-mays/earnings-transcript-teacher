from transcript.loader import read_text_file, extract_transcript_text
from transcript.analysis import clean_text, tokenize, count_word_frequency
from transcript.keywords import extract_keywords
from transcript.themes import extract_themes
from transcript.takeaways import extract_takeaways
from transcript.sections import extract_transcript_sections, extract_qa_exchanges, enrich_speakers


def main(file_path: str = "./transcripts/MSFT.json") -> None:
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    print("Basic stats:")
    tokens = tokenize(clean_text(raw_text))
    word_counts = count_word_frequency(tokens)
    print(f"Token count: {len(tokens)}")
    # print(f"Top 10 words: {word_counts[:10]}")

    print("\nSection Extraction")
    prepared_remarks, qa = extract_transcript_sections(raw_text)
    print(f"Prepared Remarks: {len(prepared_remarks)} chars")
    print(f"Q&A: {len(qa)} chars")

    print("\nSpeaker Identification")
    profiles = enrich_speakers(raw_text, prepared_remarks, qa)
    print(f"Speakers ({len(profiles)} unique):")
    for p in profiles:
        detail = p.title or p.firm or ""
        detail_str = f", {detail}" if detail else ""
        print(f"  [{p.role:<10}] {p.name}{detail_str} ({p.turn_count} turn{'s' if p.turn_count != 1 else ''})")

    print("\nQ&A Exchange Extraction")
    exchanges = extract_qa_exchanges(qa, prepared_remarks=prepared_remarks)
    print(f"\nQ&A exchanges found: {len(exchanges)}")
    for i, exchange in enumerate(exchanges[:3], start=1):
        print(f"\n--- Exchange {i} ({len(exchange)} turns) ---")
        for speaker, text in exchange:
            print(f"  {speaker}: {text}")

    print("\nKeyword Extraction (TF-IDF)")
    keywords = extract_keywords(raw_text)
    for term, score in keywords:
        print(f"  {score:.4f}  {term}")

    print("\nTheme Extraction (NMF)")
    themes = extract_themes(raw_text)
    for topic in themes:
        print(f"  Topic {topic.label + 1}: {', '.join(topic.terms)}")

    print("\nKey Takeaways (TextRank)")
    takeaways = extract_takeaways(raw_text)
    for i, t in enumerate(takeaways, 1):
        print(f"  {i}. [{t.speaker}] {t.text}")


if __name__ == "__main__":
    main()