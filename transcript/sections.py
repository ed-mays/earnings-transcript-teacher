import re

# ---------------------------------------------------------------------------
# Section boundary patterns
# ---------------------------------------------------------------------------

PREPARED_REMARKS_PATTERN: re.Pattern = re.compile(
    r"^prepared\s+remarks\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Explicit Q&A section headings used by various transcript providers.
_QA_HEADING_PATTERN: re.Pattern = re.compile(
    r"questions?\s+and\s+answers?"      # "Questions and Answers"
    r"|question[- ]and[- ]answer"       # "Question-and-Answer"
    r"|q\s*&\s*a\s+session"            # "Q&A Session"
    r"|analyst\s+q\s*&\s*a"           # "Analyst Q&A"
    r"|operator\s+q\s*&\s*a"          # "Operator Q&A"
    r"|q\s*&\s*a",                     # bare "Q&A"
    re.IGNORECASE,
)

# Natural-language phrases that signal the moderator is opening Q&A.
_QA_TRANSITION_PATTERN: re.Pattern = re.compile(
    # "let's open it up / the floor / the call for questions"
    r"(?:let(?:'s|us)\s+)?open\s+(?:it\s+up|(?:the\s+)?(?:floor|call|line)s?)\s+(?:up\s+)?(?:to|for)\s+(?:your\s+)?questions?"

    # "now we'll take / we will take / I'll take your questions"
    r"|(?:now\s+)?(?:we(?:'ll|'re|\s+will|\s+are)|i(?:'ll|\s+will))\s+(?:now\s+)?(?:take|open\s+(?:it\s+)?up\s+for|begin\s+(?:taking\s+)?|move\s+to)\s+(?:your\s+|any\s+|some\s+)?questions?"

    # "ready / happy / pleased to take your questions"
    r"|(?:ready|happy|pleased)\s+to\s+(?:take|answer|address)\s+(?:your\s+|any\s+)?questions?"

    # "turn it over for questions", "turn the call over to Q&A"
    r"|turn\s+(?:it|the\s+call)?\s*over\s+(?:to\s+)?(?:the\s+)?(?:q\s*&\s*a|questions?)"

    # "move on to / move to the Q&A / questions portion"
    r"|move\s+(?:on\s+)?to\s+(?:the\s+)?(?:q\s*&\s*a|questions?\s*(?:portion|section|part)?)"

    # "start / begin the Q&A", "start taking questions"
    r"|(?:start|begin)\s+(?:the\s+)?(?:q\s*&\s*a|(?:taking\s+)?questions?)",
    re.IGNORECASE,
)

# Combined pattern: headings take priority over transitional phrases.
QA_PATTERN: re.Pattern = re.compile(
    _QA_HEADING_PATTERN.pattern + "|" + _QA_TRANSITION_PATTERN.pattern,
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Speaker-turn patterns (used by extract_qa_pairs)
# ---------------------------------------------------------------------------

# Matches "First Last: text..." at the start of a line.
_TURN_PATTERN: re.Pattern = re.compile(
    r"^(?P<speaker>[A-Z][a-zA-Z\-'.]+(?:\s+[A-Z][a-zA-Z\-'.]+)*)\s*:\s*(?P<text>.+?)(?=\n[A-Z]|\Z)",
    re.MULTILINE | re.DOTALL,
)

# Executive title keywords — turns from these speakers are answers, not questions.
_EXECUTIVE_TITLES: re.Pattern = re.compile(
    r"\b(CEO|CFO|COO|CTO|President|Chief|Officer|Director|VP|Vice\s+President)\b",
    re.IGNORECASE,
)

# Affiliation keywords that identify external questioners (analysts, investors).
_QUESTIONER_PATTERN: re.Pattern = re.compile(
    r"\b(Analyst|Research|Investor|Capital|Securities|Partners|Group)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_executive_set(turns: list[tuple[str, str]]) -> set[str]:
    """Infers the set of executive speakers from title keywords in their names."""
    return {speaker for speaker, _ in turns if _EXECUTIVE_TITLES.search(speaker)}


def _is_questioner(speaker: str, known_executives: set[str]) -> bool:
    """Returns True if the speaker is likely an external questioner (analyst/investor).

    Classification rules (in order):
    1. Known executives → not a questioner.
    2. Operator → not a questioner (facilitates but doesn't ask questions).
    3. Matches a firm/role keyword (Analyst, Capital, etc.) → questioner.
    4. Unknown speakers default to questioner — analysts often appear in
       transcripts by name only, without firm affiliation in the speaker field.
       Pass ``executive_names`` explicitly to override this fallback.
    """
    if speaker in known_executives:
        return False
    if speaker.lower() == "operator":
        return False
    if _QUESTIONER_PATTERN.search(speaker):
        return True
    # Intentional fallback: unrecognised speakers are treated as external
    # questioners. Callers can supply a complete executive_names set to prevent
    # internal non-executive speakers (e.g. IR hosts) from being misclassified.
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_transcript_sections(
    transcript: str,
    prepared_pattern: re.Pattern = PREPARED_REMARKS_PATTERN,
    qa_pattern: re.Pattern = QA_PATTERN,
) -> tuple[str, str]:
    """Splits an earnings transcript into Prepared Remarks and Q&A sections.

    Args:
        transcript: Raw transcript text.
        prepared_pattern: Regex to locate the prepared remarks heading.
        qa_pattern: Regex to locate the Q&A heading or transition phrase.

    Returns:
        A (prepared_remarks, qa) tuple. Falls back to (transcript, "") if
        either boundary is not found.
    """
    prepared_match = prepared_pattern.search(transcript)
    qa_match = qa_pattern.search(transcript)

    if not prepared_match and not qa_match:
        # No section markers found at all — return the full transcript.
        return transcript, ""

    if not qa_match:
        # Only a prepared remarks heading found; no Q&A boundary.
        return transcript[prepared_match.end():], ""

    if not prepared_match:
        # Only a Q&A boundary found (common when transcripts lack headings).
        return transcript[:qa_match.start()], transcript[qa_match.end():]

    prepared_remarks = transcript[prepared_match.end():qa_match.start()]
    qa = transcript[qa_match.end():]
    return prepared_remarks, qa


def extract_qa_pairs(
    transcript: str,
    executive_names: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Extracts question-and-answer pairs from an earnings transcript.

    Speaker turns are identified by the "Speaker Name: text" format. Analyst/
    investor turns are treated as questions; consecutive executive turns that
    follow are joined as the answer.

    Args:
        transcript: Raw transcript text (full or Q&A section only).
        executive_names: Known executive speaker names. When omitted, inferred
            from title keywords in speaker names.

    Returns:
        List of (question, answer) string tuples.
    """
    turns = [
        (m.group("speaker").strip(), m.group("text").strip())
        for m in _TURN_PATTERN.finditer(transcript)
    ]

    if executive_names is None:
        executive_names = _build_executive_set(turns)

    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(turns):
        speaker, text = turns[i]
        if _is_questioner(speaker, executive_names):
            # Collect all consecutive executive turns as the answer.
            answer_parts: list[str] = []
            j = i + 1
            while j < len(turns) and not _is_questioner(turns[j][0], executive_names):
                answer_parts.append(turns[j][1])
                j += 1
            if answer_parts:
                pairs.append((text, " ".join(answer_parts)))
            i = j
        else:
            i += 1

    return pairs
