export type ExperimentStatus =
  | 'CREATED'
  | 'TRAINING'
  | 'VALIDATING'
  | 'CALIBRATING'
  | 'PAPER'
  | 'PROMOTION'
  | 'PRODUCTION'
  | 'FAILED'
  | 'ARCHIVED';

export interface Experiment {
  runId: string;
  status: ExperimentStatus;
  dataset: string;
  featureVersion: string;
  algorithm: string;
  created: string;
  duration: string;
  score: number | null;
  metadata: {
    epochs?: number;
    batchSize?: number;
    learningRate?: number;
    optimizer?: string;
    loss?: string;
  };
  metrics?: {
    trainLoss: number;
    valLoss: number;
    sharpeRatio?: number;
    maxDrawdown?: number;
  };
}

export const mockExperiments: Experiment[] = [
  {
    runId: 'exp-20260711-001',
    status: 'PRODUCTION',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'LSTM-Attention',
    created: '2026-07-01T08:15:00Z',
    duration: '4h 23m',
    score: 0.87,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    },
    metrics: {
      trainLoss: 0.042,
      valLoss: 0.051,
      sharpeRatio: 2.34,
      maxDrawdown: 0.12
    }
  },
  {
    runId: 'exp-20260711-002',
    status: 'TRAINING',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.3.0-rc1',
    algorithm: 'Transformer-XL',
    created: '2026-07-11T14:30:00Z',
    duration: '2h 15m',
    score: null,
    metadata: {
      epochs: 150,
      batchSize: 64,
      learningRate: 0.0005,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260710-045',
    status: 'PROMOTION',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'GRU-Ensemble',
    created: '2026-07-10T22:10:00Z',
    duration: '3h 47m',
    score: 0.82,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'Huber'
    },
    metrics: {
      trainLoss: 0.038,
      valLoss: 0.046,
      sharpeRatio: 2.12,
      maxDrawdown: 0.15
    }
  },
  {
    runId: 'exp-20260710-044',
    status: 'CALIBRATING',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'LSTM-Attention',
    created: '2026-07-10T19:45:00Z',
    duration: '5h 12m',
    score: 0.79,
    metadata: {
      epochs: 120,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    },
    metrics: {
      trainLoss: 0.045,
      valLoss: 0.053,
      sharpeRatio: 1.98,
      maxDrawdown: 0.18
    }
  },
  {
    runId: 'exp-20260710-043',
    status: 'PAPER',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.1.5',
    algorithm: 'TCN-Deep',
    created: '2026-07-10T16:20:00Z',
    duration: '6h 05m',
    score: 0.75,
    metadata: {
      epochs: 90,
      batchSize: 512,
      learningRate: 0.003,
      optimizer: 'Adam',
      loss: 'MAE'
    },
    metrics: {
      trainLoss: 0.052,
      valLoss: 0.061,
      sharpeRatio: 1.84,
      maxDrawdown: 0.21
    }
  },
  {
    runId: 'exp-20260710-042',
    status: 'VALIDATING',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'ResNet-LSTM',
    created: '2026-07-10T13:55:00Z',
    duration: '4h 38m',
    score: 0.81,
    metadata: {
      epochs: 100,
      batchSize: 256,
      learningRate: 0.0015,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260710-041',
    status: 'FAILED',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.3.0-rc1',
    algorithm: 'Transformer-XL',
    created: '2026-07-10T11:30:00Z',
    duration: '1h 12m',
    score: null,
    metadata: {
      epochs: 150,
      batchSize: 32,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260710-040',
    status: 'PRODUCTION',
    dataset: 'ds-futures-2026q1',
    featureVersion: 'fv-v4.1.3',
    algorithm: 'GRU-Ensemble',
    created: '2026-07-05T09:15:00Z',
    duration: '3h 55m',
    score: 0.85,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'Huber'
    },
    metrics: {
      trainLoss: 0.040,
      valLoss: 0.048,
      sharpeRatio: 2.21,
      maxDrawdown: 0.14
    }
  },
  {
    runId: 'exp-20260709-039',
    status: 'ARCHIVED',
    dataset: 'ds-equity-2026q1',
    featureVersion: 'fv-v4.0.2',
    algorithm: 'LSTM-Attention',
    created: '2026-07-04T15:40:00Z',
    duration: '4h 18m',
    score: 0.71,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'Adam',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260709-038',
    status: 'CREATED',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'WaveNet',
    created: '2026-07-11T21:00:00Z',
    duration: '0m',
    score: null,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260709-037',
    status: 'TRAINING',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'LSTM-Attention',
    created: '2026-07-11T18:45:00Z',
    duration: '4h 10m',
    score: null,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260708-036',
    status: 'VALIDATING',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'Transformer-XL',
    created: '2026-07-11T16:20:00Z',
    duration: '3h 25m',
    score: 0.78,
    metadata: {
      epochs: 120,
      batchSize: 64,
      learningRate: 0.0008,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260708-035',
    status: 'CALIBRATING',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.1.5',
    algorithm: 'TCN-Deep',
    created: '2026-07-11T12:10:00Z',
    duration: '5h 45m',
    score: 0.73,
    metadata: {
      epochs: 90,
      batchSize: 512,
      learningRate: 0.003,
      optimizer: 'Adam',
      loss: 'MAE'
    }
  },
  {
    runId: 'exp-20260708-034',
    status: 'PAPER',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'ResNet-LSTM',
    created: '2026-07-11T08:30:00Z',
    duration: '4h 50m',
    score: 0.80,
    metadata: {
      epochs: 100,
      batchSize: 256,
      learningRate: 0.0015,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    },
    metrics: {
      trainLoss: 0.044,
      valLoss: 0.052,
      sharpeRatio: 2.05,
      maxDrawdown: 0.16
    }
  },
  {
    runId: 'exp-20260707-033',
    status: 'PROMOTION',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'GRU-Ensemble',
    created: '2026-07-10T23:45:00Z',
    duration: '3h 40m',
    score: 0.83,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'Huber'
    },
    metrics: {
      trainLoss: 0.039,
      valLoss: 0.047,
      sharpeRatio: 2.15,
      maxDrawdown: 0.13
    }
  },
  {
    runId: 'exp-20260707-032',
    status: 'FAILED',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.3.0-rc1',
    algorithm: 'WaveNet',
    created: '2026-07-10T20:15:00Z',
    duration: '2h 05m',
    score: null,
    metadata: {
      epochs: 100,
      batchSize: 64,
      learningRate: 0.005,
      optimizer: 'Adam',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260707-031',
    status: 'PRODUCTION',
    dataset: 'ds-equity-2026q1',
    featureVersion: 'fv-v4.1.3',
    algorithm: 'LSTM-Attention',
    created: '2026-06-28T10:20:00Z',
    duration: '4h 30m',
    score: 0.86,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    },
    metrics: {
      trainLoss: 0.041,
      valLoss: 0.050,
      sharpeRatio: 2.28,
      maxDrawdown: 0.13
    }
  },
  {
    runId: 'exp-20260706-030',
    status: 'ARCHIVED',
    dataset: 'ds-futures-2026q1',
    featureVersion: 'fv-v4.0.1',
    algorithm: 'GRU-Ensemble',
    created: '2026-06-25T14:35:00Z',
    duration: '3h 50m',
    score: 0.68,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'MAE'
    }
  },
  {
    runId: 'exp-20260706-029',
    status: 'TRAINING',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'Transformer-XL',
    created: '2026-07-11T20:00:00Z',
    duration: '2h 55m',
    score: null,
    metadata: {
      epochs: 150,
      batchSize: 64,
      learningRate: 0.0005,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260705-028',
    status: 'VALIDATING',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'TCN-Deep',
    created: '2026-07-11T17:40:00Z',
    duration: '3h 15m',
    score: 0.76,
    metadata: {
      epochs: 90,
      batchSize: 512,
      learningRate: 0.003,
      optimizer: 'Adam',
      loss: 'MAE'
    }
  },
  {
    runId: 'exp-20260705-027',
    status: 'CALIBRATING',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'ResNet-LSTM',
    created: '2026-07-11T14:10:00Z',
    duration: '4h 45m',
    score: 0.77,
    metadata: {
      epochs: 100,
      batchSize: 256,
      learningRate: 0.0015,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260704-026',
    status: 'PAPER',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.1.5',
    algorithm: 'LSTM-Attention',
    created: '2026-07-11T10:25:00Z',
    duration: '4h 20m',
    score: 0.74,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260704-025',
    status: 'PROMOTION',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'WaveNet',
    created: '2026-07-11T06:50:00Z',
    duration: '5h 30m',
    score: 0.81,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    },
    metrics: {
      trainLoss: 0.043,
      valLoss: 0.051,
      sharpeRatio: 2.08,
      maxDrawdown: 0.15
    }
  },
  {
    runId: 'exp-20260703-024',
    status: 'FAILED',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.3.0-rc1',
    algorithm: 'Transformer-XL',
    created: '2026-07-10T22:30:00Z',
    duration: '1h 45m',
    score: null,
    metadata: {
      epochs: 120,
      batchSize: 32,
      learningRate: 0.002,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260703-023',
    status: 'PRODUCTION',
    dataset: 'ds-crypto-2026q1',
    featureVersion: 'fv-v4.1.2',
    algorithm: 'TCN-Deep',
    created: '2026-06-20T11:15:00Z',
    duration: '6h 10m',
    score: 0.84,
    metadata: {
      epochs: 90,
      batchSize: 512,
      learningRate: 0.003,
      optimizer: 'Adam',
      loss: 'MAE'
    },
    metrics: {
      trainLoss: 0.048,
      valLoss: 0.057,
      sharpeRatio: 2.18,
      maxDrawdown: 0.14
    }
  },
  {
    runId: 'exp-20260702-022',
    status: 'ARCHIVED',
    dataset: 'ds-equity-2026q1',
    featureVersion: 'fv-v3.9.8',
    algorithm: 'LSTM-Attention',
    created: '2026-06-15T09:40:00Z',
    duration: '4h 25m',
    score: 0.69,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'Adam',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260702-021',
    status: 'CREATED',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'GRU-Ensemble',
    created: '2026-07-11T21:30:00Z',
    duration: '0m',
    score: null,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'Huber'
    }
  },
  {
    runId: 'exp-20260701-020',
    status: 'TRAINING',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'ResNet-LSTM',
    created: '2026-07-11T19:15:00Z',
    duration: '3h 40m',
    score: null,
    metadata: {
      epochs: 100,
      batchSize: 256,
      learningRate: 0.0015,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  },
  {
    runId: 'exp-20260701-019',
    status: 'VALIDATING',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.1',
    algorithm: 'Transformer-XL',
    created: '2026-07-11T15:50:00Z',
    duration: '3h 05m',
    score: 0.79,
    metadata: {
      epochs: 150,
      batchSize: 64,
      learningRate: 0.0005,
      optimizer: 'AdamW',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260630-018',
    status: 'CALIBRATING',
    dataset: 'ds-futures-2026q2',
    featureVersion: 'fv-v4.1.5',
    algorithm: 'GRU-Ensemble',
    created: '2026-07-11T11:20:00Z',
    duration: '3h 35m',
    score: 0.80,
    metadata: {
      epochs: 80,
      batchSize: 256,
      learningRate: 0.002,
      optimizer: 'SGD',
      loss: 'Huber'
    }
  },
  {
    runId: 'exp-20260630-017',
    status: 'FAILED',
    dataset: 'ds-crypto-2026q2',
    featureVersion: 'fv-v4.3.0-rc1',
    algorithm: 'WaveNet',
    created: '2026-07-10T18:40:00Z',
    duration: '1h 20m',
    score: null,
    metadata: {
      epochs: 100,
      batchSize: 64,
      learningRate: 0.004,
      optimizer: 'Adam',
      loss: 'MSE'
    }
  },
  {
    runId: 'exp-20260629-016',
    status: 'PAPER',
    dataset: 'ds-equity-2026q2',
    featureVersion: 'fv-v4.2.0',
    algorithm: 'LSTM-Attention',
    created: '2026-07-11T07:55:00Z',
    duration: '4h 15m',
    score: 0.76,
    metadata: {
      epochs: 100,
      batchSize: 128,
      learningRate: 0.001,
      optimizer: 'AdamW',
      loss: 'SmoothL1'
    }
  }
];
