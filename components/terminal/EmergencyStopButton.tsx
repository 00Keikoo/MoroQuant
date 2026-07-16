'use client';

import { useState } from 'react';
import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { emergencyStop } from '@/lib/api/ml-trading';
import { toast } from '@/lib/utils/toast';

export default function EmergencyStopButton() {
  const { mode } = useTradingMode();
  const [isConfirming, setIsConfirming] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const isDisabled = mode !== 'LIVE';

  const handleClick = () => {
    if (isDisabled) return;
    setIsConfirming(true);
  };

  const handleConfirm = async () => {
    setIsExecuting(true);
    try {
      await emergencyStop();
      toast('Emergency stop executed successfully', 'success');
      setIsConfirming(false);
    } catch (error) {
      console.error('Emergency stop failed:', error);
      toast('Emergency stop failed. Please try again.', 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCancel = () => {
    setIsConfirming(false);
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={isDisabled}
        className={`
          relative px-6 py-2.5 font-bold text-sm tracking-wider
          transition-all rounded-sm
          ${
            isDisabled
              ? 'bg-[#1C1C1C] text-[#666666] cursor-not-allowed border border-[#262626]'
              : 'bg-[#DC2626] text-white hover:bg-[#B91C1C] hover:shadow-lg hover:shadow-red-900/50 border border-[#EF4444]'
          }
        `}
        title={isDisabled ? 'Emergency Stop only active in LIVE mode' : 'Immediately disable autonomous trading'}
      >
        <span className="flex items-center gap-2">
          <span className="text-lg">🛑</span>
          EMERGENCY STOP
        </span>
      </button>

      {isConfirming && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-[#141414] border-2 border-[#DC2626] rounded p-6 max-w-md">
            <h3 className="text-lg font-bold text-white mb-4">Confirm Emergency Stop</h3>
            <p className="text-[#A1A1A1] mb-2">This will immediately:</p>
            <ul className="text-[#A1A1A1] mb-6 space-y-1 list-disc list-inside">
              <li>Disable autonomous trading</li>
              <li>Cancel all future automated entries</li>
              <li>Stop scheduler from opening new positions</li>
              <li>Switch mode to OFF</li>
            </ul>
            <p className="text-yellow-500 text-sm mb-6">Existing positions will remain open.</p>
            <div className="flex gap-3">
              <button
                onClick={handleConfirm}
                disabled={isExecuting}
                className="flex-1 bg-[#DC2626] text-white py-2 px-4 rounded hover:bg-[#B91C1C] font-bold disabled:opacity-50"
              >
                {isExecuting ? 'Stopping...' : 'CONFIRM STOP'}
              </button>
              <button
                onClick={handleCancel}
                disabled={isExecuting}
                className="flex-1 bg-transparent border border-[#262626] text-[#A1A1A1] py-2 px-4 rounded hover:bg-[#1C1C1C] disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
