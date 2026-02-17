"""Prompt templates for bio generation."""

SYSTEM_PROMPT = """You are an expert copywriter specializing in writing compelling, authentic content for mental health professionals. Your writing:
- Precisely matches the therapist's existing voice, tone, and style
- Mirrors the language patterns and aesthetic found in their original content
- Highlights relevant credentials and experience naturally
- Focuses on how the therapist helps clients with specific concerns
- Stays within the specified word count"""


def create_bio_prompt(
    therapist_name: str,
    credentials: str,
    original_bio: str,
    specialty_name: str,
    specialty_content: str
) -> str:
    """
    Create a prompt for generating a specialty-specific bio.

    Args:
        therapist_name: Name of the therapist
        credentials: Therapist's credentials (e.g., "LCSW, PhD")
        original_bio: The therapist's original bio text
        specialty_name: Name of the specialty (e.g., "Anxiety Therapy")
        specialty_content: Description of the specialty from the website

    Returns:
        Formatted prompt string
    """
    creds_text = f" ({credentials})" if credentials else ""

    prompt = f"""Generate a 110-word bio box for {therapist_name}{creds_text} that will appear on the "{specialty_name}" page of their therapy website.

**Therapist's Original Bio:**
{original_bio}

**About the Specialty ({specialty_name}):**
{specialty_content[:500]}

**Requirements:**
1. Write EXACTLY 110 words (100-125 is acceptable)
2. Precisely match the voice, tone, style, and language patterns from {therapist_name}'s original bio
3. Highlight their relevant experience, training, or approach specifically related to {specialty_name}
4. Include credentials naturally if relevant to this specialty
5. Focus on how {therapist_name} helps clients dealing with this specific concern
6. Maintain the exact same level of formality, personality, and aesthetic as the original content
7. Write in third person (he/she/they) if the original bio uses third person, or first person (I) if it uses first person

**Output only the bio text - no additional commentary, headers, or explanation.**"""

    return prompt


def create_fallback_bio_prompt(
    therapist_name: str,
    credentials: str,
    original_bio: str,
    specialty_name: str
) -> str:
    """
    Create a fallback prompt when specialty content is minimal or missing.

    Args:
        therapist_name: Name of the therapist
        credentials: Therapist's credentials
        original_bio: The therapist's original bio text
        specialty_name: Name of the specialty

    Returns:
        Formatted prompt string
    """
    creds_text = f" ({credentials})" if credentials else ""

    prompt = f"""Generate a 110-word bio box for {therapist_name}{creds_text} that will appear on the "{specialty_name}" page of their therapy website.

**Therapist's Original Bio:**
{original_bio}

**Specialty Focus:**
{specialty_name}

**Requirements:**
1. Write EXACTLY 110 words (100-125 is acceptable)
2. Precisely match the voice, tone, style, and language patterns from {therapist_name}'s original bio
3. Adapt their general approach and experience to be relevant for clients seeking help with {specialty_name}
4. If their bio mentions relevant training or experience for {specialty_name}, emphasize it
5. If not, focus on their general therapeutic approach and how it helps with concerns like {specialty_name}
6. Include credentials naturally
7. Maintain the exact same level of formality, personality, and aesthetic as the original content
8. Write in the same person (first/third) as the original bio

**Output only the bio text - no additional commentary, headers, or explanation.**"""

    return prompt
