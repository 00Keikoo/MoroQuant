"""Crypto price fetching service - Binance Futures API."""

import requests
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CryptoPriceService:
    """On-demand crypto price fetching from Binance Futures API."""

    def __init__(self, symbols: list[str]):
        self.symbols = symbols
        self.price_cache: Dict[str, Dict] = {}

    def fetch_price(self, symbol: str) -> Optional[float]:
        """Fetch single price from Binance Futures API."""
        try:
            url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return float(data['price'])

            return None
        except Exception as e:
            logger.debug(f"Error fetching price for {symbol}: {e}")
            return None

    def fetch_and_cache(self, symbol: str) -> Optional[Dict]:
        """Fetch price and update cache."""
        price = self.fetch_price(symbol)
        if price is not None:
            self.price_cache[symbol] = {
                'price': price,
                'timestamp': datetime.now().isoformat(),
                'source': 'binance_futures',
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

            if age_seconds < 30:
                return cached

        return self.fetch_and_cache(symbol)


_crypto_service: Optional[CryptoPriceService] = None

def get_crypto_service() -> CryptoPriceService:
    """Get or create global crypto price service."""
    global _crypto_service
    if _crypto_service is None:
        symbols = [
            'BTCUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ZECUSDT',
            'SUIUSDT', 'ADAUSDT', 'ETHUSDT', 'HYPEUSDT', 'LINKUSDT', 'LTCUSDT'
        ]
        _crypto_service = CryptoPriceService(symbols)
    return _crypto_service
