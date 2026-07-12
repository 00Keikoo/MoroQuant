export type PromotionStage =
  | 'VALIDATION'
  | 'CALIBRATION'
  | 'EVALUATION'
  | 'RISK_REVIEW'
  | 'READY'
  | 'PRODUCTION';

export type PromotionDecision = 'APPROVED' | 'REJECTED' | 'PENDING' | 'ON_HOLD';

export interface PromotionCandidate {
  id: string;
  modelVersion: string;
  experimentId: string;
  datasetVersion: string;
  featureVersion: string;
  validationScore: number;
  calibrationScore: number;
  evaluationScore: number;
  promotionScore: number;
  riskScore: number;
  currentStage: PromotionStage;
  reviewer: string;
  decision: PromotionDecision;
  promotionEta: string;
  submittedAt: string;
  validationPassed: boolean;
  calibrationPassed: boolean;
  evaluationPassed: boolean;
  riskReviewPassed: boolean;
  rollbackPlan: string;
  criticalIssues: number;
  blockers: string[];
}

export const mockPromotionQueue: PromotionCandidate[] = [
  {
    id: 'PMC-001',
    modelVersion: 'v2.3.4',
    experimentId: 'EXP-20260712-001',
    datasetVersion: 'DS-2026Q3-v1',
    featureVersion: 'FT-2026-07-v2',
    validationScore: 0.892,
    calibrationScore: 0.876,
    evaluationScore: 0.884,
    promotionScore: 0.881,
    riskScore: 0.12,
    currentStage: 'READY',
    reviewer: 'alice.wong',
    decision: 'APPROVED',
    promotionEta: '2026-07-14',
    submittedAt: '2026-07-10T08:30:00Z',
    validationPassed: true,
    calibrationPassed: true,
    evaluationPassed: true,
    riskReviewPassed: true,
    rollbackPlan: 'Automated rollback to v2.3.3 on critical error',
    criticalIssues: 0,
    blockers: []
  },
  {
    id: 'PMC-002',
    modelVersion: 'v2.3.3',
    experimentId: 'EXP-20260708-003',
    datasetVersion: 'DS-2026Q3-v1',
    featureVersion: 'FT-2026-07-v1',
    validationScore: 0.868,
    calibrationScore: 0.854,
    evaluationScore: 0.872,
    promotionScore: 0.865,
    riskScore: 0.18,
    currentStage: 'RISK_REVIEW',
    reviewer: 'bob.chen',
    decision: 'PENDING',
    promotionEta: '2026-07-16',
    submittedAt: '2026-07-09T14:20:00Z',
    validationPassed: true,
    calibrationPassed: true,
    evaluationPassed: true,
    riskReviewPassed: false,
    rollbackPlan: 'Manual rollback required',
    criticalIssues: 1,
    blockers: ['High variance in edge cases']
  },
  {
    id: 'PMC-003',
    modelVersion: 'v2.4.0-rc1',
    experimentId: 'EXP-20260705-012',
    datasetVersion: 'DS-2026Q2-v4',
    featureVersion: 'FT-2026-06-v8',
    validationScore: 0.901,
    calibrationScore: 0.889,
    evaluationScore: 0.895,
    promotionScore: 0.891,
    riskScore: 0.24,
    currentStage: 'EVALUATION',
    reviewer: 'carol.smith',
    decision: 'PENDING',
    promotionEta: '2026-07-18',
    submittedAt: '2026-07-07T11:45:00Z',
    validationPassed: true,
    calibrationPassed: true,
    evaluationPassed: false,
    riskReviewPassed: false,
    rollbackPlan: 'Canary deployment with auto-rollback',
    criticalIssues: 0,
    blockers: ['Performance regression in high-frequency scenarios']
  },
  {
    id: 'PMC-004',
    modelVersion: 'v2.2.8',
    experimentId: 'EXP-20260701-008',
    datasetVersion: 'DS-2026Q2-v3',
    featureVersion: 'FT-2026-06-v5',
    validationScore: 0.743,
    calibrationScore: 0.756,
    evaluationScore: 0,
    promotionScore: 0,
    riskScore: 0.42,
    currentStage: 'CALIBRATION',
    reviewer: 'david.kim',
    decision: 'ON_HOLD',
    promotionEta: '2026-07-22',
    submittedAt: '2026-07-06T09:15:00Z',
    validationPassed: true,
    calibrationPassed: false,
    evaluationPassed: false,
    riskReviewPassed: false,
    rollbackPlan: 'Not defined',
    criticalIssues: 2,
    blockers: ['Calibration drift detected', 'Missing risk assessment']
  },
  {
    id: 'PMC-005',
    modelVersion: 'v2.5.0-beta',
    experimentId: 'EXP-20260630-020',
    datasetVersion: 'DS-2026Q2-v2',
    featureVersion: 'FT-2026-06-v3',
    validationScore: 0.821,
    calibrationScore: 0,
    evaluationScore: 0,
    promotionScore: 0,
    riskScore: 0.56,
    currentStage: 'VALIDATION',
    reviewer: 'eve.liu',
    decision: 'PENDING',
    promotionEta: '2026-07-25',
    submittedAt: '2026-07-05T16:00:00Z',
    validationPassed: false,
    calibrationPassed: false,
    evaluationPassed: false,
    riskReviewPassed: false,
    rollbackPlan: 'Not defined',
    criticalIssues: 3,
    blockers: ['Data leakage suspected', 'Feature engineering issues', 'Overfitting detected']
  },
  {
    id: 'PMC-006',
    modelVersion: 'v2.3.5',
    experimentId: 'EXP-20260711-007',
    datasetVersion: 'DS-2026Q3-v1',
    featureVersion: 'FT-2026-07-v2',
    validationScore: 0.887,
    calibrationScore: 0.881,
    evaluationScore: 0.879,
    promotionScore: 0.882,
    riskScore: 0.15,
    currentStage: 'PRODUCTION',
    reviewer: 'alice.wong',
    decision: 'APPROVED',
    promotionEta: '2026-07-12',
    submittedAt: '2026-07-08T10:00:00Z',
    validationPassed: true,
    calibrationPassed: true,
    evaluationPassed: true,
    riskReviewPassed: true,
    rollbackPlan: 'Automated rollback to v2.3.4 on critical error',
    criticalIssues: 0,
    blockers: []
  },
  {
    id: 'PMC-007',
    modelVersion: 'v2.1.9',
    experimentId: 'EXP-20260628-015',
    datasetVersion: 'DS-2026Q2-v1',
    featureVersion: 'FT-2026-06-v2',
    validationScore: 0.698,
    calibrationScore: 0.701,
    evaluationScore: 0.689,
    promotionScore: 0.695,
    riskScore: 0.68,
    currentStage: 'VALIDATION',
    reviewer: 'frank.nguyen',
    decision: 'REJECTED',
    promotionEta: 'N/A',
    submittedAt: '2026-07-03T13:30:00Z',
    validationPassed: false,
    calibrationPassed: false,
    evaluationPassed: false,
    riskReviewPassed: false,
    rollbackPlan: 'Not applicable',
    criticalIssues: 5,
    blockers: ['Below minimum threshold', 'Architecture incompatibility']
  }
];
