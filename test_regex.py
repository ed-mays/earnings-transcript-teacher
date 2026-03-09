import re
text = "Our next question comes from the line of Jane Smith with UBS. Please go ahead."
pattern = re.compile(
    r"(?:next|first|last|a)?\s*question[s]?\s+(?:will\s+)?comes?\s+from\s+(?:the\s+line\s+of\s+)?"
    r"(?P<name>[A-Z][a-zA-Z.']+(?:\s+[A-Z][a-zA-Z.']+)+)"
    r"(?:\s+(?:at|with|from)\s+(?P<firm>[A-Z][A-Za-z0-9\s&,.-]+?)(?=\.\s|,\s|\n|$|\s+Please|\s+And))?",
    re.IGNORECASE,
)
for m in pattern.finditer(text):
    print("Found name:", m.group("name"))
    print("Found firm:", m.group("firm"))
