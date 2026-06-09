import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# API Keys
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY")
ALPHA_VANTAGE_KEY   = os.getenv("ALPHA_VANTAGE_KEY")
POLYGON_API_KEY     = os.getenv("POLYGON_API_KEY")
MONGODB_URI         = os.getenv("MONGODB_URI")
SEC_USER_AGENT      = os.getenv("SEC_USER_AGENT", "FinancialAgent dev@example.com")

# Paths
BASE_DIR     = Path(__file__).parent
DATA_DIR     = BASE_DIR / "data"
FILINGS_DIR  = DATA_DIR / "filings"
CACHE_DIR    = DATA_DIR / "cache"
REPORTS_DIR  = DATA_DIR / "reports"

# Create folders if they don't exist
for folder in [FILINGS_DIR, CACHE_DIR, REPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)