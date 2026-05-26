YouTube Clip Sourcing - Deployment Checklist

✅ BUILT:
1. youtube_fetcher.py - Searches YouTube for investment clips, filters by duration, 
   deduplicates, scores by engagement, prioritizes channel diversity

2. clip_trimmer.py - Downloads clips with yt-dlp, auto-trims to ~45s with ffmpeg

3. Updated publisher.py - Added send_video() and post_youtube_clip() methods

4. Updated scheduler.py - Added run_youtube_clips() task, runs at 10:00 & 18:00 UTC

5. Updated bot.py - Added /clips and /fetchclips commands

6. Updated config.py - Added all YouTube settings

7. Updated requirements.txt - Added yt-dlp

8. Updated railway.json - Added ffmpeg/ffprobe apt packages

9. Created YOUTUBE_SETUP.md - Full documentation

📋 YOU NEED TO DO:

1. GET YOUTUBE API KEY:
   → https://console.cloud.google.com/apis/credentials
   → Enable YouTube Data API v3
   → Create API Key

2. ADD TO RAILWAY ENV:
   YOUTUBE_API_KEY=your_key_here
   (Railway dashboard → Variables)

3. DEPLOY:
   git add .
   git commit -m "Add YouTube clip sourcing"
   git push railway main

4. TEST:
   Send /fetchclips to your bot
   Or wait for 10:00/18:00 UTC scheduled run

⚙️ OPTIONAL CUSTOMIZATION:
   MAX_CLIPS_PER_RUN=3 (default)
   CLIP_QUALITY=720 (default)
   TARGET_CLIP_DURATION=45 (default)
   CHANNEL_WHITELIST=Channel1,Channel2 (optional)

📊 QUOTA:
   Uses ~403/10000 YouTube API units/day
   Well within free tier

🎬 FEATURES:
   - Auto-trims to best 45-second segment
   - Skips first 3 seconds (intros)
   - Tracks last 50 channels for diversity
   - Deduplicates by video ID
   - Auto-cleans clips after 48h
   - Formatted captions with views, channel, link
