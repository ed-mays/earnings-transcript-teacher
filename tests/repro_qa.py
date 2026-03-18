import json
import re
import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from parsing.sections import QA_PATTERN, extract_transcript_sections

def test_detection(file_path):
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}: File not found")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    transcript = data.get('transcript', '')
    
    # Test 1: Regex Match Count
    matches = list(QA_PATTERN.finditer(transcript))
    print(f"\n--- File: {os.path.basename(file_path)} ---")
    print(f"Regex matches: {len(matches)}")
    
    # Test 2: Actual Extraction
    prepared, qa = extract_transcript_sections(transcript)
    print(f"Prepared length: {len(prepared)}")
    print(f"Q&A length:      {len(qa)}")
    
    if qa:
        # Show the first 100 chars of Q&A to verify boundary
        snippet = qa[:150].replace('\n', ' ')
        print(f"Q&A Start: {snippet}...")
    else:
        print("!!! NO Q&A DETECTED !!!")

def run_tests():
    transcripts = [
        "transcripts/TSLA.json",
        "transcripts/AAPL.json",
        "transcripts/MSFT.json",
        "transcripts/NVDA.json",
        "transcripts/WMT.json"
    ]
    for t in transcripts:
        test_detection(t)

if __name__ == "__main__":
    run_tests()
