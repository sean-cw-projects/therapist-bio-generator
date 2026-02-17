"""Quick test script to verify improved page detection."""
import requests
from src.scraper.content_extractor import extract_therapists

# Test with the actual website
test_url = "https://www.couplestherapistboulder.com/about"

print(f"Testing extraction from: {test_url}")
print("=" * 60)

try:
    response = requests.get(test_url, timeout=10)
    response.raise_for_status()

    therapists = extract_therapists(response.text, test_url)

    print(f"\nFound {len(therapists)} therapist(s):\n")

    for therapist in therapists:
        print(f"Name: {therapist.name}")
        print(f"Credentials: {therapist.credentials}")
        print(f"Bio snippet: {therapist.bio_text[:150]}...")
        print(f"Source: {therapist.source_url}")
        print("-" * 60)

    if len(therapists) == 0:
        print("No therapists extracted (this may be correct if it's a directory page)")

except Exception as e:
    print(f"Error: {e}")
