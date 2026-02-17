"""Bio generation using Claude API."""
import time
import logging
from typing import List, Optional, Callable
from anthropic import Anthropic
from ..models.data_models import Therapist, Specialty, GeneratedBio
from .prompts import SYSTEM_PROMPT, create_bio_prompt, create_fallback_bio_prompt

logger = logging.getLogger("bio_generator")


class BioGenerator:
    """Generates specialty-specific bios using Claude API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 300,
        temperature: float = 0.7,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the bio generator.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens for generation
            temperature: Temperature for generation (0.0-1.0)
            progress_callback: Optional callback for progress updates
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.progress_callback = progress_callback
        self.total_tokens_used = 0

    def _log(self, message: str):
        """Log a progress message."""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)

    def generate_bios(
        self,
        therapists: List[Therapist],
        specialties: List[Specialty]
    ) -> List[GeneratedBio]:
        """
        Generate bios for all therapist-specialty combinations.

        Processes one therapist at a time to manage context better for group practices.

        Args:
            therapists: List of therapists
            specialties: List of specialties

        Returns:
            List of GeneratedBio objects
        """
        generated_bios = []
        total_combinations = len(therapists) * len(specialties)

        self._log(f"Generating {total_combinations} bio(s) for {len(therapists)} therapist(s)...")

        # Process one therapist at a time (better for group practices)
        for therapist_idx, therapist in enumerate(therapists, 1):
            # Show which therapist we're processing
            if len(therapists) > 1:
                self._log(f"\n--- Processing Therapist {therapist_idx}/{len(therapists)}: {therapist.name} ---")

            # Generate all specialties for this therapist
            for specialty_idx, specialty in enumerate(specialties, 1):
                overall_progress = (therapist_idx - 1) * len(specialties) + specialty_idx

                if len(therapists) > 1:
                    # For group practices: show both therapist progress and specialty progress
                    self._log(f"[{overall_progress}/{total_combinations}] Generating {therapist.name} - {specialty.name}")
                else:
                    # For single therapist: simpler progress message
                    self._log(f"Generating bio {overall_progress}/{total_combinations}: {therapist.name} - {specialty.name}")

                bio = self._generate_single_bio(therapist, specialty)

                if bio:
                    generated_bios.append(bio)
                else:
                    self._log(f"Failed to generate bio for {therapist.name} - {specialty.name}")

                # Small delay between API calls
                if overall_progress < total_combinations:
                    time.sleep(0.5)

        self._log(f"\nGeneration complete! Total tokens used: {self.total_tokens_used}")
        self._log(f"Estimated cost: ${self.total_tokens_used * 0.000009:.4f}")

        return generated_bios

    def _generate_single_bio(
        self,
        therapist: Therapist,
        specialty: Specialty
    ) -> Optional[GeneratedBio]:
        """
        Generate a single bio for a therapist-specialty combination.

        Args:
            therapist: The therapist
            specialty: The specialty

        Returns:
            GeneratedBio or None if generation failed
        """
        # Create prompt
        prompt = create_bio_prompt(
            therapist_name=therapist.name,
            credentials=therapist.credentials or "",
            original_bio=therapist.bio_text,
            specialty_name=specialty.name,
            specialty_content=specialty.content
        )

        # Try to generate with retries
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                # Extract bio text
                bio_text = response.content[0].text.strip()

                # Track token usage
                self.total_tokens_used += response.usage.input_tokens + response.usage.output_tokens

                # Validate word count (target: 110 words, acceptable: 100-125)
                word_count = len(bio_text.split())

                if word_count < 90:
                    self._log(f"Bio too short ({word_count} words), retrying...")
                    if attempt < max_retries - 1:
                        continue
                elif word_count > 135:
                    self._log(f"Bio too long ({word_count} words), retrying...")
                    if attempt < max_retries - 1:
                        continue

                # Success!
                return GeneratedBio(
                    therapist_name=therapist.name,
                    specialty_name=specialty.name,
                    bio_text=bio_text,
                    source_about_url=therapist.source_url
                )

            except Exception as e:
                error_msg = f"Error generating bio (attempt {attempt + 1}/{max_retries}): {str(e)}"
                self._log(error_msg)
                logger.error(error_msg, exc_info=True)

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Try fallback prompt on final attempt
                    logger.warning(f"All retries failed, trying fallback prompt for {therapist.name} - {specialty.name}")
                    return self._generate_with_fallback(therapist, specialty)

        return None

    def _generate_with_fallback(
        self,
        therapist: Therapist,
        specialty: Specialty
    ) -> Optional[GeneratedBio]:
        """
        Try generating with a simpler fallback prompt.

        Args:
            therapist: The therapist
            specialty: The specialty

        Returns:
            GeneratedBio or None if generation failed
        """
        try:
            prompt = create_fallback_bio_prompt(
                therapist_name=therapist.name,
                credentials=therapist.credentials or "",
                original_bio=therapist.bio_text,
                specialty_name=specialty.name
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            bio_text = response.content[0].text.strip()
            self.total_tokens_used += response.usage.input_tokens + response.usage.output_tokens

            return GeneratedBio(
                therapist_name=therapist.name,
                specialty_name=specialty.name,
                bio_text=bio_text,
                source_about_url=therapist.source_url
            )

        except Exception as e:
            error_msg = f"Fallback generation also failed: {str(e)}"
            self._log(error_msg)
            logger.error(error_msg, exc_info=True)
            return None

    def get_estimated_cost(self, num_bios: int) -> float:
        """
        Estimate the cost for generating a number of bios.

        Args:
            num_bios: Number of bios to generate

        Returns:
            Estimated cost in dollars
        """
        # Rough estimate: ~5000 tokens per bio (input + output)
        estimated_tokens = num_bios * 5000
        # Claude Sonnet 4.5 pricing: $3 per million input tokens, $15 per million output tokens
        # Average: ~$9 per million tokens
        cost_per_token = 0.000009
        return estimated_tokens * cost_per_token
