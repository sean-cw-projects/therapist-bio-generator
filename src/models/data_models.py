"""Data models for the therapist bio generator."""
from pydantic import BaseModel, HttpUrl
from typing import List, Optional


class Therapist(BaseModel):
    """Represents a therapist/clinician found on the website."""
    name: str
    credentials: Optional[str] = None
    bio_text: str
    source_url: HttpUrl


class Specialty(BaseModel):
    """Represents a therapy specialty/service offered."""
    name: str
    content: str
    url: HttpUrl


class GeneratedBio(BaseModel):
    """Represents a generated bio for a therapist-specialty combination."""
    therapist_name: str
    specialty_name: str
    bio_text: str  # Should be ~150 words
    source_about_url: HttpUrl


class ScrapingResult(BaseModel):
    """Result of scraping a therapy website."""
    website_url: HttpUrl
    therapists: List[Therapist]
    specialties: List[Specialty]
    errors: List[str] = []
