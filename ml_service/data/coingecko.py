"""CoinGecko market dominance data fetcher."""

import time
import requests
from typing import Optional, Dict
import pandas as pd

from utils.logger import get_logger
from data.database import get_database

logger = get_logger()


class CoinGeckoFetcher:
    """Fetch market dominance data from CoinGecko API."""

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.db = get_database()

    def fetch_market_dominance(self) -> Optional[Dict]:
        """
        Fetch global market data including BTC and stablecoin dominance.

        Returns:
            Dictionary with btc_dominance, usdt_dominance, total_market_cap
            or None if fetch fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/global",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            global_data = data.get('data', {})

            btc_percentage = global_data.get('market_cap_percentage', {}).get('btc', 0)
            total_market_cap = global_data.get('total_market_cap', {}).get('usd', 0)

            stablecoin_percentage = 0
            market_cap_percentage = global_data.get('market_cap_percentage', {})

            for coin in ['usdt', 'usdc', 'busd', 'dai', 'tusd']:
                stablecoin_percentage += market_cap_percentage.get(coin, 0)

            result = {
                'btc_dominance': btc_percentage,
                'usdt_dominance': stablecoin_percentage,
                'total_market_cap': total_market_cap,
                'timestamp': int(time.time())
            }

            logger.info(
                f"Fetched market dominance: BTC={btc_percentage:.2f}%, "
                f"Stablecoin={stablecoin_percentage:.2f}%, "
                f"Total MCap=${total_market_cap/1e9:.2f}B"
            )

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch CoinGecko data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing CoinGecko data: {e}")
            return None

    def store_market_dominance(self, data: Dict) -> bool:
        """
        Store market dominance data in database.

        Args:
            data: Dictionary with btc_dominance, usdt_dominance, total_market_cap, timestamp

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO market_dominance
                    (timestamp, btc_dominance, usdt_dominance, total_market_cap)
                    VALUES (?, ?, ?, ?)
                """, (
                    data['timestamp'],
                    data['btc_dominance'],
                    data['usdt_dominance'],
                    data['total_market_cap']
                ))

                conn.commit()
                logger.info(f"Stored market dominance data for timestamp {data['timestamp']}")
                return True

        except Exception as e:
            logger.error(f"Failed to store market dominance: {e}")
            return False

    def fetch_and_store(self) -> bool:
        """
        Fetch market dominance from CoinGecko and store in database.

        Returns:
            True if successful, False otherwise
        """
        data = self.fetch_market_dominance()
        if data is None:
            return False

        return self.store_market_dominance(data)

    def get_dominance_dataframe(
        self,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Retrieve market dominance data as DataFrame.

        Args:
            start_timestamp: Optional start timestamp filter
            end_timestamp: Optional end timestamp filter

        Returns:
            DataFrame with columns: timestamp, btc_dominance, usdt_dominance, total_market_cap
        """
        try:
            with self.db.get_connection() as conn:
                query = """
                    SELECT timestamp, btc_dominance, usdt_dominance, total_market_cap
                    FROM market_dominance
                    WHERE 1=1
                """
                params = []

                if start_timestamp:
                    query += " AND timestamp >= ?"
                    params.append(start_timestamp)

                if end_timestamp:
                    query += " AND timestamp <= ?"
                    params.append(end_timestamp)

                query += " ORDER BY timestamp ASC"

                df = pd.read_sql_query(query, conn, params=params)
                return df

        except Exception as e:
            logger.error(f"Failed to retrieve market dominance: {e}")
            return pd.DataFrame()


def get_coingecko_fetcher() -> CoinGeckoFetcher:
    """Get CoinGecko fetcher instance."""
    if not hasattr(get_coingecko_fetcher, "_fetcher"):
        get_coingecko_fetcher._fetcher = CoinGeckoFetcher()
    return get_coingecko_fetcher._fetcher
