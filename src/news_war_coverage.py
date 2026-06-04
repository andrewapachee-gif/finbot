import json
import asyncio
import logging
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from config import logger, DATA_DIR

class WarCoverageMonitor:
    """Real-time war and geopolitical news monitoring."""
    
    def __init__(self):
        self.state_file = DATA_DIR / "war_coverage.json"
        self.state = self._load_state()
        self.feeds = []  # Initialize feeds list for compatibility
        
        # War-specific RSS feeds
        self.war_feeds = {
            'geopolitical': [
                {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tier": 1},
                {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best", "tier": 1},
                {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "tier": 1},
                {"name": "AP News", "url": "https://feeds.apnews.com/APNews", "tier": 1},
                {"name": "CNN World", "url": "http://rss.cnn.com/rss/edition_world.rss", "tier": 2},
            ],
            'defense_military': [
                {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/", "tier": 1},
                {"name": "Jane's Defence", "url": "https://www.janes.com/rss", "tier": 1},
                {"name": "Military.com", "url": "https://www.military.com/rss", "tier": 2},
            ],
            'energy_oil': [
                {"name": "OilPrice.com", "url": "https://oilprice.com/rss", "tier": 1},
                {"name": "Energy Intelligence", "url": "https://www.energyintel.com/rss", "tier": 1},
                {"name": "Platts Oil", "url": "https://www.spglobal.com/commodityinsights/rss", "tier": 1},
            ],
            'middle_east': [
                {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/", "tier": 1},
                {"name": "Jerusalem Post", "url": "https://www.jpost.com/rss", "tier": 1},
                {"name": "Tehran Times", "url": "https://www.tehrantimes.com/rss", "tier": 2},
                {"name": "Al-Monitor", "url": "https://www.al-monitor.com/rss", "tier": 1},
            ]
        }
        
        # Keywords for US-Israel-Iran conflict
        self.conflict_keywords = [
            'israel', 'iran', 'gaza', 'hamas', 'hezbollah', 'houthi',
            'missile', 'strike', 'attack', 'retaliation', 'escalation',
            'war', 'conflict', 'military', 'defense', 'idf', 'irgc',
            'nuclear', 'sanctions', 'oil', 'strait', 'hormuz'
        ]
        
        # Market impact keywords
        self.market_keywords = [
            'oil', 'crude', 'brent', 'opec', 'energy', 'gas',
            'gold', 'safe haven', 'treasury', 'bond', 'dollar',
            'stock', 'market', 'futures', 'trading', 'volatility'
        ]
        
        # Feed cache (avoid re-fetching same feeds too often)
        self.feed_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _load_state(self) -> Dict:
        """Load war coverage state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'posted_stories': [],
            'conflict_intensity': 'low',
            'market_impact_level': 'low',
            'last_check': None
        }
    
    def _save_state(self):
        """Save war coverage state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    async def fetch_war_news(self) -> List[Dict]:
        """Fetch war news from all feeds."""
        all_articles = []
        
        for category, feeds in self.war_feeds.items():
            for feed_info in feeds:
                try:
                    # Check cache
                    cache_key = feed_info['url']
                    cached = self.feed_cache.get(cache_key)
                    if cached and (datetime.utcnow() - cached['time']).seconds < self.cache_ttl:
                        articles = cached['articles']
                    else:
                        # Fetch with timeout
                        articles = await self._fetch_feed(feed_info, category)
                        self.feed_cache[cache_key] = {
                            'articles': articles,
                            'time': datetime.utcnow()
                        }
                    
                    all_articles.extend(articles)
                    
                except Exception as e:
                    logger.warning(f"Feed error ({feed_info['name']}): {e}")
                
                # Rate limit between feeds
                await asyncio.sleep(1)
        
        # Score and sort
        scored = []
        for article in all_articles:
            article['urgency_score'] = self._score_urgency(article)
            article['market_impact'] = self._score_market_impact(article)
            scored.append(article)
        
        scored.sort(key=lambda x: x['urgency_score'], reverse=True)
        return scored
    
    async def _fetch_feed(self, feed_info: Dict, category: str) -> List[Dict]:
        """Fetch a single RSS feed."""
        import aiohttp
        
        url = feed_info['url']
        name = feed_info['name']
        tier = feed_info['tier']
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers={'User-Agent': 'FinBot/1.0'}) as resp:
                    if resp.status != 200:
                        logger.warning(f"Feed returned status {resp.status}: {name}")
                        return []
                    
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    
                    if not feed.entries:
                        logger.warning(f"Feed parse failed or empty: {name}")
                        return []
                    
                    articles = []
                    for entry in feed.entries[:5]:  # Top 5 per feed
                        article = {
                            'id': entry.get('id', entry.get('link', '')),
                            'title': entry.get('title', ''),
                            'summary': entry.get('summary', entry.get('description', '')),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                            'source': name,
                            'category': category,
                            'tier': tier
                        }
                        articles.append(article)
                    
                    return articles
                    
        except asyncio.TimeoutError:
            logger.warning(f"Feed timeout (10s): {name}")
            return []
        except Exception as e:
            logger.warning(f"Feed parse failed or empty: {name}")
            return []
    
    def _score_urgency(self, article: Dict) -> float:
        """Score article urgency (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        # Keyword matches
        keyword_count = sum(1 for kw in self.conflict_keywords if kw in text)
        score += min(keyword_count * 0.15, 0.6)
        
        # Tier bonus (tier 1 sources weighted higher)
        tier = article.get('tier', 2)
        score += (3 - tier) * 0.1
        
        # Breaking/Urgent in title
        if any(word in article['title'].lower() for word in ['breaking', 'urgent', 'alert', 'live']):
            score += 0.2
        
        # Recent bonus (within last hour)
        try:
            published = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
            hours_old = (datetime.utcnow() - published.replace(tzinfo=None)).total_seconds() / 3600
            if hours_old < 1:
                score += 0.15
            elif hours_old < 6:
                score += 0.05
        except:
            pass
        
        return min(score, 1.0)
    
    def _score_market_impact(self, article: Dict) -> float:
        """Score market impact (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        # Market keyword matches
        keyword_count = sum(1 for kw in self.market_keywords if kw in text)
        score += min(keyword_count * 0.2, 0.8)
        
        # Oil-specific (high impact)
        if any(word in text for word in ['oil', 'crude', 'brent', 'opec', 'hormuz']):
            score += 0.2
        
        # Gold/safe haven
        if any(word in text for word in ['gold', 'safe haven', 'treasury']):
            score += 0.1
        
        return min(score, 1.0)
    
    def is_duplicate(self, article_id: str) -> bool:
        """Check if story was already posted."""
        return article_id in self.state['posted_stories']
    
    def mark_posted(self, article_id: str):
        """Mark story as posted."""
        self.state['posted_stories'].append(article_id)
        # Keep only last 100
        self.state['posted_stories'] = self.state['posted_stories'][-100:]
        self._save_state()
    
    async def get_breaking_stories(self) -> List[Dict]:
        """Get urgent breaking stories for posting."""
        articles = await self.fetch_war_news()
        
        breaking = []
        for article in articles:
            if article['urgency_score'] >= 0.7 and not self.is_duplicate(article['id']):
                breaking.append(article)
                
        return breaking[:3]  # Max 3 breaking stories
    
    def format_war_alert(self, article: Dict) -> str:
        """Format war news as urgent alert."""
        from growth_engine import growth_engine
        
        # Use growth engine's war formatting
        text = growth_engine.format_war_post(article)
        
        return text
    
    def get_conflict_summary(self) -> str:
        """Get current conflict summary for channel update."""
        intensity = self.state.get('conflict_intensity', 'low')
        market_impact = self.state.get('market_impact_level', 'low')
        
        intensity_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
            'critical': '⚫'
        }
        
        text = f"""🌍 <b>Geopolitical Monitor</b>

{intensity_emoji.get(intensity, '⚪')} <b>Conflict Intensity:</b> {intensity.upper()}
📈 <b>Market Impact:</b> {market_impact.upper()}

<b>Watchlist:</b>
🛢 Oil & Energy — $USO, $XLE, $XOM
🥇 Safe Haven — $GLD, $TLT, $UUP
🛡 Defense — $LMT, $RTX, $NOC
📉 Volatility — $VIX, $UVXY

<i>Updates every 30 minutes during active conflict</i>"""
        
        return text
    
    async def run_war_check(self):
        """Run war coverage check and post urgent news."""
        from publisher import publisher
        from bot import bot
        
        logger.info("Running war coverage check...")
        
        breaking = await self.get_breaking_stories()
        
        if not breaking:
            logger.info("No urgent war news found")
            return
        
        for article in breaking:
            formatted = self.format_war_alert(article)
            
            # Post with high priority - try publisher first, fallback to bot
            success = False
            try:
                success = await publisher.send_message(formatted)
            except (AttributeError, TypeError) as e:
                logger.warning(f"Publisher send failed: {e}, trying bot fallback")
            
            if not success:
                try:
                    from bot import bot
                    if bot.bot:
                        success = await bot.send_message(formatted)
                    else:
                        await bot.initialize()
                        success = await bot.send_message(formatted)
                except Exception as e2:
                    logger.error(f"Bot fallback also failed: {e2}")
            
            if success:
                self.mark_posted(article['id'])
                logger.info(f"Posted war alert: {article['title'][:50]}...")
                
                # Update conflict intensity
                avg_urgency = sum(a['urgency_score'] for a in breaking) / len(breaking)
                if avg_urgency > 0.8:
                    self.state['conflict_intensity'] = 'critical'
                elif avg_urgency > 0.6:
                    self.state['conflict_intensity'] = 'high'
                elif avg_urgency > 0.4:
                    self.state['conflict_intensity'] = 'medium'
                else:
                    self.state['conflict_intensity'] = 'low'
                
                self._save_state()
            else:
                logger.error(f"Failed to post war alert: {article['title'][:50]}...")
            
            # Rate limit
            await asyncio.sleep(30)

# Singleton instance
war_monitor = WarCoverageMonitor()
