import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def health_server():
    """Simple health check server for Railway."""
    app = web.Application()
    
    async def health(request):
        return web.Response(text='OK', status=200)
    
    app.router.add_get('/health', health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("Health check server started on port 8080")
    return runner

async def stop_health_server(runner):
    """Stop health check server."""
    await runner.cleanup()
    logger.info("Health check server stopped")
