# Therapist Bio Generator

A streamlined tool for generating unique, specialty-specific bio boxes for therapists using Claude AI. Simply copy and paste content to generate professional bios in seconds.

## Features

- **Manual Entry (Primary)**: Copy-paste workflow for quick bio generation
  - Paste therapist "about" information once
  - Generate bios for multiple specialties one at a time
  - Bios accumulate during your session
  - Export to CSV or Google Sheets
- **AI Generation**: Uses Claude API to generate unique 110-word bios
- **Session Management**: Therapist info persists while you work through multiple specialties
- **Flexible Export**: Download as CSV (no setup) or export to Google Sheets
- **Web-Based**: Accessible to your team online
- **Free Hosting**: Deploy to Streamlit Cloud at no cost

> **Note**: Web scraping feature is under development and available as a secondary option

## How It Works (Manual Entry)

1. Paste the therapist's about/bio text (persists for session)
2. Optionally enter the therapist's name
3. Paste a specialty page content (e.g., "Anxiety Therapy")
4. **Optional**: If the specialty page has an existing bio, paste it in the expandable section
5. Click "Generate Bio" → bio appears below
6. Repeat for more specialties → bios accumulate
7. Export all bios to CSV or Google Sheets when done

Each bio is unique, specialty-specific, and approximately 110 words.

**Specialty-Specific Bio**: If a specialty page already has bio text for the therapist, you can include it to create an even more tailored bio. This is combined with the main about text to give Claude maximum context.

## Setup

### Prerequisites

- Python 3.9 or higher
- [Anthropic API Key](https://console.anthropic.com)
- Google Cloud account with Sheets API enabled

### 1. Clone or Download

```bash
git clone <your-repo-url>
cd therapist-bio-generator
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Get Anthropic API Key

1. Go to [https://console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-`)

### 4. Set Up Google Sheets API

#### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

#### Step 2: Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Enter a name (e.g., "Therapist Bio Generator")
4. Click "Create and Continue"
5. Skip granting additional access (click "Continue" then "Done")

#### Step 3: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create" - a JSON file will download
6. Save this file securely (you'll need it for configuration)

### 5. Configure API Key (Required)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Optional: Google Sheets Export**

If you want to export to Google Sheets (CSV export works without this):

```
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account","project_id":"...paste entire JSON here..."}
SHEET_RECIPIENT_EMAIL=your-email@example.com
```

## Running Locally

```bash
# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Manual Entry (Recommended)

1. Open the app and go to the "Generate Bios (Manual Entry)" tab
2. Paste the therapist's about/bio text (this persists for your session)
3. Optionally enter the therapist's name (if not in the bio text)
4. Paste a specialty page content (with title on first line, e.g., "Anxiety Therapy")
5. **Optional**: Expand "Existing Bio on Specialty Page" and paste any specialty-specific bio if available
6. Click "Generate Bio"
7. Repeat steps 4-6 for additional specialties
8. Export all bios:
   - **CSV**: Download button (works immediately, no setup)
   - **Google Sheets**: Export button (requires Google credentials)
9. Click "Start New Session" when ready for a new therapist

### Web Scraping (Coming Soon)

The web scraping tab is currently under development. Use manual entry for now.

## Deployment (Streamlit Cloud)

Deploy for free so your team can access the tool online.

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository and branch
5. Set main file path: `app.py`
6. Click "Advanced settings"

### Step 3: Add Secrets

In the "Secrets" section, paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

(Copy the fields from your service account JSON file)

### Step 4: Deploy

Click "Deploy" and wait for the app to build and launch. You'll get a public URL to share with your team.

## Project Structure

```
therapist-bio-generator/
├── src/
│   ├── scraper/
│   │   ├── website_scraper.py      # Main orchestrator
│   │   ├── page_finder.py          # Find therapist & specialty pages
│   │   ├── content_extractor.py    # Extract bio content
│   │   └── url_validator.py        # URL validation
│   ├── generator/
│   │   ├── bio_generator.py        # Claude API integration
│   │   └── prompts.py              # Prompt templates
│   ├── sheets/
│   │   └── sheets_writer.py        # Google Sheets output
│   └── models/
│       └── data_models.py          # Pydantic models
├── app.py                          # Main Streamlit app
├── requirements.txt
└── README.md
```

## Cost Estimates

- **Hosting**: FREE (Streamlit Cloud free tier)
- **Google Sheets API**: FREE
- **Claude API**: ~$0.015 per bio generated
  - Example: 5 therapists × 8 specialties = 40 bios = ~$0.60
  - The app shows cost estimates before generation

## Troubleshooting

### "No therapists found"

- The site may not have a standard team/about page
- Try providing a direct URL to the team page
- Check if the site requires authentication

### "No specialties found"

- The site may not have separate specialty pages
- Specialty pages might use different URL patterns
- Try manually identifying specialty pages and report them for future improvements

### "Failed to write to Google Sheets"

- Check that your service account JSON is valid
- Ensure Google Sheets API is enabled in your Google Cloud project
- Try sharing a test spreadsheet with your service account email

### Scraping Issues

- Some sites have anti-scraping measures
- JavaScript-heavy sites may take longer to load
- Check your internet connection
- Try a different therapy website to test

## Limitations

- Works best with standard therapy website structures
- May not find all specialty pages on complex sites
- Requires public (non-authenticated) website pages
- Rate limited to be respectful to target sites (1-2 second delays)

## Future Enhancements

- Caching to avoid re-scraping
- Manual URL input for specialty pages
- Customizable bio length and tone
- Preview mode before generating all bios
- Better detection for non-standard site structures

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License - feel free to use and modify for your needs.
