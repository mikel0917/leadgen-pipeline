import os

TARGET_STATE = os.getenv("TARGET_STATE", "FL")
TARGET_CITIES = os.getenv("TARGET_CITIES", "Miami").split(",")
TARGET_ZIPS = [z.strip() for z in os.getenv("TARGET_ZIPS", "").split(",") if z.strip()]
MIN_AGE = int(os.getenv("MIN_AGE", "45"))
MAX_AGE = int(os.getenv("MAX_AGE", "85"))
DAILY_LEAD_LIMIT = int(os.getenv("DAILY_LEAD_LIMIT", "100"))

VOTER_FILE_PATH = os.getenv("VOTER_FILE_PATH", "data/voter_files/")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "data/output/")
DB_PATH = os.getenv("DB_PATH", "data/leads.db")

GMAIL_ACCOUNTS = [
    {
        "email": os.getenv("GMAIL_1_EMAIL", ""),
        "password": os.getenv("GMAIL_1_PASSWORD", ""),
        "smtp": "smtp.gmail.com",
        "port": 587,
        "daily_limit": 50,
    },
]

LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SCRAPE_DELAY_SECONDS = int(os.getenv("SCRAPE_DELAY_SECONDS", "3"))
