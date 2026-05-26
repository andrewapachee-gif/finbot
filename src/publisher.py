import json
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import (
    POSTING_MODE, DAILY_DIGEST_TIME, MAX_POSTS_PER_DAY,
    ENABLE_POLLS, ENABLE_WEEKLY_ROUNDUP, 
    WEEKLY_ROUNDUP_DAY, WEEKLY_ROUNDUP_TIME,
    QUEUE_FILE, POSTED_FILE, logger
)

class Publisher:
    """Handles publishing content to Telegram channel."""
    
    def __init__(self):
        self.posted_today = 0
        self.last_post_time = None
        self.posted_articles = self._load_posted()
        
    def _load_posted(self) -> set:
        """Load list of already posted article IDs."""
        if POSTED_FILE.exists():
            with open(POSTED_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('posted_ids', []))
        return set()
        
    def _save_posted(self):
        """Save posted article IDs."""
        with open(POSTED_FILE, 'w') as f:
            json.dump({'posted_ids': list(self.posted_articles)}, f)
            
    def is_duplicate(self, article_id: str) -> bool:
        """Check if article was already posted."""
        return article_id in self.posted_articles
        
    def mark_posted(self, article_id: str):
        """Mark article as posted."""
        self.posted_articles.add(article_id)
        self._save_posted()
        
    def format_article(self, article: Dict) -> str:
        """Format article for Telegram post."""
        analysis = article.get('ai_analysis', {})
        rewrite = analysis.get('rewrite', article['summary'])
        sentiment = analysis.get('sentiment', 'neutral')
        tickers = analysis.get('tickers', [])
        breaking = analysis.get('breaking', False)
        
        # Sentiment emoji
        sentiment_emoji = {
            'bullish': '🟢',
            'bearish': '🔴',
            'neutral': '⚪'
        }.get(sentiment.lower(), '⚪')
        
        # Breaking news tag
        breaking_tag = "🚨 <b>BREAKING</b>\n" if breaking else ""
        
        # Format tickers
        tickers_str = ""
        if tickers:
            ticker_tags = ' '.join([f"#{t}" for t in tickers])
            tickers_str = f"\n📊 {ticker_tags}"
            
        text = f"""{breaking_tag}<b>{article['title']}</b>

{rewrite[:400]}

{sentiment_emoji} Sentiment: <i>{sentiment.title()}</i>{tickers_str}

🔗 <a href="{article['link']}">Read full article</a>
📰 {article['source']}"""
        
        return text
        
    async def post_article(self, article: Dict) -> bool:
        """Post a single article to channel."""
        # Lazy import to avoid circular dependency
        from bot import bot
        
        if self.posted_today >= MAX_POSTS_PER_DAY:
            logger.warning(f"Daily post limit reached ({MAX_POSTS_PER_DAY})")
            return False
            
        if self.is_duplicate(article['id']):
            logger.info(f"Skipping duplicate: {article['title'][:50]}")
            return False
            
        text = self.format_article(article)
        
        success = await bot.send_message(text)
        if success:
            self.mark_posted(article['id'])
            self.posted_today += 1
            self.last_post_time = datetime.utcnow()
            logger.info(f"Posted: {article['title'][:50]}...")
            
            # Add reaction buttons if enabled
            if ENABLE_POLLS and article.get('ai_analysis', {}).get('tickers'):
                await self._add_engagement_poll(article)
                
        return success
        
    async def _add_engagement_poll(self, article: Dict):
        """Add a poll for engagement."""
        # Lazy import to avoid circular dependency
        from bot import bot
        
        tickers = article.get('ai_analysis', {}).get('tickers', [])
        if not tickers:
            return
            
        question = f"What's your take on {tickers[0]}?"
        options = ["🟢 Bullish", "🔴 Bearish", "⚪ Neutral"]
        
        await bot.send_poll(question, options)
        
    async def post_daily_digest(self, articles: List[Dict]):
        """Post daily digest of top articles."""
        # Lazy import to avoid circular dependency
        from bot import bot
        from ai_filter import ai_filter
        
        if not articles:
            logger.info("No articles for digest")
            return
            
        digest = ai_filter.generate_daily_digest(articles)
        
        # Add header
        today = datetime.utcnow().strftime("%B %d, %Y")
        header = f"📅 <b>Daily Finance Digest</b> | {today}\n\n"
        
        text = header + digest
        
        # Add footer
        footer = "\n\n📈 Stay informed. Invest wisely."
        text += footer
        
        await bot.send_message(text)
        logger.info("Daily digest posted")
        
    async def post_weekly_roundup(self, articles: List[Dict]):
        """Post weekly market roundup."""
        # Lazy import to avoid circular dependency
        from bot import bot
        from ai_filter import ai_filter
        
        if not articles:
            logger.info("No articles for weekly roundup")
            return
            
        roundup = ai_filter.generate_weekly_roundup(articles)
        
        # Add header
        week_end = datetime.utcnow().strftime("%B %d, %Y")
        header = f"📊 <b>Weekly Market Roundup</b> | Week ending {week_end}\n\n"
        
        text = header + roundup
        
        await bot.send_message(text)
        logger.info("Weekly roundup posted")
        
    async def post_market_summary(self, market_data: Dict):
        """Post market summary."""
        # Lazy import to avoid circular dependency
        from bot import bot
        
        if not market_data:
            return
            
        text = "📊 <b>Market Snapshot</b>\n\n"
        
        for name, data in market_data.items():
            change_emoji = "🟢" if data['change'] > 0 else "🔴"
            text += f"{change_emoji} <b>{name}</b>: {data['price']} ({data['change']:+.2f}%)\n"
            
        await bot.send_message(text)
        logger.info("Market summary posted")

    async def post_youtube_clip(self, clip: Dict, video_path: str = None) -> bool:
        """Post a YouTube clip to the channel."""
        from bot import bot
        from youtube_fetcher import youtube_fetcher
        
        if self.posted_today >= MAX_POSTS_PER_DAY:
            logger.warning(f"Daily post limit reached ({MAX_POSTS_PER_DAY})")
            return False
            
        if self.is_duplicate(clip['video_id']):
            logger.info(f"Skipping duplicate clip: {clip['title'][:50]}")
            return False
            
        # Format caption
        sentiment_emoji = "🎬"
        channel = clip.get('channel_title', 'Unknown')
        
        caption = f"""{sentiment_emoji} <b>{clip['title']}</b>

📺 {channel}
⏱ {clip.get('duration_sec', '?')}s
👀 {clip.get('view_count', 0):,} views

🔗 <a href="{clip['url']}">Watch on YouTube</a>

#YouTubeClip #Finance #Investing"""
        
        # Try video upload first, fallback to thumbnail+link
        if video_path and os.path.exists(video_path):
            success = await self.send_video(video_path, caption)
        else:
            # Fallback: send thumbnail with link
            success = await bot.bot.send_photo(
                chat_id=bot.channel_id,
                photo=clip.get('thumbnail', ''),
                caption=caption,
                parse_mode='HTML'
            )
            
        if success:
            self.mark_posted(clip['video_id'])
            self.posted_today += 1
            youtube_fetcher.mark_posted(clip['video_id'], clip['channel_id'])
            logger.info(f"Posted clip: {clip['title'][:50]}...")
            return True
        return False
        
    async def send_video(self, video_path: str, caption: str, parse_mode: str = "HTML"):
        """Send a video file to the channel."""
        try:
            from telegram import InputFile
            
            with open(video_path, 'rb') as f:
                await bot.bot.send_video(
                    chat_id=bot.channel_id,
                    video=InputFile(f),
                    caption=caption,
                    parse_mode=parse_mode,
                    supports_streaming=True
                )
            logger.info(f"Video sent to {bot.channel_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
            return False
        
    def reset_daily_counter(self):
        """Reset daily post counter."""
        self.posted_today = 0
        logger.info("Daily post counter reset")

# Singleton instance
publisher = Publisher()
