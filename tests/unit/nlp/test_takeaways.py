import pytest
import textwrap
from nlp.takeaways import extract_takeaways

def test_extract_takeaways_basic():
    # textwrap.dedent prevents leading spaces which break the ^ speaker regex
    text = textwrap.dedent("""\
    Operator:
    Welcome to the call.
    Satya Nadella:
    Thank you. This was a record quarter for our cloud division. We saw 50% year-over-year growth. 
    We expect this trend to continue as more enterprise customers migrate their workloads.
    Amy Hood:
    I want to add that our margins improved sequentially. This gives us great confidence for the next year.
    Operator:
    Next question.
    """)
    
    takeaways = extract_takeaways(text, top_n=2)
    
    # We should get a maximum of 2 takeaways
    # Text must have at least 3 attributed sentences to run TextRank
    assert len(takeaways) == 2
    
    # TextRank should identify the most central sentences.
    # We are just verifying that the text extraction contains real sentences we provided.
    text_content = [t.text for t in takeaways]
    has_growth = any("50%" in t for t in text_content)
    has_margins = any("margins" in t for t in text_content)
    assert has_growth or has_margins

def test_extract_takeaways_empty():
    assert extract_takeaways("") == []

def test_extract_takeaways_short():
    assert len(extract_takeaways("Just one sentence.")) == 0
