import { MQPanel, MQEmptyState } from '@/components/mqds';
import { ArrowUpCircle } from 'lucide-react';

export default function PromotionPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Promotion">
        <MQEmptyState
          icon={<ArrowUpCircle size={48} />}
          title="Promotion"
          description="Model promotion pipeline and gate checks"
        />
      </MQPanel>
    </div>
  );
}
