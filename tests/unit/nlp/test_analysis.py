from nlp.analysis import clean_text, tokenize, count_word_frequency

def test_clean_text():
    raw = "Hello   world! This is a TEST. \nNew line."
    expected = "hello   world this is a test \nnew line"
    assert clean_text(raw) == expected

def test_tokenize():
    # Tokenize simply calls text.split(), but doesn't remove stopwords!
    cleaned = "the quick brown fox jumps over the lazy dog in a test"
    tokens = tokenize(cleaned)
    assert "the" in tokens
    assert "a" in tokens
    assert "quick" in tokens
    assert len(tokens) == 12

def test_count_word_frequency():
    tokens = ["apple", "banana", "apple", "orange", "banana", "apple", "the", "a"]
    # Function will exclude 'the' and 'a' by default stop_words
    freq = count_word_frequency(tokens)
    # returns list of (word, count) tuples
    assert freq[0] == ("apple", 3)
    # Convert to dict to check others
    freq_dict = dict(freq)
    assert freq_dict.get("banana") == 2
    assert freq_dict.get("orange") == 1
    assert "the" not in freq_dict
    assert "a" not in freq_dict
