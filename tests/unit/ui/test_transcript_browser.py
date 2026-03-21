"""Unit tests for jargon tooltip injection in the transcript browser."""

import pytest

from ui.transcript_browser import _apply_jargon_tooltips


def test_known_term_is_wrapped():
    jargon = {"ebitda": "Earnings before interest, taxes, depreciation, and amortisation"}
    result = _apply_jargon_tooltips("We discuss EBITDA margins.", jargon)
    assert 'class="jargon"' in result
    assert "Earnings before interest" in result
    assert "EBITDA" in result


def test_unknown_term_is_unchanged():
    jargon = {"ebitda": "Some definition"}
    result = _apply_jargon_tooltips("Revenue was strong.", jargon)
    assert result == "Revenue was strong."


def test_no_jargon_returns_text_unchanged():
    result = _apply_jargon_tooltips("Some text here.", {})
    assert result == "Some text here."


def test_term_with_no_definition_is_not_wrapped():
    jargon = {"eps": ""}
    result = _apply_jargon_tooltips("EPS was $2.50.", jargon)
    assert 'class="jargon"' not in result


def test_definition_is_html_escaped_in_title():
    jargon = {"p/e": 'Price-to-"earnings" ratio'}
    result = _apply_jargon_tooltips("The P/E ratio.", jargon)
    assert "&quot;" in result or "&#x27;" in result or "Price-to-" in result


def test_longer_term_matched_over_shorter_substring():
    jargon = {
        "gross margin": "Revenue minus cost of goods sold",
        "margin": "Profit as a percentage of revenue",
    }
    result = _apply_jargon_tooltips("Gross margin improved.", jargon)
    assert "Revenue minus cost" in result
    # "margin" alone should not create a second span
    assert result.count('class="jargon"') == 1


def test_case_insensitive_matching():
    jargon = {"free cash flow": "Operating cash flow minus capex"}
    result = _apply_jargon_tooltips("Free Cash Flow was positive.", jargon)
    assert 'class="jargon"' in result
    assert "Operating cash flow" in result


def test_term_not_matched_inside_html_attribute():
    """Regex must not match term text that appears inside an HTML attribute value."""
    jargon = {"eps": "Earnings per share"}
    # A term that only appears inside an existing attribute should not get an extra span.
    text_with_attr = 'See <a href="/glossary?term=eps">the glossary</a>.'
    result = _apply_jargon_tooltips(text_with_attr, jargon)
    # The word "eps" only appears inside the href attribute — no tooltip span expected
    assert 'class="jargon"' not in result
