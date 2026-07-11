import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Beaker } from 'lucide-react';

export default function ExperimentsPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Experiments">
        <MQEmptyState
          icon={<Beaker size={48} />}
          title="Experiments"
          description="Experiment registry and training runs"
        />
      </MQPanel>
    </div>
  );
}
