import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from config import (
    DAILY_DIGEST_TIME, ENABLE_WEEKLY_ROUNDUP,
    WEEKLY_ROUNDUP_DAY, WEEKLY_ROUNDUP_TIME,
    POSTING_MODE, logger
)
from rss_fetcher import fetcher
from ai_filter import ai_filter
from publisher import publisher
from queue_manager import queue_manager

class Scheduler:
    """Manages scheduled tasks for the bot."""

    def __init__(self):
        self.running = False
        self.daily_articles = []  # Store articles for daily digest

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
        """Setup scheduled jobs."""
        # Daily digest
        schedule.every().day.at(DAILY_DIGEST_TIME).do(
            lambda: asyncio.create_task(self.run_daily_digest())
        )

        # Market summary (twice daily)
        schedule.every().day.at("09:00").do(
            lambda: asyncio.create_task(self.run_market_summary())
        )
        schedule.every().day.at("16:00").do(
            lambda: asyncio.create_task(self.run_market_summary())
        )

        # Breaking news check (every 6 hours)
        schedule.every(6).hours.do(
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
            day_func.at(WEEKLY_ROUNDUP_TIME).do(
                lambda: asyncio.create_task(self.run_weekly_roundup())
            )

        # Reset daily counter at midnight
        schedule.every().day.at("00:00").do(
            publisher.reset_daily_counter
        )

        logger.info("Schedule setup complete")

    async def run(self):
        """Run the scheduler loop."""
        self.running = True
        self.setup_schedule()

        logger.info("Scheduler started")

        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")

# Singleton instance
scheduler = Scheduler()
