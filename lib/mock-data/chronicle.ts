export type ResearchJourney = {
  journeyId: string;
  title: string;
  researcher: string;
  startDate: string;
  endDate: string;
  status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED' | 'PAUSED';
  events: TimelineEvent[];
};

export type TimelineEvent = {
  id: string;
  journeyId: string;
  timestamp: string;
  eventType: string;
  entity: string;
  entityId: string;
  action: string;
  user: string;
  metadata: string;
  status: 'SUCCESS' | 'FAILED' | 'WARNING' | 'INFO';
  details?: {
    metrics?: Record<string, number | string>;
    logs?: string[];
    artifacts?: string[];
  };
};

export const mockResearchJourneys: ResearchJourney[] = [
  {
    journeyId: 'journey_001',
    title: 'BTCUSDT 1h Model Development',
    researcher: 'research.team',
    startDate: '2026-07-10T08:00:00Z',
    endDate: '2026-07-12T16:00:00Z',
    status: 'IN_PROGRESS',
    events: [
      {
        id: 'evt_001',
        journeyId: 'journey_001',
        timestamp: '2026-07-10T08:00:00Z',
        eventType: 'DATASET',
        entity: 'dataset_btc_1h_v31',
        entityId: 'dataset_btc_1h_v31',
        action: 'Dataset Imported',
        user: 'research.team',
        metadata: 'Symbol: BTCUSDT, Timeframe: 1h',
        status: 'SUCCESS',
        details: {
          metrics: { rows: 8760, features: 124, timespan: '365d' },
          artifacts: ['dataset_btc_1h_v31.parquet', 'dataset_btc_1h_v31_stats.json']
        }
      },
      {
        id: 'evt_002',
        journeyId: 'journey_001',
        timestamp: '2026-07-10T11:30:00Z',
        eventType: 'FEATURE',
        entity: 'feature_store_v18',
        entityId: 'feature_store_v18',
        action: 'Feature Store Generated',
        user: 'research.team',
        metadata: 'Features: 124',
        status: 'SUCCESS',
        details: {
          metrics: { features: 124, samples: 8760 }
        }
      },
      {
        id: 'evt_003',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T09:15:00Z',
        eventType: 'EXPERIMENT',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Experiment Created',
        user: 'research.team',
        metadata: 'Strategy: BTCUSDT 1h',
        status: 'SUCCESS',
        details: {
          metrics: { folds: 5 }
        }
      },
      {
        id: 'evt_004',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T10:00:00Z',
        eventType: 'TRAINING',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Training Started',
        user: 'research.team',
        metadata: 'Method: Purged Walk Forward',
        status: 'INFO',
        details: {
          metrics: { folds: 5 }
        }
      },
      {
        id: 'evt_005',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T11:20:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Fold 1',
        user: 'research.team',
        metadata: 'Weighted F1: 0.78',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.78, longF1: 0.82, neutralF1: 0.76, shortF1: 0.75 }
        }
      },
      {
        id: 'evt_006',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T12:40:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Fold 2',
        user: 'research.team',
        metadata: 'Weighted F1: 0.81',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.81, longF1: 0.84, neutralF1: 0.79, shortF1: 0.80 }
        }
      },
      {
        id: 'evt_007',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T14:00:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Fold 3',
        user: 'research.team',
        metadata: 'Weighted F1: 0.79',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.79, longF1: 0.81, neutralF1: 0.78, shortF1: 0.77 }
        }
      },
      {
        id: 'evt_008',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T15:20:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Fold 4',
        user: 'research.team',
        metadata: 'Weighted F1: 0.82',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.82, longF1: 0.85, neutralF1: 0.80, shortF1: 0.81 }
        }
      },
      {
        id: 'evt_009',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T16:40:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Fold 5',
        user: 'research.team',
        metadata: 'Weighted F1: 0.80',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.80, longF1: 0.83, neutralF1: 0.79, shortF1: 0.78 }
        }
      },
      {
        id: 'evt_010',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T17:00:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Purged Walk Forward Complete',
        user: 'research.team',
        metadata: 'Average Weighted F1: 0.80',
        status: 'SUCCESS',
        details: {
          metrics: { avgWeightedF1: 0.80, avgLongF1: 0.83, avgNeutralF1: 0.78, avgShortF1: 0.78 }
        }
      },
      {
        id: 'evt_011',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T09:00:00Z',
        eventType: 'CALIBRATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Calibration',
        user: 'research.team',
        metadata: 'ECE After: 0.024',
        status: 'SUCCESS',
        details: {
          metrics: { eceBefore: 0.089, eceAfter: 0.024, brierScore: 0.041 }
        }
      },
      {
        id: 'evt_012',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T11:00:00Z',
        eventType: 'EVALUATION',
        entity: 'exp_btc_194',
        entityId: 'exp_btc_194',
        action: 'Evaluation',
        user: 'research.team',
        metadata: 'PSI: 0.12, Drift: Low',
        status: 'SUCCESS',
        details: {
          metrics: { psi: 0.12, drift: 'low', confidenceDistribution: 0.87, predictionStability: 0.91 }
        }
      },
      {
        id: 'evt_013',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T13:00:00Z',
        eventType: 'MODEL',
        entity: 'model_btc_v194',
        entityId: 'model_btc_v194',
        action: 'Model Registered',
        user: 'research.team',
        metadata: 'Version: v194',
        status: 'SUCCESS',
        details: {
          metrics: { weightedF1: 0.80 },
          artifacts: ['model_btc_v194.pkl', 'model_btc_v194_config.json']
        }
      },
      {
        id: 'evt_014',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T14:00:00Z',
        eventType: 'PROMOTION',
        entity: 'model_btc_v194',
        entityId: 'model_btc_v194',
        action: 'Candidate',
        user: 'research.team',
        metadata: 'Status: Candidate',
        status: 'INFO'
      }
    ]
  },
  {
    journeyId: 'journey_002',
    title: 'ETHUSDT 4h Production Deployment',
    researcher: 'ml.ops',
    startDate: '2026-07-09T06:00:00Z',
    endDate: '2026-07-12T13:15:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_006',
        journeyId: 'journey_002',
        timestamp: '2026-07-09T06:00:00Z',
        eventType: 'MODEL',
        entity: 'model_eth_v203',
        entityId: 'model_eth_v203',
        action: 'Model Registered',
        user: 'ml.ops',
        metadata: 'Symbol: ETHUSDT, Timeframe: 4h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_007',
        journeyId: 'journey_002',
        timestamp: '2026-07-10T10:00:00Z',
        eventType: 'EVALUATION',
        entity: 'model_eth_v203',
        entityId: 'model_eth_v203',
        action: 'Evaluation',
        user: 'ml.ops',
        metadata: 'PSI: 0.08',
        status: 'INFO'
      },
      {
        id: 'evt_008',
        journeyId: 'journey_002',
        timestamp: '2026-07-11T14:20:00Z',
        eventType: 'CALIBRATION',
        entity: 'model_eth_v203',
        entityId: 'model_eth_v203',
        action: 'Calibration',
        user: 'ml.ops',
        metadata: 'ECE After: 0.021',
        status: 'SUCCESS',
        details: {
          metrics: { eceBefore: 0.089, eceAfter: 0.021, brierScore: 0.045 }
        }
      },
      {
        id: 'evt_009',
        journeyId: 'journey_002',
        timestamp: '2026-07-11T16:00:00Z',
        eventType: 'PROMOTION',
        entity: 'model_eth_v203',
        entityId: 'model_eth_v203',
        action: 'Approved',
        user: 'ml.ops',
        metadata: 'Status: Approved',
        status: 'SUCCESS'
      },
      {
        id: 'evt_010',
        journeyId: 'journey_002',
        timestamp: '2026-07-12T09:00:00Z',
        eventType: 'PRODUCTION',
        entity: 'prod_eth_4h',
        entityId: 'prod_eth_4h',
        action: 'Production',
        user: 'ml.ops',
        metadata: 'Deployed to prod_eth_4h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_011',
        journeyId: 'journey_002',
        timestamp: '2026-07-12T13:15:00Z',
        eventType: 'SIGNAL',
        entity: 'sig_8821',
        entityId: 'sig_8821',
        action: 'Signal Generated',
        user: 'ml.ops',
        metadata: 'Direction: LONG, Confidence: 0.87',
        status: 'SUCCESS',
        details: {
          metrics: { confidence: 0.87, direction: 'LONG' },
          artifacts: ['sig_8821.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_003',
    title: 'SOLUSDT 1h Validation Failure Analysis',
    researcher: 'quant.team',
    startDate: '2026-07-11T08:00:00Z',
    endDate: '2026-07-12T12:45:00Z',
    status: 'FAILED',
    events: [
      {
        id: 'evt_012',
        journeyId: 'journey_003',
        timestamp: '2026-07-11T08:00:00Z',
        eventType: 'MODEL',
        entity: 'model_sol_v187',
        entityId: 'model_sol_v187',
        action: 'Model Registered',
        user: 'quant.team',
        metadata: 'Symbol: SOLUSDT, Timeframe: 1h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_013',
        journeyId: 'journey_003',
        timestamp: '2026-07-11T14:30:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_sol_187',
        entityId: 'exp_sol_187',
        action: 'Fold 4',
        user: 'quant.team',
        metadata: 'Weighted F1: 0.58',
        status: 'INFO'
      },
      {
        id: 'evt_014',
        journeyId: 'journey_003',
        timestamp: '2026-07-12T12:45:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_sol_187',
        entityId: 'exp_sol_187',
        action: 'Fold 5',
        user: 'quant.team',
        metadata: 'Weighted F1: 0.54',
        status: 'FAILED',
        details: {
          metrics: { weightedF1: 0.54, threshold: 0.75 },
          logs: ['Failed threshold check', 'Performance degradation detected']
        }
      }
    ]
  },
  {
    journeyId: 'journey_004',
    title: 'BNBUSDT 4h Recalibration',
    researcher: 'ml.ops',
    startDate: '2026-07-12T09:00:00Z',
    endDate: '2026-07-12T11:20:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_015',
        journeyId: 'journey_004',
        timestamp: '2026-07-12T09:00:00Z',
        eventType: 'CALIBRATION',
        entity: 'model_bnb_v156',
        entityId: 'model_bnb_v156',
        action: 'Calibration',
        user: 'ml.ops',
        metadata: 'Method: Isotonic',
        status: 'INFO'
      },
      {
        id: 'evt_016',
        journeyId: 'journey_004',
        timestamp: '2026-07-12T11:20:00Z',
        eventType: 'CALIBRATION',
        entity: 'model_bnb_v156',
        entityId: 'model_bnb_v156',
        action: 'Calibration',
        user: 'ml.ops',
        metadata: 'ECE After: 0.031',
        status: 'SUCCESS',
        details: {
          metrics: { eceAfter: 0.031, eceBefore: 0.089, brierScore: 0.058 }
        }
      }
    ]
  },
  {
    journeyId: 'journey_005',
    title: 'HYPEUSDT 1h Feature Store Pipeline',
    researcher: 'data.eng',
    startDate: '2026-07-11T14:00:00Z',
    endDate: '2026-07-12T10:05:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_017',
        journeyId: 'journey_005',
        timestamp: '2026-07-11T14:00:00Z',
        eventType: 'DATASET',
        entity: 'dataset_hype_1h_v12',
        entityId: 'dataset_hype_1h_v12',
        action: 'Dataset Imported',
        user: 'data.eng',
        metadata: 'Symbol: HYPEUSDT, Timeframe: 1h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_018',
        journeyId: 'journey_005',
        timestamp: '2026-07-12T08:00:00Z',
        eventType: 'FEATURE',
        entity: 'feature_store_v19',
        entityId: 'feature_store_v19',
        action: 'Feature Store Generated',
        user: 'data.eng',
        metadata: 'Features: 98',
        status: 'INFO'
      },
      {
        id: 'evt_019',
        journeyId: 'journey_005',
        timestamp: '2026-07-12T10:05:00Z',
        eventType: 'FEATURE',
        entity: 'feature_store_v19',
        entityId: 'feature_store_v19',
        action: 'Feature Store Generated',
        user: 'data.eng',
        metadata: 'Features: 98',
        status: 'SUCCESS',
        details: {
          metrics: { features: 98, samples: 4380 },
          artifacts: ['feature_store_v19.parquet', 'feature_store_v19_schema.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_006',
    title: 'BTCUSDT 1h Trade Execution',
    researcher: 'research.team',
    startDate: '2026-07-12T07:00:00Z',
    endDate: '2026-07-12T09:30:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_020',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T07:00:00Z',
        eventType: 'SIGNAL',
        entity: 'sig_8822',
        entityId: 'sig_8822',
        action: 'Signal Generated',
        user: 'research.team',
        metadata: 'Direction: SHORT, Confidence: 0.82',
        status: 'SUCCESS'
      },
      {
        id: 'evt_021',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T08:15:00Z',
        eventType: 'TRADE',
        entity: 'trade_551',
        entityId: 'trade_551',
        action: 'Trade Closed',
        user: 'research.team',
        metadata: 'PnL: +2.4%',
        status: 'SUCCESS',
        details: {
          metrics: { pnl: 0.024, duration: '1.25h', confidence: 0.82 }
        }
      },
      {
        id: 'evt_022',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T09:30:00Z',
        eventType: 'AI_REVIEW',
        entity: 'trade_551',
        entityId: 'trade_551',
        action: 'AI Review',
        user: 'research.team',
        metadata: 'Decision Quality: High',
        status: 'SUCCESS',
        details: {
          artifacts: ['trade_551_review.json', 'trade_551_lessons.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_007',
    title: 'ETHUSDT 4h Drift Detection',
    researcher: 'research.team',
    startDate: '2026-07-11T16:00:00Z',
    endDate: '2026-07-12T08:50:00Z',
    status: 'FAILED',
    events: [
      {
        id: 'evt_023',
        journeyId: 'journey_007',
        timestamp: '2026-07-11T16:00:00Z',
        eventType: 'DATASET',
        entity: 'dataset_eth_4h_v18',
        entityId: 'dataset_eth_4h_v18',
        action: 'Dataset Imported',
        user: 'research.team',
        metadata: 'Symbol: ETHUSDT, Timeframe: 4h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_024',
        journeyId: 'journey_007',
        timestamp: '2026-07-12T06:00:00Z',
        eventType: 'EVALUATION',
        entity: 'exp_eth_203',
        entityId: 'exp_eth_203',
        action: 'Evaluation',
        user: 'research.team',
        metadata: 'PSI: 0.48',
        status: 'INFO'
      },
      {
        id: 'evt_025',
        journeyId: 'journey_007',
        timestamp: '2026-07-12T08:50:00Z',
        eventType: 'EVALUATION',
        entity: 'exp_eth_203',
        entityId: 'exp_eth_203',
        action: 'Evaluation',
        user: 'research.team',
        metadata: 'Drift: High',
        status: 'FAILED',
        details: {
          logs: ['Drift threshold exceeded', 'PSI: 0.48 > 0.25'],
          metrics: { psi: 0.48, threshold: 0.25 }
        }
      }
    ]
  },
  {
    journeyId: 'journey_008',
    title: 'SOLUSDT 1h Model Promotion',
    researcher: 'quant.team',
    startDate: '2026-07-11T18:00:00Z',
    endDate: '2026-07-12T06:00:00Z',
    status: 'PAUSED',
    events: [
      {
        id: 'evt_026',
        journeyId: 'journey_008',
        timestamp: '2026-07-11T18:00:00Z',
        eventType: 'MODEL',
        entity: 'model_sol_v187',
        entityId: 'model_sol_v187',
        action: 'Model Registered',
        user: 'quant.team',
        metadata: 'Symbol: SOLUSDT, Timeframe: 1h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_027',
        journeyId: 'journey_008',
        timestamp: '2026-07-12T03:00:00Z',
        eventType: 'VALIDATION',
        entity: 'exp_sol_187',
        entityId: 'exp_sol_187',
        action: 'Purged Walk Forward Complete',
        user: 'quant.team',
        metadata: 'Weighted F1: 0.78',
        status: 'SUCCESS'
      },
      {
        id: 'evt_028',
        journeyId: 'journey_008',
        timestamp: '2026-07-12T06:00:00Z',
        eventType: 'PROMOTION',
        entity: 'model_sol_v187',
        entityId: 'model_sol_v187',
        action: 'Candidate',
        user: 'quant.team',
        metadata: 'Status: Candidate',
        status: 'WARNING',
        details: {
          metrics: { weightedF1: 0.78 },
          logs: ['Pending: Calibration check', 'Pending: Risk review']
        }
      }
    ]
  },
  {
    journeyId: 'journey_009',
    title: 'BTCUSDT 1h Feature Store Update',
    researcher: 'data.eng',
    startDate: '2026-07-12T02:00:00Z',
    endDate: '2026-07-12T04:45:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_029',
        journeyId: 'journey_009',
        timestamp: '2026-07-12T02:00:00Z',
        eventType: 'FEATURE',
        entity: 'feature_store_v20',
        entityId: 'feature_store_v20',
        action: 'Feature Store Generated',
        user: 'data.eng',
        metadata: 'Symbol: BTCUSDT, Timeframe: 1h',
        status: 'INFO'
      },
      {
        id: 'evt_030',
        journeyId: 'journey_009',
        timestamp: '2026-07-12T04:45:00Z',
        eventType: 'FEATURE',
        entity: 'feature_store_v20',
        entityId: 'feature_store_v20',
        action: 'Feature Store Generated',
        user: 'data.eng',
        metadata: 'Features: 132',
        status: 'SUCCESS',
        details: {
          metrics: { features: 132, samples: 8760 },
          artifacts: ['feature_store_v20.parquet']
        }
      }
    ]
  },
  {
    journeyId: 'journey_010',
    title: 'BTCUSDT 1h Trade Analysis',
    researcher: 'quant.team',
    startDate: '2026-07-10T10:00:00Z',
    endDate: '2026-07-12T15:00:00Z',
    status: 'IN_PROGRESS',
    events: [
      {
        id: 'evt_031',
        journeyId: 'journey_010',
        timestamp: '2026-07-10T10:00:00Z',
        eventType: 'PRODUCTION',
        entity: 'prod_btc_1h',
        entityId: 'prod_btc_1h',
        action: 'Production',
        user: 'quant.team',
        metadata: 'Symbol: BTCUSDT, Timeframe: 1h',
        status: 'SUCCESS'
      },
      {
        id: 'evt_032',
        journeyId: 'journey_010',
        timestamp: '2026-07-11T08:00:00Z',
        eventType: 'SIGNAL',
        entity: 'sig_8821',
        entityId: 'sig_8821',
        action: 'Signal Generated',
        user: 'quant.team',
        metadata: 'Direction: LONG, Confidence: 0.84',
        status: 'INFO'
      },
      {
        id: 'evt_033',
        journeyId: 'journey_010',
        timestamp: '2026-07-12T14:00:00Z',
        eventType: 'TRADE',
        entity: 'trade_552',
        entityId: 'trade_552',
        action: 'Trade Closed',
        user: 'quant.team',
        metadata: 'PnL: +1.8%',
        status: 'SUCCESS',
        details: {
          metrics: { pnl: 0.018, duration: '30h', confidence: 0.84 }
        }
      },
      {
        id: 'evt_034',
        journeyId: 'journey_010',
        timestamp: '2026-07-12T15:00:00Z',
        eventType: 'AI_REVIEW',
        entity: 'trade_552',
        entityId: 'trade_552',
        action: 'Lessons Learned',
        user: 'quant.team',
        metadata: 'Status: Complete',
        status: 'INFO'
      }
    ]
  }
];

export const getAllEvents = (): TimelineEvent[] => {
  return mockResearchJourneys.flatMap(journey => journey.events);
};

export const getEventsByJourney = (journeyId: string): TimelineEvent[] => {
  const journey = mockResearchJourneys.find(j => j.journeyId === journeyId);
  return journey ? journey.events : [];
};

export const getJourneyById = (journeyId: string): ResearchJourney | undefined => {
  return mockResearchJourneys.find(j => j.journeyId === journeyId);
};
