import asyncio
import schedule
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from config import (
    DAILY_DIGEST_TIME, ENABLE_WEEKLY_ROUNDUP,
    WEEKLY_ROUNDUP_DAY, WEEKLY_ROUNDUP_TIME,
    POSTING_MODE, logger, DATA_DIR
)
from rss_fetcher import fetcher
from youtube_fetcher import youtube_fetcher
from clip_trimmer import trimmer
from ai_filter import ai_filter
from publisher import publisher
from queue_manager import queue_manager

# US Eastern Time schedule (converted to UTC for server)
# ET = UTC-4 (EDT) or UTC-5 (EST)
# All times below are UTC equivalents for US ET times

class Scheduler:
    """Manages scheduled tasks for the bot."""

    def __init__(self):
        self.running = False
        self.daily_articles = []  # Store articles for daily digest

    async def run_youtube_clips(self):
        """Fetch and post YouTube clips."""
        # Prevent concurrent execution
        if getattr(self, '_youtube_running', False):
            logger.warning("YouTube clip fetch already running, skipping")
            return
        
        self._youtube_running = True
        logger.info("Fetching YouTube clips...")
        
        try:
            await youtube_fetcher.initialize()
            
            # Fetch unique clips
            clips = await youtube_fetcher.fetch_unique_clips()
            
            if not clips:
                logger.info("No new clips found")
                await youtube_fetcher.close()
                return
                
            # Download and trim each clip (if tools available)
            for clip in clips:
                try:
                    video_path = await trimmer.auto_trim(
                        clip['video_id'], 
                        clip['title']
                    )
                    
                    # Post to channel (video or thumbnail fallback)
                    if POSTING_MODE == 'auto':
                        await publisher.post_youtube_clip(clip, str(video_path) if video_path else None)
                    elif POSTING_MODE == 'queue':
                        # Add to queue with video path
                        clip['video_path'] = str(video_path) if video_path else None
                        queue_manager.add_to_queue(clip)
                        logger.info(f"Added clip to queue: {clip['title'][:50]}...")
                        
                    # Rate limit between posts
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Failed to process clip {clip['video_id']}: {e}")
                    
            # Cleanup old clips
            trimmer.cleanup_old_clips()
            
            await youtube_fetcher.close()
            logger.info("YouTube clip fetch complete")
        finally:
            self._youtube_running = False

    async def run_daily_digest(self):
        """Fetch and post daily digest."""
        logger.info("Running daily digest...")

        # Fetch articles
        await fetcher.initialize()
        articles = await fetcher.fetch_all_feeds()

        if not articles:
            logger.warning("No articles fetched for digest")
            await fetcher.close()
            return

        # Analyze with AI (if configured)
        if ai_filter.client:
            analyzed = await ai_filter.analyze_batch(articles)
            # Filter passed articles
            passed = [a for a in analyzed if a.get('passed_filter', False)]
        else:
            logger.info("AI filtering disabled - using all articles")
            passed = articles

        if not passed:
            logger.warning("No articles passed AI filter")
            await fetcher.close()
            return

        # Store for weekly roundup
        self.daily_articles.extend(passed)

        # Handle posting based on mode
        if POSTING_MODE == 'auto':
            # Post digest
            await publisher.post_daily_digest(passed[:5])  # Top 5
            
            # Post individual breaking news
            breaking = [a for a in passed if a.get('ai_analysis', {}).get('breaking', False)]
            for article in breaking[:3]:  # Max 3 breaking
                await publisher.post_article(article)
                
        elif POSTING_MODE == 'queue':
            # Add to queue for manual review
            for article in passed[:10]:
                queue_manager.add_to_queue(article)
            logger.info(f"Added {len(passed[:10])} articles to queue")
            
        else:  # manual mode
            logger.info("Manual mode - articles fetched but not posted")
            # Just store in daily articles for weekly roundup

        await fetcher.close()
        logger.info("Daily digest complete")

    async def run_weekly_roundup(self):
        """Post weekly roundup."""
        logger.info("Running weekly roundup...")

        if not self.daily_articles:
            logger.warning("No articles for weekly roundup")
            return

        await publisher.post_weekly_roundup(self.daily_articles)

        # Clear weekly buffer
        self.daily_articles = []
        logger.info("Weekly roundup complete")

    async def run_market_summary(self):
        """Post market summary."""
        logger.info("Running market summary...")

        await fetcher.initialize()
        market_data = await fetcher.fetch_market_data()
        await publisher.post_market_summary(market_data)
        await fetcher.close()

    async def run_breaking_news_check(self):
        """Check for breaking news."""
        logger.info("Checking for breaking news...")

        await fetcher.initialize()
        articles = await fetcher.fetch_all_feeds()

        if articles:
            analyzed = await ai_filter.analyze_batch(articles[:5])  # Check top 5
            breaking = [a for a in analyzed if a.get('ai_analysis', {}).get('breaking', False)]

            for article in breaking:
                if not publisher.is_duplicate(article['id']):
                    if POSTING_MODE == 'auto':
                        await publisher.post_article(article)
                    elif POSTING_MODE == 'queue':
                        queue_manager.add_to_queue(article)
                        logger.info(f"Added breaking news to queue: {article['title'][:50]}...")

        await fetcher.close()

    def setup_schedule(self):
        """Setup scheduled jobs in US Eastern Time (5x daily clips)."""
        # Convert US times to UTC for schedule library
        # US ET: 06:00, 10:00, 14:00, 18:00, 22:00 -> UTC: 10:00, 14:00, 18:00, 22:00, 02:00
        
        # Daily digest at 08:00 ET (12:00 UTC)
        schedule.every().day.at("12:00").do(
            lambda: asyncio.create_task(self.run_daily_digest())
        )

        # Market summary (twice daily ET)
        # 09:00 ET -> 13:00 UTC (pre-market open)
        schedule.every().day.at("13:00").do(
            lambda: asyncio.create_task(self.run_market_summary())
        )
        # 16:00 ET -> 20:00 UTC (market close)
        schedule.every().day.at("20:00").do(
            lambda: asyncio.create_task(self.run_market_summary())
        )

        # YouTube clips (5x daily in US time)
        # 06:00 ET -> 10:00 UTC (early morning US)
        schedule.every().day.at("10:00").do(
            lambda: asyncio.create_task(self.run_youtube_clips())
        )
        # 10:00 ET -> 14:00 UTC (morning US)
        schedule.every().day.at("14:00").do(
            lambda: asyncio.create_task(self.run_youtube_clips())
        )
        # 14:00 ET -> 18:00 UTC (afternoon US)
        schedule.every().day.at("18:00").do(
            lambda: asyncio.create_task(self.run_youtube_clips())
        )
        # 18:00 ET -> 22:00 UTC (evening US)
        schedule.every().day.at("22:00").do(
            lambda: asyncio.create_task(self.run_youtube_clips())
        )
        # 22:00 ET -> 02:00 UTC (late night US)
        schedule.every().day.at("02:00").do(
            lambda: asyncio.create_task(self.run_youtube_clips())
        )

        # Breaking news check (every 4 hours for faster response)
        schedule.every(4).hours.do(
            lambda: asyncio.create_task(self.run_breaking_news_check())
        )

        # Weekly roundup
        if ENABLE_WEEKLY_ROUNDUP:
            day_map = {
                'monday': schedule.every().monday,
                'tuesday': schedule.every().tuesday,
                'wednesday': schedule.every().wednesday,
                'thursday': schedule.every().thursday,
                'friday': schedule.every().friday,
                'saturday': schedule.every().saturday,
                'sunday': schedule.every().sunday
            }
            day_func = day_map.get(WEEKLY_ROUNDUP_DAY.lower(), schedule.every().sunday)
            # 18:00 ET Sunday -> 22:00 UTC
            day_func.at("22:00").do(
                lambda: asyncio.create_task(self.run_weekly_roundup())
            )

        # Reset daily counter at midnight ET (04:00 UTC)
        schedule.every().day.at("04:00").do(
            publisher.reset_daily_counter
        )

        logger.info("Schedule setup complete (US Eastern Time)")
        logger.info("Clip times (ET): 06:00, 10:00, 14:00, 18:00, 22:00")
        logger.info("Digest: 08:00 ET | Market summaries: 09:00, 16:00 ET")

    async def run(self):
        """Run the scheduler loop."""
        self.running = True
        self.setup_schedule()

        logger.info("Scheduler started")
        logger.info("Schedule: US Eastern Time (ET)")
        logger.info("Clip times (ET): 06:00, 10:00, 14:00, 18:00, 22:00")
        logger.info("Digest: 08:00 ET | Market summaries: 09:00, 16:00 ET")
        
        # Run initial tasks on startup (skip if already ran recently)
        startup_file = DATA_DIR / "last_startup.json"
        skip_startup = False
        if startup_file.exists():
            try:
                with open(startup_file, 'r') as f:
                    data = json.load(f)
                    last_run = datetime.fromisoformat(data.get('last_startup', '2000-01-01'))
                    if (datetime.utcnow() - last_run).total_seconds() < 3600:  # 1 hour
                        skip_startup = True
                        logger.info("Skipping startup tasks (ran recently)")
            except:
                pass
        
        if not skip_startup:
            logger.info("Running startup tasks...")
            try:
                await self.run_youtube_clips()
            except Exception as e:
                logger.error(f"Startup YouTube clips failed: {e}")
            try:
                await self.run_daily_digest()
            except Exception as e:
                logger.error(f"Startup digest failed: {e}")
            
            # Record startup time
            with open(startup_file, 'w') as f:
                json.dump({'last_startup': datetime.utcnow().isoformat()}, f)

        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")

# Singleton instance
scheduler = Scheduler()
