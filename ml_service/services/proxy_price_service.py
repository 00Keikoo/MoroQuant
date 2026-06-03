"""Proxy/ETF price fetching service - Yahoo Finance API."""

from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProxyPriceService:
    """On-demand ETF price fetching from Yahoo Finance."""

    def __init__(self, symbols: Dict[str, str]):
        self.symbols = symbols
        self.price_cache: Dict[str, Dict] = {}

    def fetch_price(self, ticker: str) -> Optional[float]:
        """Fetch single price from Yahoo Finance."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d', interval='1m')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"Error fetching price for {ticker}: {e}")
        return None

    def fetch_and_cache(self, symbol: str) -> Optional[Dict]:
        """Fetch price and update cache."""
        if symbol not in self.symbols:
            return None

        ticker = self.symbols[symbol]
        price = self.fetch_price(ticker)

        if price is not None:
            self.price_cache[symbol] = {
                'price': price,
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker,
                'source': 'yfinance',
                'live': True
            }
            return self.price_cache[symbol]
        return None

    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get price for symbol, fetching fresh if needed."""
        cached = self.price_cache.get(symbol)

        if cached:
            cached_time = datetime.fromisoformat(cached['timestamp'])
            age_seconds = (datetime.now() - cached_time).total_seconds()

            if age_seconds < 60:
                return cached

        return self.fetch_and_cache(symbol)


_proxy_service: Optional[ProxyPriceService] = None

def get_proxy_service() -> ProxyPriceService:
    """Get or create global proxy price service."""
    global _proxy_service
    if _proxy_service is None:
        symbols = {
            'ES_proxy': 'SPY',
            'NQ_proxy': 'QQQ',
            'GC_proxy': 'GLD',
            'CL_proxy': 'USO',
            'ZB_proxy': 'TLT'
        }
        _proxy_service = ProxyPriceService(symbols)
    return _proxy_service
