import json
import string, time
from pathlib import Path

# Common English function words (articles, prepositions, conjunctions, pronouns, auxiliaries, etc.)
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "nor", "so", "yet", "for", "of",
    "in", "on", "at", "to", "by", "up", "as", "is", "it", "its", "be",
    "am", "are", "was", "were", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may",
    "might", "must", "can", "could", "that", "this", "these", "those",
    "i", "we", "you", "he", "she", "they", "me", "us", "him", "her",
    "them", "my", "our", "your", "his", "their", "what", "which", "who",
    "whom", "when", "where", "why", "how", "if", "than", "then", "not",
    "no", "from", "with", "about", "into", "through", "during", "before",
    "after", "above", "below", "between", "each", "both", "all", "more",
    "also", "just", "very", "too", "well", "out", "over", "such", "own",
}

def read_text_file(file_path: str) -> str:
    """Reads the content of a text file using pathlib."""
    return Path(file_path).read_text(encoding="utf-8")

def extract_transcript_text(json_content: str) -> str:
    """Parses the JSON content and extracts the transcript text."""
    return json.loads(json_content)["transcript"]

def measure_execution_time(func):
    """Decorator to measure the execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"Function '{func.__name__}' executed in {end_time - start_time:.6f} seconds.")
        return result
    return wrapper

def count_word_frequency(words: list[str]) -> list[tuple[str, int]]:
    """Counts content word frequency, excluding common function words."""
    word_counts = {}
    for word in words:
        if word not in STOP_WORDS:
            word_counts[word] = word_counts.get(word, 0) + 1
    sorted_word_counts = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_word_counts

def extract_transcript_sections(transcript: str) -> tuple[str, str]:
    """Splits the transcript into 'Prepared Remarks' and 'Q&A' sections.

    Recognises a range of Q&A heading variants used across earnings transcript
    providers (e.g. Seeking Alpha, Motley Fool, S&P Capital IQ, Bloomberg).
    """
    prepared_remarks_marker = "Prepared Remarks"
    qa_markers = [
        "Questions and Answers",
        "Question-and-Answer",
        "Question and Answer",
        "Q&A Session",
        "Q&A",
        "Analyst Q&A",
        "Operator Q&A",
    ]

    prepared_remarks_index = transcript.find(prepared_remarks_marker)

    # Find the first Q&A marker that actually appears in the transcript
    qa_index = -1
    matched_qa_marker = ""
    for marker in qa_markers:
        idx = transcript.find(marker)
        if idx != -1:
            qa_index = idx
            matched_qa_marker = marker
            break

    if prepared_remarks_index == -1 or qa_index == -1:
        # Fall back gracefully if either section header is missing
        return transcript, ""

    prepared_remarks = transcript[prepared_remarks_index + len(prepared_remarks_marker):qa_index]
    qa = transcript[qa_index + len(matched_qa_marker):]
    return prepared_remarks, qa

@measure_execution_time
def clean_text(text: str) -> list[str]:
    """Converts text to lowercase, removes punctuation, and tokenizes into words."""
    cleaned = text.lower().translate(str.maketrans("", "", string.punctuation))
    return cleaned.split()

def main() -> None:
    file_path = "./transcripts/CLOV Q3 2025 Earnings Transcript.json"
    content = read_text_file(file_path)
    raw_transcript_text = extract_transcript_text(content)
    tokens = clean_text(raw_transcript_text)
    word_counts = count_word_frequency(tokens)
    print(f"Token count: {len(tokens)}")
    print(f"First 10 tokens: {tokens[:10]}")
    # print(f"Word counts: {word_counts}")
    transcript_sections = extract_transcript_sections(raw_transcript_text)
    print(f"Prepared Remarks: {len(transcript_sections[0])}")
    print(f"Q&A: {len(transcript_sections[1])}")

if __name__ == "__main__":
    main()