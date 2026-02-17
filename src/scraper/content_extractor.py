"""Extract content from therapy website pages."""
import re
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from ..models.data_models import Therapist, Specialty


def extract_therapists(html: str, page_url: str) -> List[Therapist]:
    """
    Extract therapist information from a team/about page.

    Handles both:
    - Individual therapist pages (extract single therapist)
    - Directory pages with structured team member cards (extract multiple)
    - Generic directory pages are skipped

    Args:
        html: HTML content of the page
        page_url: URL of the page being parsed

    Returns:
        List of Therapist objects
    """
    import sys
    print(f"DEBUG: extract_therapists called for: {page_url}", file=sys.stderr, flush=True)

    soup = BeautifulSoup(html, 'lxml')
    therapists = []

    # Get full text for directory detection
    text_content = soup.get_text()

    # Check if this is a generic directory page (should be skipped)
    if _is_directory_page(soup, text_content, page_url):
        print(f"DEBUG: Detected as directory page, skipping: {page_url}", file=sys.stderr, flush=True)
        print(f"Skipping directory page: {page_url}")
        # Don't try to extract from directory pages - they should link to individual pages
        return []

    print(f"DEBUG: Not a directory page, proceeding with extraction", file=sys.stderr, flush=True)

    # Try to find multiple therapists (repeating pattern with structured cards)
    # Look for common class names
    team_selectors = [
        '.therapist', '.team-member', '.clinician', '.staff-member',
        '.practitioner', '[class*="team-"]', '[class*="therapist-"]',
        '[class*="clinician-"]', '[class*="staff-"]'
    ]

    team_members = []
    for selector in team_selectors:
        team_members = soup.select(selector)
        if len(team_members) > 0:
            break

    if len(team_members) > 1:
        # Multiple structured therapist cards found - extract each
        print(f"Found {len(team_members)} therapist cards on page")
        for member in team_members:
            therapist = _extract_single_therapist(member, page_url)
            if therapist:
                therapists.append(therapist)
    else:
        # Single therapist page or different structure
        # Try to extract from main content
        print(f"DEBUG: Extracting from main content for single therapist", file=sys.stderr, flush=True)
        therapist = _extract_from_main_content(soup, page_url)
        if therapist:
            print(f"DEBUG: Successfully extracted therapist: {therapist.name}", file=sys.stderr, flush=True)
            therapists.append(therapist)
        else:
            print(f"DEBUG: Failed to extract therapist from main content", file=sys.stderr, flush=True)

    print(f"DEBUG: Returning {len(therapists)} therapist(s)", file=sys.stderr, flush=True)
    return therapists


def _extract_single_therapist(element, page_url: str) -> Optional[Therapist]:
    """Extract therapist info from a single HTML element."""
    try:
        # Find name (usually in h2, h3, h4, or strong tag)
        name_elem = element.find(['h2', 'h3', 'h4', 'h5', 'strong', '.name'])
        if name_elem:
            name = name_elem.get_text(strip=True)
        else:
            # Fallback: use first text content that looks like a name
            text = element.get_text(strip=True)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            name = lines[0] if lines else "Unknown"

        # Extract credentials
        credentials = _extract_credentials(element.get_text())

        # Get bio text (all text content, cleaned)
        bio_text = _clean_text(element.get_text())

        if bio_text and len(bio_text) > 50:  # Minimum bio length
            return Therapist(
                name=name,
                credentials=credentials,
                bio_text=bio_text,
                source_url=page_url
            )
    except Exception as e:
        print(f"Error extracting therapist: {e}")

    return None


