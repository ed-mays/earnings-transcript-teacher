import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Section boundary patterns
# ---------------------------------------------------------------------------

PREPARED_REMARKS_PATTERN: re.Pattern = re.compile(
    r"^prepared\s+remarks\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Explicit Q&A section headings — must appear as a standalone line to avoid
# matching boilerplate like "A question and answer session will follow...".
_QA_HEADING_PATTERN: re.Pattern = re.compile(
    r"^(?:"
    r"questions?\s+and\s+answers?"      # "Questions and Answers"
    r"|question[- ]and[- ]answer"       # "Question-and-Answer"
    r"|q\s*&\s*a\s+session"            # "Q&A Session"
    r"|analyst\s+q\s*&\s*a"           # "Analyst Q&A"
    r"|operator\s+q\s*&\s*a"          # "Operator Q&A"
    r"|q\s*&\s*a"                      # bare "Q&A"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE,
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

    # "move on/over to the Q&A / questions portion", "move to Q and A"
    r"|move\s+(?:on|over)?\s*to\s+(?:the\s+)?(?:q\s*(?:&|and)\s*a|questions?\s*(?:portion|section|part)?)"

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

# Operator turn that introduces an analyst before their question:
# "Our first question comes from Keith Weiss with Morgan Stanley."
# "The next question comes from the line of Mark Moerdler with Bernstein Research."
_ANALYST_INTRO_PATTERN: re.Pattern = re.compile(
    r"(?:next|first|last|a)?\s*question[s]?\s+(?:will\s+)?comes?\s+from\s+(?:the\s+line\s+of\s+)?"
    r"(?P<name>[A-Z][a-zA-Z.']+(?:\s+[A-Z][a-zA-Z.']+)+)"
    r"(?:\s+(?:at|with|from)\s+(?P<firm>[A-Z][A-Za-z0-9\s&,.-]+?)(?=\.\s|,\s|\n|$|\s+Please|\s+And))?",
    re.IGNORECASE,
)

# Executive introduction: "Satya Nadella, Chairman and CEO" or "Amy Hood, CFO".
# NOTE: no re.IGNORECASE — proper names and title-case keywords are reliable
# case anchors and case-sensitivity is what prevents the name group from being
# too greedy (e.g. matching whole sentences rather than just "First Last").
_EXEC_INTRO_PATTERN: re.Pattern = re.compile(
    # Proper name: each word starts with a capital, rest lowercase (handles initials too).
    r"(?P<name>[A-Z][a-z.']*\.?(?:\s+[A-Z][a-z.']*\.?)+),\s+"
    # Optional prefix: handles possessives like "Clover Health's " or "the company's ".
    r"(?:[^,;\n]{0,50}?)?"
    r"(?P<title>(?:Chairman|Chief|President|Co-CEO|CEO|CFO|COO|CTO|"
    r"Executive\s+Vice\s+President|Senior\s+Vice\s+President|EVP|SVP|"
    r"Vice\s+Chairman|Managing\s+Director)(?:[^,;\n.]|\.\S)*)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_executive_set(turns: list[tuple[str, str]]) -> set[str]:
    """Infers the set of executive speakers from title keywords in their names."""
    return {speaker for speaker, _ in turns if _EXECUTIVE_TITLES.search(speaker)}


def _speaker_sections(name: str, prepared: str, qa: str) -> set[str]:
    """Returns which sections {'prepared', 'qa'} a speaker appears in."""
    pattern = re.compile(rf"^{re.escape(name)}\s*:", re.MULTILINE)
    sections: set[str] = set()
    if pattern.search(prepared):
        sections.add("prepared")
    if pattern.search(qa):
        sections.add("qa")
    return sections


def _parse_analyst_introductions(transcript: str) -> dict[str, str | None]:
    """Extract {name: firm_or_None} from operator turns that introduce analysts."""
    result: dict[str, str | None] = {}
    for m in _TURN_PATTERN.finditer(transcript):
        if m.group("speaker").strip().lower() != "operator":
            continue
        for am in _ANALYST_INTRO_PATTERN.finditer(m.group("text")):
            name = am.group("name").strip()
            firm_raw = am.group("firm")
            result[name] = firm_raw.strip() if firm_raw else None
    return result


def _parse_executive_introductions(prepared_remarks: str) -> dict[str, str]:
    """Extract {name: title} from executive introductions in the prepared remarks."""
    result: dict[str, str] = {}
    for m in _EXEC_INTRO_PATTERN.finditer(prepared_remarks):
        name = m.group("name").strip()
        title = m.group("title").strip()
        if len(name.split()) >= 2:   # require at least a first + last name
            result[name] = title
    return result


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
# Speaker profiles
# ---------------------------------------------------------------------------

@dataclass
class SpeakerProfile:
    """Enriched metadata for a single transcript speaker."""
    name: str
    role: str           # "executive" | "analyst" | "operator" | "unknown"
    title: str | None   # e.g. "Chairman and CEO"   — from executive introduction
    firm: str | None    # e.g. "Morgan Stanley"     — from operator introduction
    turn_count: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_speakers(transcript: str) -> list[tuple[str, int]]:
    """Returns the unique speakers in the transcript, in order of first appearance.

    Args:
        transcript: Raw transcript text.

    Returns:
        List of (speaker_name, turn_count) tuples, ordered by first appearance.
    """
    seen: dict[str, int] = {}
    for m in _TURN_PATTERN.finditer(transcript):
        speaker = m.group("speaker").strip()
        seen[speaker] = seen.get(speaker, 0) + 1
    return list(seen.items())


def enrich_speakers(
    transcript: str,
    prepared_remarks: str | None = None,
    qa: str | None = None,
) -> list[SpeakerProfile]:
    """Returns enriched speaker profiles with role, title, and firm where detectable.

    Classification uses three signals in priority order:
    1. Operator introduction parsing  → role=analyst, firm extracted
    2. Executive introduction parsing → role=executive, title extracted
    3. Section-presence fallback      → prepared-only=executive, qa-only=analyst

    Args:
        transcript: Full raw transcript text.
        prepared_remarks: Pre-computed prepared remarks section. If omitted,
            sections are computed automatically.
        qa: Pre-computed Q&A section. If omitted, computed automatically.

    Returns:
        List of SpeakerProfile, in order of first appearance.
    """
    if prepared_remarks is None or qa is None:
        prepared_remarks, qa = extract_transcript_sections(transcript)

    analyst_firm_map = _parse_analyst_introductions(transcript)
    exec_title_map = _parse_executive_introductions(prepared_remarks)

    # Collect speakers in first-appearance order with turn counts.
    seen: dict[str, int] = {}
    for m in _TURN_PATTERN.finditer(transcript):
        name = m.group("speaker").strip()
        seen[name] = seen.get(name, 0) + 1

    profiles: list[SpeakerProfile] = []
    for name, turn_count in seen.items():
        if name.lower() == "operator":
            role, title, firm = "operator", None, None
        elif name in analyst_firm_map:
            role, title, firm = "analyst", None, analyst_firm_map[name]
        elif name in exec_title_map:
            role, title, firm = "executive", exec_title_map[name], None
        else:
            sections = _speaker_sections(name, prepared_remarks, qa)
            if "qa" in sections and "prepared" not in sections:
                # Only in Q&A → external analyst/investor.
                role, title, firm = "analyst", None, None
            elif sections:
                # In prepared remarks (only, or both sections) → executive/IR.
                # Analysts don't speak during prepared remarks, so appearing
                # there is a reliable indicator of an internal speaker.
                role, title, firm = "executive", None, None
            else:
                role, title, firm = "unknown", None, None

        profiles.append(SpeakerProfile(
            name=name, role=role, title=title, firm=firm, turn_count=turn_count,
        ))

    return profiles


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
    # Use the LAST Q&A match — operator boilerplate near the top of the
    # transcript often contains the same phrases as the real Q&A transition,
    # so the final occurrence is the most reliable boundary.
    all_qa_matches = list(qa_pattern.finditer(transcript))
    qa_match = all_qa_matches[-1] if all_qa_matches else None

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


# A single turn within a Q&A exchange: (speaker, text).
Turn = tuple[str, str]

# A full Q&A exchange: all turns from one analyst's question thread,
# including any clarification back-and-forth, until the next analyst speaks.
Exchange = list[Turn]


def extract_qa_exchanges(
    qa_text: str,
    executive_names: set[str] | None = None,
) -> list[Exchange]:
    """Extracts Q&A exchanges from the Q&A section of an earnings transcript.

    Each exchange groups all turns belonging to one analyst's question thread,
    including clarification requests from executives and follow-up from the
    analyst, until a *different* analyst begins a new question.

    A new exchange boundary is drawn when:
    - A questioner speaks, AND
    - The current exchange already contains at least one executive turn, AND
    - The speaker is different from the analyst who opened the current exchange.

    Args:
        qa_text: The Q&A section of the transcript (output of
            ``extract_transcript_sections``), NOT the full transcript.
        executive_names: Known executive speaker names. When omitted, inferred
            from title keywords in speaker names.

    Returns:
        List of exchanges. Each exchange is a list of (speaker, text) turns
        in conversation order.
    """
    turns: list[Turn] = [
        (m.group("speaker").strip(), m.group("text").strip())
        for m in _TURN_PATTERN.finditer(qa_text)
    ]

    if executive_names is None:
        executive_names = _build_executive_set(turns)

    exchanges: list[Exchange] = []
    current_exchange: Exchange = []
    current_questioner: str | None = None
    had_exec_response: bool = False

    for speaker, text in turns:
        if _is_questioner(speaker, executive_names):
            if had_exec_response and speaker != current_questioner:
                # A different analyst starting after an exec response → new exchange.
                if current_exchange:
                    exchanges.append(current_exchange)
                current_exchange = []
                current_questioner = speaker
                had_exec_response = False
            elif current_questioner is None:
                current_questioner = speaker
            # Same questioner speaking again (clarification) → stays in exchange.
            current_exchange.append((speaker, text))
        else:
            # Executive or operator turn.
            current_exchange.append((speaker, text))
            had_exec_response = True

    if current_exchange:
        exchanges.append(current_exchange)

    return exchanges
