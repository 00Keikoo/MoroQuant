import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Clock } from 'lucide-react';

export default function ModelsPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Models">
        <MQEmptyState
          icon={<Clock size={48} />}
          title="Models"
          description="Model registry and version history"
        />
      </MQPanel>
    </div>
  );
}
