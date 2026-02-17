"""URL validation and normalization utilities."""
import requests
from urllib.parse import urlparse, urljoin
from typing import Optional


def normalize_url(url: str) -> str:
    """
    Normalize a URL by adding https:// if missing and removing trailing slashes.

    Args:
        url: The URL to normalize

    Returns:
        Normalized URL string
    """
    url = url.strip()

    # Add https:// if no scheme provided
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]

    return url


def validate_url(url: str, timeout: int = 10) -> tuple[bool, Optional[str]]:
    """
    Validate that a URL is accessible.

    Args:
        url: The URL to validate
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Normalize first
        url = normalize_url(url)

        # Parse to validate structure
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "Invalid URL format"

        # Make HEAD request to check accessibility
        response = requests.head(url, timeout=timeout, allow_redirects=True)

        if response.status_code >= 400:
            return False, f"Site returned status code {response.status_code}"

        return True, None

    except requests.exceptions.Timeout:
        return False, "Request timed out - site may be down"
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to site"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def join_url(base_url: str, path: str) -> str:
    """
    Join a base URL with a path, handling relative and absolute paths.

    Args:
        base_url: The base URL
        path: The path to join

    Returns:
        Complete URL
    """
    # If path is already absolute, return it
    if path.startswith('http://') or path.startswith('https://'):
        return path

    return urljoin(base_url, path)
