"""Main website scraper orchestrator."""
import time
import requests
import logging
from typing import Optional, Callable
from ..models.data_models import ScrapingResult, Therapist, Specialty
from .url_validator import normalize_url, validate_url
from .page_finder import find_pages_intelligently, deduplicate_urls
from .content_extractor import extract_therapists, extract_specialty

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """Orchestrates scraping of therapy websites."""

    def __init__(
        self,
        rate_limit_delay: float = 1.0,
        timeout: int = 30000,
        progress_callback: Optional[Callable[[str], None]] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the scraper.

        Args:
            rate_limit_delay: Delay between requests in seconds
            timeout: Page load timeout in milliseconds
            progress_callback: Optional callback for progress updates
            api_key: Optional Anthropic API key for intelligent URL discovery
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.api_key = api_key

    def _log(self, message: str):
        """Log a progress message."""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)

    def scrape_website(
        self,
        url: str,
        manual_about_urls: list = None,
        manual_specialty_urls: list = None
    ) -> ScrapingResult:
        """
        Scrape a therapy website for therapists and specialties.

        Args:
            url: The website URL to scrape
            manual_about_urls: Optional list of manual therapist/about page URLs
            manual_specialty_urls: Optional list of manual specialty page URLs

        Returns:
            ScrapingResult with therapists, specialties, and any errors
        """
        errors = []
        therapists = []
        specialties = []

        # Normalize URL
        url = normalize_url(url)
        self._log(f"Scraping {url}")

        # Validate URL
        is_valid, error = validate_url(url)
        if not is_valid:
            errors.append(f"URL validation failed: {error}")
            return ScrapingResult(
                website_url=url,
                therapists=[],
                specialties=[],
                errors=errors
            )

        try:
            # Debug: Check if API key is available
            import sys
            print(f"DEBUG: API key present: {bool(self.api_key)}", file=sys.stderr, flush=True)
            print(f"DEBUG: API key value (first 10 chars): {self.api_key[:10] if self.api_key else 'None'}", file=sys.stderr, flush=True)

            # Use intelligent discovery if API key is available
            if self.api_key:
                print("DEBUG: Entering intelligent discovery branch", file=sys.stderr, flush=True)
                self._log("Using intelligent AI-powered page discovery...")
                therapist_urls, specialty_urls = find_pages_intelligently(url, self.api_key)
                print(f"DEBUG: Intelligent discovery returned: {len(therapist_urls)} therapist URLs, {len(specialty_urls)} specialty URLs", file=sys.stderr, flush=True)

                # Add manual URLs if provided
                if manual_about_urls:
                    self._log(f"Adding {len(manual_about_urls)} manual therapist URL(s)")
                    therapist_urls.extend([normalize_url(u) for u in manual_about_urls])
                    therapist_urls = deduplicate_urls(therapist_urls)

                if manual_specialty_urls:
                    self._log(f"Adding {len(manual_specialty_urls)} manual specialty URL(s)")
                    specialty_urls.extend([normalize_url(u) for u in manual_specialty_urls])
                    specialty_urls = deduplicate_urls(specialty_urls)

            else:
                # Fallback to old pattern-based approach
                self._log("API key not provided, using pattern-based discovery...")
                # Load homepage
                self._log("Loading homepage...")
                homepage_html = self._load_page(url)

                if not homepage_html:
                    errors.append("Failed to load homepage")
                    return ScrapingResult(
                        website_url=url,
                        therapists=[],
                        specialties=[],
                        errors=errors
                    )

                # Find therapist pages (legacy)
                from .page_finder import _find_therapist_pages_legacy, _find_specialty_pages_legacy
                self._log("Finding therapist pages...")
                therapist_urls = _find_therapist_pages_legacy(homepage_html, url)
                therapist_urls = deduplicate_urls(therapist_urls)

                # Add manual therapist URLs
                if manual_about_urls:
                    self._log(f"Adding {len(manual_about_urls)} manual therapist URL(s)")
                    therapist_urls.extend([normalize_url(u) for u in manual_about_urls])
                    therapist_urls = deduplicate_urls(therapist_urls)

                # Find specialty pages (legacy)
                self._log("Finding specialty pages...")
                specialty_urls_scored = _find_specialty_pages_legacy(homepage_html, url)
                specialty_urls = [url for url, score in specialty_urls_scored[:20]]  # Limit to top 20
                specialty_urls = deduplicate_urls(specialty_urls)

                # Add manual specialty URLs
                if manual_specialty_urls:
                    self._log(f"Adding {len(manual_specialty_urls)} manual specialty URL(s)")
                    specialty_urls.extend([normalize_url(u) for u in manual_specialty_urls])
                    specialty_urls = deduplicate_urls(specialty_urls)

            self._log(f"Found {len(therapist_urls)} total therapist page(s)")
            self._log(f"Found {len(specialty_urls)} total specialty page(s)")

            # Scrape therapist pages
            for therapist_url in therapist_urls:
                time.sleep(self.rate_limit_delay)

                self._log(f"Scraping therapist page: {therapist_url}")
                therapist_html = self._load_page(therapist_url)

                if therapist_html:
                    page_therapists = extract_therapists(therapist_html, therapist_url)
                    therapists.extend(page_therapists)
                    self._log(f"Found {len(page_therapists)} therapist(s) on this page")

            # Add manual specialty URLs
            if manual_specialty_urls:
                self._log(f"Adding {len(manual_specialty_urls)} manual specialty URL(s)")
                specialty_urls.extend([normalize_url(u) for u in manual_specialty_urls])
                specialty_urls = deduplicate_urls(specialty_urls)

            self._log(f"Found {len(specialty_urls)} total specialty page(s)")

            # Scrape specialty pages
            for specialty_url in specialty_urls:
                time.sleep(self.rate_limit_delay)

                self._log(f"Scraping specialty page: {specialty_url}")
                specialty_html = self._load_page(specialty_url)

                if specialty_html:
                    specialty = extract_specialty(specialty_html, specialty_url)
                    if specialty:
                        specialties.append(specialty)
                        self._log(f"Extracted specialty: {specialty.name}")

        except Exception as e:
            errors.append(f"Scraping error: {str(e)}")
            self._log(f"Error: {str(e)}")

        # Summary
        self._log(f"Scraping complete: {len(therapists)} therapist(s), {len(specialties)} specialty(ies)")

        if not therapists:
            errors.append("No therapists found - please check if the site has a team/about page")

        if not specialties:
            errors.append("No specialties found - the site may not have separate specialty pages")

        return ScrapingResult(
            website_url=url,
            therapists=therapists,
            specialties=specialties,
            errors=errors
        )

    def _load_page(self, url: str) -> Optional[str]:
        """
        Load a page and return its HTML content using HTTP requests.

        Args:
            url: URL to load

        Returns:
            HTML content or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout / 1000,  # Convert ms to seconds
                allow_redirects=True
            )

            if response.status_code >= 400:
                self._log(f"Failed to load {url}: status {response.status_code}")
                return None

            return response.text

        except requests.exceptions.Timeout:
            self._log(f"Timeout loading {url}")
            return None
        except requests.exceptions.RequestException as e:
            self._log(f"Error loading {url}: {str(e)}")
            return None
