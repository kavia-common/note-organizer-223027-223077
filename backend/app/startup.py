import os
from dotenv import load_dotenv

from .db import init_db, seed_data

def setup_app():
    """
    Load environment, initialize DB, and optionally seed sample data.
    """
    load_dotenv()
    init_db()
    if os.getenv("SEED_ON_STARTUP", "false").lower() in ("1", "true", "yes", "y"):
        seed_data()
