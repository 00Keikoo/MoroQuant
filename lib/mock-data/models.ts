export type ModelRegistryEntry = {
  id: string;
  modelVersion: string;
  experimentId: string;
  datasetVersion: string;
  featureVersion: string;
  algorithm: string;
  trainingDate: string;
  validationScore: number;
  calibrationScore: number;
  evaluationScore: number;
  promotionScore: number;
  overallScore: number;
  lifecycleStatus: 'CANDIDATE' | 'PRODUCTION' | 'ARCHIVED';
  rollbackAvailable: boolean;
  governanceStatus: 'APPROVED' | 'PENDING' | 'REJECTED' | 'UNDER_REVIEW';
  activatedAt: string | null;
  purgedWalkForward: boolean;
  folds: number;
  eceBefore: number;
  eceAfter: number;
  brierScore: number;
  stabilityScore: number;
  consistencyScore: number;
  riskScore: number;
  promotionDecision: 'APPROVED' | 'REJECTED' | 'PENDING' | null;
  rollbackTargetVersion: string | null;
};

export const mockModelRegistry: ModelRegistryEntry[] = [
  {
    id: 'mdl_reg_001',
    modelVersion: 'v2.4.1',
    experimentId: 'exp_btc_momentum_v3',
    datasetVersion: 'ds_v2.4.1',
    featureVersion: 'feat_v1.8.3',
    algorithm: 'XGBoost',
    trainingDate: '2026-07-12T10:30:00Z',
    validationScore: 0.712,
    calibrationScore: 0.962,
    evaluationScore: 0.845,
    promotionScore: 0.873,
    overallScore: 0.848,
    lifecycleStatus: 'PRODUCTION',
    rollbackAvailable: true,
    governanceStatus: 'APPROVED',
    activatedAt: '2026-07-12T14:00:00Z',
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.142,
    eceAfter: 0.038,
    brierScore: 0.089,
    stabilityScore: 0.876,
    consistencyScore: 0.834,
    riskScore: 0.145,
    promotionDecision: 'APPROVED',
    rollbackTargetVersion: 'v2.3.8'
  },
  {
    id: 'mdl_reg_002',
    modelVersion: 'v2.4.0',
    experimentId: 'exp_eth_reversal_v2',
    datasetVersion: 'ds_v2.4.0',
    featureVersion: 'feat_v1.8.2',
    algorithm: 'LightGBM',
    trainingDate: '2026-07-11T14:15:00Z',
    validationScore: 0.681,
    calibrationScore: 0.955,
    evaluationScore: 0.812,
    promotionScore: 0.816,
    overallScore: 0.816,
    lifecycleStatus: 'PRODUCTION',
    rollbackAvailable: true,
    governanceStatus: 'APPROVED',
    activatedAt: '2026-07-11T18:30:00Z',
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.156,
    eceAfter: 0.045,
    brierScore: 0.102,
    stabilityScore: 0.843,
    consistencyScore: 0.798,
    riskScore: 0.178,
    promotionDecision: 'APPROVED',
    rollbackTargetVersion: 'v2.3.7'
  },
  {
    id: 'mdl_reg_003',
    modelVersion: 'v2.3.9',
    experimentId: 'exp_multi_trend_v4',
    datasetVersion: 'ds_v2.3.8',
    featureVersion: 'feat_v1.8.1',
    algorithm: 'CatBoost',
    trainingDate: '2026-07-10T09:45:00Z',
    validationScore: 0.589,
    calibrationScore: 0.911,
    evaluationScore: 0.734,
    promotionScore: 0.678,
    overallScore: 0.728,
    lifecycleStatus: 'CANDIDATE',
    rollbackAvailable: false,
    governanceStatus: 'UNDER_REVIEW',
    activatedAt: null,
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.178,
    eceAfter: 0.089,
    brierScore: 0.145,
    stabilityScore: 0.712,
    consistencyScore: 0.689,
    riskScore: 0.256,
    promotionDecision: 'PENDING',
    rollbackTargetVersion: null
  },
  {
    id: 'mdl_reg_004',
    modelVersion: 'v2.3.8',
    experimentId: 'exp_breakout_v2',
    datasetVersion: 'ds_v2.3.6',
    featureVersion: 'feat_v1.7.9',
    algorithm: 'XGBoost',
    trainingDate: '2026-07-08T11:00:00Z',
    validationScore: 0.745,
    calibrationScore: 0.968,
    evaluationScore: 0.867,
    promotionScore: 0.893,
    overallScore: 0.868,
    lifecycleStatus: 'ARCHIVED',
    rollbackAvailable: true,
    governanceStatus: 'APPROVED',
    activatedAt: '2026-07-08T16:00:00Z',
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.134,
    eceAfter: 0.032,
    brierScore: 0.078,
    stabilityScore: 0.901,
    consistencyScore: 0.856,
    riskScore: 0.112,
    promotionDecision: 'APPROVED',
    rollbackTargetVersion: 'v2.3.5'
  },
  {
    id: 'mdl_reg_005',
    modelVersion: 'v2.3.7',
    experimentId: 'exp_volatility_v1',
    datasetVersion: 'ds_v2.3.7',
    featureVersion: 'feat_v1.8.0',
    algorithm: 'RandomForest',
    trainingDate: '2026-07-09T16:20:00Z',
    validationScore: 0.523,
    calibrationScore: 0.833,
    evaluationScore: 0.645,
    promotionScore: 0.567,
    overallScore: 0.642,
    lifecycleStatus: 'CANDIDATE',
    rollbackAvailable: false,
    governanceStatus: 'REJECTED',
    activatedAt: null,
    purgedWalkForward: false,
    folds: 3,
    eceBefore: 0.201,
    eceAfter: 0.167,
    brierScore: 0.198,
    stabilityScore: 0.623,
    consistencyScore: 0.578,
    riskScore: 0.378,
    promotionDecision: 'REJECTED',
    rollbackTargetVersion: null
  },
  {
    id: 'mdl_reg_006',
    modelVersion: 'v2.3.6',
    experimentId: 'exp_mean_reversion_v3',
    datasetVersion: 'ds_v2.3.5',
    featureVersion: 'feat_v1.7.8',
    algorithm: 'LightGBM',
    trainingDate: '2026-07-07T13:30:00Z',
    validationScore: 0.698,
    calibrationScore: 0.947,
    evaluationScore: 0.823,
    promotionScore: 0.841,
    overallScore: 0.827,
    lifecycleStatus: 'ARCHIVED',
    rollbackAvailable: true,
    governanceStatus: 'APPROVED',
    activatedAt: '2026-07-07T19:00:00Z',
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.149,
    eceAfter: 0.053,
    brierScore: 0.095,
    stabilityScore: 0.854,
    consistencyScore: 0.812,
    riskScore: 0.165,
    promotionDecision: 'APPROVED',
    rollbackTargetVersion: 'v2.3.4'
  },
  {
    id: 'mdl_reg_007',
    modelVersion: 'v2.4.2',
    experimentId: 'exp_sentiment_v1',
    datasetVersion: 'ds_v2.3.4',
    featureVersion: 'feat_v1.7.7',
    algorithm: 'XGBoost',
    trainingDate: '2026-07-06T08:00:00Z',
    validationScore: 0.0,
    calibrationScore: 0.0,
    evaluationScore: 0.0,
    promotionScore: 0.0,
    overallScore: 0.0,
    lifecycleStatus: 'CANDIDATE',
    rollbackAvailable: false,
    governanceStatus: 'PENDING',
    activatedAt: null,
    purgedWalkForward: true,
    folds: 5,
    eceBefore: 0.0,
    eceAfter: 0.0,
    brierScore: 0.0,
    stabilityScore: 0.0,
    consistencyScore: 0.0,
    riskScore: 0.0,
    promotionDecision: 'PENDING',
    rollbackTargetVersion: null
  }
];
