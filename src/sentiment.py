import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from config import logger
from textblob import TextBlob

class SentimentAnalyzer:
    """Analyzes sentiment of financial text."""
    
    def __init__(self):
        # Financial keywords for context-aware sentiment
        self.bullish_keywords = {
            'surge', 'rally', 'soar', 'jump', 'gain', 'rise', 'bull', 'bullish',
            'breakout', 'moon', ' ATH', 'all-time high', 'record high', 'outperform',
            'beat', 'exceed', 'strong', 'growth', 'expansion', 'upgrade', 'buy',
            'overweight', 'outperform', 'positive', 'optimistic', 'confident',
            'momentum', 'rally', 'rebound', 'recovery', 'boom', 'prosper',
            'thrive', 'flourish', 'excel', 'triumph', 'victory', 'success',
            'profit', 'earnings beat', 'revenue growth', 'margin expansion',
            'guidance raise', 'price target increase', 'upgrade', 'initiate buy',
        }
        
        self.bearish_keywords = {
            'crash', 'plunge', 'tumble', 'drop', 'fall', 'bear', 'bearish',
            'dump', 'correction', 'recession', 'decline', 'sell', 'underweight',
            'underperform', 'negative', 'pessimistic', 'worried', 'concern',
            'risk', 'threat', 'danger', 'warning', 'caution', 'alert',
            'downturn', 'slump', 'crisis', 'collapse', 'meltdown', 'panic',
            'loss', 'miss', 'guidance cut', 'layoff', 'firing', 'bankruptcy',
            'default', 'downgrade', 'sell-off', 'liquidation', 'margin call',
            'support break', 'death cross', 'oversold', 'capitulation',
        }
        
        self.neutral_keywords = {
            'flat', 'steady', 'stable', 'unchanged', 'hold', 'neutral',
            'sideways', 'consolidation', 'range-bound', 'wait', 'see',
            'mixed', 'uncertain', 'unclear', 'pending', 'awaiting',
            'monitor', 'watch', 'observe', 'track', 'follow',
        }
        
    def analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of text."""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.0}
            
        text_lower = text.lower()
        
        # Count keyword matches
        bullish_count = sum(1 for word in self.bullish_keywords if word in text_lower)
        bearish_count = sum(1 for word in self.bearish_keywords if word in text_lower)
        neutral_count = sum(1 for word in self.neutral_keywords if word in text_lower)
        
        # Use TextBlob as secondary signal
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        
        # Combine signals
        keyword_score = (bullish_count - bearish_count) / max(bullish_count + bearish_count + neutral_count, 1)
        combined_score = (keyword_score * 0.7) + (textblob_polarity * 0.3)
        
        # Determine sentiment
        if combined_score > 0.1:
            sentiment = 'bullish'
        elif combined_score < -0.1:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
            
        # Calculate confidence
        total_signals = bullish_count + bearish_count + neutral_count
        confidence = min(total_signals / 5, 1.0)  # Max confidence at 5+ signals
        
        return {
            'sentiment': sentiment,
            'score': round(combined_score, 3),
            'confidence': round(confidence, 3),
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'neutral_signals': neutral_count,
            'textblob_score': round(textblob_polarity, 3)
        }
        
    def analyze_article(self, article: Dict) -> Dict:
        """Analyze sentiment of an article."""
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        return self.analyze_text(text)
        
    def get_market_mood(self, articles: List[Dict]) -> str:
        """Get overall market mood from multiple articles."""
        if not articles:
            return 'neutral'
            
        sentiments = [self.analyze_article(a) for a in articles]
        
        bullish = sum(1 for s in sentiments if s['sentiment'] == 'bullish')
        bearish = sum(1 for s in sentiments if s['sentiment'] == 'bearish')
        neutral = sum(1 for s in sentiments if s['sentiment'] == 'neutral')
        
        total = len(sentiments)
        
        if bullish / total > 0.5:
            return 'bullish'
        elif bearish / total > 0.5:
            return 'bearish'
        else:
            return 'neutral'
            
    def format_sentiment_emoji(self, sentiment: str) -> str:
        """Get emoji for sentiment."""
        return {
            'bullish': '🟢',
            'bearish': '🔴',
            'neutral': '⚪'
        }.get(sentiment, '⚪')
        
    def add_sentiment_context(self, article: Dict) -> Dict:
        """Add sentiment analysis to article."""
        sentiment = self.analyze_article(article)
        article['sentiment_analysis'] = sentiment
        return article

# Singleton instance
sentiment_analyzer = SentimentAnalyzer()