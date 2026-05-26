import asyncio
import logging
import signal
import sys
from datetime import datetime
from config import logger, POSTING_MODE
from bot import bot
from scheduler import scheduler
from health import health_server, stop_health_server

class FinBot:
    """Main bot application."""
    
    def __init__(self):
        self.running = False
        self.health_runner = None
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("=" * 50)
        logger.info("FinBot Starting")
        logger.info("=" * 50)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize bot
        await bot.initialize()
        
        # Start health check server (for Railway)
        self.health_runner = await health_server()
        
        logger.info(f"Posting mode: {POSTING_MODE}")
        logger.info("Bot initialized successfully")
        
    async def run(self):
        """Run the bot."""
        await self.initialize()
        
        self.running = True
        
        # Start scheduler
        scheduler_task = asyncio.create_task(scheduler.run())
        
        # Start bot polling
        bot_task = asyncio.create_task(bot.run())
        
        logger.info("FinBot is running!")
        
        # Wait for shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup
            scheduler.stop()
            await bot.stop()
            
            if self.health_runner:
                await stop_health_server(self.health_runner)
            
            # Cancel tasks
            scheduler_task.cancel()
            bot_task.cancel()
            
            try:
                await scheduler_task
                await bot_task
            except asyncio.CancelledError:
                pass
                
            logger.info("FinBot shutdown complete")
            
    async def run_once(self):
        """Run a single cycle (for testing)."""
        await self.initialize()
        
        # Run daily digest once
        await scheduler.run_daily_digest()
        
        await bot.stop()
        logger.info("Single run complete")

async def main():
    """Main entry point."""
    finbot = FinBot()
    
    # Check for command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        await finbot.run_once()
    else:
        await finbot.run()

if __name__ == "__main__":
    asyncio.run(main())
