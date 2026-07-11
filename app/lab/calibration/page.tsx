import { MQPanel, MQEmptyState } from '@/components/mqds';
import { TrendingUp } from 'lucide-react';

export default function CalibrationPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Calibration">
        <MQEmptyState
          icon={<TrendingUp size={48} />}
          title="Calibration"
          description="Probability calibration and reliability curves"
        />
      </MQPanel>
    </div>
  );
}
