from db.repositories.calls import CallRepository


def test_get_all_calls(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    m_cursor.fetchall.return_value = [
        ("MSFT", "Q1 2024 MSFT", "Microsoft Corp", None),
        ("AAPL", "Q2 2024 AAPL", "Apple Inc", None),
    ]

    repo = CallRepository("fake_connection_string")
    calls = repo.get_all_calls()

    m_cursor.execute.assert_called_once_with(
        """
                        SELECT ticker, fiscal_quarter, company_name, call_date
                        FROM calls
                        ORDER BY created_at DESC
                        """
    )

    assert len(calls) == 2
    assert calls[0] == ("MSFT", "Q1 2024 MSFT", "Microsoft Corp", None)


def test_get_company_info_found(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = ("Microsoft Corp", "Technology")

    repo = CallRepository("fake_connection_string")
    result = repo.get_company_info("MSFT")

    assert result == ("Microsoft Corp", "Technology")
    m_cursor.execute.assert_called_once_with(
        "SELECT company_name, industry FROM calls WHERE ticker = %s LIMIT 1",
        ("MSFT",),
    )


def test_get_company_info_not_found(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = None

    repo = CallRepository("fake_connection_string")
    result = repo.get_company_info("UNKNOWN")

    assert result == ("", "")


def test_get_call_date_found(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = ("2024-01-30",)

    repo = CallRepository("fake_connection_string")
    result = repo.get_call_date("MSFT")

    assert result == "2024-01-30"


def test_get_call_date_not_found(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = None

    repo = CallRepository("fake_connection_string")
    result = repo.get_call_date("UNKNOWN")

    assert result is None
