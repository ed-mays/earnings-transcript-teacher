import pytest
from unittest.mock import MagicMock
from services.company_info import fetch_company_info


def test_fetch_company_info_success(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "Apple Inc.",
        "sicDescription": "Electronic Computers",
    }
    mock_get = mocker.patch("services.company_info.requests.get", return_value=mock_response)

    company_name, industry = fetch_company_info("320193")

    assert company_name == "Apple Inc."
    assert industry == "Electronic Computers"
    mock_get.assert_called_once()
    assert "CIK0000320193" in mock_get.call_args[0][0]


def test_fetch_company_info_missing_fields(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mocker.patch("services.company_info.requests.get", return_value=mock_response)

    company_name, industry = fetch_company_info("320193")

    assert company_name == ""
    assert industry == ""


def test_fetch_company_info_network_error(mocker):
    mocker.patch("services.company_info.requests.get", side_effect=Exception("timeout"))

    company_name, industry = fetch_company_info("320193")

    assert company_name == ""
    assert industry == ""


def test_fetch_company_info_http_error(mocker):
    import requests as requests_lib
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests_lib.HTTPError("404 Not Found")
    mocker.patch("services.company_info.requests.get", return_value=mock_response)

    company_name, industry = fetch_company_info("000000")

    assert company_name == ""
    assert industry == ""


def test_fetch_company_info_integer_cik(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"name": "Tesla, Inc.", "sicDescription": "Motor Vehicles & Passenger Car Bodies"}
    mock_get = mocker.patch("services.company_info.requests.get", return_value=mock_response)

    company_name, industry = fetch_company_info(1318605)

    assert company_name == "Tesla, Inc."
    assert "CIK0001318605" in mock_get.call_args[0][0]
