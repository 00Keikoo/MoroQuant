import { MarketAnalysis, NewsItem, NewsAnalysis, MarketPair } from '../types';

export async function generateNewsAnalysis(newsItem: NewsItem): Promise<NewsAnalysis> {
  try {
    const response = await fetch('/api/ai/analyze-news', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ newsItem }),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error generating news analysis:', error);
    return {
      cause: 'Analysis error',
      marketImpact: 'neutral',
      affectedAssets: [],
      institutionalPerspective: 'Error generating analysis.',
    };
  }
}

export async function generateMarketAnalysis(
  pairs: Map<string, MarketPair>,
  news: NewsItem[]
): Promise<MarketAnalysis> {
  try {
    const pairsData = Array.from(pairs.values());

    const response = await fetch('/api/ai/analyze-market', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pairs: pairsData, news }),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error generating market analysis:', error);
    return {
      sentiment: 'neutral',
      keyLevels: {},
      bias: {},
      riskFactors: ['Analysis unavailable'],
      summary: 'Unable to generate market analysis at this time. Please check API connection.',
      timestamp: Date.now(),
    };
  }
}
