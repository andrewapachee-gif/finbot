import os
import json
import logging
from typing import Dict, List, Optional
from config import (
    AI_PROVIDER, AI_MODEL, OPENAI_API_KEY, 
    ANTHROPIC_API_KEY, MISTRAL_API_KEY, 
    MIN_ARTICLE_RELEVANCE, logger
)

class AIFilter:
    """Filters and rewrites content using AI."""
    
    def __init__(self):
        self.provider = AI_PROVIDER
        self.model = AI_MODEL
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Initialize AI client based on provider."""
        logger.info(f"Initializing AI client: provider={self.provider}, model={self.model}")
        
        if self.provider == "none":
            logger.warning("AI provider set to 'none'. Content filtering disabled.")
            return
            
        if self.provider == "openai" and OPENAI_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        elif self.provider == "anthropic" and ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        elif self.provider == "mistral" and MISTRAL_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(
                    api_key=MISTRAL_API_KEY,
                    base_url="https://api.mistral.ai/v1"
                )
                logger.info("Mistral client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mistral client: {e}")
                self.client = None
        else:
            logger.warning(f"No AI provider configured (provider={self.provider}, keys available: openai={bool(OPENAI_API_KEY)}, anthropic={bool(ANTHROPIC_API_KEY)}, mistral={bool(MISTRAL_API_KEY)}). Content filtering disabled.")
            
    def _build_prompt(self, article: Dict) -> str:
        """Build prompt for AI analysis."""
        return f"""Analyze this financial news article and determine its relevance and quality.

Title: {article['title']}
Source: {article['source']} (Tier {article['tier']})
Summary: {article['summary']}

Please provide:
1. Relevance score (0.0-1.0) - How relevant is this to finance/investing/AI?
2. Quality score (0.0-1.0) - Is this high-quality, factual content?
3. Sentiment - Bullish, Bearish, or Neutral
4. Key tickers/assets mentioned (if any)
5. Rewrite - A concise, engaging summary (max 200 words) suitable for Telegram
6. Breaking news - Is this time-sensitive breaking news? (true/false)

Respond in JSON format:
{{
    "relevance": 0.0,
    "quality": 0.0,
    "sentiment": "neutral",
    "tickers": ["TICKER1", "TICKER2"],
    "rewrite": "concise summary here",
    "breaking": false,
    "reasoning": "brief explanation"
}}"""

    async def analyze_article(self, article: Dict) -> Optional[Dict]:
        """Analyze a single article with AI."""
        if not self.client:
            logger.warning(f"AI client not available, skipping analysis for: {article.get('title', 'Unknown')[:50]}...")
            return None
            
        try:
            prompt = self._build_prompt(article)
            
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            else:
                # OpenAI / Mistral
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                    temperature=0.3
                )
                content = response.choices[0].message.content
                
            # Parse JSON from response
            # Sometimes the AI wraps it in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            analysis = json.loads(content)
            
            # Merge with original article data
            result = {
                **article,
                "ai_analysis": analysis,
                "passed_filter": (
                    analysis.get("relevance", 0) >= MIN_ARTICLE_RELEVANCE and
                    analysis.get("quality", 0) >= 0.5
                )
            }
            
            logger.info(
                f"Article '{article['title'][:50]}...' - "
                f"Relevance: {analysis.get('relevance', 0):.2f}, "
                f"Sentiment: {analysis.get('sentiment', 'unknown')}"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
            
    async def analyze_batch(self, articles: List[Dict]) -> List[Dict]:
        """Analyze multiple articles."""
        results = []
        
        for article in articles:
            analysis = await self.analyze_article(article)
            if analysis:
                results.append(analysis)
                
        # Sort by relevance score
        results.sort(
            key=lambda x: x.get("ai_analysis", {}).get("relevance", 0),
            reverse=True
        )
        
        return results
        
    def generate_daily_digest(self, articles: List[Dict]) -> str:
        """Generate a daily digest from top articles."""
        if not self.client:
            return "Daily digest (AI unavailable)"
            
        # Prepare article summaries
        summaries = []
        for article in articles[:5]:
            rewrite = article.get("ai_analysis", {}).get("rewrite", article["summary"])
            sentiment = article.get("ai_analysis", {}).get("sentiment", "neutral")
            tickers = article.get("ai_analysis", {}).get("tickers", [])
            
            summaries.append(f"""
- {article['title']}
  {rewrite[:150]}...
  Sentiment: {sentiment} | Tickers: {', '.join(tickers) if tickers else 'None'}
""")
        
        prompt = f"""Create an engaging daily finance digest for Telegram based on these articles:

{''.join(summaries)}

Write a concise, engaging summary (max 400 words) that:
1. Highlights the most important stories
2. Notes key market sentiment
3. Mentions notable tickers/assets
4. Ends with a brief "Market Pulse" section

Format with Telegram HTML (use <b> for bold, <i> for italic).
Keep it punchy and readable."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1500,
                    temperature=0.5
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate digest: {e}")
            return "Daily digest generation failed."
            
    def generate_weekly_roundup(self, articles: List[Dict]) -> str:
        """Generate a weekly market roundup."""
        if not self.client:
            return "Weekly roundup (AI unavailable)"
            
        # Aggregate sentiment and top stories
        bullish = sum(1 for a in articles if a.get("ai_analysis", {}).get("sentiment") == "bullish")
        bearish = sum(1 for a in articles if a.get("ai_analysis", {}).get("sentiment") == "bearish")
        
        prompt = f"""Create a weekly market roundup based on:
- Total articles: {len(articles)}
- Bullish sentiment: {bullish}
- Bearish sentiment: {bearish}
- Neutral: {len(articles) - bullish - bearish}

Write an engaging weekly summary (max 500 words) with:
1. "Week in Review" - key themes
2. "Bull Case" - positive developments
3. "Bear Case" - risks and concerns
4. "Watch List" - what to watch next week

Use Telegram HTML formatting."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.5
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate weekly roundup: {e}")
            return "Weekly roundup generation failed."

# Singleton instance
ai_filter = AIFilter()
