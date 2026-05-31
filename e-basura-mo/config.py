"""App settings and shared lists."""
from pathlib import Path

APP_NAME = "E-Basura Mo"
APP_TAGLINE = "Waste reports and collection tracking for your barangay — works offline."

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "e_basura.db"
PHOTOS_DIR = DATA_DIR / "photos"
REPORTS_DIR = DATA_DIR / "reports"

REPORT_TYPES = [
    "Overflowing trash",
    "Illegal dumping",
    "Missed pickup",
    "Other",
]
REPORT_STATUSES = ["Pending", "Assigned", "Resolved"]
PICKUP_WASTE_TYPES = [
    "Bulky furniture",
    "Electronics",
    "Construction debris",
    "Other",
]
PICKUP_STATUSES = ["Pending", "Assigned", "Completed"]

DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# Colors
PRIMARY = "#1b4332"
BG = "#f1f3f4"
CARD = "#ffffff"
TEXT = "#1b1b1b"
MUTED = "#6c757d"
DANGER = "#9d0208"
