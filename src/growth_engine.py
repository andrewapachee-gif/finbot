import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from config import logger, DATA_DIR

class GrowthEngine:
    """Viral mechanics and engagement optimization for channel growth."""
    
    def __init__(self):
        self.state_file = DATA_DIR / "growth_state.json"
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load growth state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'viral_posts_count': 0,
            'engagement_polls_sent': 0,
            'forward_ctas_used': 0,
            'exclusive_teasers_sent': 0,
            'last_viral_post': None,
            'top_performing_format': None,
            'subscriber_milestones': []
        }
        
    def _save_state(self):
        """Save growth state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def generate_viral_cta(self, article_type: str = 'article') -> str:
        """Generate a forward-trigger call-to-action."""
        ctas = {
            'article': [
                "\n\n📢 <i>Forward this to someone who needs to see it</i>",
                "\n\n💡 <i>Know a trader who'd find this useful? Share it.</i>",
                "\n\n🎯 <i>This affects your portfolio. Share with your circle.</i>",
                "\n\n📈 <i>Tag someone who trades this ticker</i>",
            ],
            'breaking': [
                "\n\n🚨 <i>Breaking — forward to your trading group NOW</i>",
                "\n\n⚡ <i>Time-sensitive. Share before the market reacts.</i>",
                "\n\n📲 <i>Your trading buddies need this. Forward it.</i>",
            ],
            'clip': [
                "\n\n🎬 <i>Watch this, then forward to someone who trades</i>",
                "\n\n👀 <i>This clip breaks it down perfectly. Share it.</i>",
            ],
            'war': [
                "\n\n🌍 <i>Geopolitical alert — forward to your network</i>",
                "\n\n⚠️ <i>This impacts global markets. Share widely.</i>",
            ]
        }
        
        import random
        cta_list = ctas.get(article_type, ctas['article'])
        return random.choice(cta_list)
    
    def generate_engagement_poll(self, article: Dict) -> Optional[Dict]:
        """Generate engagement poll for high-relevance articles."""
        tickers = article.get('ai_analysis', {}).get('tickers', [])
        sentiment = article.get('ai_analysis', {}).get('sentiment', 'neutral')
        
        if not tickers:
            return None
            
        ticker = tickers[0]
        
        polls = [
            {
                'question': f"What's your move on {ticker}?",
                'options': ["🟢 Buy", "🔴 Sell", "⚪ Hold", "📊 Watch"]
            },
            {
                'question': f"{ticker} — where by Friday?",
                'options': ["📈 Up 5%+", "📉 Down 5%+", "➡️ Flat", "🎲 Who knows"]
            },
            {
                'question': f"This news makes {ticker}...",
                'options': ["🚀 Bullish", "🐻 Bearish", "🤷 Neutral", "💣 Volatile"]
            }
        ]
        
        import random
        poll = random.choice(polls)
        self.state['engagement_polls_sent'] += 1
        self._save_state()
        return poll
    
    def generate_exclusive_teaser(self, article: Dict) -> str:
        """Generate exclusive content teaser."""
        teasers = [
            "\n\n🔒 <i>Full analysis + 3 more tickers in the channel. Stay tuned.</i>",
            "\n\n👁‍🗨 <i>Deep dive on this dropping later today. Only here.</i>",
            "\n\n📊 <i>Full sector breakdown + price targets — next post.</i>",
        ]
        
        import random
        teaser = random.choice(teasers)
        self.state['exclusive_teasers_sent'] += 1
        self._save_state()
        return teaser
    
    def format_viral_post(self, article: Dict, article_type: str = 'article') -> str:
        """Format article with viral optimization."""
        from publisher import publisher
        
        # Get base formatted text
        base_text = publisher.format_article(article)
        
        # Add viral CTA
        cta = self.generate_viral_cta(article_type)
        
        # Add exclusive teaser for high-relevance articles
        analysis = article.get('ai_analysis', {})
        relevance = analysis.get('relevance', 0)
        
        if relevance >= 0.8:
            teaser = self.generate_exclusive_teaser(article)
            viral_text = base_text + cta + teaser
        else:
            viral_text = base_text + cta
        
        self.state['forward_ctas_used'] += 1
        self._save_state()
        
        return viral_text
    
    def format_war_post(self, article: Dict) -> str:
        """Format war/geopolitical news with urgency."""
        title = article['title']
        summary = article.get('summary', '')[:300]
        source = article['source']
        link = article['link']
        
        # Market impact analysis
        impact = self._analyze_market_impact(article)
        
        text = f"""🚨 <b>BREAKING — URGENT</b>

<b>{title}</b>

{summary}

{impact}

⏰ <i>Developing story — updates as they come</i>
🔗 <a href="{link}">Source: {source}</a>

⚠️ <i>This affects markets. Forward to your trading circle.</i>"""
        
        return text
    
    def _analyze_market_impact(self, article: Dict) -> str:
        """Analyze market impact of geopolitical news."""
        title_lower = article['title'].lower()
        summary_lower = article.get('summary', '').lower()
        text = title_lower + ' ' + summary_lower
        
        impacts = []
        
        # Oil impact
        if any(word in text for word in ['oil', 'crude', 'petroleum', 'opec', 'energy']):
            impacts.append("🛢 <b>Oil:</b> Expect volatility — watch $USO, $XLE")
        
        # Gold/safe haven
        if any(word in text for word in ['war', 'attack', 'missile', 'strike', 'conflict']):
            impacts.append("🥇 <b>Safe Haven:</b> Gold $GLD and bonds likely bid")
        
        # Defense stocks
        if any(word in text for word in ['military', 'defense', 'weapon', 'iran', 'israel']):
            impacts.append("🛡 <b>Defense:</b> $LMT, $RTX, $NOC on watch")
        
        # Market volatility
        if any(word in text for word in ['escalation', 'retaliation', 'sanctions']):
            impacts.append("📉 <b>VIX:</b> Expect spike — hedges get expensive")
        
        if not impacts:
            impacts.append("📊 <b>Markets:</b> Monitor futures for gap reaction")
        
        return "\n".join(impacts)
    
    def record_milestone(self, subscriber_count: int):
        """Record subscriber milestone."""
        milestones = [1000, 5000, 10000, 25000, 50000, 100000]
        
        for milestone in milestones:
            if subscriber_count >= milestone and milestone not in self.state['subscriber_milestones']:
                self.state['subscriber_milestones'].append(milestone)
                self._save_state()
                return milestone
        
        return None
    
    def get_growth_stats(self) -> Dict:
        """Get growth engine statistics."""
        return {
            'viral_posts_count': self.state['viral_posts_count'],
            'engagement_polls_sent': self.state['engagement_polls_sent'],
            'forward_ctas_used': self.state['forward_ctas_used'],
            'exclusive_teasers_sent': self.state['exclusive_teasers_sent'],
            'subscriber_milestones': self.state['subscriber_milestones'],
            'top_performing_format': self.state.get('top_performing_format', 'Not yet determined')
        }

# Singleton instance
growth_engine = GrowthEngine()
