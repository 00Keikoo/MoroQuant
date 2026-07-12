export type CalibrationRun = {
  id: string;
  modelVersion: string;
  experiment: string;
  datasetVersion: string;
  featureVersion: string;
  calibrationMethod: string;
  eceBefore: number;
  eceAfter: number;
  brierScore: number;
  calibrationDate: string;
  status: 'PASSED' | 'FAILED' | 'RUNNING' | 'PENDING' | 'WARNING';
};

export const mockCalibrationRuns: CalibrationRun[] = [
  {
    id: 'cal_20260712_001',
    modelVersion: 'model_v3.2.1',
    experiment: 'exp_btc_momentum_v3',
    datasetVersion: 'ds_v2.4.1',
    featureVersion: 'feat_v1.8.3',
    calibrationMethod: 'Platt Scaling',
    eceBefore: 0.142,
    eceAfter: 0.038,
    brierScore: 0.156,
    calibrationDate: '2026-07-12T11:00:00Z',
    status: 'PASSED'
  },
  {
    id: 'cal_20260711_002',
    modelVersion: 'model_v3.1.8',
    experiment: 'exp_eth_reversal_v2',
    datasetVersion: 'ds_v2.4.0',
    featureVersion: 'feat_v1.8.2',
    calibrationMethod: 'Isotonic Regression',
    eceBefore: 0.156,
    eceAfter: 0.045,
    brierScore: 0.172,
    calibrationDate: '2026-07-11T14:45:00Z',
    status: 'PASSED'
  },
  {
    id: 'cal_20260710_003',
    modelVersion: 'model_v3.1.5',
    experiment: 'exp_multi_trend_v4',
    datasetVersion: 'ds_v2.3.8',
    featureVersion: 'feat_v1.8.1',
    calibrationMethod: 'Temperature Scaling',
    eceBefore: 0.178,
    eceAfter: 0.089,
    brierScore: 0.203,
    calibrationDate: '2026-07-10T10:15:00Z',
    status: 'WARNING'
  },
  {
    id: 'cal_20260709_004',
    modelVersion: 'model_v3.0.9',
    experiment: 'exp_volatility_v1',
    datasetVersion: 'ds_v2.3.7',
    featureVersion: 'feat_v1.8.0',
    calibrationMethod: 'Beta Calibration',
    eceBefore: 0.201,
    eceAfter: 0.167,
    brierScore: 0.289,
    calibrationDate: '2026-07-09T16:50:00Z',
    status: 'FAILED'
  },
  {
    id: 'cal_20260708_005',
    modelVersion: 'model_v3.2.0',
    experiment: 'exp_breakout_v2',
    datasetVersion: 'ds_v2.3.6',
    featureVersion: 'feat_v1.7.9',
    calibrationMethod: 'Platt Scaling',
    eceBefore: 0.134,
    eceAfter: 0.032,
    brierScore: 0.148,
    calibrationDate: '2026-07-08T11:30:00Z',
    status: 'PASSED'
  },
  {
    id: 'cal_20260707_006',
    modelVersion: 'model_v3.1.3',
    experiment: 'exp_mean_reversion_v3',
    datasetVersion: 'ds_v2.3.5',
    featureVersion: 'feat_v1.7.8',
    calibrationMethod: 'Isotonic Regression',
    eceBefore: 0.0,
    eceAfter: 0.0,
    brierScore: 0.0,
    calibrationDate: '2026-07-07T14:00:00Z',
    status: 'RUNNING'
  },
  {
    id: 'cal_20260706_007',
    modelVersion: 'model_v3.0.5',
    experiment: 'exp_sentiment_v1',
    datasetVersion: 'ds_v2.3.4',
    featureVersion: 'feat_v1.7.7',
    calibrationMethod: 'Temperature Scaling',
    eceBefore: 0.0,
    eceAfter: 0.0,
    brierScore: 0.0,
    calibrationDate: '2026-07-06T08:30:00Z',
    status: 'PENDING'
  }
];