def _extract_from_main_content(soup: BeautifulSoup, page_url: str) -> Optional[Therapist]:
    """Extract therapist info from main content area (single therapist site)."""
    import sys
    print(f"DEBUG: _extract_from_main_content called", file=sys.stderr, flush=True)
    try:
        # Remove nav, footer, header, sidebar
        for tag in soup.find_all(['nav', 'header', 'footer', 'aside']):
            tag.decompose()

        # Look for main content area
        main_content = soup.find(['main', 'article', '[role="main"]', '#content', '.content'])

        if not main_content:
            main_content = soup.find('body')

        if not main_content:
            print(f"DEBUG: No main content found", file=sys.stderr, flush=True)
            return None

        # Get text content for analysis
        text_content = main_content.get_text()
        print(f"DEBUG: Text content length: {len(text_content)} chars", file=sys.stderr, flush=True)

        # FIRST: Check if this is a directory page - if so, skip it
        if _is_directory_page(soup, text_content, page_url):
            print(f"DEBUG: _is_directory_page returned True, skipping", file=sys.stderr, flush=True)
            print(f"Detected directory page, skipping: {page_url}")
            return None

        print(f"DEBUG: Not a directory page, continuing", file=sys.stderr, flush=True)

        # SECOND: Try to extract name from URL (most reliable for individual pages)
        name_from_url = _extract_name_from_url(page_url)
        print(f"DEBUG: name_from_url = {name_from_url}", file=sys.stderr, flush=True)

        if name_from_url:
            # Validate that this name is the page owner
            is_owner = _validate_name_is_page_owner(name_from_url, soup, text_content)
            print(f"DEBUG: _validate_name_is_page_owner returned {is_owner}", file=sys.stderr, flush=True)
            if is_owner:
                print(f"Extracted name from URL: {name_from_url}")
                name = name_from_url
            else:
                # URL had a name but it doesn't match page content
                # Fall back to content extraction
                name = _extract_therapist_name(soup, main_content, text_content, page_url)
                print(f"DEBUG: Fallback name extraction returned: {name}", file=sys.stderr, flush=True)
        else:
            # No name in URL, extract from content
            name = _extract_therapist_name(soup, main_content, text_content, page_url)
            print(f"DEBUG: Name from content: {name}", file=sys.stderr, flush=True)

        # Extract credentials
        credentials = _extract_credentials(text_content)
        print(f"DEBUG: Extracted credentials: {credentials}", file=sys.stderr, flush=True)

        # Get bio text
        bio_text = _clean_text(text_content)
        print(f"DEBUG: Bio text length: {len(bio_text) if bio_text else 0} chars", file=sys.stderr, flush=True)

        if bio_text and len(bio_text) > 100:
            print(f"DEBUG: Bio text length check passed, creating Therapist object", file=sys.stderr, flush=True)
            return Therapist(
                name=name,
                credentials=credentials,
                bio_text=bio_text,
                source_url=page_url
            )
    except Exception as e:
        print(f"Error extracting from main content: {e}")

    return None


