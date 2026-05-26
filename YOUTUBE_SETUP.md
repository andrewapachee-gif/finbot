# YouTube Clip Sourcing Setup

## Overview
FinBot can now source investment-related clips from YouTube, trim them, and post them to your Telegram channel.

## Prerequisites

1. **YouTube Data API v3 Key**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create a project or select existing
   - Enable **YouTube Data API v3**
   - Create an **API Key** (restrict to YouTube Data API for security)
   - Copy the key

2. **System Dependencies**
   - `yt-dlp` (for downloading clips)
   - `ffmpeg` + `ffprobe` (for trimming)

## Installation

### Local Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install yt-dlp
pip install yt-dlp

# Install ffmpeg (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install ffmpeg

# Install ffmpeg (macOS)
brew install ffmpeg
```

### Railway Deployment
Railway uses Nixpacks which should auto-detect Python requirements. However, `ffmpeg` needs to be added:

Create/modify `railway.toml` or use the Railway dashboard to add a custom build command:
```toml
[build]
builder = "NIXPACKS"

[build.nixpacks]
aptPackages = ["ffmpeg", "ffprobe"]
```

Or add to `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "nixpacksPlan": {
      "phases": {
        "setup": {
          "aptPackages": ["ffmpeg", "ffprobe"]
        }
      }
    }
  },
  "deploy": {
    "startCommand": "python src/main.py",
    "restartPolicy": {
      "type": "ON_FAILURE",
      "maxRetries": 10
    }
  }
}
```

## Configuration

Add to your `.env` file:
```env
# Required
YOUTUBE_API_KEY=your_youtube_api_key_here

# Optional - Clip Settings
MAX_CLIP_DURATION=120        # Max seconds to consider
MIN_CLIP_DURATION=15         # Min seconds to consider
MAX_CLIPS_PER_RUN=3        # Max clips per fetch
CLIP_QUALITY=720           # Max resolution
TARGET_CLIP_DURATION=45    # Target length after trim
MAX_CLIP_FILE_SIZE_MB=20   # Telegram upload limit
```

## How It Works

1. **Search**: Bot searches YouTube for investment-related shorts using rotating queries
2. **Filter**: Filters by duration, deduplicates, scores by engagement
3. **Diversity**: Prioritizes clips from channels not recently used
4. **Download**: Uses `yt-dlp` to download best quality under size limit
5. **Trim**: Uses `ffmpeg` to trim to ~45 seconds (skips intro, keeps best segment)
6. **Post**: Uploads as native Telegram video with formatted caption

## Commands

- `/clips` - Show clip stats and recent channels
- `/fetchclips` - Manually trigger clip fetch

## Schedule
- Clips fetched at **10:00 UTC** and **18:00 UTC** daily
- Old clips auto-cleaned after 48 hours

## Channel Diversity

The bot tracks the last 50 channels used and prioritizes new ones. This ensures your audience sees content from varied sources rather than the same channels repeatedly.

## Troubleshooting

**"yt-dlp not found"**
- Install: `pip install yt-dlp`

**"ffmpeg not found"**
- Install system ffmpeg package

**"YouTube API returned 403"**
- Check API key is valid and YouTube Data API v3 is enabled
- Check quota isn't exceeded (10,000 units/day default)

**Videos too large for Telegram**
- Reduce `CLIP_QUALITY` (try 480)
- Reduce `MAX_CLIP_DURATION`
- Enable Telegram bot's file size limits (50MB for regular bots)

## Quota Usage

YouTube Data API quota (10,000 units/day):
- Search: 100 units per request
- Video details: 1 unit per request (50 videos max per call)

With default settings:
- 4 category searches/day = 400 units
- 1 video details call = ~1-3 units
- **Total: ~403 units/day** (well under limit)
