"""
SEC EDGAR tools for accessing SEC filings and financial data.

Uses local file cache for fast lookups. Cache file can be downloaded from:
https://www.sec.gov/files/company_tickers.json

Run the sync script to download/update the cache:
    python -m app.services.sec_edgar_server.sync_tickers
"""
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import aiofiles


# Local cache file path
_CACHE_DIR = Path("/data/sec_edgar_cache")
_CACHE_FILE = _CACHE_DIR / "company_tickers.json"


class SECEdgarTools:
    """SEC EDGAR tools with local cache and background updates."""

    def __init__(self):
        """Initialize SEC EDGAR tools."""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            # Store requests module and exceptions for later use
            self.requests = requests
            self.requests_exceptions = requests.exceptions

            # Create session with retry logic
            self.session = requests.Session()

            # Configure retry strategy
            retry_strategy = Retry(
                total=3,  # Total retries
                backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
                status_forcelist=[500, 502, 503, 504],  # Retry on these status codes
                allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only retry these methods
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

            self.base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
            self.api_base = "https://data.sec.gov"

            # Set longer timeouts
            self.timeout = 30  # 30 seconds timeout

            # Ensure cache directory exists
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

        except ImportError:
            logger.error("[SEC EDGAR] requests library not available")
            raise ImportError("requests library is required")

    def _make_request(self, url: str, headers: Optional[Dict] = None) -> Optional[Any]:
        """Make HTTP request with retry logic and timeout handling."""
        try:
            if headers is None:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Referer": "https://www.sec.gov",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive"
                }

            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response

        except self.requests_exceptions.Timeout:
            logger.warning(f"[SEC EDGAR] Request timeout for {url}")
            return None
        except self.requests_exceptions.ConnectionError as e:
            logger.error(f"[SEC EDGAR] Connection error for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[SEC EDGAR] Request error for {url}: {str(e)}")
            return None

    def _load_local_cache(self) -> Dict[str, str]:
        """Load company tickers from local cache file.

        Returns:
            Dictionary mapping ticker symbols to CIKs
        """
        try:
            if not _CACHE_FILE.exists():
                logger.warning("[SEC EDGAR] Local cache file not found")
                _CACHE_DIR.mkdir(parents=True, exist_ok=True)
                return {}

            # Read file synchronously (works in both sync and async contexts)
            with open(_CACHE_FILE, 'r') as f:
                data = json.load(f)

                # SEC data format: {"0": {cik_str, ticker, title}, "1": {...}, ...}
                # Build ticker -> CIK mapping
                tickers = {}
                for item in data.values():
                    ticker = item.get("ticker", "").upper()
                    cik = str(item.get("cik_str", "")).zfill(10)

                    if ticker and cik:
                        tickers[ticker] = cik

                logger.info(f"[SEC EDGAR] Loaded {len(tickers)} company tickers from local cache")
                return tickers

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error loading local cache: {str(e)}")
            return {}

    def _save_local_cache(self, tickers: Dict[str, str]) -> bool:
        """Save company tickers to local cache file in SEC official format.

        Args:
            tickers: Dictionary mapping ticker symbols to CIKs

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert ticker->CIK mapping to SEC official format
            # SEC format: {"0": {cik_str, ticker, title}, "1": {...}, ...}
            data = {}
            for idx, (ticker, cik) in enumerate(tickers.items()):
                data[str(idx)] = {
                    "cik_str": int(cik.lstrip('0')),
                    "ticker": ticker,
                    "title": ticker  # SEC format requires title, use ticker as placeholder
                }

            # Ensure cache directory exists
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Write synchronously for simplicity
            with open(_CACHE_FILE, 'w') as f:
                json.dump(data, f)

            logger.info(f"[SEC EDGAR] Saved {len(tickers)} company tickers to local cache")
            return True

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error saving local cache: {str(e)}")
            return False

    def _load_company_tickers(self) -> Dict[str, str]:
        """Load complete company tickers from SEC EDGAR.

        Returns:
            Dictionary mapping ticker symbols to CIKs
        """
        try:
            # SEC provides complete company data in JSON
            ticker_url = "https://www.sec.gov/files/company_tickers.json"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            response = self._make_request(ticker_url, headers)

            if not response:
                logger.warning("[SEC EDGAR] Failed to load company tickers from SEC")
                return {}

            data = response.json()

            # Build ticker to CIK mapping
            ticker_to_cik = {}
            for item in data.values():
                ticker = item.get("ticker", "").upper()
                cik = item.get("cik_str", "")

                if ticker and cik:
                    ticker_to_cik[ticker] = str(cik).zfill(10)

            logger.info(f"[SEC EDGAR] Loaded {len(ticker_to_cik)} company tickers from SEC")
            return ticker_to_cik

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error loading company tickers: {str(e)}")
            return {}

    async def _update_cache_async(self) -> bool:
        """Async background task to update local cache from SEC.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("[SEC EDGAR] Background cache update started")
            tickers = self._load_company_tickers()

            if tickers:
                self._save_local_cache(tickers)
                logger.info("[SEC EDGAR] Background cache update completed")
                return True
            else:
                logger.warning("[SEC EDGAR] Background cache update failed - no data retrieved")
                return False

        except Exception as e:
            logger.error(f"[SEC EDGAR] Background cache update error: {str(e)}")
            return False

    def _normalize_identifier(self, identifier: str) -> tuple[str, str]:
        """Normalize identifier to (cik, ticker) tuple.

        Accepts either ticker symbol (e.g., "AAPL") or CIK number (e.g., "0000320193").
        Returns (cik, ticker) where one will be empty string if not applicable.

        Args:
            identifier: Ticker symbol or CIK number

        Returns:
            Tuple of (cik, ticker)
        """
        identifier = identifier.strip().upper()

        # Check if it's a CIK (all digits, 10 chars)
        if identifier.isdigit():
            cik = identifier.zfill(10)
            ticker = ""
            return cik, ticker

        # It's a ticker symbol - convert to CIK
        tickers = self._load_local_cache()
        if identifier in tickers:
            cik = tickers[identifier]
            return cik, identifier

        # Not found in cache - return empty
        return "", identifier

    def get_cik_by_ticker(self, ticker: str) -> Dict[str, Any]:
        """Convert ticker symbol to CIK using local cache.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "NVDA", "MSFT")

        Returns:
            Dictionary with success status, CIK, and ticker
        """
        try:
            # 参数验证
            if not ticker or not isinstance(ticker, str):
                return {
                    "success": False,
                    "error": "股票代码不能为空",
                    "suggestion": "请提供有效的股票代码，例如：AAPL、BABA、PDD",
                    "example": "get_cik_by_ticker('AAPL')"
                }

            ticker = ticker.upper().strip()

            # 验证ticker格式（1-10个字符，仅字母）
            if len(ticker) > 10 or not ticker.isalpha():
                return {
                    "success": False,
                    "error": "无效的股票代码格式",
                    "suggestion": "股票代码应为1-10个字母，例如：AAPL、MSFT、GOOGL",
                    "example": "get_cik_by_ticker('AAPL')"
                }

            # Try to load from local cache first (fast!)
            tickers = self._load_local_cache()

            if tickers and ticker in tickers:
                cik = tickers[ticker]
                return {
                    "success": True,
                    "cik": cik,
                    "ticker": ticker,
                    "cik_padded": cik.zfill(10),
                    "source": "Local SEC cache"
                }

            # Fallback: Try to fetch from SEC EDGAR website
            logger.info(f"[SEC EDGAR] {ticker} not in local cache, trying SEC EDGAR website")
            search_url = f"{self.base_url}?action=getcompany&CIK={ticker}&type=ticker&owner=exclude"
            response = self._make_request(search_url)

            if response and response.status_code == 200:
                # Parse HTML response
                import re
                cik_match = re.search(r'CIK=(\d{10})', response.text)
                if cik_match:
                    cik = cik_match.group(1)
                    # Save to local cache for next query
                    existing_cache = self._load_local_cache()
                    existing_cache[ticker.upper()] = cik
                    self._save_local_cache(existing_cache)
                    logger.info(f"[SEC EDGAR] Saved CIK {cik} for ticker {ticker} to local cache")
                    return {
                        "success": True,
                        "cik": cik,
                        "ticker": ticker,
                        "cik_padded": cik.zfill(10),
                        "source": "SEC EDGAR (real-time lookup)"
                    }

            # Not found
            return {
                "success": False,
                "error": f"未找到股票代码对应的CIK：{ticker}",
                "suggestion": "请验证股票代码是否正确，或使用公司搜索功能"
            }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting CIK for {ticker}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get CIK: {str(e)}",
                "suggestion": "SEC EDGAR service may be slow. Please try again in a moment."
            }

    def get_company_info(self, identifier: str) -> Dict[str, Any]:
        """Get company information from SEC EDGAR.

        Accepts either ticker symbol (e.g., "AAPL") or CIK number (e.g., "0000320193").

        Args:
            identifier: Company ticker symbol or CIK number

        Returns:
            Dictionary with company details
        """
        try:
            # 参数验证
            if not identifier or not isinstance(identifier, str):
                return {
                    "success": False,
                    "error": "公司标识符不能为空",
                    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
                    "example": "get_company_info('AAPL') 或 get_company_info('0000320193')"
                }

            identifier = identifier.strip()

            # 验证identifier格式（strip后检查长度）
            if len(identifier) == 0 or len(identifier) > 20:
                return {
                    "success": False,
                    "error": "无效的公司标识符长度",
                    "suggestion": "股票代码应为1-10个字母，CIK应为10位数字",
                    "example": "get_company_info('AAPL') 或 get_company_info('0000320193')"
                }

            # Normalize identifier (ticker -> CIK)
            cik, ticker = self._normalize_identifier(identifier)

            if not cik:
                return {
                    "success": False,
                    "error": f"未找到标识符对应的CIK：{identifier}",
                    "suggestion": "请验证股票代码或CIK号码是否正确"
                }

            # Get company submissions JSON from SEC API
            submissions_url = f"{self.api_base}/submissions/CIK{cik}.json"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            response = self._make_request(submissions_url, headers)

            if not response:
                return {
                    "success": False,
                    "error": f"Timeout or connection error fetching data for {identifier}",
                    "suggestion": "SEC EDGAR service may be slow. Please try again in a moment."
                }

            data = response.json()

            # Extract company info from top level
            company_name = data.get("name", "")
            tickers = data.get("tickers", [])
            sic = data.get("sic")
            sic_description = data.get("sicDescription")
            state_of_incorporation = data.get("stateOfIncorporation")
            website = data.get("website")
            description = data.get("description")

            # Extract filings info
            if "filings" in data and "recent" in data["filings"]:
                recent = data["filings"]["recent"]
                filings_count = len(recent.get("form", []))

                # Get most recent filing date
                recent_filing_date = recent.get("filingDate", [None])[0] if isinstance(recent.get("filingDate"), list) else recent.get("filingDate")

                return {
                    "success": True,
                    "cik": cik,
                    "name": company_name or f"Company {cik.lstrip('0')}",
                    "identifier": identifier.upper(),
                    "tickers": tickers,
                    "ticker": tickers[0] if tickers else ticker,
                    "sic": sic,
                    "industry": sic_description,
                    "state_of_incorporation": state_of_incorporation,
                    "website": website,
                    "description": description,
                    "filings_count": filings_count,
                    "most_recent_filing": recent_filing_date,
                    "info": "Company information retrieved from SEC EDGAR"
                }
            else:
                return {
                    "success": False,
                    "error": f"No filings found for identifier: {identifier}",
                    "suggestion": "Please verify the ticker symbol or CIK number"
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
            # 参数验证
            if not query or not isinstance(query, str):
                return {
                    "success": False,
                    "error": "搜索关键词不能为空",
                    "suggestion": "请提供至少2个字符的公司名称关键词",
                    "example": "search_companies('Apple') 或 search_companies('Technology')"
                }

            query = query.strip()

            if len(query) < 2:
                return {
                    "success": False,
                    "error": f"搜索关键词太短：'{query}'",
                    "suggestion": "请提供至少2个字符的公司名称关键词",
                    "example": "search_companies('Apple') 或 search_companies('Tesla')"
                }

            if not isinstance(limit, int) or limit < 1 or limit > 100:
                return {
                    "success": False,
                    "error": f"无效的返回数量限制：{limit}",
                    "suggestion": "返回数量应在1-100之间",
                    "example": "search_companies('Apple', limit=10)"
                }

            # Use local cache for search (SEC EDGAR search endpoint blocked)
            tickers = self._load_local_cache()

            if not tickers:
                return {
                    "success": False,
                    "error": "本地缓存未初始化",
                    "suggestion": "SEC 缓存正在下载，请稍后再试"
                }

            # Search by ticker (exact match) and title (contains)
            import re
            companies = []
            query_upper = query.upper()

            # Load full cache data for title search
            if not _CACHE_FILE.exists():
                return {
                    "success": False,
                    "error": "本地缓存文件不存在",
                    "suggestion": "请等待 SEC 缓存下载完成"
                }

            with open(_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)

            for item in cache_data.values():
                ticker = item.get("ticker", "").upper()
                title = item.get("title", "").upper()
                cik = str(item.get("cik_str", "")).zfill(10)

                # Exact ticker match
                if ticker == query_upper:
                    companies.insert(0, {"cik": cik, "ticker": ticker, "name": item.get("title", "")})
                    if len(companies) >= limit:
                        break

                # Partial title match
                elif query_upper in title:
                    if len(companies) < limit:
                        companies.append({"cik": cik, "ticker": ticker, "name": item.get("title", "")})

            if companies:
                return {
                    "success": True,
                    "companies": companies[:limit],
                    "count": len(companies[:limit]),
                    "query": query,
                    "source": "Local SEC cache"
                }

            return {
                "success": False,
                "error": f"未找到匹配的公司：{query}",
                "suggestion": "请尝试股票代码或公司名称搜索"
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
            from datetime import datetime, timedelta

            # 参数验证
            if not identifier or not isinstance(identifier, str):
                return {
                    "success": False,
                    "error": "公司标识符不能为空",
                    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
                    "example": "get_recent_filings('AAPL') 或 get_recent_filings('0000320193', form_type='10-K')"
                }

            identifier = identifier.strip()

            # 验证days参数
            if not isinstance(days, int) or days < 1 or days > 3650:
                return {
                    "success": False,
                    "error": f"无效的天数参数：{days}",
                    "suggestion": "天数应在1-3650之间（约10年）",
                    "example": "get_recent_filings('AAPL', days=90)"
                }

            # 验证limit参数
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                return {
                    "success": False,
                    "error": f"无效的返回数量限制：{limit}",
                    "suggestion": "返回数量应在1-100之间",
                    "example": "get_recent_filings('AAPL', limit=20)"
                }

            # 验证form_type参数
            valid_forms = ["10-K", "10-Q", "8-K", "10-K/A", "10-Q/A", "8-K/A", "DEF 14A", "S-1", "4", "3"]
            if form_type is not None:
                if not isinstance(form_type, str) or not form_type.strip():
                    return {
                        "success": False,
                        "error": "无效的表格类型参数",
                        "suggestion": f"有效的表格类型包括：{', '.join(valid_forms)}",
                        "example": "get_recent_filings('AAPL', form_type='10-K')"
                    }

                form_type = form_type.strip().upper()
                # 不强制要求form_type必须在valid_forms中，因为可能还有其他类型

            # Get CIK from identifier
            if isinstance(identifier, str) and identifier.isdigit():
                cik = identifier.lstrip('0')
            else:
                cik_result = self.get_cik_by_ticker(identifier)
                if not cik_result["success"]:
                    return {
                        "success": False,
                        "error": f"未找到标识符对应的CIK：{identifier}",
                        "suggestion": "请验证股票代码是否正确"
                    }
                cik = cik_result["cik"].lstrip('0')

            # Get company submissions JSON from SEC API
            submissions_url = f"{self.api_base}/submissions/CIK{cik.zfill(10)}.json"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            response = self._make_request(submissions_url, headers)

            if not response:
                return {
                    "success": False,
                    "error": f"Timeout or connection error fetching filings for {identifier}",
                    "suggestion": "SEC EDGAR service may be slow. Please try again in a moment."
                }

            data = response.json()

            # Extract filings from submissions
            if "filings" not in data or "recent" not in data["filings"]:
                return {
                    "success": False,
                    "error": f"No filings found for identifier: {identifier}"
                }

            recent = data["filings"]["recent"]

            # Extract filing data
            filings = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for i in range(len(recent.get("form", []))):
                form = recent["form"][i]
                filing_date_str = recent["filingDate"][i] if i < len(recent.get("filingDate", [])) else None
                accession_number = recent["accessionNumber"][i] if i < len(recent.get("accessionNumber", [])) else None
                primary_document = recent.get("primaryDocument", [None])[0] if i < len(recent.get("primaryDocument", [None])) else None
                primary_doc_description = recent.get("primaryDocDescription", [None])[0] if i < len(recent.get("primaryDocDescription", [None])) else None

                if not filing_date_str:
                    continue

                try:
                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")

                    # Filter by date
                    if filing_date < cutoff_date:
                        continue

                    # Filter by form type if specified
                    if form_type and form != form_type:
                        continue

                    # Build filing URLs
                    if accession_number:
                        # Replace dashes in accession number
                        acc_no_dashes = accession_number.replace('-', '')
                        cik_clean = cik.zfill(10)

                        # Index page (lists all documents)
                        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_no_dashes}/{accession_number}-index.htm"

                        # Primary document URL (direct link to main document)
                        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_no_dashes}/{primary_document}" if primary_document else index_url

                        filings.append({
                            "accession_number": accession_number,
                            "form_type": form,
                            "filing_date": filing_date_str,
                            "primary_document": primary_document or "",
                            "document_description": primary_doc_description or "",
                            "index_url": index_url,
                            "document_url": doc_url,
                            "url": doc_url  # For backward compatibility
                        })
                except (ValueError, IndexError):
                    continue

                if len(filings) >= limit:
                    break

            if filings:
                return {
                    "success": True,
                    "identifier": identifier.upper(),
                    "cik": cik.zfill(10),
                    "form_type": form_type,
                    "filings": filings,
                    "count": len(filings),
                    "days": days
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到符合条件的内容：{identifier}",
                    "suggestion": "请尝试调整表格类型过滤器或增加天数参数"
                }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting recent filings: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get recent filings: {str(e)}"
            }

    def get_company_facts(self, identifier: str) -> Dict[str, Any]:
        """Get company facts and financial metrics.

        Since SEC's XBRL Facts API is no longer available, this function
        provides links to 10-K and 10-Q filings where financial data can be found.

        Args:
            identifier: Company ticker symbol or CIK number

        Returns:
            Dictionary with company facts and links to financial documents
        """
        try:
            # 参数验证
            if not identifier or not isinstance(identifier, str):
                return {
                    "success": False,
                    "error": "公司标识符不能为空",
                    "suggestion": "请提供股票代码（如AAPL）或CIK号码（如0000320193）",
                    "example": "get_company_facts('AAPL') 或 get_company_facts('0000320193')"
                }

            identifier = identifier.strip()

            # 验证identifier格式（strip后检查长度）
            if len(identifier) == 0 or len(identifier) > 20:
                return {
                    "success": False,
                    "error": "无效的公司标识符长度",
                    "suggestion": "股票代码应为1-10个字母，CIK应为10位数字",
                    "example": "get_company_facts('AAPL') 或 get_company_facts('0000320193')"
                }

            # Get CIK from identifier
            cik, ticker = self._normalize_identifier(identifier)

            if not cik:
                return {
                    "success": False,
                    "error": f"未找到标识符对应的CIK：{identifier}",
                    "suggestion": "请验证股票代码或CIK号码是否正确"
                }

            # Get company submissions JSON from SEC API
            submissions_url = f"{self.api_base}/submissions/CIK{cik}.json"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }

            response = self._make_request(submissions_url, headers)

            if not response:
                return {
                    "success": False,
                    "error": f"Timeout or connection error fetching data for {identifier}",
                    "suggestion": "SEC EDGAR service may be slow. Please try again in a moment."
                }

            data = response.json()

            # Extract company info
            company_name = data.get("name", "")
            tickers = data.get("tickers", [])
            sic_description = data.get("sicDescription")

            # Get recent 10-K and 10-Q filings with financial data
            if "filings" not in data or "recent" not in data["filings"]:
                return {
                    "success": False,
                    "error": f"No filings found for identifier: {identifier}"
                }

            recent = data["filings"]["recent"]

            # Find 10-K (annual) and 10-Q (quarterly) filings
            annual_filings = []
            quarterly_filings = []

            for i in range(len(recent.get("form", []))):
                form = recent["form"][i]
                if form == "10-K":
                    accession_number = recent["accessionNumber"][i]
                    filing_date = recent["filingDate"][i]
                    primary_document = recent.get("primaryDocument", [None])[i] if i < len(recent.get("primaryDocument", [None])) else None

                    acc_no_dashes = accession_number.replace('-', '')
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary_document}" if primary_document else ""

                    annual_filings.append({
                        "accession_number": accession_number,
                        "filing_date": filing_date,
                        "document_url": doc_url,
                        "index_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{accession_number}-index.htm"
                    })

                elif form == "10-Q":
                    accession_number = recent["accessionNumber"][i]
                    filing_date = recent["filingDate"][i]
                    primary_document = recent.get("primaryDocument", [None])[i] if i < len(recent.get("primaryDocument", [None])) else None

                    acc_no_dashes = accession_number.replace('-', '')
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary_document}" if primary_document else ""

                    quarterly_filings.append({
                        "accession_number": accession_number,
                        "filing_date": filing_date,
                        "document_url": doc_url,
                        "index_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{accession_number}-index.htm"
                    })

            return {
                "success": True,
                "cik": cik,
                "name": company_name or f"Company {cik.lstrip('0')}",
                "identifier": identifier.upper(),
                "tickers": tickers,
                "industry": sic_description,
                "filings_summary": {
                    "annual_reports_10k": len(annual_filings),
                    "quarterly_reports_10q": len(quarterly_filings)
                },
                "latest_annual_filing": annual_filings[0] if annual_filings else None,
                "latest_quarterly_filing": quarterly_filings[0] if quarterly_filings else None,
                "financial_documents": {
                    "annual_10k": annual_filings[:3],
                    "quarterly_10q": quarterly_filings[:4]
                },
                "info": "Financial data available in 10-K (annual) and 10-Q (quarterly) reports",
                "note": "SEC's XBRL Facts API is no longer available. Financial statements are in the 10-K and 10-Q HTML documents."
            }

        except Exception as e:
            logger.error(f"[SEC EDGAR] Error getting company facts for {identifier}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get company facts: {str(e)}"
            }

