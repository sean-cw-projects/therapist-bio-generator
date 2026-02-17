"""AI-powered URL classification using Claude API."""
import json
from typing import List, Dict
from anthropic import Anthropic


def classify_urls_with_ai(
    urls: List[str],
    api_key: str,
    base_url: str
) -> Dict[str, List[str]]:
    """
    Use Claude AI to classify URLs into therapist pages vs specialty pages.

    Args:
        urls: List of URLs to classify
        api_key: Anthropic API key
        base_url: The base URL of the website (for context)

    Returns:
        Dictionary with keys: 'therapist_pages', 'specialty_pages', 'other'
    """
    if not urls:
        return {'therapist_pages': [], 'specialty_pages': [], 'other': []}

    # Limit to reasonable number of URLs to avoid token limits
    if len(urls) > 100:
        print(f"[WARNING] Too many URLs ({len(urls)}), sampling 100 most relevant")
        urls = _filter_relevant_urls(urls, base_url)[:100]

    print(f"[AI] Using AI to classify {len(urls)} URLs...")

    # DEBUG: Show sample URLs being classified
    import sys
    print(f"DEBUG: Sample URLs being sent to AI:", file=sys.stderr, flush=True)
    for url in urls[:10]:
        print(f"  - {url}", file=sys.stderr, flush=True)

    client = Anthropic(api_key=api_key)

    # Build the prompt
    url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])

    prompt = f"""You are analyzing URLs from a therapy/counseling website to identify which pages contain therapist bios vs which contain specialty/service descriptions.

Website: {base_url}

URLs to classify:
{url_list}

Classify each URL into one of these categories:

1. **therapist_pages**: Individual therapist/clinician bio pages
   - Look for patterns like: /about-[name], /team/[name], /staff/[name], /therapists/[name]
   - Examples: /about-john-smith, /team/dr-jane-doe, /staff/therapists/mary-jones
   - Individual names in URL path

2. **specialty_pages**: Service/specialty/treatment pages
   - Look for patterns like: /services/[specialty], /[specialty]-therapy, /treatment/[issue]
   - Examples: /anxiety-therapy, /services/couples-counseling, /emdr
   - Treatment modalities, conditions, or service offerings

3. **other**: Homepage, contact, blog, general info
   - Examples: /, /contact, /blog, /resources, /insurance, /faq

Return ONLY a valid JSON object in this exact format (no markdown, no explanation):
{{
  "therapist_pages": ["url1", "url2"],
  "specialty_pages": ["url3", "url4"],
  "other": ["url5"]
}}

Important:
- Include the FULL URL in your response, exactly as provided above
- Be generous with therapist pages - when in doubt, include it
- Group practice sites may have multiple therapist pages
- Return ONLY the JSON object, nothing else"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        result = json.loads(response_text)

        print(f"[OK] AI classified URLs:")
        print(f"  - {len(result.get('therapist_pages', []))} therapist pages")
        print(f"  - {len(result.get('specialty_pages', []))} specialty pages")
        print(f"  - {len(result.get('other', []))} other pages")

        # DEBUG: Print actual therapist pages found
        import sys
        therapist_pages = result.get('therapist_pages', [])
        if therapist_pages:
            print(f"DEBUG: Therapist pages found:", file=sys.stderr, flush=True)
            for url in therapist_pages[:10]:  # Show first 10
                print(f"  - {url}", file=sys.stderr, flush=True)
        else:
            print(f"DEBUG: NO therapist pages found. Sample 'other' URLs:", file=sys.stderr, flush=True)
            for url in result.get('other', [])[:10]:
                print(f"  - {url}", file=sys.stderr, flush=True)

        return result

    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing AI response: {e}")
        print(f"Response was: {response_text}")
        # Fallback to empty classification
        return {'therapist_pages': [], 'specialty_pages': [], 'other': urls}

    except Exception as e:
        print(f"[ERROR] Error calling Claude API: {e}")
        # Fallback to empty classification
        return {'therapist_pages': [], 'specialty_pages': [], 'other': urls}


def _filter_relevant_urls(urls: List[str], base_url: str) -> List[str]:
    """
    Filter URLs to keep most relevant ones.

    Prioritizes:
    - URLs with names or specialty keywords
    - Shorter paths (more likely to be main pages)
    - Avoids blog posts, resources, etc.
    """
    scored_urls = []

    for url in urls:
        score = 0
        path = url.replace(base_url, '').lower()

        # Boost for potential therapist pages
        if any(word in path for word in ['about', 'team', 'staff', 'therapist', 'clinician', 'dr-', 'meet']):
            score += 10

        # Boost for potential specialty pages
        if any(word in path for word in ['therapy', 'counseling', 'treatment', 'service', 'anxiety',
                                          'depression', 'trauma', 'couples', 'family', 'emdr', 'cbt']):
            score += 5

        # Penalize likely non-content pages
        if any(word in path for word in ['blog', 'post', 'article', 'resource', 'tag', 'category',
                                          'archive', 'wp-content', 'feed', 'sitemap']):
            score -= 20

        # Prefer shorter paths
        path_depth = path.count('/')
        score -= path_depth

        scored_urls.append((score, url))

    # Sort by score (descending) and return URLs
    scored_urls.sort(reverse=True, key=lambda x: x[0])
    return [url for score, url in scored_urls]
