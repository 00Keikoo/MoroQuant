import { MQPanel, MQEmptyState } from '@/components/mqds';
import { Zap } from 'lucide-react';

export default function TradeForensicsPage() {
  return (
    <div className="p-4 space-y-4">
      <MQPanel title="Trade Forensics">
        <MQEmptyState
          icon={<Zap size={48} />}
          title="Trade Forensics"
          description="Trade replay, analysis, and AI review"
        />
      </MQPanel>
    </div>
  );
}
