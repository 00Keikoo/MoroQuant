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
    title: 'LSTM Market Predictor Development',
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
        entity: 'Q4_2025_Full',
        entityId: 'ds_101',
        action: 'Dataset Created',
        user: 'research.team',
        metadata: 'Size: 4.2M rows',
        status: 'SUCCESS',
        details: {
          metrics: { rows: 4200000, features: 87, timespan: '90d' },
          artifacts: ['ds_101.parquet', 'ds_101_stats.json']
        }
      },
      {
        id: 'evt_002',
        journeyId: 'journey_001',
        timestamp: '2026-07-10T11:30:00Z',
        eventType: 'FEATURE',
        entity: 'Price_Momentum_v3',
        entityId: 'feat_201',
        action: 'Feature Engineered',
        user: 'research.team',
        metadata: 'Importance: 92%',
        status: 'SUCCESS',
        details: {
          metrics: { importance: 0.92, correlation: 0.78 }
        }
      },
      {
        id: 'evt_003',
        journeyId: 'journey_001',
        timestamp: '2026-07-11T09:15:00Z',
        eventType: 'EXPERIMENT',
        entity: 'LSTM_Market_Predictor_v1',
        entityId: 'exp_2847',
        action: 'Training Started',
        user: 'research.team',
        metadata: 'Epochs: 50',
        status: 'INFO',
        details: {
          metrics: { epochs: 50, batchSize: 256 }
        }
      },
      {
        id: 'evt_004',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T14:30:00Z',
        eventType: 'EXPERIMENT',
        entity: 'LSTM_Market_Predictor_v1',
        entityId: 'exp_2847',
        action: 'Training Complete',
        user: 'research.team',
        metadata: 'Val Accuracy: 87.3%',
        status: 'SUCCESS',
        details: {
          metrics: { valAccuracy: 0.873, valLoss: 0.234, trainTime: '4.2h' }
        }
      },
      {
        id: 'evt_005',
        journeyId: 'journey_001',
        timestamp: '2026-07-12T15:45:00Z',
        eventType: 'MODEL',
        entity: 'LSTM_Market_Predictor',
        entityId: 'mdl_001',
        action: 'Model Registered',
        user: 'research.team',
        metadata: 'Version: v1.0',
        status: 'SUCCESS',
        details: {
          metrics: { accuracy: 0.873, precision: 0.891 },
          artifacts: ['mdl_001.h5', 'mdl_001_config.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_002',
    title: 'Ensemble Multi-Strategy Production Push',
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
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'mdl_004',
        action: 'Model Registered',
        user: 'ml.ops',
        metadata: 'Version: v2.1',
        status: 'SUCCESS'
      },
      {
        id: 'evt_007',
        journeyId: 'journey_002',
        timestamp: '2026-07-10T10:00:00Z',
        eventType: 'VALIDATION',
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'val_004',
        action: 'Validation Started',
        user: 'ml.ops',
        metadata: 'Test Set: Q2_2026',
        status: 'INFO'
      },
      {
        id: 'evt_008',
        journeyId: 'journey_002',
        timestamp: '2026-07-11T14:20:00Z',
        eventType: 'VALIDATION',
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'val_004',
        action: 'Validation Passed',
        user: 'ml.ops',
        metadata: 'Accuracy: 89.7%',
        status: 'SUCCESS',
        details: {
          metrics: { accuracy: 0.897, f1Score: 0.903, auc: 0.912 }
        }
      },
      {
        id: 'evt_009',
        journeyId: 'journey_002',
        timestamp: '2026-07-11T16:00:00Z',
        eventType: 'CALIBRATION',
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'cal_004',
        action: 'Calibration Complete',
        user: 'ml.ops',
        metadata: 'ECE: 2.1%',
        status: 'SUCCESS',
        details: {
          metrics: { ece: 0.021, brier: 0.045 }
        }
      },
      {
        id: 'evt_010',
        journeyId: 'journey_002',
        timestamp: '2026-07-12T09:00:00Z',
        eventType: 'PROMOTION',
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'prm_004',
        action: 'Promotion Approved',
        user: 'ml.ops',
        metadata: 'Gates: 8/8',
        status: 'SUCCESS'
      },
      {
        id: 'evt_011',
        journeyId: 'journey_002',
        timestamp: '2026-07-12T13:15:00Z',
        eventType: 'MODEL',
        entity: 'Ensemble_Multi_Strategy',
        entityId: 'mdl_004',
        action: 'Promoted to Production',
        user: 'ml.ops',
        metadata: 'Approval Score: 95%',
        status: 'SUCCESS',
        details: {
          metrics: { approvalScore: 0.95 },
          artifacts: ['mdl_004_prod.bin', 'mdl_004_manifest.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_003',
    title: 'XGBoost Ensemble Validation Failure Analysis',
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
        entity: 'XGBoost_Ensemble',
        entityId: 'mdl_003',
        action: 'Model Registered',
        user: 'quant.team',
        metadata: 'Version: v1.2',
        status: 'SUCCESS'
      },
      {
        id: 'evt_013',
        journeyId: 'journey_003',
        timestamp: '2026-07-11T14:30:00Z',
        eventType: 'VALIDATION',
        entity: 'XGBoost_Ensemble',
        entityId: 'val_003',
        action: 'Validation Started',
        user: 'quant.team',
        metadata: 'Test Set: Live_2026_Q2',
        status: 'INFO'
      },
      {
        id: 'evt_014',
        journeyId: 'journey_003',
        timestamp: '2026-07-12T12:45:00Z',
        eventType: 'VALIDATION',
        entity: 'XGBoost_Ensemble',
        entityId: 'val_003',
        action: 'Validation Failed',
        user: 'quant.team',
        metadata: 'Accuracy: 58.9%',
        status: 'FAILED',
        details: {
          metrics: { accuracy: 0.589, threshold: 0.75 },
          logs: ['Failed threshold check', 'Performance degradation detected']
        }
      }
    ]
  },
  {
    journeyId: 'journey_004',
    title: 'RandomForest Classifier Recalibration',
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
        entity: 'RandomForest_Classifier',
        entityId: 'cal_002',
        action: 'Recalibration Started',
        user: 'ml.ops',
        metadata: 'Method: Isotonic',
        status: 'INFO'
      },
      {
        id: 'evt_016',
        journeyId: 'journey_004',
        timestamp: '2026-07-12T11:20:00Z',
        eventType: 'CALIBRATION',
        entity: 'RandomForest_Classifier',
        entityId: 'cal_002',
        action: 'Recalibration Complete',
        user: 'ml.ops',
        metadata: 'ECE: 3.1%',
        status: 'SUCCESS',
        details: {
          metrics: { ece: 0.031, previousEce: 0.089, improvement: 0.058 }
        }
      }
    ]
  },
  {
    journeyId: 'journey_005',
    title: 'Sentiment Analysis v3 Pipeline',
    researcher: 'data.eng',
    startDate: '2026-07-11T14:00:00Z',
    endDate: '2026-07-12T10:05:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_017',
        journeyId: 'journey_005',
        timestamp: '2026-07-11T14:00:00Z',
        eventType: 'FEATURE',
        entity: 'Sentiment_Score_Aggregator',
        entityId: 'feat_301',
        action: 'Feature Engineered',
        user: 'data.eng',
        metadata: 'Sources: 12',
        status: 'SUCCESS'
      },
      {
        id: 'evt_018',
        journeyId: 'journey_005',
        timestamp: '2026-07-12T08:00:00Z',
        eventType: 'DATASET',
        entity: 'Sentiment_Analysis_v3',
        entityId: 'ds_015',
        action: 'Dataset Processing',
        user: 'data.eng',
        metadata: 'Stage: ETL',
        status: 'INFO'
      },
      {
        id: 'evt_019',
        journeyId: 'journey_005',
        timestamp: '2026-07-12T10:05:00Z',
        eventType: 'DATASET',
        entity: 'Sentiment_Analysis_v3',
        entityId: 'ds_015',
        action: 'Dataset Created',
        user: 'data.eng',
        metadata: 'Size: 2.4M rows',
        status: 'SUCCESS',
        details: {
          metrics: { rows: 2400000, features: 24, sources: 12 },
          artifacts: ['ds_015.parquet', 'ds_015_schema.json']
        }
      }
    ]
  },
  {
    journeyId: 'journey_006',
    title: 'Volume Momentum Feature Deployment',
    researcher: 'research.team',
    startDate: '2026-07-12T07:00:00Z',
    endDate: '2026-07-12T09:30:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_020',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T07:00:00Z',
        eventType: 'FEATURE',
        entity: 'Volume_Momentum_Ratio',
        entityId: 'feat_128',
        action: 'Feature Engineered',
        user: 'research.team',
        metadata: 'Lookback: 20d',
        status: 'SUCCESS'
      },
      {
        id: 'evt_021',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T08:15:00Z',
        eventType: 'FEATURE',
        entity: 'Volume_Momentum_Ratio',
        entityId: 'feat_128',
        action: 'Backtesting Complete',
        user: 'research.team',
        metadata: 'Sharpe: 2.4',
        status: 'SUCCESS',
        details: {
          metrics: { sharpe: 2.4, importance: 0.87, correlation: 0.72 }
        }
      },
      {
        id: 'evt_022',
        journeyId: 'journey_006',
        timestamp: '2026-07-12T09:30:00Z',
        eventType: 'FEATURE',
        entity: 'Volume_Momentum_Ratio',
        entityId: 'feat_128',
        action: 'Feature Deployed',
        user: 'research.team',
        metadata: 'Importance: 87%',
        status: 'SUCCESS',
        details: {
          artifacts: ['feat_128_pipeline.py', 'feat_128_config.yaml']
        }
      }
    ]
  },
  {
    journeyId: 'journey_007',
    title: 'Transformer Attention Model Development',
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
        entity: 'High_Freq_Trades_2026',
        entityId: 'ds_016',
        action: 'Dataset Created',
        user: 'research.team',
        metadata: 'Size: 8.1M rows',
        status: 'SUCCESS'
      },
      {
        id: 'evt_024',
        journeyId: 'journey_007',
        timestamp: '2026-07-12T06:00:00Z',
        eventType: 'EXPERIMENT',
        entity: 'Transformer_Attention',
        entityId: 'exp_2846',
        action: 'Training Started',
        user: 'research.team',
        metadata: 'Layers: 12, Heads: 8',
        status: 'INFO'
      },
      {
        id: 'evt_025',
        journeyId: 'journey_007',
        timestamp: '2026-07-12T08:50:00Z',
        eventType: 'EXPERIMENT',
        entity: 'Transformer_Attention',
        entityId: 'exp_2846',
        action: 'Training Failed',
        user: 'research.team',
        metadata: 'Error: OOM',
        status: 'FAILED',
        details: {
          logs: ['GPU memory exceeded', 'Required: 32GB, Available: 24GB'],
          metrics: { memoryRequired: 32, memoryAvailable: 24 }
        }
      }
    ]
  },
  {
    journeyId: 'journey_008',
    title: 'GRU Volatility Model Promotion',
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
        entity: 'GRU_Volatility_Model',
        entityId: 'mdl_005',
        action: 'Model Registered',
        user: 'quant.team',
        metadata: 'Version: v3.0',
        status: 'SUCCESS'
      },
      {
        id: 'evt_027',
        journeyId: 'journey_008',
        timestamp: '2026-07-12T03:00:00Z',
        eventType: 'VALIDATION',
        entity: 'GRU_Volatility_Model',
        entityId: 'val_005',
        action: 'Validation Passed',
        user: 'quant.team',
        metadata: 'Accuracy: 84.2%',
        status: 'SUCCESS'
      },
      {
        id: 'evt_028',
        journeyId: 'journey_008',
        timestamp: '2026-07-12T06:00:00Z',
        eventType: 'PROMOTION',
        entity: 'GRU_Volatility_Model',
        entityId: 'prm_005',
        action: 'Promotion Pending',
        user: 'quant.team',
        metadata: 'Gates: 6/8',
        status: 'WARNING',
        details: {
          metrics: { gatesPassed: 6, gatesTotal: 8 },
          logs: ['Pending: Calibration check', 'Pending: Risk review']
        }
      }
    ]
  },
  {
    journeyId: 'journey_009',
    title: 'Market Depth v2 Data Update',
    researcher: 'data.eng',
    startDate: '2026-07-12T02:00:00Z',
    endDate: '2026-07-12T04:45:00Z',
    status: 'COMPLETED',
    events: [
      {
        id: 'evt_029',
        journeyId: 'journey_009',
        timestamp: '2026-07-12T02:00:00Z',
        eventType: 'DATASET',
        entity: 'Market_Depth_v2',
        entityId: 'ds_014',
        action: 'Dataset Update Started',
        user: 'data.eng',
        metadata: 'Source: Exchange API',
        status: 'INFO'
      },
      {
        id: 'evt_030',
        journeyId: 'journey_009',
        timestamp: '2026-07-12T04:45:00Z',
        eventType: 'DATASET',
        entity: 'Market_Depth_v2',
        entityId: 'ds_014',
        action: 'Dataset Updated',
        user: 'data.eng',
        metadata: 'Added: 340K rows',
        status: 'SUCCESS',
        details: {
          metrics: { rowsAdded: 340000, totalRows: 5200000 },
          artifacts: ['ds_014_v2.parquet']
        }
      }
    ]
  },
  {
    journeyId: 'journey_010',
    title: 'Mean Reversion Strategy Backtest',
    researcher: 'quant.team',
    startDate: '2026-07-10T10:00:00Z',
    endDate: '2026-07-12T15:00:00Z',
    status: 'IN_PROGRESS',
    events: [
      {
        id: 'evt_031',
        journeyId: 'journey_010',
        timestamp: '2026-07-10T10:00:00Z',
        eventType: 'FEATURE',
        entity: 'Zscore_Normalized',
        entityId: 'feat_401',
        action: 'Feature Engineered',
        user: 'quant.team',
        metadata: 'Window: 60d',
        status: 'SUCCESS'
      },
      {
        id: 'evt_032',
        journeyId: 'journey_010',
        timestamp: '2026-07-11T08:00:00Z',
        eventType: 'EXPERIMENT',
        entity: 'Mean_Reversion_v2',
        entityId: 'exp_2848',
        action: 'Backtest Started',
        user: 'quant.team',
        metadata: 'Period: 2024-2026',
        status: 'INFO'
      },
      {
        id: 'evt_033',
        journeyId: 'journey_010',
        timestamp: '2026-07-12T14:00:00Z',
        eventType: 'EXPERIMENT',
        entity: 'Mean_Reversion_v2',
        entityId: 'exp_2848',
        action: 'Backtest Complete',
        user: 'quant.team',
        metadata: 'Sharpe: 1.8',
        status: 'SUCCESS',
        details: {
          metrics: { sharpe: 1.8, maxDrawdown: 0.12, winRate: 0.64 }
        }
      },
      {
        id: 'evt_034',
        journeyId: 'journey_010',
        timestamp: '2026-07-12T15:00:00Z',
        eventType: 'VALIDATION',
        entity: 'Mean_Reversion_v2',
        entityId: 'val_010',
        action: 'Validation Started',
        user: 'quant.team',
        metadata: 'Test Set: Out_of_Sample',
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
