import { MQPanel, MQEmptyState } from '@/components/mqds';
import { LayoutDashboard } from 'lucide-react';

export default function CommandCenterPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Research Command Center">
        <MQEmptyState
          icon={<LayoutDashboard size={48} />}
          title="Command Center"
          description="Active experiment monitoring and research queue management"
        />
      </MQPanel>
    </div>
  );
}
