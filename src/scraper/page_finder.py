"""Find therapist and specialty pages on therapy websites using AI classification."""
import re
from typing import List, Tuple
from urllib.parse import urlparse
from .sitemap_parser import fetch_sitemap_urls, crawl_homepage_links
from .url_classifier import classify_urls_with_ai


def find_pages_intelligently(
    base_url: str,
    api_key: str
) -> Tuple[List[str], List[str]]:
    """
    Intelligently discover and classify pages using sitemap + AI.

    This is the NEW approach that replaces hardcoded URL patterns.

    Args:
        base_url: Base URL of the website
        api_key: Anthropic API key for AI classification

    Returns:
        Tuple of (therapist_urls, specialty_urls)
    """
    print("\n[DISCOVERY] Discovering pages intelligently...")

    # Step 1: Get all URLs from sitemap or homepage
    urls = fetch_sitemap_urls(base_url)

    if not urls:
        # Fallback: crawl homepage for links
        print("[DISCOVERY] No sitemap found, crawling homepage...")
        urls = crawl_homepage_links(base_url)

    if not urls:
        print("[ERROR] Could not discover any URLs")
        return [], []

    # Step 2: Use AI to classify URLs
    classified = classify_urls_with_ai(urls, api_key, base_url)

    therapist_urls = classified.get('therapist_pages', [])
    specialty_urls = classified.get('specialty_pages', [])

    print(f"\n[OK] Intelligent discovery complete:")
    print(f"  - Found {len(therapist_urls)} therapist page(s)")
    print(f"  - Found {len(specialty_urls)} specialty page(s)")

    return therapist_urls, specialty_urls


# Legacy functions - kept for backward compatibility
# These now internally use the intelligent approach

def find_therapist_pages(html: str, base_url: str, api_key: str = None) -> List[str]:
    """
    Find potential therapist/team pages on the website.

    DEPRECATED: This function now uses intelligent AI-based discovery.
    The html parameter is ignored - we use sitemap instead.

    Args:
        html: HTML content (ignored, kept for compatibility)
        base_url: Base URL of the website
        api_key: Optional Anthropic API key (required for intelligent mode)

    Returns:
        List of URLs for therapist pages
    """
    if api_key:
        therapist_urls, _ = find_pages_intelligently(base_url, api_key)
        return therapist_urls
    else:
        # Fallback to old pattern matching if no API key
        return _find_therapist_pages_legacy(html, base_url)


def find_specialty_pages(html: str, base_url: str, api_key: str = None) -> List[Tuple[str, int]]:
    """
    Find potential specialty/service pages on the website.

    DEPRECATED: This function now uses intelligent AI-based discovery.
    The html parameter is ignored - we use sitemap instead.

    Args:
        html: HTML content (ignored, kept for compatibility)
        base_url: Base URL of the website
        api_key: Optional Anthropic API key (required for intelligent mode)

    Returns:
        List of tuples (URL, score) - score is always 10 for AI-classified pages
    """
    if api_key:
        _, specialty_urls = find_pages_intelligently(base_url, api_key)
        # Return with score of 10 for compatibility
        return [(url, 10) for url in specialty_urls]
    else:
        # Fallback to old pattern matching if no API key
        return _find_specialty_pages_legacy(html, base_url)


# Legacy implementations (only used as fallback)

def _find_therapist_pages_legacy(html: str, base_url: str) -> List[str]:
    """Legacy pattern-based therapist page finder (fallback only)."""
    from bs4 import BeautifulSoup
    from .url_validator import join_url

    soup = BeautifulSoup(html, 'lxml')
    potential_urls = set()

    # Common paths to check
    common_paths = [
        '/team', '/about', '/therapists', '/clinicians',
        '/meet-the-team', '/our-team', '/staff', '/meet-our-therapists',
        '/about-us', '/our-therapists', '/our-clinicians', '/providers'
    ]

    for path in common_paths:
        potential_urls.add(join_url(base_url, path))

    # Find links in navigation with relevant keywords
    nav_keywords = ['team', 'about', 'therapist', 'clinician', 'staff', 'provider', 'meet', 'bio']

    all_links = soup.find_all('a', href=True)

    for link in all_links:
        href = link['href']
        link_text = link.get_text(strip=True).lower()
        full_url = join_url(base_url, href)
        url_lower = full_url.lower()

        # Skip if external link
        if not _is_same_domain(full_url, base_url):
            continue

        # Check if link text contains relevant keywords
        if any(keyword in link_text for keyword in nav_keywords):
            potential_urls.add(full_url)

        # Check if URL path contains relevant keywords
        url_path = urlparse(full_url).path.lower()
        if any(keyword in url_path for keyword in nav_keywords):
            potential_urls.add(full_url)

    return list(potential_urls)


