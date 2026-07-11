import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Table } from 'lucide-react';

export default function ChroniclePage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Research Chronicle">
        <MQEmptyState
          icon={<Table size={48} />}
          title="Chronicle"
          description="Timeline of all research events and activities"
        />
      </MQPanel>
    </div>
  );
}