def _extract_therapist_name(soup: BeautifulSoup, main_content, text_content: str, page_url: str) -> str:
    """
    Extract therapist name using multiple strategies, prioritizing most reliable sources.

    Returns the most likely name or "Unknown Therapist" if none found.
    """
    # Strategy 1: Check H1 (highest priority - usually contains page subject)
    h1 = main_content.find('h1')
    if h1:
        h1_text = h1.get_text(strip=True)
        # Clean common prefixes
        h1_text = re.sub(r'^(About|Meet|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+', '', h1_text, flags=re.IGNORECASE)
        if _looks_like_person_name(h1_text):
            if _validate_name_is_page_owner(h1_text, soup, text_content):
                return h1_text

    # Strategy 2: Check page title
    title = soup.find('title')
    if title:
        title_text = title.get_text(strip=True)
        # Try to extract name from title (e.g., "About Dr. Jane Doe | Therapy")
        name_in_title = re.search(r'(?:About|Meet|Dr\.?|)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', title_text)
        if name_in_title:
            potential_name = name_in_title.group(1).strip()
            if _looks_like_person_name(potential_name):
                if _validate_name_is_page_owner(potential_name, soup, text_content):
                    return potential_name

    # Strategy 3: Look for patterns like "I'm [Name]" or "My name is [Name]"
    # (High confidence - first person identification)
    intro_patterns = [
        r"I'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        r"I am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        r"My name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    ]

    for pattern in intro_patterns:
        match = re.search(pattern, text_content)
        if match:
            potential_name = match.group(1).strip()
            if _looks_like_person_name(potential_name):
                return potential_name

    # Strategy 4: Look for names with credentials nearby (but validate it's the page owner)
    # Pattern like "Jane Doe, LCSW, PhD" or "John Smith MA, LPC"
    name_with_creds_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[,\s]+([A-Z]{2,6}(?:[,\s]+[A-Z]{2,6})*)'
    matches = re.findall(name_with_creds_pattern, text_content)

    # Check each match and validate it's the page owner
    for match in matches:
        potential_name = match[0].strip()
        if _looks_like_person_name(potential_name):
            # Only use this name if it appears to be the page owner
            if _validate_name_is_page_owner(potential_name, soup, text_content):
                return potential_name
            # If first person language exists, use first match even without validation
            elif _has_first_person_language(text_content):
                return potential_name

    # Strategy 5: Check meta tags for author/name
    meta_name = soup.find('meta', attrs={'name': 'author'})
    if meta_name and meta_name.get('content'):
        potential_name = meta_name['content'].strip()
        if _looks_like_person_name(potential_name):
            return potential_name

    # Strategy 6: Look for h2 tags that look like names (with validation)
    for heading_tag in ['h2', 'h3']:
        headings = main_content.find_all(heading_tag)
        for heading in headings:
            text = heading.get_text(strip=True)
            text = re.sub(r'^(About|Meet|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+', '', text, flags=re.IGNORECASE)
            if _looks_like_person_name(text):
                if _validate_name_is_page_owner(text, soup, text_content):
                    return text

    # Fallback
    return "Unknown Therapist"


def _is_directory_page(soup: BeautifulSoup, text_content: str, page_url: str) -> bool:
    """
    Detect if this is a directory/team page listing multiple therapists.

    Directory pages should be skipped or handled differently than individual pages.

    Returns True if this appears to be a directory page.
    """
    import sys

    # Check 1: URL is generic (/about, /team, /staff, /our-therapists)
    url_path = urlparse(page_url).path.lower().strip('/')
    generic_paths = ['about', 'team', 'staff', 'our-team', 'our-therapists',
                     'our-staff', 'clinicians', 'therapists', 'meet-the-team']

    print(f"DEBUG: Directory check 1 - url_path='{url_path}', in generic_paths={url_path in generic_paths}", file=sys.stderr, flush=True)
    if url_path in generic_paths:
        print(f"DEBUG: Failed check 1 - generic path", file=sys.stderr, flush=True)
        return True

    # Check 2: Multiple names with credentials (5+ suggests directory)
    name_cred_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[,\s]+([A-Z]{2,6}(?:[,\s]+[A-Z]{2,6})*)'
    matches = re.findall(name_cred_pattern, text_content)

    # Extract unique potential names
    unique_names = set()
    for match in matches:
        name = match[0].strip()

        # Clean the name: remove newlines, extra whitespace, and trailing garbage
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
        name = re.split(r'\n', name)[0]  # Take only first line if multiline
        name = name.strip()

        # Only consider if it looks like a person name
        if _looks_like_person_name(name):
            unique_names.add(name)

    print(f"DEBUG: Directory check 2 - found {len(unique_names)} unique names with credentials", file=sys.stderr, flush=True)
    # Increase threshold to 5 to avoid false positives from city names, institutions, etc.
    if len(unique_names) >= 5:
        print(f"DEBUG: Failed check 2 - multiple names: {list(unique_names)[:5]}", file=sys.stderr, flush=True)
        return True

    # Check 3: Multiple "Learn more" or "Read bio" links (common in directories)
    learn_more_links = soup.find_all('a', string=re.compile(r'(learn more|read more|read bio|view profile|meet)', re.IGNORECASE))
    print(f"DEBUG: Directory check 3 - found {len(learn_more_links)} learn more links", file=sys.stderr, flush=True)
    if len(learn_more_links) >= 3:
        print(f"DEBUG: Failed check 3 - multiple learn more links", file=sys.stderr, flush=True)
        return True

    # Check 4: Repeating structural patterns (multiple team member cards)
    team_containers = soup.find_all(['div', 'article'], class_=re.compile(r'(team|staff|clinician|therapist|member)', re.IGNORECASE))
    print(f"DEBUG: Directory check 4 - found {len(team_containers)} team containers", file=sys.stderr, flush=True)
    if len(team_containers) >= 3:
        print(f"DEBUG: Failed check 4 - multiple team containers", file=sys.stderr, flush=True)
        return True

    print(f"DEBUG: Passed all directory checks - this is an individual page", file=sys.stderr, flush=True)

    return False


def _extract_name_from_url(page_url: str) -> Optional[str]:
    """
    Extract therapist name from URL path.

    Examples:
        /about-deb-azorsky -> "Deb Azorsky"
        /team/sue-johnson -> "Sue Johnson"
        /deb-azorsky -> "Deb Azorsky"
        /staff/dr-jane-doe -> "Jane Doe"

    Returns None if no name found in URL.
    """
    url_path = urlparse(page_url).path.strip('/')

    # Get the last part of the path (most specific)
    path_parts = url_path.split('/')
    last_part = path_parts[-1] if path_parts else ""

    if not last_part:
        return None

    # Remove common prefixes
    prefixes = ['about-', 'meet-', 'dr-', 'doctor-', 'therapist-']
    for prefix in prefixes:
        if last_part.startswith(prefix):
            last_part = last_part[len(prefix):]
            break

    # Convert URL slug to proper name
    # "deb-azorsky" -> "Deb Azorsky"
    name_parts = last_part.replace('_', '-').split('-')

    # Filter out common URL words
    stop_words = ['and', 'the', 'of', 'at', 'in', 'on', 'for', 'to']
    name_parts = [part for part in name_parts if part.lower() not in stop_words]

    # Capitalize each part
    name_parts = [part.capitalize() for part in name_parts if part]

    # Names are typically 2-4 words
    if len(name_parts) >= 2 and len(name_parts) <= 4:
        potential_name = ' '.join(name_parts)
        if _looks_like_person_name(potential_name):
            return potential_name

    return None


def _has_first_person_language(text_content: str) -> bool:
    """
    Check if the page uses first-person language (suggests individual page).

    Returns True if first-person pronouns are found.
    """
    # Look for first-person pronouns
    first_person_pattern = r'\b(I am|I\'m|I have|I\'ve|I specialize|I work|I help|my practice|my approach|my background)\b'

    matches = re.findall(first_person_pattern, text_content, re.IGNORECASE)

    # Need at least 2 instances to be confident
    return len(matches) >= 2


def _validate_name_is_page_owner(name: str, soup: BeautifulSoup, text_content: str) -> bool:
    """
    Validate that the extracted name is the page owner, not just mentioned.

    Checks:
    - Name appears in H1 or title
    - Name appears multiple times
    - First-person language near the name

    Returns True if name is likely the page owner.
    """
    if not name:
        return False

    # Check 1: Name in H1
    h1 = soup.find('h1')
    if h1 and name.lower() in h1.get_text().lower():
        return True

    # Check 2: Name in page title
    title = soup.find('title')
    if title and name.lower() in title.get_text().lower():
        return True

    # Check 3: Name appears multiple times (page owner mentioned throughout)
    name_occurrences = len(re.findall(re.escape(name), text_content, re.IGNORECASE))
    if name_occurrences >= 3:
        return True

    # Check 4: First-person language exists on page
    if _has_first_person_language(text_content):
        return True

    return False


def _looks_like_person_name(text: str) -> bool:
    """
    Check if text looks like a person's name.

    Returns False for:
    - Questions (contains '?')
    - Generic titles (Therapist, Counselor, etc.)
    - Long phrases (more than 4 words)
    - All caps text
    - Text with special characters
    - Location names (cities, states, etc.)
    """
    if not text or len(text) < 3:
        return False

    # Remove common prefixes
    text = re.sub(r'^(Dr\.?|Mr\.?|Ms\.?|Mrs\.?|Miss)\s+', '', text, flags=re.IGNORECASE)

    # Check for disqualifying patterns
    if '?' in text or '!' in text:
        return False

    if text.isupper():  # All caps
        return False

    # Too many words (names are typically 2-3 words)
    words = text.split()
    if len(words) > 4 or len(words) < 2:
        return False

    # Check for generic therapy-related words
    generic_terms = [
        'therapist', 'counselor', 'psychologist', 'psychiatrist',
        'therapy', 'counseling', 'psychotherapy', 'services',
        'about', 'welcome', 'home', 'contact', 'why', 'how', 'what',
        'our', 'team', 'staff', 'practice', 'clinic', 'center'
    ]

    text_lower = text.lower()
    if any(term in text_lower for term in generic_terms):
        return False

    # Filter out location names
    # Common directional prefixes
    if words[0].lower() in ['east', 'west', 'north', 'south', 'new']:
        return False

    # Common location words
    location_terms = [
        'saint', 'st.', 'san', 'santa', 'port', 'mount', 'fort',
        'lake', 'city', 'beach', 'river', 'bay', 'valley', 'springs',
        'hills', 'heights', 'park', 'grove', 'point', 'island',
        'college', 'university', 'hospital', 'center', 'institute'
    ]
    if any(term in text_lower for term in location_terms):
        return False

    # Must start with capital letter and contain at least one more capital (for last name)
    if not re.match(r'^[A-Z][a-z]+\s+[A-Z]', text):
        return False

    return True


def _extract_credentials(text: str) -> Optional[str]:
    """Extract credentials from text (e.g., LCSW, PhD, PsyD)."""
    # Common therapy credentials
    credential_pattern = r'\b([A-Z]{2,6}(?:-[A-Z]+)?)\b'
    common_credentials = [
        'LCSW', 'LMFT', 'LMHC', 'PHD', 'PSYD', 'MD', 'LCSW-C',
        'LPC', 'LPCC', 'LCPC', 'MSW', 'MA', 'MS', 'CADC', 'NCC',
        'LICSW', 'LISW', 'LCMHC', 'LCAT', 'ATR', 'RN', 'PMHNP',
        'CST', 'ACS', 'ACSW', 'LCADC', 'CAADC', 'CSAC', 'LMHP'
    ]

    found_credentials = []
    matches = re.findall(credential_pattern, text)

    for match in matches:
        if match.upper() in common_credentials:
            found_credentials.append(match.upper())

    # Remove duplicates and return as comma-separated string
    if found_credentials:
        return ', '.join(sorted(set(found_credentials)))

    return None


def _clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_specialty(html: str, page_url: str) -> Optional[Specialty]:
    """
    Extract specialty information from a specialty page.

    Args:
        html: HTML content of the page
        page_url: URL of the page

    Returns:
        Specialty object or None
    """
    soup = BeautifulSoup(html, 'lxml')

    try:
        # Remove nav, footer, header, sidebar
        for tag in soup.find_all(['nav', 'header', 'footer', 'aside']):
            tag.decompose()

        # Extract specialty name from title or h1
        name = None

        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
        else:
            # Try page title
            title = soup.find('title')
            if title:
                name = title.get_text(strip=True)

        # Fallback: extract from URL
        if not name:
            # Get last part of URL path
            url_parts = page_url.rstrip('/').split('/')
            name = url_parts[-1].replace('-', ' ').replace('_', ' ').title()

        # Extract main content
        main_content = soup.find(['main', 'article', '[role="main"]', '#content', '.content'])

        if not main_content:
            main_content = soup.find('body')

        content = _clean_text(main_content.get_text()) if main_content else ""

        if name and content and len(content) > 100:
            return Specialty(
                name=name,
                content=content[:1000],  # Limit content length
                url=page_url
            )
    except Exception as e:
        print(f"Error extracting specialty: {e}")

    return None
        
