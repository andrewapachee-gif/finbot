import sys
import asyncio
sys.path.insert(0, 'src')

from scheduler import scheduler
from publisher import publisher
from bot import bot
from queue_manager import queue_manager
from content_hooks import HIGH_RETENTION_HOOKS, format_hook_for_telegram
from growth_engine import growth_engine
from analytics_tracker import analytics_tracker
from news_war_coverage import war_monitor
from rss_fetcher import fetcher
from ai_filter import ai_filter
from youtube_fetcher import youtube_fetcher
from clip_trimmer import trimmer
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, POSTING_MODE, MAX_POSTS_PER_DAY, OPENAI_API_KEY

print('=== FULL SYSTEM DEBUG ===')
print()

# Config check
print(f'✅ Config: TOKEN={TELEGRAM_BOT_TOKEN[:20]}... CHANNEL={TELEGRAM_CHANNEL_ID} MODE={POSTING_MODE}')
print(f'✅ OpenAI: {"SET" if OPENAI_API_KEY else "NOT SET"}')
print(f'✅ Max posts/day: {MAX_POSTS_PER_DAY}')
print()

# Publisher check
print(f'✅ Publisher: posted_today={publisher.posted_today}')
print(f'✅ Posted articles count: {len(publisher.posted_articles)}')
print()

# Queue check
pending = queue_manager.get_pending()
print(f'✅ Queue: {len(pending)} pending articles')
print()

# Hooks check
print(f'✅ Hooks: {len(HIGH_RETENTION_HOOKS)} loaded')
for h in HIGH_RETENTION_HOOKS[:3]:
    print(f'  #{h["id"]}: {h["trigger"]}')
print()

# Growth engine check
stats = growth_engine.get_growth_stats()
print(f'✅ Growth Engine: CTAs={stats["forward_ctas_used"]} Polls={stats["engagement_polls_sent"]} Teasers={stats["exclusive_teasers_sent"]}')
print()

# YouTube check
print(f'✅ YouTube: API key={"SET" if youtube_fetcher.api_key else "NOT SET"}')
print(f'✅ Quota: {youtube_fetcher.quota.get_status()}')
print(f'✅ Posted videos: {len(youtube_fetcher.posted_videos)}')
print(f'✅ Channel history: {len(youtube_fetcher.channel_history)}')
print()

# War coverage check
print(f'✅ War Monitor: feeds={len(war_monitor.feeds)} war_feeds={len(war_monitor.war_feeds)} categories')
for cat, feeds in war_monitor.war_feeds.items():
    print(f'  {cat}: {len(feeds)} feeds')
print()

# RSS Fetcher check
print(f'✅ RSS Fetcher: initialized')
print()

# AI Filter check
print(f'✅ AI Filter: client={"READY" if ai_filter.client else "NOT READY"}')
print()

# Analytics check
print(f'✅ Analytics: active')
print()

print('=== ALL MODULES LOADED SUCCESSFULLY ===')
