import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Target } from 'lucide-react';

export default function ValidationPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Validation">
        <MQEmptyState
          icon={<Target size={48} />}
          title="Validation"
          description="Model validation and walk-forward testing"
        />
      </MQPanel>
    </div>
  );
}
