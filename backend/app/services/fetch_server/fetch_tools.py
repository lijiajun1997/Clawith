"""
Fetch tools for web scraping and content conversion.

Adapted from MCP Fetch Server to work within the Clawith framework.
"""
import re
from typing import Tuple
from urllib.parse import urlparse, urlunparse
from loguru import logger


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    try:
        import markdownify
        import readabilipy.simple_json

        ret = readabilipy.simple_json.simple_json_from_html_string(
            html, use_readability=True
        )
        if not ret["content"]:
            return "<error>Page failed to be simplified from HTML</error>"
        content = markdownify.markdownify(
            ret["content"],
            heading_style=markdownify.ATX,
        )
        return content
    except Exception as e:
        logger.error(f"[fetch_server] Error extracting content from HTML: {str(e)}")
        return f"<error>Failed to extract content: {str(e)}</error>"


def get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL.

    Args:
        url: Website URL to get robots.txt for

    Returns:
        URL of the robots.txt file
    """
    # Parse the URL into components
    parsed = urlparse(url)

    # Reconstruct the base URL with just scheme, netloc, and /robots.txt path
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))

    return robots_url


async def check_may_autonomously_fetch_url(
    url: str,
    user_agent: str,
    proxy_url: str | None = None
) -> Tuple[bool, str]:
    """
    Check if the URL can be fetched by the user agent according to the robots.txt file.

    Returns:
        Tuple of (allowed: bool, error_message: str)
    """
    try:
        from httpx import AsyncClient, HTTPError
        from protego import Protego

        robot_txt_url = get_robots_txt_url(url)

        async with AsyncClient(proxy=proxy_url, timeout=10.0) as client:
            try:
                response = await client.get(
                    robot_txt_url,
                    follow_redirects=True,
                    headers={"User-Agent": user_agent},
                )
            except HTTPError:
                return False, f"Failed to fetch robots.txt {robot_txt_url} due to a connection issue"

            if response.status_code in (401, 403):
                return False, f"robots.txt ({robot_txt_url}) forbids access (status {response.status_code})"
            elif 400 <= response.status_code < 500:
                # No robots.txt or client error, assume allowed
                return True, ""

            robot_txt = response.text

        # Process robots.txt - remove comments
        processed_robot_txt = "\n".join(
            line for line in robot_txt.splitlines() if not line.strip().startswith("#")
        )
        robot_parser = Protego.parse(processed_robot_txt)

        if not robot_parser.can_fetch(str(url), user_agent):
            return False, f"The site's robots.txt specifies that autonomous fetching is not allowed for {url}"

        return True, ""

    except Exception as e:
        logger.warning(f"[fetch_server] Error checking robots.txt: {str(e)}")
        # On error, allow but with warning
        return True, f"Warning: Could not verify robots.txt: {str(e)}"


async def fetch_url(
    url: str,
    user_agent: str,
    force_raw: bool = False,
    proxy_url: str | None = None,
    timeout: int = 30
) -> Tuple[str, str, str]:
    """
    Fetch the URL and return the content in a form ready for the LLM.

    Returns:
        Tuple of (content: str, prefix: str, error: str)
    """
    try:
        from httpx import AsyncClient, HTTPError

        async with AsyncClient(proxy=proxy_url, timeout=timeout) as client:
            try:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": user_agent},
                )
            except HTTPError as e:
                return "", "", f"Failed to fetch {url}: {str(e)}"

            if response.status_code >= 400:
                return "", "", f"Failed to fetch {url} - status code {response.status_code}"

            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = (
            "<html" in page_raw[:100].lower() or
            "text/html" in content_type or
            not content_type
        )

        if is_page_html and not force_raw:
            content = extract_content_from_html(page_raw)
            return content, "", ""
        else:
            prefix = f"Content type {content_type} cannot be simplified to markdown, showing raw content:\n\n"
            return page_raw, prefix, ""

    except Exception as e:
        logger.error(f"[fetch_server] Error fetching URL {url}: {str(e)}")
        return "", "", f"Failed to fetch {url}: {str(e)}"


def sanitize_url(url: str) -> str:
    """Sanitize and validate URL.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    # Remove any leading/trailing whitespace
    url = url.strip()

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    return url


def is_valid_url(url: str) -> bool:
    """Check if URL is valid.

    Args:
        url: URL to validate

    Returns:
        True if URL appears valid, False otherwise
    """
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def truncate_content(content: str, max_length: int = 5000, start_index: int = 0) -> Tuple[str, bool]:
    """Truncate content to max length and indicate if more content is available.

    Args:
        content: Content to truncate
        max_length: Maximum length to return
        start_index: Start index for slicing

    Returns:
        Tuple of (truncated_content: str, has_more: bool)
    """
    original_length = len(content)

    if start_index >= original_length:
        return "<error>No more content available.</error>", False

    truncated_content = content[start_index:start_index + max_length]

    if not truncated_content:
        return "<error>No more content available.</error>", False

    has_more = (start_index + max_length) < original_length

    if has_more:
        next_start = start_index + len(truncated_content)
        remaining = original_length - next_start
        truncated_content += f"\n\n<error>Content truncated. {remaining} more characters available. Use start_index={next_start} to continue.</error>"

    return truncated_content, has_more