def _find_specialty_pages_legacy(html: str, base_url: str) -> List[Tuple[str, int]]:
    """Legacy pattern-based specialty page finder (fallback only)."""
    from bs4 import BeautifulSoup
    from .url_validator import join_url

    soup = BeautifulSoup(html, 'lxml')
    url_scores = {}

    all_links = soup.find_all('a', href=True)

    for link in all_links:
        href = link['href']
        full_url = join_url(base_url, href)

        if full_url in url_scores:
            continue

        if not _is_same_domain(full_url, base_url):
            continue

        score = _score_specialty_url(
            full_url,
            link.get_text(strip=True),
            _get_parent_context(link)
        )

        if score > 0:
            url_scores[full_url] = score

    sorted_urls = sorted(url_scores.items(), key=lambda x: x[1], reverse=True)
    filtered_urls = [(url, score) for url, score in sorted_urls if score >= 3]

    return filtered_urls


def _score_specialty_url(url: str, link_text: str, context: str) -> int:
    """Score a URL based on how likely it is to be a specialty page."""
    score = 0
    url_lower = url.lower()
    link_text_lower = link_text.lower()
    context_lower = context.lower()

    if re.search(r'/[\w-]+-therapy/?$', url_lower):
        score += 3
    if re.search(r'/[\w-]+-counseling/?$', url_lower):
        score += 3
    if re.search(r'/[\w-]+-treatment/?$', url_lower):
        score += 2

    service_keywords = ['service', 'specialty', 'specialize', 'treatment', 'help']
    if any(keyword in url_lower for keyword in service_keywords):
        score += 2

    nav_keywords = ['service', 'specialty', 'specialties', 'offering', 'offerings', 'we help', 'conditions']
    if any(keyword in context_lower for keyword in nav_keywords):
        score += 2

    specialty_indicators = [
        'therapy', 'counseling', 'treatment', 'anxiety', 'depression',
        'trauma', 'emdr', 'couples', 'family', 'individual', 'grief',
        'addiction', 'ptsd', 'ocd'
    ]
    if any(indicator in link_text_lower for indicator in specialty_indicators):
        score += 2

    excluded_keywords = [
        'contact', 'about', 'team', 'blog', 'privacy', 'terms',
        'faq', 'insurance', 'fees', 'location', 'directions', 'schedule'
    ]
    if any(keyword in url_lower for keyword in excluded_keywords):
        score -= 5

    parsed = urlparse(url)
    if parsed.path in ['', '/', '/index', '/index.html', '/home']:
        score -= 5

    return score


def _get_parent_context(element) -> str:
    """Get text context from parent elements (nav, section, etc.)."""
    context = ""
    parent = element.find_parent(['nav', 'section', 'div'])
    if parent:
        heading = parent.find(['h1', 'h2', 'h3', 'h4'])
        if heading:
            context = heading.get_text(strip=True)
    return context


def _is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    domain1 = urlparse(url1).netloc
    domain2 = urlparse(url2).netloc
    return domain1 == domain2


def deduplicate_urls(urls: List[str]) -> List[str]:
    """
    Remove duplicate URLs, keeping only one version.

    Handles cases like /page vs /page/ or http vs https.
    """
    seen = set()
    unique_urls = []

    for url in urls:
        # Normalize for comparison
        normalized = url.lower().rstrip('/')

        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)

    return unique_urls
