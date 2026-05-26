import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# AI Provider
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# Determine which AI provider to use
if AI_MODEL.lower() in ["none", "disabled", ""]:
    AI_PROVIDER = "none"
elif "claude" in AI_MODEL.lower() and ANTHROPIC_API_KEY:
    AI_PROVIDER = "anthropic"
elif "mistral" in AI_MODEL.lower() and MISTRAL_API_KEY:
    AI_PROVIDER = "mistral"
else:
    AI_PROVIDER = "openai"

# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
MAX_CLIP_DURATION = os.getenv("MAX_CLIP_DURATION", "120")
MIN_CLIP_DURATION = os.getenv("MIN_CLIP_DURATION", "15")
MAX_CLIPS_PER_RUN = os.getenv("MAX_CLIPS_PER_RUN", "3")
CLIP_QUALITY = os.getenv("CLIP_QUALITY", "720")
TARGET_CLIP_DURATION = os.getenv("TARGET_CLIP_DURATION", "45")
MAX_CLIP_FILE_SIZE_MB = os.getenv("MAX_CLIP_FILE_SIZE_MB", "20")

# Bot Behavior
POSTING_MODE = os.getenv("POSTING_MODE", "auto")  # auto, queue, manual
DAILY_DIGEST_TIME = os.getenv("DAILY_DIGEST_TIME", "09:00")
BREAKING_NEWS_THRESHOLD = float(os.getenv("BREAKING_NEWS_THRESHOLD", "0.8"))
MAX_POSTS_PER_DAY = int(os.getenv("MAX_POSTS_PER_DAY", "10"))

# Content Filtering
MIN_ARTICLE_RELEVANCE = float(os.getenv("MIN_ARTICLE_RELEVANCE", "0.6"))
SENTIMENT_ANALYSIS = os.getenv("SENTIMENT_ANALYSIS", "true").lower() == "true"
EXTRACT_TICKERS = os.getenv("EXTRACT_TICKERS", "true").lower() == "true"

# Features
ENABLE_POLLS = os.getenv("ENABLE_POLLS", "true").lower() == "true"
ENABLE_WEEKLY_ROUNDUP = os.getenv("ENABLE_WEEKLY_ROUNDUP", "true").lower() == "true"
WEEKLY_ROUNDUP_DAY = os.getenv("WEEKLY_ROUNDUP_DAY", "Sunday")
WEEKLY_ROUNDUP_TIME = os.getenv("WEEKLY_ROUNDUP_TIME", "18:00")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/finbot.log")

# File paths
FEEDS_FILE = DATA_DIR / "feeds.json"
QUEUE_FILE = DATA_DIR / "queue.json"
POSTED_FILE = DATA_DIR / "posted.json"

# Default RSS feeds
DEFAULT_FEEDS = {
    "markets": [
        {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/business/news.rss", "tier": 1},
        {"name": "Reuters Finance", "url": "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best", "tier": 1},
        {"name": "WSJ Markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "tier": 1},
        {"name": "Financial Times", "url": "https://www.ft.com/?format=rss", "tier": 1},
        {"name": "MarketWatch", "url": "https://www.marketwatch.com/rss/topstories", "tier": 2},
        {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss", "tier": 2},
        {"name": "Seeking Alpha", "url": "https://seekingalpha.com/feed.xml", "tier": 2},
    ],
    "ai_tech": [
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "tier": 1},
        {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "tier": 1},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "tier": 1},
        {"name": "MIT AI News", "url": "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml", "tier": 1},
        {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/", "tier": 2},
        {"name": "Machine Learning Mastery", "url": "https://machinelearningmastery.com/feed/", "tier": 2},
    ],
    "crypto": [
        {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "tier": 1},
        {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "tier": 1},
        {"name": "Decrypt", "url": "https://decrypt.co/feed", "tier": 1},
        {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "tier": 2},
        {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/", "tier": 2},
    ],
    "macro": [
        {"name": "ZeroHedge", "url": "https://feeds.feedburner.com/zerohedge/feed", "tier": 2},
        {"name": "Real Vision", "url": "https://www.realvision.com/rss", "tier": 1},
        {"name": "Macro Hive", "url": "https://www.macrohive.com/feed/", "tier": 2},
        {"name": "Fed RSS", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "tier": 1},
    ]
}


def load_feeds():
    """Load RSS feeds from file or create default."""
    if FEEDS_FILE.exists():
        with open(FEEDS_FILE, "r") as f:
            return json.load(f)
    
    # Save default feeds
    with open(FEEDS_FILE, "w") as f:
        json.dump(DEFAULT_FEEDS, f, indent=2)
    return DEFAULT_FEEDS


def setup_logging():
    """Configure logging."""
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    log_file_path = BASE_DIR / LOG_FILE
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("finbot")


# Initialize
logger = setup_logging()
FEEDS = load_feeds()