# FinBot - AI-Powered Finance Telegram Bot

A custom Python bot for automating finance, AI, and investing content on your Telegram channel.

## Features

- **RSS Feed Aggregation** - Multiple financial news sources
- **AI Content Filtering** - GPT/Claude to filter noise and rewrite articles
- **Sentiment Analysis** - Bullish/bearish/neutral tagging
- **Ticker/Token Extraction** - Auto-detect mentioned stocks and crypto
- **Scheduled Posting** - Daily digests + breaking news alerts
- **Telegram Publishing** - Rich formatted posts with reactions
- **Content Queue** - Review before posting (optional)
- **Engagement Hooks** - Polls, market summaries, weekly roundups

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

3. Run the bot:
```bash
python src/main.py
```

## Project Structure

```
finbot/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration loader
│   ├── bot.py               # Telegram bot handler
│   ├── rss_fetcher.py       # RSS feed aggregation
│   ├── ai_filter.py         # AI content filtering/rewriting
│   ├── sentiment.py         # Sentiment analysis
│   ├── ticker_extractor.py  # Stock/crypto detection
│   ├── scheduler.py         # Post scheduling
│   ├── publisher.py         # Telegram publishing
│   └── queue_manager.py     # Content queue
├── data/
│   ├── feeds.json           # RSS feed sources
│   ├── queue.json           # Pending posts
│   └── posted.json          # Posted article tracking
├── logs/                    # Log files
├── .env                     # Environment variables
├── .env.example             # Example env file
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build
└── docker-compose.yml       # Docker compose setup
```

## Deployment

### Railway (Recommended for 24/7)
1. Fork this repo or push to GitHub
2. Go to https://railway.app
3. New Project → Deploy from GitHub
4. Add environment variables in Railway dashboard
5. Deploy — bot runs 24/7 automatically

### Docker (Recommended)
```bash
docker-compose up -d
```

### Systemd Service
See `systemd/finbot.service` for Linux service setup.

## License
MIT
