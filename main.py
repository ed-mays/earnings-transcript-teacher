from transcript.loader import read_text_file, extract_transcript_text
from transcript.analysis import clean_text, tokenize, count_word_frequency
from transcript.sections import extract_transcript_sections, extract_qa_pairs


def main(file_path: str = "./transcripts/CLOV Q3 2025 Earnings Transcript.json") -> None:
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    tokens = tokenize(clean_text(raw_text))
    word_counts = count_word_frequency(tokens)
    print(f"Token count: {len(tokens)}")
    # print(f"Top 10 words: {word_counts[:10]}")

    prepared_remarks, qa = extract_transcript_sections(raw_text)
    print(f"Prepared Remarks: {len(prepared_remarks)} chars")
    print(f"Q&A: {len(qa)} chars")

    qa_pairs = extract_qa_pairs(raw_text)
    print(f"\nQ&A pairs found: {len(qa_pairs)}")
    for i, (question, answer) in enumerate(qa_pairs[:3], start=1):
        print(f"\n--- Pair {i} ---")
        print(f"Q: {question[:200]}")
        print(f"A: {answer[:200]}")


if __name__ == "__main__":
    main()