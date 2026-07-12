export type FeatureStatus =
  | 'ACTIVE'
  | 'DEPRECATED'
  | 'EXPERIMENTAL'
  | 'VALIDATING'
  | 'FAILED'
  | 'ARCHIVED';

export type FeatureCategory =
  | 'Technical Indicator'
  | 'Market Microstructure'
  | 'Order Flow'
  | 'Volatility'
  | 'Price Action'
  | 'Volume Profile'
  | 'Time Series'
  | 'Sentiment';

export type FeatureType =
  | 'Continuous'
  | 'Categorical'
  | 'Binary'
  | 'Ordinal';

export interface Feature {
  id: string;
  name: string;
  version: string;
  status: FeatureStatus;
  category: FeatureCategory;
  type: FeatureType;
  created: string;
  description: string;
  usedByDatasets: number;
  usedByExperiments: number;
  importance: number;
  nullRate: number;
  correlation?: number;
  computeTime?: string;
  dependencies?: string[];
  statistics?: {
    mean?: number;
    std?: number;
    min?: number;
    max?: number;
    uniqueValues?: number;
  };
}

export const mockFeatures: Feature[] = [
  {
    id: 'feat-rsi-14',
    name: 'RSI_14',
    version: 'v2.1.0',
    status: 'ACTIVE',
    category: 'Technical Indicator',
    type: 'Continuous',
    created: '2026-01-15T10:30:00Z',
    description: 'Relative Strength Index with 14-period lookback',
    usedByDatasets: 24,
    usedByExperiments: 156,
    importance: 0.89,
    nullRate: 0.02,
    correlation: 0.67,
    computeTime: '0.8ms',
    dependencies: ['close_price'],
    statistics: {
      mean: 52.3,
      std: 18.7,
      min: 0.0,
      max: 100.0
    }
  },
  {
    id: 'feat-vwap',
    name: 'VWAP',
    version: 'v3.0.1',
    status: 'ACTIVE',
    category: 'Market Microstructure',
    type: 'Continuous',
    created: '2026-02-20T14:15:00Z',
    description: 'Volume-Weighted Average Price',
    usedByDatasets: 30,
    usedByExperiments: 203,
    importance: 0.92,
    nullRate: 0.01,
    correlation: 0.78,
    computeTime: '1.2ms',
    dependencies: ['close_price', 'volume'],
    statistics: {
      mean: 125.45,
      std: 42.18,
      min: 10.2,
      max: 850.3
    }
  },
  {
    id: 'feat-obv',
    name: 'OBV',
    version: 'v1.5.2',
    status: 'ACTIVE',
    category: 'Volume Profile',
    type: 'Continuous',
    created: '2026-01-10T09:45:00Z',
    description: 'On-Balance Volume indicator',
    usedByDatasets: 18,
    usedByExperiments: 98,
    importance: 0.73,
    nullRate: 0.03,
    correlation: 0.54,
    computeTime: '0.6ms',
    dependencies: ['close_price', 'volume']
  },
  {
    id: 'feat-atr-20',
    name: 'ATR_20',
    version: 'v2.0.0',
    status: 'ACTIVE',
    category: 'Volatility',
    type: 'Continuous',
    created: '2026-03-05T11:20:00Z',
    description: 'Average True Range with 20-period lookback',
    usedByDatasets: 22,
    usedByExperiments: 145,
    importance: 0.85,
    nullRate: 0.02,
    correlation: 0.62,
    computeTime: '1.1ms',
    dependencies: ['high_price', 'low_price', 'close_price'],
    statistics: {
      mean: 3.42,
      std: 1.87,
      min: 0.1,
      max: 15.8
    }
  },
  {
    id: 'feat-orderflow-imb',
    name: 'OrderFlow_Imbalance',
    version: 'v1.8.3',
    status: 'ACTIVE',
    category: 'Order Flow',
    type: 'Continuous',
    created: '2026-02-28T16:50:00Z',
    description: 'Order flow imbalance between bid and ask',
    usedByDatasets: 15,
    usedByExperiments: 87,
    importance: 0.81,
    nullRate: 0.05,
    correlation: 0.59,
    computeTime: '2.3ms',
    dependencies: ['bid_volume', 'ask_volume'],
    statistics: {
      mean: 0.12,
      std: 0.45,
      min: -1.0,
      max: 1.0
    }
  },
  {
    id: 'feat-macd',
    name: 'MACD',
    version: 'v2.2.1',
    status: 'ACTIVE',
    category: 'Technical Indicator',
    type: 'Continuous',
    created: '2026-01-25T13:30:00Z',
    description: 'Moving Average Convergence Divergence',
    usedByDatasets: 26,
    usedByExperiments: 178,
    importance: 0.88,
    nullRate: 0.02,
    correlation: 0.71,
    computeTime: '1.5ms',
    dependencies: ['close_price'],
    statistics: {
      mean: 0.85,
      std: 2.34,
      min: -12.5,
      max: 15.8
    }
  },
  {
    id: 'feat-bollinger-width',
    name: 'Bollinger_Width',
    version: 'v1.9.0',
    status: 'ACTIVE',
    category: 'Volatility',
    type: 'Continuous',
    created: '2026-03-12T10:15:00Z',
    description: 'Bollinger Bands width normalized',
    usedByDatasets: 20,
    usedByExperiments: 132,
    importance: 0.79,
    nullRate: 0.03,
    correlation: 0.64,
    computeTime: '1.0ms',
    dependencies: ['close_price'],
    statistics: {
      mean: 0.18,
      std: 0.12,
      min: 0.01,
      max: 0.85
    }
  },
  {
    id: 'feat-price-momentum',
    name: 'Price_Momentum_5m',
    version: 'v3.1.2',
    status: 'ACTIVE',
    category: 'Price Action',
    type: 'Continuous',
    created: '2026-02-15T15:40:00Z',
    description: '5-minute price momentum',
    usedByDatasets: 28,
    usedByExperiments: 195,
    importance: 0.91,
    nullRate: 0.01,
    correlation: 0.76,
    computeTime: '0.5ms',
    dependencies: ['close_price'],
    statistics: {
      mean: 0.02,
      std: 0.15,
      min: -0.98,
      max: 1.23
    }
  },
  {
    id: 'feat-volume-spike',
    name: 'Volume_Spike_Indicator',
    version: 'v1.3.1',
    status: 'ACTIVE',
    category: 'Volume Profile',
    type: 'Binary',
    created: '2026-03-01T09:25:00Z',
    description: 'Binary indicator for volume spikes above 3 std dev',
    usedByDatasets: 19,
    usedByExperiments: 124,
    importance: 0.77,
    nullRate: 0.02,
    correlation: 0.52,
    computeTime: '0.7ms',
    dependencies: ['volume'],
    statistics: {
      uniqueValues: 2
    }
  },
  {
    id: 'feat-microstructure-noise',
    name: 'Microstructure_Noise',
    version: 'v2.0.5',
    status: 'ACTIVE',
    category: 'Market Microstructure',
    type: 'Continuous',
    created: '2026-02-10T12:10:00Z',
    description: 'Market microstructure noise estimate',
    usedByDatasets: 12,
    usedByExperiments: 76,
    importance: 0.68,
    nullRate: 0.08,
    correlation: 0.48,
    computeTime: '3.1ms',
    dependencies: ['tick_data', 'spread'],
    statistics: {
      mean: 0.0012,
      std: 0.0008,
      min: 0.0,
      max: 0.015
    }
  },
  {
    id: 'feat-trend-strength',
    name: 'Trend_Strength',
    version: 'v1.7.4',
    status: 'ACTIVE',
    category: 'Price Action',
    type: 'Continuous',
    created: '2026-03-18T14:55:00Z',
    description: 'ADX-based trend strength indicator',
    usedByDatasets: 21,
    usedByExperiments: 139,
    importance: 0.82,
    nullRate: 0.03,
    correlation: 0.58,
    computeTime: '1.8ms',
    dependencies: ['high_price', 'low_price', 'close_price'],
    statistics: {
      mean: 28.5,
      std: 12.3,
      min: 0.0,
      max: 75.4
    }
  },
  {
    id: 'feat-realized-vol',
    name: 'Realized_Volatility_1h',
    version: 'v2.3.0',
    status: 'ACTIVE',
    category: 'Volatility',
    type: 'Continuous',
    created: '2026-01-30T11:45:00Z',
    description: '1-hour realized volatility',
    usedByDatasets: 25,
    usedByExperiments: 168,
    importance: 0.87,
    nullRate: 0.02,
    correlation: 0.69,
    computeTime: '2.5ms',
    dependencies: ['returns_1m'],
    statistics: {
      mean: 0.15,
      std: 0.08,
      min: 0.01,
      max: 0.95
    }
  },
  {
    id: 'feat-sentiment-score',
    name: 'Sentiment_Score',
    version: 'v0.9.2',
    status: 'EXPERIMENTAL',
    category: 'Sentiment',
    type: 'Continuous',
    created: '2026-04-01T08:30:00Z',
    description: 'Aggregate sentiment score from news and social media',
    usedByDatasets: 5,
    usedByExperiments: 23,
    importance: 0.62,
    nullRate: 0.15,
    correlation: 0.41,
    computeTime: '15.2ms',
    dependencies: ['news_feed', 'twitter_feed'],
    statistics: {
      mean: 0.05,
      std: 0.32,
      min: -1.0,
      max: 1.0
    }
  },
  {
    id: 'feat-tick-direction',
    name: 'Tick_Direction',
    version: 'v1.2.0',
    status: 'ACTIVE',
    category: 'Market Microstructure',
    type: 'Categorical',
    created: '2026-02-05T10:20:00Z',
    description: 'Tick direction indicator (uptick, downtick, no change)',
    usedByDatasets: 16,
    usedByExperiments: 94,
    importance: 0.71,
    nullRate: 0.04,
    computeTime: '0.4ms',
    dependencies: ['tick_data'],
    statistics: {
      uniqueValues: 3
    }
  },
  {
    id: 'feat-spread-ratio',
    name: 'Spread_Ratio',
    version: 'v2.1.3',
    status: 'ACTIVE',
    category: 'Market Microstructure',
    type: 'Continuous',
    created: '2026-03-08T13:15:00Z',
    description: 'Bid-ask spread relative to mid price',
    usedByDatasets: 23,
    usedByExperiments: 151,
    importance: 0.84,
    nullRate: 0.02,
    correlation: 0.66,
    computeTime: '0.9ms',
    dependencies: ['bid_price', 'ask_price'],
    statistics: {
      mean: 0.0008,
      std: 0.0004,
      min: 0.0001,
      max: 0.005
    }
  },
  {
    id: 'feat-time-of-day',
    name: 'Time_Of_Day_Sine',
    version: 'v1.0.0',
    status: 'ACTIVE',
    category: 'Time Series',
    type: 'Continuous',
    created: '2026-01-05T09:00:00Z',
    description: 'Sine-transformed time of day for cyclical encoding',
    usedByDatasets: 32,
    usedByExperiments: 218,
    importance: 0.74,
    nullRate: 0.0,
    computeTime: '0.2ms',
    dependencies: ['timestamp'],
    statistics: {
      mean: 0.0,
      std: 0.707,
      min: -1.0,
      max: 1.0
    }
  },
  {
    id: 'feat-ema-crossover',
    name: 'EMA_Crossover_12_26',
    version: 'v1.6.2',
    status: 'DEPRECATED',
    category: 'Technical Indicator',
    type: 'Binary',
    created: '2025-11-20T14:30:00Z',
    description: 'Binary indicator for EMA 12/26 crossover (deprecated)',
    usedByDatasets: 8,
    usedByExperiments: 45,
    importance: 0.58,
    nullRate: 0.03,
    computeTime: '1.3ms',
    dependencies: ['close_price'],
    statistics: {
      uniqueValues: 2
    }
  },
  {
    id: 'feat-order-book-imb',
    name: 'OrderBook_Imbalance_L2',
    version: 'v2.4.1',
    status: 'ACTIVE',
    category: 'Order Flow',
    type: 'Continuous',
    created: '2026-03-22T16:20:00Z',
    description: 'Level-2 order book imbalance',
    usedByDatasets: 14,
    usedByExperiments: 89,
    importance: 0.80,
    nullRate: 0.06,
    correlation: 0.63,
    computeTime: '4.5ms',
    dependencies: ['orderbook_l2'],
    statistics: {
      mean: 0.08,
      std: 0.38,
      min: -1.0,
      max: 1.0
    }
  },
  {
    id: 'feat-volatility-regime',
    name: 'Volatility_Regime',
    version: 'v1.4.0',
    status: 'ACTIVE',
    category: 'Volatility',
    type: 'Categorical',
    created: '2026-02-25T12:40:00Z',
    description: 'Volatility regime classification (low, medium, high)',
    usedByDatasets: 17,
    usedByExperiments: 112,
    importance: 0.76,
    nullRate: 0.04,
    computeTime: '1.6ms',
    dependencies: ['realized_volatility'],
    statistics: {
      uniqueValues: 3
    }
  },
  {
    id: 'feat-gap-indicator',
    name: 'Gap_Indicator',
    version: 'v1.1.5',
    status: 'ACTIVE',
    category: 'Price Action',
    type: 'Binary',
    created: '2026-03-15T10:50:00Z',
    description: 'Binary indicator for price gaps',
    usedByDatasets: 11,
    usedByExperiments: 67,
    importance: 0.65,
    nullRate: 0.05,
    computeTime: '0.6ms',
    dependencies: ['open_price', 'prev_close'],
    statistics: {
      uniqueValues: 2
    }
  },
  {
    id: 'feat-fractal-dim',
    name: 'Fractal_Dimension',
    version: 'v0.5.1',
    status: 'EXPERIMENTAL',
    category: 'Price Action',
    type: 'Continuous',
    created: '2026-04-10T15:25:00Z',
    description: 'Hurst exponent-based fractal dimension',
    usedByDatasets: 3,
    usedByExperiments: 12,
    importance: 0.54,
    nullRate: 0.22,
    computeTime: '28.3ms',
    dependencies: ['price_series'],
    statistics: {
      mean: 0.52,
      std: 0.08,
      min: 0.3,
      max: 0.7
    }
  },
  {
    id: 'feat-liquidity-score',
    name: 'Liquidity_Score',
    version: 'v1.8.0',
    status: 'ACTIVE',
    category: 'Market Microstructure',
    type: 'Continuous',
    created: '2026-02-18T11:35:00Z',
    description: 'Composite liquidity score',
    usedByDatasets: 19,
    usedByExperiments: 128,
    importance: 0.78,
    nullRate: 0.04,
    correlation: 0.61,
    computeTime: '2.8ms',
    dependencies: ['volume', 'spread', 'depth'],
    statistics: {
      mean: 0.65,
      std: 0.22,
      min: 0.1,
      max: 1.0
    }
  },
  {
    id: 'feat-failed-calc',
    name: 'Complex_Alpha_Signal',
    version: 'v0.2.0',
    status: 'FAILED',
    category: 'Technical Indicator',
    type: 'Continuous',
    created: '2026-04-05T09:10:00Z',
    description: 'Complex alpha signal (computation failed)',
    usedByDatasets: 0,
    usedByExperiments: 0,
    importance: 0.0,
    nullRate: 1.0,
    computeTime: 'N/A',
    dependencies: ['multiple_sources']
  },
  {
    id: 'feat-archived-stoch',
    name: 'Stochastic_Oscillator',
    version: 'v1.2.3',
    status: 'ARCHIVED',
    category: 'Technical Indicator',
    type: 'Continuous',
    created: '2025-10-15T13:20:00Z',
    description: 'Stochastic oscillator (archived)',
    usedByDatasets: 5,
    usedByExperiments: 32,
    importance: 0.61,
    nullRate: 0.03,
    computeTime: '1.1ms',
    dependencies: ['high_price', 'low_price', 'close_price']
  },
  {
    id: 'feat-validating-ml',
    name: 'ML_Feature_Interaction',
    version: 'v0.8.0',
    status: 'VALIDATING',
    category: 'Technical Indicator',
    type: 'Continuous',
    created: '2026-04-15T14:45:00Z',
    description: 'Machine learning-derived feature interaction',
    usedByDatasets: 2,
    usedByExperiments: 8,
    importance: 0.68,
    nullRate: 0.12,
    computeTime: '45.7ms',
    dependencies: ['rsi', 'macd', 'volume']
  }
];
