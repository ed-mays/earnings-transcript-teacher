import logging
import requests

logger = logging.getLogger(__name__)

_EDGAR_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def build_company_context(ticker: str, company_name: str, industry: str) -> str:
    """Return a human-readable company context string for LLM prompts."""
    if company_name and industry:
        return f"{company_name} ({ticker}) — {industry}"
    if company_name:
        return f"{company_name} ({ticker})"
    return ticker


def fetch_company_info(cik: str | int) -> tuple[str, str]:
    """Return (company_name, industry) from the SEC EDGAR API using the CIK.

    Falls back to empty strings on any error so ingestion is never blocked.
    """
    try:
        cik_int = int(cik)
        url = _EDGAR_URL.format(cik=cik_int)
        response = requests.get(url, headers={"User-Agent": "earnings-transcript-teacher"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        company_name = data.get("name", "")
        industry = data.get("sicDescription", "")
        return (company_name, industry)
    except Exception as e:
        logger.warning(f"Could not fetch company info for CIK {cik} from SEC EDGAR: {e}")
        return ("", "")
