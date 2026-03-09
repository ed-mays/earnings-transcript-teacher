import json
from pathlib import Path


def read_text_file(file_path: str) -> str:
    """Reads the content of a text file and returns it as a string."""
    return Path(file_path).read_text(encoding="utf-8")


def extract_transcript_text(json_content: str) -> str:
    """Parses JSON content and returns the value of the 'transcript' key."""
    return json.loads(json_content)["transcript"]
