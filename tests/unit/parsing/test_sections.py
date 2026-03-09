import pytest
import textwrap
from parsing.sections import (
    extract_transcript_sections,
    enrich_speakers,
    extract_qa_exchanges,
    _is_questioner
)

def test_extract_transcript_sections_splits_correctly():
    raw_text = textwrap.dedent("""\
    Good morning. We will begin with prepared remarks.
    Operator:
    Thank you. Please go ahead.
    Satya Nadella:
    Welcome to our earnings call. This was a great quarter.
    Operator:
    We will now open the floor for questions.
    John Doe:
    Hi, great quarter. Can you explain the cloud numbers?
    Satya:
    Yes, they went up.
    """)
    prepared, qa = extract_transcript_sections(raw_text)
    
    assert "Welcome to our earnings call." in prepared
    assert "Can you explain the cloud numbers?" not in prepared
    assert "Can you explain the cloud numbers?" in qa
    assert "Welcome to our earnings call." not in qa

def test_extract_transcript_sections_missing_qa_fallback():
    raw_text = textwrap.dedent("""\
    Good morning.
    Satya Nadella:
    Welcome to our earnings call. This was a great quarter.
    """)
    prepared, qa = extract_transcript_sections(raw_text)
    
    assert "Welcome to our earnings call" in prepared
    assert qa == ""

def test_enrich_speakers():
    raw_text = textwrap.dedent("""\
    Operator:
    Welcome to the call. I will turn it over to Satya Nadella, Chairman and CEO.
    Satya Nadella:
    Thank you.
    Operator:
    The next question is from the line of Jane Smith with UBS.
    Jane Smith:
    Hi, thanks.
    """)
    prepared = textwrap.dedent("""\
    Operator:
    Welcome to the call. I will turn it over to Satya Nadella, Chairman and CEO.
    Satya Nadella:
    Thank you.
    """)
    qa = textwrap.dedent("""\
    Operator:
    The next question is from the line of Jane Smith with UBS.
    Jane Smith:
    Hi, thanks.
    """)
    
    profiles = enrich_speakers(raw_text, prepared, qa)
    
    assert len(profiles) == 3
    
    operator = next((p for p in profiles if p.name == "Operator"), None)
    satya = next((p for p in profiles if p.name == "Satya Nadella"), None)
    jane = next((p for p in profiles if p.name == "Jane Smith"), None)
    
    assert operator is not None
    assert operator.role == "operator"
    
    assert satya is not None
    assert satya.role == "executive"
    assert satya.title == "Chairman and CEO"
    
    assert jane is not None
    assert jane.role == "analyst"

def test_is_questioner():
    executives = {"Satya Nadella", "Amy Hood"}
    assert _is_questioner("Satya Nadella", executives) is False
    assert _is_questioner("Operator", executives) is False
    assert _is_questioner("Jane Smith", executives) is True
