import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")       # folder for output reports
GOOGLE_DOC_SCRAPBOOK_ID = os.getenv("GOOGLE_DOC_SCRAPBOOK_ID")     # folder containing per-competitor docs

GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

DB_PATH = "db/competitor_intel.db"

# Google OAuth scopes needed
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents.readonly",
]
