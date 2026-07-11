import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Cpu } from 'lucide-react';

export default function FeaturesPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Features">
        <MQEmptyState
          icon={<Cpu size={48} />}
          title="Features"
          description="Feature store and engineering pipelines"
        />
      </MQPanel>
    </div>
  );
}
