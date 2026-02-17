"""Parse sitemaps to discover all URLs on a therapy website."""
import requests
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def fetch_sitemap_urls(base_url: str, timeout: int = 10) -> List[str]:
    """
    Fetch all URLs from a website's sitemap.

    Args:
        base_url: The base URL of the website
        timeout: Request timeout in seconds

    Returns:
        List of URLs found in sitemap, or empty list if no sitemap found
    """
    urls = []

    # Try common sitemap locations
    sitemap_urls = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap-index.xml",
        f"{base_url}/sitemap1.xml"
    ]

    for sitemap_url in sitemap_urls:
        try:
            print(f"Trying sitemap: {sitemap_url}")
            response = requests.get(sitemap_url, timeout=timeout)

            if response.status_code == 200:
                print(f"[OK] Found sitemap at: {sitemap_url}")
                urls = _parse_sitemap_xml(response.text, base_url)

                if urls:
                    print(f"[OK] Extracted {len(urls)} URLs from sitemap")
                    return urls

        except requests.RequestException as e:
            print(f"  Could not fetch {sitemap_url}: {e}")
            continue

    # If no sitemap found, try robots.txt
    print("No sitemap.xml found, checking robots.txt...")
    sitemap_from_robots = _get_sitemap_from_robots(base_url, timeout)

    if sitemap_from_robots:
        try:
            response = requests.get(sitemap_from_robots, timeout=timeout)
            if response.status_code == 200:
                print(f"[OK] Found sitemap from robots.txt: {sitemap_from_robots}")
                urls = _parse_sitemap_xml(response.text, base_url)
                if urls:
                    print(f"[OK] Extracted {len(urls)} URLs from sitemap")
                    return urls
        except requests.RequestException:
            pass

    print("No sitemap found, will fall back to crawling")
    return []


def _parse_sitemap_xml(xml_content: str, base_url: str) -> List[str]:
    """
    Parse sitemap XML and extract all URLs.

    Handles both regular sitemaps and sitemap indexes.
    """
    urls = []

    try:
        root = ET.fromstring(xml_content)

        # Remove namespace for easier parsing
        # Sitemaps use namespace like {http://www.sitemaps.org/schemas/sitemap/0.9}
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

        # Check if this is a sitemap index (contains other sitemaps)
        sitemap_locs = root.findall('.//sitemap/loc')

        if sitemap_locs:
            # This is a sitemap index, fetch each sub-sitemap
            print(f"Found sitemap index with {len(sitemap_locs)} sub-sitemaps")
            for loc in sitemap_locs:
                if loc.text:
                    try:
                        response = requests.get(loc.text, timeout=10)
                        if response.status_code == 200:
                            sub_urls = _parse_sitemap_xml(response.text, base_url)
                            urls.extend(sub_urls)
                    except requests.RequestException:
                        continue
        else:
            # Regular sitemap, extract URLs
            url_locs = root.findall('.//url/loc')

            for loc in url_locs:
                if loc.text:
                    url = loc.text.strip()
                    # Only include URLs from the same domain
                    if urlparse(url).netloc == urlparse(base_url).netloc:
                        urls.append(url)

    except ET.ParseError as e:
        print(f"Error parsing sitemap XML: {e}")

    return urls


def _get_sitemap_from_robots(base_url: str, timeout: int = 10) -> Optional[str]:
    """Check robots.txt for sitemap URL."""
    try:
        robots_url = f"{base_url}/robots.txt"
        response = requests.get(robots_url, timeout=timeout)

        if response.status_code == 200:
            for line in response.text.split('\n'):
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    return sitemap_url
    except requests.RequestException:
        pass

    return None


def crawl_homepage_links(base_url: str, timeout: int = 10) -> List[str]:
    """
    Fallback: Crawl homepage to discover internal links.

    Use this when no sitemap is available.
    """
    urls = []

    try:
        print(f"Crawling homepage for links: {base_url}")
        response = requests.get(base_url, timeout=timeout)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')

            # Find all internal links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)

                # Only include URLs from same domain
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    # Remove fragments and query params for cleaner URLs
                    clean_url = full_url.split('#')[0].split('?')[0]

                    if clean_url and clean_url not in urls:
                        urls.append(clean_url)

            print(f"[OK] Found {len(urls)} links on homepage")

    except requests.RequestException as e:
        print(f"Error crawling homepage: {e}")

    return urls
