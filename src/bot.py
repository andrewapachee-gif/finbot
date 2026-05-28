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
        self.application.add_handler(CommandHandler("analytics", self.analytics_command))
        self.application.add_handler(CommandHandler("crosspromo", self.crosspromo_command))
        self.application.add_handler(CommandHandler("viralpost", self.viralpost_command))
        self.application.add_handler(CommandHandler("warcheck", self.warcheck_command))
        self.application.add_handler(CommandHandler("directory", self.directory_command))
        self.application.add_handler(CommandHandler("growthstats", self.growthstats_command))
        
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
            "/fetchclips - Manually fetch clips\n"
            "/analytics - Channel analytics\n"
            "/crosspromo - Cross-promotion status\n"
            "/viralpost - Viral post template\n"
            "/warcheck - Check war news\n"
            "/directory - Directory submission guide\n"
            "/growthstats - Full growth metrics"
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
        quota_status = youtube_fetcher.quota.get_status()
        
        text = (
            f"🎬 YouTube Clip Stats:\n\n"
            f"Posted clips: {posted_count}\n"
            f"Recent channels: {len(recent_channels)}\n"
            f"Max clips/run: {MAX_CLIPS_PER_RUN}\n"
            f"Schedule: 5x daily (US ET)\n\n"
            f"{quota_status}\n\n"
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
    
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analytics command - show growth stats."""
        from analytics_tracker import analytics_tracker
        
        summary = analytics_tracker.get_analytics_summary()
        await update.message.reply_text(summary, parse_mode="HTML")
        
    async def crosspromo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /crosspromo command - show cross-promo status."""
        from cross_promo import cross_promo
        
        report = cross_promo.get_outreach_report()
        await update.message.reply_text(report, parse_mode="HTML")
        
    async def viralpost_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /viralpost command - generate viral post template."""
        from growth_engine import growth_engine
        
        cta = growth_engine.generate_viral_cta('article')
        teaser = growth_engine.generate_exclusive_teaser({'ai_analysis': {'relevance': 0.9}})
        
        text = f"""🎯 <b>Viral Post Template</b>

<b>CTA Example:</b>{cta}

<b>Exclusive Teaser:</b>{teaser}

<b>Growth Stats:</b>
• Forward CTAs used: {growth_engine.state['forward_ctas_used']}
• Engagement polls sent: {growth_engine.state['engagement_polls_sent']}
• Exclusive teasers sent: {growth_engine.state['exclusive_teasers_sent']}

Use these in your next post!"""
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    async def warcheck_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /warcheck command - manual war news check."""
        await update.message.reply_text("🌍 Checking war coverage...")
        
        from news_war_coverage import war_monitor
        
        try:
            await war_monitor.run_war_check()
            await update.message.reply_text("✅ War check complete")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
            
    async def directory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /directory command - show directory submission guide."""
        from directory_submitter import directory_submitter
        
        guide = directory_submitter.get_submission_guide()
        await update.message.reply_text(guide, parse_mode="HTML")
        
    async def growthstats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /growthstats command - show all growth metrics."""
        from growth_engine import growth_engine
        from analytics_tracker import analytics_tracker
        from cross_promo import cross_promo
        
        stats = growth_engine.get_growth_stats()
        report = analytics_tracker.get_growth_report()
        
        text = f"""🚀 <b>Growth Engine Stats</b>

<b>Viral Mechanics:</b>
• Forward CTAs: {stats['forward_ctas_used']}
• Engagement polls: {stats['engagement_polls_sent']}
• Exclusive teasers: {stats['exclusive_teasers_sent']}

<b>Subscribers:</b>
• Current: {report['current_subscribers']:,}
• Weekly growth: +{report['weekly_growth']:,}
• Monthly growth: +{report['monthly_growth']:,}

<b>Engagement:</b>
• Avg rate: {report['avg_engagement_rate']:.1f}%
• Best format: {report['best_post_type'] or 'N/A'}
• Posts tracked: {report['total_posts_tracked']}

<b>Milestones:</b>
• Reached: {', '.join(str(m) for m in stats['subscriber_milestones']) or 'None yet'}

Keep pushing! 📈"""
        
        await update.message.reply_text(text, parse_mode="HTML")
        
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
