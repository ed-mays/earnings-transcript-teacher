import pytest
from parsing.loader import extract_transcript_text

def test_extract_transcript_text_valid_json():
    json_str = '{"transcript": "Hello world from Microsoft!"}'
    result = extract_transcript_text(json_str)
    assert result == "Hello world from Microsoft!"

def test_extract_transcript_text_missing_key():
    json_str = '{"other_key": "No text here"}'
    with pytest.raises(KeyError):
        extract_transcript_text(json_str)

def test_extract_transcript_text_invalid_json():
    json_str = 'Not a json array'
    with pytest.raises(Exception):
        extract_transcript_text(json_str)
