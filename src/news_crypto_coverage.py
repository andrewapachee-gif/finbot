import json
import asyncio
import logging
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from config import logger, DATA_DIR, BREAKING_NEWS_THRESHOLD

class CryptoNewsMonitor:
    """Real-time cryptocurrency news monitoring with price alerts and regulatory tracking."""
    
    def __init__(self):
        self.state_file = DATA_DIR / "crypto_coverage.json"
        self.state = self._load_state()
        
        # Crypto-specific RSS feeds (expanded beyond config.py defaults)
        self.crypto_feeds = {
            'news': [
                {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "tier": 1},
                {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "tier": 1},
                {"name": "Decrypt", "url": "https://decrypt.co/feed", "tier": 1},
                {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "tier": 2},
                {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/", "tier": 2},
                {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "tier": 2},
                {"name": "Blockworks", "url": "https://blockworks.co/news/feed", "tier": 1},
            ],
            'regulatory': [
                {"name": "SEC Press Releases", "url": "https://www.sec.gov/cgi/browse-edgar?action=getcurrent&type=&company=&dateb=&owner=include&start=0&count=40&output=atom", "tier": 1},
                {"name": "CFTC News", "url": "https://www.cftc.gov/rss/PressReleases.xml", "tier": 1},
                {"name": "FinCEN Updates", "url": "https://www.fincen.gov/news/news-feed", "tier": 1},
                {"name": "CoinDesk Policy", "url": "https://www.coindesk.com/policy/feed", "tier": 2},
            ],
            'market_data': [
                {"name": "CoinMarketCap News", "url": "https://coinmarketcap.com/rss/feed", "tier": 2},
                {"name": "CryptoPanic", "url": "https://cryptopanic.com/news/rss/", "tier": 1},
            ],
            'exchange': [
                {"name": "Binance Blog", "url": "https://www.binance.com/en/blog/rss", "tier": 2},
                {"name": "Coinbase Blog", "url": "https://blog.coinbase.com/feed", "tier": 2},
                {"name": "Kraken Blog", "url": "https://blog.kraken.com/feed/", "tier": 2},
            ]
        }
        
        # Keywords for crypto urgency scoring
        self.urgency_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'cardano', 'ada',
            'binance', 'coinbase', 'kraken', 'etf', 'sec', 'regulation', 'regulatory',
            'hack', 'exploit', 'breach', 'wallet', 'drain', 'rug pull', 'scam',
            'approval', 'reject', 'deny', 'greenlight', 'spot etf', 'bitcoin etf',
            'halving', 'fork', 'upgrade', 'merge', 'shapella', 'dencun',
            'fed', 'rate', 'interest', 'inflation', 'cpi', 'ppi',
            'crash', 'pump', 'dump', 'rally', 'surge', 'plunge', 'moon', 'bear',
            'whale', 'institutional', 'blackrock', 'fidelity', 'grayscale',
            'cbdc', 'stablecoin', 'tether', 'usdt', 'usdc', 'depeg',
            'lawsuit', 'settlement', 'fine', 'penalty', 'enforcement',
            'delist', 'listing', 'partnership', 'integration', 'adoption',
            'ai', 'artificial intelligence', 'machine learning', 'neural',
        ]
        
        # Price impact keywords
        self.price_keywords = [
            'price', 'surge', 'plunge', 'rally', 'crash', 'dump', 'pump',
            'breakout', 'support', 'resistance', 'all-time high', 'ath',
            'correction', 'rebound', 'volatile', 'volatility', 'liquidation'
        ]
        
        # Regulatory keywords (higher weight)
        self.regulatory_keywords = [
            'sec', 'cftc', 'finra', 'regulation', 'regulatory', 'compliance',
            'framework', 'bill', 'legislation', 'hearing', 'testimony',
            'gensler', 'etf approval', 'spot bitcoin', 'spot ethereum',
            'delist', 'suspension', 'enforcement', 'lawsuit', 'settlement'
        ]
        
        # Security incident keywords (highest weight)
        self.security_keywords = [
            'hack', 'exploit', 'breach', 'drain', 'stolen', 'stole', 'theft',
            'rug pull', 'exit scam', 'phishing', 'compromised', 'vulnerability',
            'bridge', 'multisig', 'gnosis', 'safe', 'trezor', 'ledger'
        ]
        
        # Feed cache
        self.feed_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _load_state(self) -> Dict:
        """Load crypto coverage state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'posted_stories': [],
            'market_intensity': 'low',
            'regulatory_alert_level': 'low',
            'security_alert_level': 'low',
            'last_check': None,
            'price_alerts_sent': [],
            'top_coins_mentioned': {}
        }
    
    def _save_state(self):
        """Save crypto coverage state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    async def fetch_crypto_news(self) -> List[Dict]:
        """Fetch crypto news from all feeds."""
        all_articles = []
        
        for category, feeds in self.crypto_feeds.items():
            for feed_info in feeds:
                try:
                    cache_key = feed_info['url']
                    cached = self.feed_cache.get(cache_key)
                    if cached and (datetime.utcnow() - cached['time']).seconds < self.cache_ttl:
                        articles = cached['articles']
                    else:
                        articles = await self._fetch_feed(feed_info, category)
                        self.feed_cache[cache_key] = {
                            'articles': articles,
                            'time': datetime.utcnow()
                        }
                    
                    all_articles.extend(articles)
                    
                except Exception as e:
                    logger.warning(f"Crypto feed error ({feed_info['name']}): {e}")
                
                await asyncio.sleep(1)
        
        # Score and sort
        scored = []
        for article in all_articles:
            article['urgency_score'] = self._score_urgency(article)
            article['price_impact'] = self._score_price_impact(article)
            article['regulatory_score'] = self._score_regulatory(article)
            article['security_score'] = self._score_security(article)
            article['composite_score'] = (
                article['urgency_score'] * 0.3 +
                article['price_impact'] * 0.2 +
                article['regulatory_score'] * 0.3 +
                article['security_score'] * 0.2
            )
            scored.append(article)
        
        scored.sort(key=lambda x: x['composite_score'], reverse=True)
        return scored
    
    async def _fetch_feed(self, feed_info: Dict, category: str) -> List[Dict]:
        """Fetch a single RSS feed."""
        import aiohttp
        
        url = feed_info['url']
        name = feed_info['name']
        tier = feed_info['tier']
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
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
                    for entry in feed.entries[:8]:  # Top 8 per feed
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
            logger.warning(f"Feed timeout (15s): {name}")
            return []
        except Exception as e:
            logger.warning(f"Feed error: {name}: {e}")
            return []
    
    def _score_urgency(self, article: Dict) -> float:
        """Score article urgency (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        # Keyword matches
        keyword_count = sum(1 for kw in self.urgency_keywords if kw in text)
        score += min(keyword_count * 0.12, 0.5)
        
        # Tier bonus
        tier = article.get('tier', 2)
        score += (3 - tier) * 0.1
        
        # Breaking/Urgent in title
        if any(word in article['title'].lower() for word in ['breaking', 'urgent', 'alert', 'live', 'just']):
            score += 0.2
        
        # Recent bonus
        try:
            published = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
            hours_old = (datetime.utcnow() - published.replace(tzinfo=None)).total_seconds() / 3600
            if hours_old < 1:
                score += 0.15
            elif hours_old < 3:
                score += 0.08
            elif hours_old < 6:
                score += 0.03
        except:
            pass
        
        return min(score, 1.0)
    
    def _score_price_impact(self, article: Dict) -> float:
        """Score potential price impact (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        keyword_count = sum(1 for kw in self.price_keywords if kw in text)
        score += min(keyword_count * 0.15, 0.6)
        
        # Major coin mention
        major_coins = ['bitcoin', 'btc', 'ethereum', 'eth']
        if any(coin in text for coin in major_coins):
            score += 0.2
        
        # ETF mention (high price impact)
        if 'etf' in text:
            score += 0.15
        
        return min(score, 1.0)
    
    def _score_regulatory(self, article: Dict) -> float:
        """Score regulatory significance (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        keyword_count = sum(1 for kw in self.regulatory_keywords if kw in text)
        score += min(keyword_count * 0.2, 0.8)
        
        # SEC/CFTC direct mention
        if any(word in text for word in ['sec', 'cftc', 'gensler']):
            score += 0.15
        
        # ETF approval/denial
        if any(phrase in text for phrase in ['etf approval', 'approved', 'denied', 'rejected']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_security(self, article: Dict) -> float:
        """Score security incident severity (0-1)."""
        text = (article['title'] + ' ' + article.get('summary', '')).lower()
        
        score = 0.0
        
        keyword_count = sum(1 for kw in self.security_keywords if kw in text)
        score += min(keyword_count * 0.25, 0.9)
        
        # Exchange hack (highest severity)
        if any(word in text for word in ['binance', 'coinbase', 'kraken', 'ftx']):
            score += 0.1
        
        # Amount stolen
        import re
        amounts = re.findall(r'\$[\d,]+(?:\.\d+)?\s*(?:million|billion|m|b)?', text, re.IGNORECASE)
        if amounts:
            score += 0.1
        
        return min(score, 1.0)
    
    def is_duplicate(self, article_id: str) -> bool:
        """Check if story was already posted."""
        return article_id in self.state['posted_stories']
    
    def mark_posted(self, article_id: str):
        """Mark story as posted."""
        self.state['posted_stories'].append(article_id)
        self.state['posted_stories'] = self.state['posted_stories'][-150:]
        self._save_state()
    
    async def get_breaking_stories(self) -> List[Dict]:
        """Get urgent breaking crypto stories."""
        articles = await self.fetch_crypto_news()
        
        breaking = []
        for article in articles:
            if article['composite_score'] >= 0.65 and not self.is_duplicate(article['id']):
                breaking.append(article)
        
        return breaking[:5]  # Max 5 breaking stories
    
    def format_crypto_alert(self, article: Dict) -> str:
        """Format crypto news as alert."""
        from growth_engine import growth_engine
        
        title = article['title']
        summary = article.get('summary', '')[:280]
        source = article['source']
        link = article['link']
        category = article.get('category', 'news')
        
        # Clean summary
        import re
        summary_clean = re.sub(r'<[^>]+>', '', summary)
        
        # Determine alert type
        alert_emoji = "📰"
        alert_label = "CRYPTO NEWS"
        
        if article.get('security_score', 0) >= 0.6:
            alert_emoji = "🚨"
            alert_label = "SECURITY ALERT"
        elif article.get('regulatory_score', 0) >= 0.6:
            alert_emoji = "⚖️"
            alert_label = "REGULATORY ALERT"
        elif article.get('price_impact', 0) >= 0.6:
            alert_emoji = "📈"
            alert_label = "MARKET ALERT"
        
        # Extract tickers mentioned
        tickers = self._extract_tickers(title + ' ' + summary)
        ticker_line = ""
        if tickers:
            ticker_line = f"\n🏷 <b>Tickers:</b> {', '.join(tickers[:4])}"
        
        text = f"""{alert_emoji} <b>{alert_label}</b>

<b>{title}</b>

{summary_clean}{ticker_line}

🔗 <a href="{link}">Source: {source}</a>
⏰ <i>{self._format_time(article.get('published', ''))}</i>

{growth_engine.generate_viral_cta('breaking')}"""
        
        return text
    
    def _extract_tickers(self, text: str) -> List[str]:
        """Extract crypto tickers from text."""
        text_lower = text.lower()
        tickers = []
        
        # Major coin mappings
        coin_map = {
            'bitcoin': 'BTC', 'btc': 'BTC',
            'ethereum': 'ETH', 'eth': 'ETH',
            'solana': 'SOL', 'sol': 'SOL',
            'cardano': 'ADA', 'ada': 'ADA',
            'binance coin': 'BNB', 'bnb': 'BNB',
            'xrp': 'XRP', 'ripple': 'XRP',
            'polkadot': 'DOT', 'dot': 'DOT',
            'polygon': 'MATIC', 'matic': 'MATIC',
            'chainlink': 'LINK', 'link': 'LINK',
            'avalanche': 'AVAX', 'avax': 'AVAX',
            'near': 'NEAR',
            'arbitrum': 'ARB', 'arb': 'ARB',
            'optimism': 'OP', 'op': 'OP',
            'uniswap': 'UNI', 'uni': 'UNI',
            'aave': 'AAVE',
            'maker': 'MKR', 'mkr': 'MKR',
            'lido': 'LDO', 'ldo': 'LDO',
            'render': 'RNDR', 'rndr': 'RNDR',
            'filecoin': 'FIL', 'fil': 'FIL',
            'injective': 'INJ', 'inj': 'INJ',
            'celestia': 'TIA', 'tia': 'TIA',
        }
        
        for keyword, ticker in coin_map.items():
            if keyword in text_lower and ticker not in tickers:
                tickers.append(ticker)
        
        return tickers
    
    def _format_time(self, published: str) -> str:
        """Format published time nicely."""
        try:
            dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
            now = datetime.utcnow()
            diff = now - dt.replace(tzinfo=None)
            
            if diff.total_seconds() < 60:
                return "Just now"
            elif diff.total_seconds() < 3600:
                return f"{int(diff.total_seconds() / 60)}m ago"
            elif diff.total_seconds() < 86400:
                return f"{int(diff.total_seconds() / 3600)}h ago"
            else:
                return f"{int(diff.total_seconds() / 86400)}d ago"
        except:
            return "Recent"
    
    def get_crypto_market_summary(self) -> str:
        """Get crypto market summary for channel update."""
        intensity = self.state.get('market_intensity', 'low')
        regulatory = self.state.get('regulatory_alert_level', 'low')
        security = self.state.get('security_alert_level', 'low')
        
        emoji_map = {
            'low': '🟢', 'medium': '🟡', 'high': '🔴', 'critical': '⚫'
        }
        
        text = f"""₿ <b>Crypto Market Monitor</b>

{emoji_map.get(intensity, '⚪')} <b>Market Intensity:</b> {intensity.upper()}
{emoji_map.get(regulatory, '⚪')} <b>Regulatory:</b> {regulatory.upper()}
{emoji_map.get(security, '⚪')} <b>Security:</b> {security.upper()}

<b>Watchlist:</b>
🏦 ETFs — BTC/ETH flows, SEC decisions
🛡 Security — Exchange hacks, bridge exploits
📊 Macro — Fed rates, CPI, DXY correlation
🤖 AI x Crypto — Agent tokens, compute markets

<i>Alerts every 20 minutes during high activity</i>"""
        
        return text
    
    async def run_crypto_check(self):
        """Run crypto news check and post urgent news."""
        from publisher import publisher
        from bot import bot
        
        logger.info("Running crypto news check...")
        
        breaking = await self.get_breaking_stories()
        
        if not breaking:
            logger.info("No urgent crypto news found")
            return
        
        # Update alert levels
        avg_security = sum(a['security_score'] for a in breaking) / len(breaking)
        avg_regulatory = sum(a['regulatory_score'] for a in breaking) / len(breaking)
        avg_price = sum(a['price_impact'] for a in breaking) / len(breaking)
        
        if avg_security > 0.7:
            self.state['security_alert_level'] = 'critical'
        elif avg_security > 0.5:
            self.state['security_alert_level'] = 'high'
        elif avg_security > 0.3:
            self.state['security_alert_level'] = 'medium'
        else:
            self.state['security_alert_level'] = 'low'
        
        if avg_regulatory > 0.7:
            self.state['regulatory_alert_level'] = 'critical'
        elif avg_regulatory > 0.5:
            self.state['regulatory_alert_level'] = 'high'
        elif avg_regulatory > 0.3:
            self.state['regulatory_alert_level'] = 'medium'
        else:
            self.state['regulatory_alert_level'] = 'low'
        
        if avg_price > 0.6:
            self.state['market_intensity'] = 'high'
        elif avg_price > 0.4:
            self.state['market_intensity'] = 'medium'
        else:
            self.state['market_intensity'] = 'low'
        
        self._save_state()
        
        # Post breaking stories
        for article in breaking:
            formatted = self.format_crypto_alert(article)
            
            success = False
            try:
                success = await publisher.send_message(formatted)
            except Exception as e:
                logger.warning(f"Publisher crypto send failed: {e}")
            
            if not success:
                try:
                    if bot.bot:
                        success = await bot.send_message(formatted)
                    else:
                        await bot.initialize()
                        success = await bot.send_message(formatted)
                except Exception as e2:
                    logger.error(f"Bot crypto fallback failed: {e2}")
            
            if success:
                self.mark_posted(article['id'])
                logger.info(f"Posted crypto alert: {article['title'][:50]}...")
            else:
                logger.error(f"Failed to post crypto alert: {article['title'][:50]}...")
            
            await asyncio.sleep(20)

# Singleton instance
crypto_monitor = CryptoNewsMonitor()
