#!/usr/bin/env python3
"""
SEC EDGAR Ticker Synchronization Script

This script downloads the complete SEC company_tickers.json file and
saves it to the local cache directory for fast lookups.

Usage:
    python -m app.services.sec_edgar_server.sync_tickers

The SEC updates this file daily. Run this script periodically to keep
your local cache up to date.

Source: https://www.sec.gov/files/company_tickers.json
"""

import sys
import json
import time
from pathlib import Path
from loguru import logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.sec_edgar_server.sec_tools import _CACHE_DIR, _CACHE_FILE


def download_tickers() -> bool:
    """Download SEC company_tickers.json and save to local cache.

    Returns:
        True if successful, False otherwise
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        logger.info("[SEC Sync] Starting SEC company tickers download...")

        # Create session with retry logic
        session = requests.Session()
        retry_strategy = Retry(
            total=5,  # More retries for download
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # SEC official data URL
        ticker_url = "https://www.sec.gov/files/company_tickers.json"

        logger.info(f"[SEC Sync] Downloading from: {ticker_url}")

        # Download with progress
        response = session.get(
            ticker_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            },
            timeout=60,  # 60 seconds timeout
            stream=True
        )

        response.raise_for_status()

        # Get total size for progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        # Ensure cache directory exists
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Download with progress indicator
        logger.info(f"[SEC Sync] Total size: {total_size / 1024 / 1024:.2f} MB")

        temp_file = _CACHE_FILE.with_suffix('.tmp')
        start_time = time.time()

        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024) == 0:  # Log every MB
                            elapsed = time.time() - start_time
                            speed = (downloaded / 1024 / 1024) / elapsed
                            logger.info(f"[SEC Sync] Progress: {progress:.1f}% ({downloaded / 1024 / 1024:.1f} MB) at {speed:.1f} MB/s")

        # Rename temp file to final file
        temp_file.replace(_CACHE_FILE)

        # Verify the file
        with open(_CACHE_FILE, 'r') as f:
            data = json.load(f)

        company_count = len(data)
        elapsed = time.time() - start_time

        logger.success(f"[SEC Sync] ✓ Download completed successfully!")
        logger.success(f"[SEC Sync] ✓ Companies: {company_count:,}")
        logger.success(f"[SEC Sync] ✓ Time: {elapsed:.1f} seconds")
        logger.success(f"[SEC Sync] ✓ Saved to: {_CACHE_FILE}")
        logger.success(f"[SEC Sync] ✓ File size: {_CACHE_FILE.stat().st_size / 1024 / 1024:.2f} MB")

        return True

    except requests.exceptions.Timeout:
        logger.error("[SEC Sync] ✗ Download timeout. Please check your internet connection and try again.")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[SEC Sync] ✗ Connection error: {str(e)}")
        logger.error("[SEC Sync] Please check if you can access https://www.sec.gov")
        return False
    except Exception as e:
        logger.error(f"[SEC Sync] ✗ Unexpected error: {str(e)}")
        return False


def main():
    """Main entry point."""
    print("=" * 70)
    print("SEC EDGAR Company Tickers Synchronization")
    print("=" * 70)
    print()
    print("This script will download the complete SEC company database")
    print("(~10,000+ companies) and save it to local cache.")
    print()
    print("Source: https://www.sec.gov/files/company_tickers.json")
    print("Cache:  /data/sec_edgar_cache/company_tickers.json")
    print()
    print("Estimated download size: ~3 MB")
    print("Estimated time: 10-60 seconds (depending on connection)")
    print()

    success = download_tickers()

    print()
    print("=" * 70)
    if success:
        print("✓ Synchronization completed successfully!")
        print()
        print("The SEC EDGAR tools will now use the local cache for fast lookups.")
        print("Run this script again to update the cache (SEC updates daily).")
        return 0
    else:
        print("✗ Synchronization failed. Please check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
