import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = os.getenv("API_ID", "0")
if API_ID.isdigit():
    API_ID = int(API_ID)
else:
    API_ID = 0
API_HASH = os.getenv("API_HASH", "")
ADMIN_ID = os.getenv("ADMIN_ID", "0")
if ADMIN_ID.isdigit():
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = 0
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

DEFAULT_DELAY_MIN = 3.0
DEFAULT_DELAY_MAX = 8.0
FLOOD_WAIT_BUFFER = 10
MAX_SEND_RETRIES = 2
MEDIA_DIR = os.getenv("MEDIA_DIR", "data/media")


def ensure_dirs():
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
