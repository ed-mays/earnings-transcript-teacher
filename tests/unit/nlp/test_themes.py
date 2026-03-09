import textwrap
from nlp.themes import extract_themes

def test_extract_themes_basic():
    # Provide multiple distinct turns so NMF has enough sub-documents 
    # extract_themes splits by turns using _TURN_PATTERN. (requires First Last: )
    text = textwrap.dedent("""\
    Satya Nadella:
    We saw great growth in our cloud revenue this quarter. Cloud services are expanding.
    Amy Hood:
    Our hardware division also shipped two million units. The new hardware is popular.
    John Doe:
    What about the AI services?
    Satya Nadella:
    Yes, AI is doing well.
    """)
    # Note test length is 4 turns. extract_themes has check: if len(turns) < n_topics + 1
    # For n_topics=2, we need at least 3 turns. 4 is good. BUT "turns" filters for length > 50!
    # Let's make the turns longer than 50 chars to survive the filter.
    text = textwrap.dedent("""\
    Satya Nadella:
    We saw absolutely tremendous, industry-leading growth in our cloud revenue this quarter. Cloud infrastructure services are expanding across the globe.
    Amy Hood:
    Our hardware division also shipped over two million units this holiday season. The new consumer hardware lineup is proving to be incredibly popular everywhere.
    John Doe:
    What about the new generative AI services? Are they driving significant consumption at the edge?
    Satya Nadella:
    Yes, generative AI is doing exceptionally well and is a core driver of our continuous revenue expansion.
    """)
    themes = extract_themes(text, n_topics=2, terms_per_topic=2)
    
    assert len(themes) == 2
    assert themes[0].label == 0 or themes[0].label == 1
    assert len(themes[0].terms) == 2
    assert themes[0].weight > 0.0

def test_extract_themes_empty_text():
    text = ""
    themes = extract_themes(text)
    assert themes == []

def test_extract_themes_short_text():
    # Less than 3 valid turns
    text = textwrap.dedent("""\
    Satya Nadella:
    Cloud growth is doing incredibly well this quarter, driving 50% year-over-year gains in our core infrastructure.
    """)
    themes = extract_themes(text, n_topics=2)
    assert themes == []
