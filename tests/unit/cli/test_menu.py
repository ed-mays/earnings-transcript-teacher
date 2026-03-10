from cli.menu import _validate_ticker


def test_valid_tickers():
    assert _validate_ticker("AAPL") is True
    assert _validate_ticker("MSFT") is True
    assert _validate_ticker("A") is True       # single-letter tickers are valid (e.g. A = Agilent)
    assert _validate_ticker("GOOGL") is True   # 5-letter ticker


def test_invalid_tickers():
    assert _validate_ticker("") is False                # empty string
    assert _validate_ticker("TOOLONG") is False         # more than 5 chars
    assert _validate_ticker("123") is False             # digits only
    assert _validate_ticker("AAP1") is False            # contains a digit
    assert _validate_ticker("aapl") is False            # lowercase (must already be uppercased by caller)
    assert _validate_ticker("AAPL Q3") is False         # spaces not allowed
    assert _validate_ticker("AAPL.") is False           # punctuation not allowed
