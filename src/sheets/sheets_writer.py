"""Google Sheets integration for outputting generated bios."""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Optional
from datetime import datetime
import logging
from ..models.data_models import GeneratedBio

logger = logging.getLogger("bio_generator")


class SheetsWriter:
    """Writes generated bios to Google Sheets."""

    def __init__(self, credentials_dict: dict, recipient_email: Optional[str] = None):
        """
        Initialize the sheets writer.

        Args:
            credentials_dict: Google service account credentials as dict
            recipient_email: Optional email to share the sheet with
        """
        self.credentials_dict = credentials_dict
        self.recipient_email = recipient_email
        self.client = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API.

        Returns:
            True if successful, False otherwise
        """
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                self.credentials_dict,
                scope
            )

            self.client = gspread.authorize(creds)
            return True

        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            return False

    def write_bios(self, bios: List[GeneratedBio], website_url: str) -> Optional[str]:
        """
        Write generated bios to a new Google Sheet.

        Args:
            bios: List of generated bios
            website_url: The website URL that was scraped

        Returns:
            URL of the created sheet, or None if failed
        """
        logger.info("Starting Google Sheets write operation...")

        if not self.client:
            logger.info("No client found, authenticating...")
            if not self.authenticate():
                logger.error("Authentication failed")
                return None
            logger.info("Authentication successful")

        try:
            # Create new spreadsheet
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            sheet_title = f"Therapist Bios - {website_url.split('//')[1].split('/')[0]} - {timestamp}"

            spreadsheet = self.client.create(sheet_title)

            # Get the first worksheet
            worksheet = spreadsheet.sheet1

            # Set up headers
            headers = ['Specialty', 'Therapist Name', 'Bio Box (150 words)', 'Source About URL']
            worksheet.update('A1:D1', [headers])

            # Format headers
            worksheet.format('A1:D1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

            # Group bios by specialty
            bios_by_specialty = {}
            for bio in bios:
                if bio.specialty_name not in bios_by_specialty:
                    bios_by_specialty[bio.specialty_name] = []
                bios_by_specialty[bio.specialty_name].append(bio)

            # Prepare rows
            rows = []
            for specialty_name in sorted(bios_by_specialty.keys()):
                specialty_bios = bios_by_specialty[specialty_name]

                for bio in specialty_bios:
                    rows.append([
                        specialty_name,
                        bio.therapist_name,
                        bio.bio_text,
                        str(bio.source_about_url)
                    ])

            # Write all rows at once
            if rows:
                worksheet.update(f'A2:D{len(rows) + 1}', rows)

                # Format the sheet
                worksheet.format('A:D', {
                    'wrapStrategy': 'WRAP',
                    'verticalAlignment': 'TOP'
                })

                # Set column widths
                worksheet.set_column_width('A', 150)  # Specialty
                worksheet.set_column_width('B', 150)  # Therapist Name
                worksheet.set_column_width('C', 400)  # Bio Box
                worksheet.set_column_width('D', 250)  # Source URL

            # Share with recipient if email provided
            if self.recipient_email:
                try:
                    spreadsheet.share(self.recipient_email, perm_type='user', role='writer')
                except Exception as e:
                    print(f"Could not share sheet: {str(e)}")

            # Return the sheet URL
            return spreadsheet.url

        except Exception as e:
            error_msg = f"Error writing to sheet: {str(e)}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            return None

    def write_to_existing_sheet(
        self,
        sheet_url: str,
        bios: List[GeneratedBio],
        worksheet_name: Optional[str] = None
    ) -> bool:
        """
        Write bios to an existing Google Sheet.

        Args:
            sheet_url: URL of existing sheet
            bios: List of generated bios
            worksheet_name: Optional specific worksheet name

        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting write to existing sheet...")

        if not self.client:
            logger.info("No client found, authenticating...")
            if not self.authenticate():
                logger.error("Authentication failed for existing sheet write")
                return False
            logger.info("Authentication successful")

        try:
            logger.info(f"Opening spreadsheet: {sheet_url}")
            # Open existing spreadsheet
            spreadsheet = self.client.open_by_url(sheet_url)
            logger.info(f"Successfully opened spreadsheet: {spreadsheet.title}")

            # Get or create worksheet
            if worksheet_name:
                try:
                    logger.info(f"Looking for worksheet: {worksheet_name}")
                    worksheet = spreadsheet.worksheet(worksheet_name)
                except:
                    logger.info(f"Worksheet not found, creating: {worksheet_name}")
                    worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=4)
            else:
                logger.info("Using first worksheet")
                worksheet = spreadsheet.sheet1

            # Clear existing content
            logger.info("Clearing worksheet content...")
            worksheet.clear()

            # Write headers and bios (same as above)
            logger.info("Writing headers...")
            headers = ['Specialty', 'Therapist Name', 'Bio Box (150 words)', 'Source About URL']
            worksheet.update('A1:D1', [headers])

            worksheet.format('A1:D1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

            # Group and write bios
            bios_by_specialty = {}
            for bio in bios:
                if bio.specialty_name not in bios_by_specialty:
                    bios_by_specialty[bio.specialty_name] = []
                bios_by_specialty[bio.specialty_name].append(bio)

            rows = []
            for specialty_name in sorted(bios_by_specialty.keys()):
                specialty_bios = bios_by_specialty[specialty_name]
                for bio in specialty_bios:
                    rows.append([
                        specialty_name,
                        bio.therapist_name,
                        bio.bio_text,
                        str(bio.source_about_url)
                    ])

            if rows:
                logger.info(f"Writing {len(rows)} rows of data...")
                worksheet.update(f'A2:D{len(rows) + 1}', rows)

                logger.info("Formatting cells...")
                worksheet.format('A:D', {
                    'wrapStrategy': 'WRAP',
                    'verticalAlignment': 'TOP'
                })

                logger.info("Setting column widths...")
                worksheet.set_column_width('A', 150)
                worksheet.set_column_width('B', 150)
                worksheet.set_column_width('C', 400)
                worksheet.set_column_width('D', 250)

            logger.info("Successfully wrote to existing sheet!")
            return True

        except Exception as e:
            error_msg = f"Error writing to existing sheet: {str(e)}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            return False
