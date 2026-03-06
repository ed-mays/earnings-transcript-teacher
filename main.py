from transcript.loader import read_text_file, extract_transcript_text
from transcript.analysis import clean_text, tokenize, count_word_frequency
from transcript.sections import extract_transcript_sections, extract_qa_exchanges


def main(file_path: str = "./transcripts/MSFT.json") -> None:
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    tokens = tokenize(clean_text(raw_text))
    word_counts = count_word_frequency(tokens)
    print(f"Token count: {len(tokens)}")
    # print(f"Top 10 words: {word_counts[:10]}")

    prepared_remarks, qa = extract_transcript_sections(raw_text)
    print(f"Prepared Remarks: {len(prepared_remarks)} chars")
    print(f"Q&A: {len(qa)} chars")

    exchanges = extract_qa_exchanges(qa)
    print(f"\nQ&A exchanges found: {len(exchanges)}")
    for i, exchange in enumerate(exchanges[:3], start=1):
        print(f"\n--- Exchange {i} ({len(exchange)} turns) ---")
        for speaker, text in exchange:
            print(f"  {speaker}: {text[:120]}")


if __name__ == "__main__":
    main()