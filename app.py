"""Main Streamlit application for therapist bio generator."""
import streamlit as st
import os
import json
import csv
from io import StringIO
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Core imports (always available)
from src.generator.bio_generator import BioGenerator
from src.sheets.sheets_writer import SheetsWriter
from src.models.data_models import Therapist, Specialty, GeneratedBio
from src.utils.logger import setup_logger

# Optional scraping imports (only needed for WIP scraping feature)
try:
    from src.scraper.website_scraper import WebsiteScraper
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = setup_logger()

# Page config
st.set_page_config(
    page_title="Therapist Bio Generator",
    page_icon="🧠",
    layout="wide"
)


def initialize_session_state():
    """Initialize session state variables."""
    if 'accumulated_bios' not in st.session_state:
        st.session_state.accumulated_bios = []
    if 'therapist_about_text' not in st.session_state:
        st.session_state.therapist_about_text = ""
    if 'therapist_name' not in st.session_state:
        st.session_state.therapist_name = ""
    if 'modalities_text' not in st.session_state:
        st.session_state.modalities_text = ""
    if 'total_tokens_used' not in st.session_state:
        st.session_state.total_tokens_used = 0
    if 'specialty_content' not in st.session_state:
        st.session_state.specialty_content = ""
    if 'specialty_bio_text' not in st.session_state:
        st.session_state.specialty_bio_text = ""


def get_api_keys():
    """Get API keys from environment, Streamlit secrets, or user input."""
    anthropic_key = None
    google_creds = None

    # Try to get from environment variables first (local development)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # Try to load Google credentials from file or JSON string
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if creds_file and Path(creds_file).exists():
        # Load from file
        with open(creds_file, 'r') as f:
            google_creds = json.load(f)
    elif creds_json:
        # Load from JSON string
        try:
            google_creds = json.loads(creds_json)
        except:
            pass

    # Try to get from Streamlit secrets (for deployment)
    if not anthropic_key:
        try:
            anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
        except:
            pass

    if not google_creds:
        try:
            google_creds = dict(st.secrets.get("gcp_service_account", {}))
        except:
            pass

    # If not found anywhere, get from user input
    if not anthropic_key:
        st.sidebar.subheader("API Configuration")
        anthropic_key = st.sidebar.text_input(
            "Anthropic API Key",
            type="password",
            help="Get your API key from https://console.anthropic.com"
        )

    if not google_creds or not google_creds.get("type"):
        st.sidebar.subheader("Google Sheets Configuration (Optional)")
        google_creds_text = st.sidebar.text_area(
            "Google Service Account JSON",
            help="Paste your service account JSON credentials here"
        )

        if google_creds_text:
            try:
                google_creds = json.loads(google_creds_text)
            except:
                st.sidebar.error("Invalid JSON format")
                google_creds = None

    return anthropic_key, google_creds


def bios_to_csv(bios):
    """Convert bios to CSV format."""
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Specialty', 'Therapist Name', 'Bio Box (110 words)', 'Source About URL'])

    # Group by specialty and write rows
    bios_by_specialty = {}
    for bio in bios:
        if bio.specialty_name not in bios_by_specialty:
            bios_by_specialty[bio.specialty_name] = []
        bios_by_specialty[bio.specialty_name].append(bio)

    for specialty_name in sorted(bios_by_specialty.keys()):
        specialty_bios = bios_by_specialty[specialty_name]
        for bio in specialty_bios:
            writer.writerow([
                specialty_name,
                bio.therapist_name,
                bio.bio_text,
                str(bio.source_about_url)
            ])

    return output.getvalue()


def extract_specialty_name(content: str) -> str:
    """Extract specialty name from the first line of pasted content."""
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if lines:
        return lines[0]
    return "Unknown Specialty"


