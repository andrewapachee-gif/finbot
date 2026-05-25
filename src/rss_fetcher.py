import feedparser
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import FEEDS, logger

class RSSFetcher:
    """Fetches and parses RSS feeds from multiple sources."""
    
    def __init__(self):
        self.feeds = FEEDS
        self.session = None
        
    async def initialize(self):
        """Initialize aiohttp session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'FinBot/1.0 (Financial News Aggregator)'
            }
        )
        
    async def fetch_feed(self, url: str) -> Optional[Dict]:
        """Fetch a single RSS feed."""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    return feedparser.parse(content)
                else:
                    logger.warning(f"Feed returned status {response.status}: {url}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch feed {url}: {e}")
            return None
            
    def parse_entries(self, feed_data: Dict, source_name: str, tier: int) -> List[Dict]:
        """Parse feed entries into standardized format."""
        articles = []
        
        if not feed_data or not hasattr(feed_data, 'entries'):
            return articles
            
        for entry in feed_data.entries[:10]:  # Top 10 from each feed
            article = {
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': entry.get('published', ''),
                'source': source_name,
                'tier': tier,
                'fetched_at': datetime.utcnow().isoformat(),
                'id': entry.get('id', entry.get('link', ''))
            }
            articles.append(article)
            
        return articles
        
    async def fetch_all_feeds(self, category: Optional[str] = None) -> List[Dict]:
        """Fetch all feeds or a specific category."""
        all_articles = []
        
        categories = [category] if category else self.feeds.keys()
        
        for cat in categories:
            if cat not in self.feeds:
                continue
                
            logger.info(f"Fetching {cat} feeds...")
            feeds = self.feeds[cat]
            
            # Fetch all feeds in category concurrently
            tasks = []
            for feed in feeds:
                task = self.fetch_feed(feed['url'])
                tasks.append((feed, task))
                
            for feed, task in tasks:
                try:
                    feed_data = await task
                    if feed_data:
                        articles = self.parse_entries(
                            feed_data, 
                            feed['name'], 
                            feed['tier']
                        )
                        all_articles.extend(articles)
                        logger.info(f"Fetched {len(articles)} from {feed['name']}")
                except Exception as e:
                    logger.error(f"Error processing {feed['name']}: {e}")
                    
        # Sort by tier (priority) and then by published date
        all_articles.sort(key=lambda x: (x['tier'], x.get('published', '')), reverse=False)
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
        
    async def fetch_market_data(self) -> Dict:
        """Fetch basic market data (requires yfinance)."""
        try:
            import yfinance as yf
            
            # Major indices
            indices = {
                'S&P 500': '^GSPC',
                'Nasdaq': '^IXIC',
                'Dow Jones': '^DJI',
                'Bitcoin': 'BTC-USD',
                'Ethereum': 'ETH-USD'
            }
            
            data = {}
            for name, ticker in indices.items():
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="2d")
                    if len(hist) >= 2:
                        latest = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        change = ((latest - prev) / prev) * 100
                        data[name] = {
                            'price': round(latest, 2),
                            'change': round(change, 2)
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch {name}: {e}")
                    
            return data
        except ImportError:
            logger.warning("yfinance not installed, skipping market data")
            return {}
            
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()

# Singleton instance
fetcher = RSSFetcher()
