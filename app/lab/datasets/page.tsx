import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Database } from 'lucide-react';

export default function DatasetsPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Datasets">
        <MQEmptyState
          icon={<Database size={48} />}
          title="Datasets"
          description="Dataset management and versioning"
        />
      </MQPanel>
    </div>
  );
}
