'use client';

import { useEffect } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TradingChart from '@/components/charts/TradingChart';
import NewsFeed from '@/components/news/NewsFeed';
import MarketStats from '@/components/indicators/MarketStats';
import MarketAnalysis from '@/components/trading/MarketAnalysis';
import HyperliquidPanel from '@/components/trading/HyperliquidPanel';
import { useMarketStore } from '@/lib/stores/marketStore';
import { useNewsStore } from '@/lib/stores/newsStore';
import { useAnalysisStore } from '@/lib/stores/analysisStore';
import { useHyperliquidStore } from '@/lib/stores/hyperliquidStore';
import { BinanceWebSocket, TOP_FUTURES_PAIRS, fetchCandlesticks, fetchFundingRate, fetchOpenInterest, fetchLongShortRatio } from '@/lib/api/binance';
import { fetchNews } from '@/lib/api/news';
import { generateNewsAnalysis, generateMarketAnalysis } from '@/lib/api/ai-analysis';
import { fetchHyperliquidMarkets } from '@/lib/api/hyperliquid';
import { calculateIndicators } from '@/lib/utils/indicators';

export default function Home() {
  const { updatePair, selectedPair, timeframe, updateCandlesticks, updateIndicators, pairs } = useMarketStore();
  const { setNews, news, updateNewsAnalysis } = useNewsStore();
  const { setAnalysis, setLoading: setAnalysisLoading } = useAnalysisStore();
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

        for (const item of newsItems.slice(0, 5)) {
          try {
            const analysis = await generateNewsAnalysis(item);
            updateNewsAnalysis(item.id, analysis);
          } catch (error) {
            console.error('Error generating news analysis:', error);
          }
        }
      } catch (error) {
        console.error('Error loading news:', error);
      }
    };

    loadNews();
    const newsInterval = setInterval(loadNews, 60000);

    return () => clearInterval(newsInterval);
  }, [setNews, updateNewsAnalysis]);

  useEffect(() => {
    const loadMarketAnalysis = async () => {
      if (pairs.size === 0 || news.length === 0) return;

      setAnalysisLoading(true);
      try {
        const analysis = await generateMarketAnalysis(pairs, news);
        setAnalysis(analysis);
      } catch (error) {
        console.error('Error generating market analysis:', error);
      } finally {
        setAnalysisLoading(false);
      }
    };

    const timer = setTimeout(loadMarketAnalysis, 2000);
    const analysisInterval = setInterval(loadMarketAnalysis, 300000);

    return () => {
      clearTimeout(timer);
      clearInterval(analysisInterval);
    };
  }, [pairs, news, setAnalysis, setAnalysisLoading]);

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

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          <div className="flex-1 flex flex-col gap-4 overflow-hidden">
            <TradingChart />
            <MarketStats />
          </div>

          <div className="w-96 flex flex-col gap-4 overflow-y-auto">
            <MarketAnalysis />
            <HyperliquidPanel />
          </div>
        </div>
      </div>

      <NewsFeed />
    </div>
  );
}
