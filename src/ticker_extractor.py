import json
import re
from typing import List, Dict, Set
from config import logger

class TickerExtractor:
    """Extracts stock tickers and crypto tokens from text."""
    
    def __init__(self):
        # Common stock tickers (major ones to reduce false positives)
        self.common_tickers = {
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ORCL', 'IBM', 'UBER', 'LYFT', 'COIN',
            'DIS', 'NKE', 'V', 'MA', 'JPM', 'BAC', 'GS', 'MS', 'WFC',
            'XOM', 'CVX', 'OXY', 'COP', 'BP', 'SHEL',
            'PFE', 'JNJ', 'MRNA', 'BNTX', 'AZN', 'GILD',
            'BA', 'LMT', 'RTX', 'NOC', 'GD',
            'T', 'VZ', 'TMUS', 'CMCSA',
            'KO', 'PEP', 'PG', 'WMT', 'TGT', 'COST',
            'BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'MATIC',
            'XRP', 'DOGE', 'SHIB', 'LTC', 'BCH', 'LINK',
            'UNI', 'AAVE', 'MKR', 'SNX', 'COMP',
            'ATOM', 'NEAR', 'ALGO', 'FTM', 'ONE',
            'SAND', 'MANA', 'AXS', 'GALA', 'ENJ',
            'CHZ', 'FLOW', 'IMX', 'RNDR', 'GRT',
            'OP', 'ARB', 'ZKS', 'STARK',
            'QNT', 'HBAR', 'IOTA', 'XLM', 'XMR',
            'ETC', 'BSV', 'TRX', 'EOS', 'XTZ',
            'VET', 'FIL', 'THETA', 'CAKE', 'SUSHI',
            'CRV', 'YFI', 'BAL', 'LDO', 'RPL',
            'FXS', 'CVX', 'SPELL', 'MIM', 'FRAX',
            'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD',
            'GOLD', 'SILVER', 'OIL', 'NG', 'CL',
            'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
            'VOO', 'VEA', 'VWO', 'BND', 'AGG',
            'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ',
            'XLF', 'XLK', 'XLE', 'XLU', 'XLI',
            'XLP', 'XLB', 'XRT', 'XBI', 'XHB',
            'SOXX', 'SMH', 'BOTZ', 'ROBO', 'IGV',
            'LIT', 'URA', 'URNM', 'TAN', 'FAN',
            'ESPO', 'NERD', 'BETZ', 'YOLO', 'MSOS',
            'WGMI', 'CRPT', 'BITS', 'DAPP', 'LEGR',
        }
        
        # Crypto-specific patterns
        self.crypto_patterns = [
            r'\$([A-Z]{2,10})\b',  # $BTC, $ETH
            r'#([A-Z]{2,10})\b',   # #BTC, #ETH
        ]
        
    def extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers and crypto tokens from text."""
        if not text:
            return []
            
        found = set()
        
        # Uppercase text for matching
        text_upper = text.upper()
        
        # Check against common tickers
        for ticker in self.common_tickers:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(ticker) + r'\b'
            if re.search(pattern, text_upper):
                found.add(ticker)
                
        # Check $ and # patterns
        for pattern in self.crypto_patterns:
            matches = re.findall(pattern, text_upper)
            for match in matches:
                if match.isalpha() and len(match) <= 10:
                    found.add(match)
                    
        # Extract potential tickers from context
        # Look for patterns like "(TICKER)" or "TICKER stock" or "TICKER price"
        context_patterns = [
            r'\(([A-Z]{1,5})\)',  # (AAPL)
            r'([A-Z]{1,5})\s+(?:stock|shares|price|trading)',  # AAPL stock
            r'(?:ticker|symbol)\s+([A-Z]{1,5})',  # ticker AAPL
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, text_upper)
            for match in matches:
                if match.isalpha() and 1 <= len(match) <= 5:
                    found.add(match)
                    
        return sorted(list(found))
        
    def extract_from_article(self, article: Dict) -> List[str]:
        """Extract tickers from article."""
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        return self.extract_tickers(text)
        
    def add_custom_ticker(self, ticker: str):
        """Add a custom ticker to the list."""
        self.common_tickers.add(ticker.upper())
        logger.info(f"Added custom ticker: {ticker.upper()}")
        
    def get_ticker_info(self, ticker: str) -> Dict:
        """Get basic info about a ticker."""
        ticker = ticker.upper()
        
        # Categorize
        crypto_tickers = {
            'BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'MATIC',
            'XRP', 'DOGE', 'SHIB', 'LTC', 'BCH', 'LINK',
            'UNI', 'AAVE', 'MKR', 'SNX', 'COMP',
            'ATOM', 'NEAR', 'ALGO', 'FTM', 'ONE',
            'SAND', 'MANA', 'AXS', 'GALA', 'ENJ',
            'CHZ', 'FLOW', 'IMX', 'RNDR', 'GRT',
            'OP', 'ARB', 'ZKS', 'STARK',
            'QNT', 'HBAR', 'IOTA', 'XLM', 'XMR',
            'ETC', 'BSV', 'TRX', 'EOS', 'XTZ',
            'VET', 'FIL', 'THETA', 'CAKE', 'SUSHI',
            'CRV', 'YFI', 'BAL', 'LDO', 'RPL',
            'FXS', 'CVX', 'SPELL', 'MIM', 'FRAX',
            'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD',
        }
        
        etf_tickers = {
            'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO',
            'BND', 'AGG', 'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ',
            'XLF', 'XLK', 'XLE', 'XLU', 'XLI', 'XLP', 'XLB', 'XRT',
            'XBI', 'XHB', 'SOXX', 'SMH', 'BOTZ', 'ROBO', 'IGV',
            'LIT', 'URA', 'URNM', 'TAN', 'FAN', 'ESPO', 'NERD',
            'BETZ', 'YOLO', 'MSOS', 'WGMI', 'CRPT', 'BITS', 'DAPP', 'LEGR',
        }
        
        commodity_tickers = {'GOLD', 'SILVER', 'OIL', 'NG', 'CL'}
        
        if ticker in crypto_tickers:
            category = "Crypto"
        elif ticker in etf_tickers:
            category = "ETF"
        elif ticker in commodity_tickers:
            category = "Commodity"
        else:
            category = "Stock"
            
        return {
            'ticker': ticker,
            'category': category,
            'is_crypto': ticker in crypto_tickers,
            'is_etf': ticker in etf_tickers,
        }

# Singleton instance
ticker_extractor = TickerExtractor()