def generate_single_bio_from_manual_input(
    therapist_about: str,
    therapist_name: str,
    modalities_text: str,
    specialty_content: str,
    specialty_bio_text: str,
    api_key: str
) -> GeneratedBio:
    """Generate a single bio from manual input.

    Args:
        therapist_about: Main therapist about/bio text
        therapist_name: Optional therapist name
        modalities_text: Optional therapeutic modalities/approaches
        specialty_content: Specialty page content
        specialty_bio_text: Optional specialty-specific bio text from the specialty page
        api_key: Anthropic API key
    """

    # Extract specialty name from first line
    specialty_name = extract_specialty_name(specialty_content)

    # Use provided name or default to "Therapist"
    final_name = therapist_name.strip() if therapist_name.strip() else "Therapist"

    # Combine main bio with modalities and specialty-specific bio if provided
    combined_bio = therapist_about
    if modalities_text and modalities_text.strip():
        combined_bio = f"{therapist_about}\n\n**Therapeutic Modalities:**\n{modalities_text.strip()}"
    if specialty_bio_text and specialty_bio_text.strip():
        combined_bio = f"{combined_bio}\n\n**Specialty-Specific Bio:**\n{specialty_bio_text.strip()}"

    # Create Therapist object
    therapist = Therapist(
        name=final_name,
        credentials=None,
        bio_text=combined_bio,
        source_url="http://manual-entry.local"
    )

    # Create Specialty object
    specialty = Specialty(
        name=specialty_name,
        content=specialty_content,
        url="http://manual-entry.local"
    )

    # Initialize generator
    generator = BioGenerator(api_key)

    # Generate bio
    bio = generator._generate_single_bio(therapist, specialty)

    # Track tokens
    st.session_state.total_tokens_used += generator.total_tokens_used

    return bio


