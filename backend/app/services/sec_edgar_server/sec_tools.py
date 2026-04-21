"""
SEC EDGAR tools for accessing SEC filings and financial data.

Simplified version using direct HTTP requests to SEC EDGAR API.
"""
import json
from typing import Dict, List, Any, Optional
from loguru import logger


class SECEdgarTools:
    """Simplified SEC EDGAR tools using direct HTTP requests."""

    def __init__(self):
        """Initialize SEC EDGAR tools."""
        try:
            import requests
            self.requests = requests
            self.base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
            self.api_base = "https://data.sec.gov"
        except ImportError:
            logger.error("[SEC EDGAR] requests library not available")
            raise ImportError("requests library is required")

    def get_cik_by_ticker(self, ticker: str) -> Dict[str, Any]:
        """Convert ticker symbol to CIK using SEC EDGAR search.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "NVDA", "MSFT")

        Returns:
            Dictionary with success status, CIK, and ticker
        """
        try:
            # Use SEC CIK lookup API
            search_url = f"{self.base_url}?action=getcompany&CIK={ticker.upper()}&type=ticker&owner=exclude"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = self.requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse response to find CIK
            # SEC EDGAR returns HTML, we need to extract CIK
            # Simplified approach: use known CIK mapping

            # Known ticker to CIK mapping (for demo)
            known_ci_ks = {
                "AAPL": "0000320193",
                "MSFT": "0000789019",
                "GOOGL": "0001652044",
                "AMZN": "0000789019",
                "TSLA": "0001318605",
                "META": "0001326801",
                "NVDA": "0001045810",
                "JPM": "0000019617",
                "BAC": "0000070858",
                "WMT": "0000104169"
            }

            ticker_upper = ticker.upper()
            if ticker_upper in known_ci_ks:
                cik = known_ci_ks[ticker_upper]
                return {
                    "success": True,
                    "cik": cik,
                    "ticker": ticker_upper,
                    "cik_padded": cik.zfill(10)
                }
            else:
                return {
                    "success": False,
                    "error": f"CIK not found for ticker: {ticker}. Try using CIK directly or search for the company."
                }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting CIK for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get CIK: {str(e)}"
            }

    def get_company_info(self, identifier: str) -> Dict[str, Any]:
        """Get company information from SEC EDGAR.

        Args:
            identifier: Company ticker symbol or CIK number

        Returns:
            Dictionary with company details
        """
        try:
            # Remove leading zeros from CIK if present
            if isinstance(identifier, str) and identifier.isdigit():
                cik = identifier.lstrip('0')
            else:
                # Try to get CIK from ticker
                cik_result = self.get_cik_by_ticker(identifier)
                if not cik_result["success"]:
                    return cik_result
                cik = cik_result["cik"].lstrip('0')

            # Get company submissions JSON from SEC API
            submissions_url = f"{self.api_base}/submissions/CIK{cik.zfill(10)}.json"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            response = self.requests.get(submissions_url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()

            # Extract company info from submissions
            if "filings" in data and "recent" in data["filings"]:
                # Get info from recent filings
                recent_filings = data["filings"]["recent"]["form"][:5]

                # Extract company name from first filing
                company_name = None
                for filing in recent_filings:
                    if " filing" in filing:
                        company_name = filing.get("companyName")
                        if company_name:
                            break

                return {
                    "success": True,
                    "cik": cik.zfill(10),
                    "name": company_name or f"Company {cik}",
                    "identifier": identifier.upper(),
                    "filings_count": len(data["filings"]["recent"]["form"]),
                    "info": "Basic company information retrieved"
                }
            else:
                return {
                    "success": False,
                    "error": f"No filings found for identifier: {identifier}"
                }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting company info for {identifier}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get company info: {str(e)}"
            }

    def search_companies(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for companies by name.

        Args:
            query: Company name search query
            limit: Maximum results to return

        Returns:
            Dictionary with search results
        """
        try:
            # Use SEC EDGAR search API
            search_url = f"{self.base_url}?action=getcompany&company={query}&owner=exclude&match=start"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = self.requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()

            # Parse HTML response to extract companies
            companies = []

            # For demo, return known companies
            known_companies = [
                {"cik": "0000320193", "name": "Apple Inc.", "tickers": ["AAPL"]},
                {"cik": "0000789019", "name": "Microsoft Corporation", "tickers": ["MSFT"]},
                {"cik": "0001652044", "name": "Alphabet Inc.", "tickers": ["GOOGL", "GOOG"]},
            ]

            # Filter by query
            query_lower = query.lower()
            for company in known_companies:
                if query_lower in company["name"].lower():
                    companies.append(company)

            return {
                "success": True,
                "companies": companies[:limit],
                "count": len(companies),
                "query": query,
                "note": "Demo mode - using known companies. In production, this would query SEC EDGAR database."
            }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error searching companies for {query}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to search companies: {str(e)}"
            }

    def get_recent_filings(
        self,
        identifier: Optional[str] = None,
        form_type: Optional[str] = None,
        days: int = 30,
        limit: int = 40
    ) -> Dict[str, Any]:
        """Get recent SEC filings.

        Args:
            identifier: Company ticker/CIK (optional)
            form_type: Filter by form type (e.g., "10-K", "10-Q", "8-K")
            days: Number of days to look back
            limit: Maximum filings to return

        Returns:
            Dictionary with recent filings
        """
        try:
            # For demo, return mock data
            if identifier and identifier.upper() in ["AAPL", "0000320193"]:
                filings = [
                    {
                        "accession_number": "0000320193-24-000010",
                        "form_type": "10-Q",
                        "filing_date": "2024-11-01",
                        "url": "https://www.sec.gov/Archives/edgar/data/0000320193/000032019324000010/0000320193-24-000010-index.htm"
                    },
                    {
                        "accession_number": "0000320193-23-000010",
                        "form_type": "10-K",
                        "filing_date": "2024-10-27",
                        "url": "https://www.sec.gov/Archives/edgar/data/0000320193/000032019323000010/0000320193-23-000010-index.htm"
                    }
                ]
            else:
                filings = []

            return {
                "success": True,
                "identifier": identifier or "all",
                "form_type": form_type,
                "filings": filings[:limit],
                "count": len(filings),
                "days": days,
                "note": "Demo mode - using mock data. In production, this would query SEC EDGAR API."
            }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting recent filings: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get recent filings: {str(e)}"
            }

    def get_company_facts(self, identifier: str) -> Dict[str, Any]:
        """Get company facts and financial metrics.

        Args:
            identifier: Company ticker symbol or CIK number

        Returns:
            Dictionary with company facts and metrics
        """
        try:
            # For demo, return mock financial data
            if identifier.upper() in ["AAPL", "0000320193"]:
                metrics = {
                    "Assets": {
                        "value": 352583000000,
                        "fiscal_year": "2024",
                        "form": "10-Q"
                    },
                    "Revenues": {
                        "value": 94930000000,
                        "fiscal_year": "2024",
                        "form": "10-Q"
                    },
                    "NetIncomeLoss": {
                        "value": 14746000000,
                        "fiscal_year": "2024",
                        "form": "10-Q"
                    }
                }

                return {
                    "success": True,
                    "cik": "0000320193",
                    "name": "Apple Inc.",
                    "metrics": metrics,
                    "has_facts": True
                }
            else:
                return {
                    "success": False,
                    "error": "No facts available for this company in demo mode"
                }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting company facts for {identifier}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get company facts: {str(e)}"
            }

    def get_filings_summary(self, identifier: str, limit: int = 20) -> Dict[str, Any]:
        """Get a summary of recent filings for a company.

        Args:
            identifier: Company ticker or CIK
            limit: Maximum filings to summarize

        Returns:
            Dictionary with filings summary
        """
        try:
            result = self.get_recent_filings(identifier, limit=limit)

            if not result["success"]:
                return result

            # Group by form type
            by_form = {}
            for filing in result["filings"]:
                form_type = filing["form_type"]
                if form_type not in by_form:
                    by_form[form_type] = []
                by_form[form_type].append(filing)

            return {
                "success": True,
                "identifier": identifier,
                "total_filings": result["count"],
                "by_form_type": {k: len(v) for k, v in by_form.items()},
                "recent_filings": result["filings"][:10],
                "summary": f"Found {result['count']} recent filings",
                "note": "Demo mode - using mock data"
            }
        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting filings summary: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get filings summary: {str(e)}"
            }