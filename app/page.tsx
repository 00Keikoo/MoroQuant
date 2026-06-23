'use client';

import { useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TradingChart from '@/components/charts/TradingChart';
import NewsFeed from '@/components/news/NewsFeed';
import MarketStats from '@/components/indicators/MarketStats';
import MarketAnalysis from '@/components/trading/MarketAnalysis';
import HyperliquidPanel from '@/components/trading/HyperliquidPanel';
import OpenPositionsPanel from '@/components/dashboard/OpenPositionsPanel';
import ModelHealthPanel from '@/components/dashboard/ModelHealthPanel';
import MarketRegimesPanel from '@/components/dashboard/MarketRegimesPanel';
import { useMarketStore } from '@/lib/stores/marketStore';
import { useNewsStore } from '@/lib/stores/newsStore';
import { useHyperliquidStore } from '@/lib/stores/hyperliquidStore';
import { BinanceWebSocket, TOP_FUTURES_PAIRS, fetchCandlesticks, fetchFundingRate, fetchOpenInterest, fetchLongShortRatio } from '@/lib/api/binance';
import { fetchNews } from '@/lib/api/news';
import { fetchHyperliquidMarkets } from '@/lib/api/hyperliquid';
import { calculateIndicators } from '@/lib/utils/indicators';

export default function Home() {
  const { updatePair, selectedPair, timeframe, updateCandlesticks, updateIndicators } = useMarketStore();
  const { setNews } = useNewsStore();
  const { setMarkets, setLoading: setHyperliquidLoading } = useHyperliquidStore();

  useEffect(() => {
    const ws = new BinanceWebSocket(
      (symbol, data) => {
        updatePair(symbol, data);
      },
      (symbol, orderbook) => {
        // Orderbook updates handled here if needed
      }
    );

    ws.connect(TOP_FUTURES_PAIRS);

    const fetchAdditionalData = async () => {
      for (const symbol of TOP_FUTURES_PAIRS.slice(0, 5)) {
        try {
          const [fundingRate, openInterest, longShortRatio] = await Promise.all([
            fetchFundingRate(symbol),
            fetchOpenInterest(symbol),
            fetchLongShortRatio(symbol),
          ]);

          updatePair(symbol, {
            fundingRate,
            openInterest,
            longShortRatio,
          });
        } catch (error) {
          console.error(`Error fetching additional data for ${symbol}:`, error);
        }
      }
    };

    fetchAdditionalData();
    const additionalDataInterval = setInterval(fetchAdditionalData, 60000);

    return () => {
      ws.disconnect();
      clearInterval(additionalDataInterval);
    };
  }, [updatePair]);

  useEffect(() => {
    const loadCandlesticks = async () => {
      try {
        const candles = await fetchCandlesticks(selectedPair, timeframe);
        updateCandlesticks(selectedPair, candles);

        const indicators = calculateIndicators(candles);
        updateIndicators(selectedPair, indicators);
      } catch (error) {
        console.error('Error loading candlesticks:', error);
      }
    };

    loadCandlesticks();
  }, [selectedPair, timeframe, updateCandlesticks, updateIndicators]);

  useEffect(() => {
    const loadNews = async () => {
      try {
        const newsItems = await fetchNews();
        setNews(newsItems);
      } catch (error) {
        console.error('Error loading news:', error);
      }
    };

    loadNews();
    const newsInterval = setInterval(loadNews, 60000);

    return () => clearInterval(newsInterval);
  }, [setNews]);

  useEffect(() => {
    const loadHyperliquid = async () => {
      setHyperliquidLoading(true);
      try {
        const markets = await fetchHyperliquidMarkets();
        setMarkets(markets);
      } catch (error) {
        console.error('Error loading Hyperliquid markets:', error);
      } finally {
        setHyperliquidLoading(false);
      }
    };

    loadHyperliquid();
    const hyperliquidInterval = setInterval(loadHyperliquid, 30000);

    return () => clearInterval(hyperliquidInterval);
  }, [setMarkets, setHyperliquidLoading]);

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />

      {/* Main scrollable content */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Top row: Chart + Analysis + Hyperliquid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <TradingChart />
            </div>
            <div className="flex flex-col gap-4">
              <MarketAnalysis />
              <HyperliquidPanel />
            </div>
          </div>

          {/* Market stats — full width */}
          <MarketStats />

          {/* Live open positions — full width */}
          <OpenPositionsPanel />

          {/* Model health + Market regimes — 50/50 split */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ModelHealthPanel />
            <MarketRegimesPanel />
          </div>
        </main>

        {/* News feed — sidebar, hidden on mobile/tablet */}
        <NewsFeed className="hidden lg:flex w-96 shrink-0 flex-col" />
      </div>
    </div>
  );
}