def render_manual_entry_tab(anthropic_key, google_creds):
    """Render the manual entry tab UI."""
    st.markdown("""
    Generate unique, specialty-specific bio boxes by pasting content directly.

    **How it works:**
    1. Paste the therapist's "about" information (persists for the session)
    2. Optionally enter the therapist's name (for first-person bios)
    3. Paste a specialty page content (including the title)
    4. Click "Generate Bio" → bio appears below
    5. Repeat for more specialties → bios accumulate
    6. Export to CSV or Google Sheets when done
    """)

    st.markdown("---")

    # Therapist Information Section (Persistent)
    st.subheader("👤 Therapist Information (Persistent)")
    st.caption("This information will be used for all bio generations in this session")

    col1, col2 = st.columns([1, 3])

    with col1:
        therapist_name = st.text_input(
            "Therapist Name (Optional)",
            value=st.session_state.therapist_name,
            placeholder="Dr. Jane Smith",
            help="Leave blank if the bio is first-person or name is included in the about text",
            key="therapist_name_input"
        )
        st.session_state.therapist_name = therapist_name

    with col2:
        therapist_about = st.text_area(
            "About/Bio Text",
            value=st.session_state.therapist_about_text,
            placeholder="Paste the therapist's full about/bio text here...",
            help="This should include credentials, background, approach, etc.",
            height=200,
            key="therapist_about_input"
        )
        st.session_state.therapist_about_text = therapist_about

        # Show character count
        if therapist_about:
            char_count = len(therapist_about)
            word_count = len(therapist_about.split())
            st.caption(f"📊 {char_count} characters | {word_count} words")

    # Optional: Therapeutic Modalities
    with st.expander("➕ Therapeutic Modalities (Optional)", expanded=False):
        st.markdown("""
        If you want to specify the therapeutic modalities/approaches the therapist uses, paste them here.
        This ensures Claude includes the correct modalities instead of guessing.
        """)
        modalities_text = st.text_area(
            "Modalities/Approaches",
            value=st.session_state.modalities_text,
            placeholder="CBT, EMDR, Psychodynamic Therapy, Mindfulness-Based Approaches, Trauma-Focused Therapy...",
            help="Optional: List the therapeutic modalities and approaches",
            height=100,
            key="modalities_input"
        )
        st.session_state.modalities_text = modalities_text

        if modalities_text:
            char_count = len(modalities_text)
            st.caption(f"📊 {char_count} characters")

    st.markdown("---")

    # Specialty Information Section (Transient)
    st.subheader("🎯 Specialty Information")
    st.caption("Paste one specialty at a time. The title should be on the first line (e.g., 'Anxiety Therapy')")

    specialty_content = st.text_area(
        "Specialty Page Content",
        value=st.session_state.specialty_content,
        placeholder="Anxiety Therapy\n\nWe help clients overcome anxiety through evidence-based approaches...",
        help="Paste the full specialty page content, with the title on the first line",
        height=200,
        key="specialty_content_input"
    )
    st.session_state.specialty_content = specialty_content

    # Show character count and extracted specialty name
    if specialty_content:
        char_count = len(specialty_content)
        word_count = len(specialty_content.split())
        specialty_name = extract_specialty_name(specialty_content)
        st.caption(f"📊 {char_count} characters | {word_count} words | Specialty: **{specialty_name}**")

    # Optional: Existing specialty-specific bio
    with st.expander("➕ Existing Bio on Specialty Page (Optional)", expanded=False):
        st.markdown("""
        If the specialty page already has a bio for this therapist, paste it here.
        This will be combined with the main about text to create a more tailored bio.
        """)
        specialty_bio_text = st.text_area(
            "Specialty-Specific Bio Text",
            value=st.session_state.specialty_bio_text,
            placeholder="Dr. Smith has been helping clients with anxiety for over 15 years...",
            help="Optional: Paste any existing bio text specific to this specialty",
            height=150,
            key="specialty_bio_input"
        )
        st.session_state.specialty_bio_text = specialty_bio_text

        if specialty_bio_text:
            char_count = len(specialty_bio_text)
            word_count = len(specialty_bio_text.split())
            st.caption(f"📊 {char_count} characters | {word_count} words")

    # Generate button
    col1, col2 = st.columns([1, 3])
    with col1:
        generate_button = st.button("✨ Generate Bio", type="primary", use_container_width=True)

    # Handle generation
    if generate_button:
        # Validation
        if not therapist_about.strip():
            st.error("❌ Please paste the therapist's about information first")
            return

        if not specialty_content.strip():
            st.error("❌ Please paste the specialty page content")
            return

        # Generate bio
        with st.spinner("🤖 Generating bio with Claude AI..."):
            try:
                bio = generate_single_bio_from_manual_input(
                    therapist_about=therapist_about,
                    therapist_name=therapist_name,
                    modalities_text=modalities_text,
                    specialty_content=specialty_content,
                    specialty_bio_text=specialty_bio_text,
                    api_key=anthropic_key
                )

                # Add to accumulated bios
                st.session_state.accumulated_bios.append(bio)

                # Clear specialty fields for next generation
                st.session_state.specialty_content = ""
                st.session_state.specialty_bio_text = ""

                # Show success
                st.success(f"✅ Generated bio for **{bio.specialty_name}**!")

                # Rerun to update display
                st.rerun()

            except Exception as e:
                logger.exception(f"Error generating bio: {str(e)}")
                st.error(f"❌ Error generating bio: {str(e)}")
                with st.expander("Error Details"):
                    import traceback
                    st.code(traceback.format_exc())

    st.markdown("---")

    # Display accumulated bios
    if st.session_state.accumulated_bios:
        st.subheader(f"📋 Generated Bios ({len(st.session_state.accumulated_bios)})")

        # Group by specialty
        bios_by_specialty = {}
        for bio in st.session_state.accumulated_bios:
            if bio.specialty_name not in bios_by_specialty:
                bios_by_specialty[bio.specialty_name] = []
            bios_by_specialty[bio.specialty_name].append(bio)

        # Display each specialty group
        for specialty_name in sorted(bios_by_specialty.keys()):
            with st.expander(f"**{specialty_name}** ({len(bios_by_specialty[specialty_name])} bio(s))", expanded=True):
                for bio in bios_by_specialty[specialty_name]:
                    # Calculate word count
                    word_count = len(bio.bio_text.split())

                    # Display bio
                    st.markdown(f"**{bio.therapist_name}** | {word_count} words")
                    st.write(bio.bio_text)
                    st.divider()

        st.markdown("---")

        # Export buttons
        st.subheader("📤 Export Options")

        col1, col2, col3 = st.columns(3)

        with col1:
            # CSV Export
            csv_data = bios_to_csv(st.session_state.accumulated_bios)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"therapist_bios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            # Google Sheets Export
            if google_creds:
                if st.button("📊 Export to Google Sheets", use_container_width=True):
                    with st.spinner("Exporting to Google Sheets..."):
                        try:
                            writer = SheetsWriter(credentials_dict=google_creds)
                            sheet_url = writer.write_bios(
                                st.session_state.accumulated_bios,
                                website_url="Manual Entry"
                            )

                            if sheet_url:
                                st.success("✅ Exported to Google Sheets!")
                                st.markdown(f"[Open Google Sheet]({sheet_url})")
                            else:
                                st.error("❌ Failed to export to Google Sheets")
                        except Exception as e:
                            logger.exception(f"Error exporting to Google Sheets: {str(e)}")
                            st.error(f"❌ Error: {str(e)}")
            else:
                st.button("📊 Export to Google Sheets", disabled=True, use_container_width=True, help="Google credentials required")

        with col3:
            # Start New Session
            if st.button("🔄 Start New Session", type="secondary", use_container_width=True):
                st.session_state.accumulated_bios = []
                st.session_state.total_tokens_used = 0
                st.session_state.specialty_content = ""
                st.session_state.specialty_bio_text = ""
                # Keep therapist info persistent (don't clear)
                st.rerun()

        # Show token usage and cost
        if st.session_state.total_tokens_used > 0:
            cost = st.session_state.total_tokens_used * 0.000009
            st.info(f"💰 Total tokens used: {st.session_state.total_tokens_used:,} | Estimated cost: ${cost:.4f}")

        st.caption("💡 Tip: Export your bios before refreshing the page to avoid losing your work!")

    else:
        st.info("👆 Paste therapist and specialty information above, then click 'Generate Bio' to get started!")


