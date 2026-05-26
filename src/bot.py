import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, POSTING_MODE, logger

class TelegramBot:
    """Handles Telegram bot operations."""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.channel_id = TELEGRAM_CHANNEL_ID
        self.application = None
        self.bot = None
        
    async def initialize(self):
        """Initialize the bot application."""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        
        self.application = Application.builder().token(self.token).build()
        self.bot = self.application.bot
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("post", self.post_command))
        self.application.add_handler(CommandHandler("queue", self.queue_command))
        self.application.add_handler(CommandHandler("clips", self.clips_command))
        self.application.add_handler(CommandHandler("fetchclips", self.fetchclips_command))
        
        logger.info("Telegram bot initialized")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 FinBot is running!\n\n"
            "Commands:\n"
            "/status - Check bot status\n"
            "/post - Manually trigger a post\n"
            "/queue - View pending posts\n"
            "/clips - YouTube clip stats\n"
            "/fetchclips - Manually fetch clips"
        )
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        # Lazy imports to avoid circular dependency
        from queue_manager import queue_manager
        from publisher import publisher
        
        pending_count = len(queue_manager.get_pending())
        await update.message.reply_text(
            "✅ FinBot Status:\n"
            f"Channel: {self.channel_id}\n"
            f"Mode: {POSTING_MODE}\n"
            f"Pending queue: {pending_count}\n"
            f"Posted today: {publisher.posted_today}\n"
            "Bot is active and monitoring feeds."
        )
        
    async def post_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command - manually trigger posting."""
        await update.message.reply_text("🔄 Triggering manual post...")
        # Lazy imports to avoid circular dependency
        from queue_manager import queue_manager
        from publisher import publisher
        
        # Get pending articles from queue
        pending = queue_manager.get_pending()
        if pending:
            article = pending[0]
            success = await publisher.post_article(article)
            if success:
                await update.message.reply_text(f"✅ Posted: {article['title'][:50]}...")
            else:
                await update.message.reply_text("❌ Failed to post")
        else:
            await update.message.reply_text("📭 No articles in queue")
        
    async def queue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /queue command - show pending posts."""
        # Lazy imports to avoid circular dependency
        from queue_manager import queue_manager
        
        pending = queue_manager.get_pending()
        if not pending:
            await update.message.reply_text("📭 No pending articles in queue")
            return
            
        text = f"📋 Pending Articles ({len(pending)}):\n\n"
        for i, article in enumerate(pending[:5], 1):  # Show top 5
            analysis = article.get('ai_analysis', {})
            sentiment = analysis.get('sentiment', 'neutral')
            relevance = analysis.get('relevance', 0)
            
            text += f"{i}. {article['title'][:60]}...\n"
            text += f"   Sentiment: {sentiment} | Relevance: {relevance:.2f}\n\n"
            
        await update.message.reply_text(text)
        
    async def clips_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clips command - show recent clips info."""
        from youtube_fetcher import youtube_fetcher
        
        posted_count = len(youtube_fetcher.posted_videos)
        recent_channels = youtube_fetcher.channel_history[-10:]
        
        text = (
            f"🎬 YouTube Clip Stats:\n\n"
            f"Posted clips: {posted_count}\n"
            f"Recent channels: {len(recent_channels)}\n"
            f"Max clips/run: 3\n"
            f"Schedule: 10:00, 18:00 UTC\n\n"
            f"Use /fetchclips to manually trigger fetch"
        )
        await update.message.reply_text(text)
        
    async def fetchclips_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /fetchclips command - manually trigger clip fetch."""
        await update.message.reply_text("🔄 Fetching YouTube clips...")
        
        from scheduler import scheduler
        
        try:
            await scheduler.run_youtube_clips()
            await update.message.reply_text("✅ Clip fetch complete")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
        
    async def send_message(self, text: str, parse_mode: str = "HTML"):
        """Send a message to the channel."""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f"Message sent to {self.channel_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
            
    async def send_photo(self, photo_url: str, caption: str, parse_mode: str = "HTML"):
        """Send a photo with caption to the channel."""
        try:
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=photo_url,
                caption=caption,
                parse_mode=parse_mode
            )
            logger.info(f"Photo sent to {self.channel_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False
            
    async def send_poll(self, question: str, options: list):
        """Send a poll to the channel."""
        try:
            await self.bot.send_poll(
                chat_id=self.channel_id,
                question=question,
                options=options,
                is_anonymous=False
            )
            logger.info(f"Poll sent to {self.channel_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send poll: {e}")
            return False
            
    async def run(self):
        """Run the bot with polling for commands."""
        await self.initialize()
        # Start polling for commands
        await self.application.initialize()
        await self.application.start()
        logger.info("Bot is running with command polling...")
        # Keep running
        while True:
            await asyncio.sleep(1)
        
    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped")

# Singleton instance
bot = TelegramBot()
