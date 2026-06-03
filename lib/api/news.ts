import { NewsItem } from '../types';

const NEWS_SOURCES = [
  'reuters',
  'bloomberg',
  'financial-times',
  'the-wall-street-journal',
];

const KEYWORDS = [
  'federal reserve',
  'interest rates',
  'inflation',
  'geopolitical',
  'war',
  'sanctions',
  'trade war',
  'cryptocurrency',
  'bitcoin',
  'ethereum',
  'central bank',
  'monetary policy',
];

export async function fetchNews(apiKey?: string): Promise<NewsItem[]> {
  if (!apiKey) {
    return fetchRSSFallback();
  }

  try {
    const query = KEYWORDS.slice(0, 3).join(' OR ');
    const sources = NEWS_SOURCES.join(',');
    const url = `https://newsapi.org/v2/everything?q=${encodeURIComponent(query)}&sources=${sources}&sortBy=publishedAt&pageSize=20&apiKey=${apiKey}`;

    const response = await fetch(url);
    const data = await response.json();

    if (data.status !== 'ok') {
      console.error('NewsAPI error:', data.message);
      return fetchRSSFallback();
    }

    return data.articles.map((article: any) => ({
      id: article.url,
      title: article.title,
      description: article.description || '',
      url: article.url,
      source: article.source.name,
      publishedAt: article.publishedAt,
      category: categorizeNews(article.title + ' ' + article.description),
    }));
  } catch (error) {
    console.error('Error fetching news:', error);
    return fetchRSSFallback();
  }
}

async function fetchRSSFallback(): Promise<NewsItem[]> {
  const mockNews: NewsItem[] = [
    {
      id: '1',
      title: 'Federal Reserve Signals Potential Rate Cut Amid Economic Slowdown',
      description: 'Fed officials hint at monetary policy shift as inflation shows signs of cooling',
      url: '#',
      source: 'Reuters',
      publishedAt: new Date().toISOString(),
      category: 'central-bank',
    },
    {
      id: '2',
      title: 'Geopolitical Tensions Rise in Middle East, Oil Prices Surge',
      description: 'Escalating conflict drives commodity markets higher',
      url: '#',
      source: 'Bloomberg',
      publishedAt: new Date(Date.now() - 3600000).toISOString(),
      category: 'geopolitical',
    },
    {
      id: '3',
      title: 'Bitcoin ETF Inflows Hit Record High as Institutional Interest Grows',
      description: 'Major financial institutions increase crypto exposure',
      url: '#',
      source: 'Financial Times',
      publishedAt: new Date(Date.now() - 7200000).toISOString(),
      category: 'crypto',
    },
    {
      id: '4',
      title: 'US-China Trade Negotiations Resume, Markets React Positively',
      description: 'Risk assets rally on hopes of trade deal progress',
      url: '#',
      source: 'Wall Street Journal',
      publishedAt: new Date(Date.now() - 10800000).toISOString(),
      category: 'macro',
    },
  ];

  return mockNews;
}

function categorizeNews(text: string): NewsItem['category'] {
  const lower = text.toLowerCase();

  if (lower.includes('fed') || lower.includes('central bank') || lower.includes('interest rate')) {
    return 'central-bank';
  }
  if (lower.includes('war') || lower.includes('conflict') || lower.includes('tension') || lower.includes('sanction')) {
    return 'geopolitical';
  }
  if (lower.includes('bitcoin') || lower.includes('crypto') || lower.includes('ethereum')) {
    return 'crypto';
  }

  return 'macro';
}
