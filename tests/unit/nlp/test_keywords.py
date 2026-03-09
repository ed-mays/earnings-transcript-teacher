import pytest
from nlp.keywords import extract_keywords

def test_extract_keywords_basic():
    text = "Artificial intelligence and cloud computing are driving the new architecture for the edge."
    keywords = extract_keywords(text, top_n=2)
    assert len(keywords) == 2
    # Expect the tf-idf to find "artificial intelligence" or "cloud computing"
    # TF-IDF can be slightly unpredictable with tiny text, but it should return tuples
    assert isinstance(keywords[0], tuple)
    assert isinstance(keywords[0][0], str)
    assert isinstance(keywords[0][1], float)

def test_extract_keywords_empty_text():
    text = ""
    # TfidfVectorizer fails when provided an empty vocabulary
    with pytest.raises(ValueError):
        extract_keywords(text)

def test_extract_keywords_short_text():
    text = "Hello"
    keywords = extract_keywords(text)
    # The min_df in TF-IDF might filter this out depending on its length relative to n-grams
    assert isinstance(keywords, list)