def render_scraping_tab(anthropic_key, google_creds):
    """Render the web scraping tab (WIP)."""
    st.warning("⚠️ **Work In Progress:** Web scraping feature is under development. Use the Manual Entry tab for now.")

    st.markdown("---")
    st.markdown("""
    ### 🔍 Automated Web Scraping

    This feature will automatically:
    - Scrape therapist bios from your website
    - Find specialty/service pages
    - Generate unique 110-word bios for each therapist-specialty combination

    **Coming soon!**
    """)

    # Keep the old scraping code here for future use
    st.markdown("---")
    st.subheader("Website URL")
    url = st.text_input(
        "Enter the therapy website URL to scrape",
        placeholder="https://example-therapy.com",
        help="Enter the homepage URL of the therapy website",
        disabled=True
    )

    st.button("Generate Bios", type="primary", disabled=True, help="Feature under development")


def main():
    """Main application function."""
    # Initialize session state
    initialize_session_state()

    st.title("🧠 Therapist Bio Generator")

    # Get API keys
    anthropic_key, google_creds = get_api_keys()

    # Check if we have necessary credentials
    if not anthropic_key:
        st.warning("⚠️ Please provide your Anthropic API key in the sidebar to continue.")
        st.markdown("""
        ### Getting Started

        1. Get an [Anthropic API key](https://console.anthropic.com)
        2. Enter it in the sidebar
        3. Start generating bios!
        """)
        return

    # Create tabs
    tab1, tab2 = st.tabs(["📝 Generate Bios (Manual Entry)", "🔍 Web Scraper (WIP)"])

    with tab1:
        render_manual_entry_tab(anthropic_key, google_creds)

    with tab2:
        render_scraping_tab(anthropic_key, google_creds)


if __name__ == "__main__":
    # Show setup instructions in sidebar
    with st.sidebar:
        st.markdown("### 📖 Quick Start Guide")
        st.markdown("""
        **Required:**
        1. Get an [Anthropic API key](https://console.anthropic.com)
        2. Enter it above

        **Optional: Google Sheets Export**
        - Create a [Google Service Account](https://console.cloud.google.com)
        - Enable the Google Sheets API
        - Paste credentials above

        Otherwise, use CSV download (works without Google setup)!
        """)

        st.divider()
        st.caption("📝 Detailed logs are saved in the `logs/` folder")

    main()
