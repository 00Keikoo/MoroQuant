export type ValidationRun = {
  id: string;
  experiment: string;
  datasetVersion: string;
  featureVersion: string;
  purgedWalkForward: boolean;
  purge: number;
  embargo: number;
  weightedF1: number;
  longF1: number;
  neutralF1: number;
  shortF1: number;
  eceBefore: number;
  eceAfter: number;
  status: 'PASSED' | 'FAILED' | 'RUNNING' | 'PENDING' | 'WARNING';
  created: string;
};

export const mockValidationRuns: ValidationRun[] = [
  {
    id: 'val_20260712_001',
    experiment: 'exp_btc_momentum_v3',
    datasetVersion: 'ds_v2.4.1',
    featureVersion: 'feat_v1.8.3',
    purgedWalkForward: true,
    purge: 2,
    embargo: 1,
    weightedF1: 0.712,
    longF1: 0.734,
    neutralF1: 0.689,
    shortF1: 0.715,
    eceBefore: 0.142,
    eceAfter: 0.038,
    status: 'PASSED',
    created: '2026-07-12T10:30:00Z'
  },
  {
    id: 'val_20260711_002',
    experiment: 'exp_eth_reversal_v2',
    datasetVersion: 'ds_v2.4.0',
    featureVersion: 'feat_v1.8.2',
    purgedWalkForward: true,
    purge: 3,
    embargo: 2,
    weightedF1: 0.681,
    longF1: 0.698,
    neutralF1: 0.652,
    shortF1: 0.693,
    eceBefore: 0.156,
    eceAfter: 0.045,
    status: 'PASSED',
    created: '2026-07-11T14:15:00Z'
  },
  {
    id: 'val_20260710_003',
    experiment: 'exp_multi_trend_v4',
    datasetVersion: 'ds_v2.3.8',
    featureVersion: 'feat_v1.8.1',
    purgedWalkForward: true,
    purge: 2,
    embargo: 1,
    weightedF1: 0.589,
    longF1: 0.612,
    neutralF1: 0.543,
    shortF1: 0.601,
    eceBefore: 0.178,
    eceAfter: 0.089,
    status: 'WARNING',
    created: '2026-07-10T09:45:00Z'
  },
  {
    id: 'val_20260709_004',
    experiment: 'exp_volatility_v1',
    datasetVersion: 'ds_v2.3.7',
    featureVersion: 'feat_v1.8.0',
    purgedWalkForward: false,
    purge: 0,
    embargo: 0,
    weightedF1: 0.523,
    longF1: 0.547,
    neutralF1: 0.489,
    shortF1: 0.534,
    eceBefore: 0.201,
    eceAfter: 0.167,
    status: 'FAILED',
    created: '2026-07-09T16:20:00Z'
  },
  {
    id: 'val_20260708_005',
    experiment: 'exp_breakout_v2',
    datasetVersion: 'ds_v2.3.6',
    featureVersion: 'feat_v1.7.9',
    purgedWalkForward: true,
    purge: 3,
    embargo: 2,
    weightedF1: 0.745,
    longF1: 0.768,
    neutralF1: 0.721,
    shortF1: 0.746,
    eceBefore: 0.134,
    eceAfter: 0.032,
    status: 'PASSED',
    created: '2026-07-08T11:00:00Z'
  },
  {
    id: 'val_20260707_006',
    experiment: 'exp_mean_reversion_v3',
    datasetVersion: 'ds_v2.3.5',
    featureVersion: 'feat_v1.7.8',
    purgedWalkForward: true,
    purge: 2,
    embargo: 1,
    weightedF1: 0.0,
    longF1: 0.0,
    neutralF1: 0.0,
    shortF1: 0.0,
    eceBefore: 0.0,
    eceAfter: 0.0,
    status: 'RUNNING',
    created: '2026-07-07T13:30:00Z'
  },
  {
    id: 'val_20260706_007',
    experiment: 'exp_sentiment_v1',
    datasetVersion: 'ds_v2.3.4',
    featureVersion: 'feat_v1.7.7',
    purgedWalkForward: true,
    purge: 2,
    embargo: 1,
    weightedF1: 0.0,
    longF1: 0.0,
    neutralF1: 0.0,
    shortF1: 0.0,
    eceBefore: 0.0,
    eceAfter: 0.0,
    status: 'PENDING',
    created: '2026-07-06T08:00:00Z'
  }
];
