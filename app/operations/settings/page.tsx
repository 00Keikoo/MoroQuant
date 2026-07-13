'use client';

import { useState } from 'react';
import { settingsData } from '@/lib/mock-data/settings';
import { TradingTopBar, TradingSidebar, TradingLayout } from '@/components/trading/shared';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'performance' | 'alerts'>('general');

  const navItems = [
    { icon: 'dashboard', label: 'Cluster Health' },
    { icon: 'psychology', label: 'Training Pipelines' },
    { icon: 'swap_horiz', label: 'Edge Routers' },
    { icon: 'pie_chart', label: 'Node Resource Allocation' },
    { icon: 'gpp_maybe', label: 'Security Firewall' },
    { icon: 'terminal', label: 'Service Logs' },
    { icon: 'insights', label: 'Alert History' },
  ];

  const renderSettingInput = (setting: typeof settingsData.general[0]) => {
    switch (setting.type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-xs cursor-pointer">
            <input
              type="checkbox"
              checked={setting.value as boolean}
              readOnly
              className="w-4 h-4 bg-surface-container border border-outline-variant"
            />
            <span className="font-body-base text-on-surface">
              {setting.value ? 'Enabled' : 'Disabled'}
            </span>
          </label>
        );
      case 'select':
        return (
          <select
            value={setting.value as string}
            className="bg-surface-container border border-outline-variant text-on-surface font-body-base px-sm py-1 min-w-[200px]"
          >
            {setting.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );
      case 'number':
        return (
          <input
            type="number"
            value={setting.value as number}
            readOnly
            className="bg-surface-container border border-outline-variant text-on-surface font-data-tabular text-data-tabular px-sm py-1 w-32"
          />
        );
      case 'string':
      default:
        return (
          <input
            type="text"
            value={setting.value as string}
            readOnly
            className="bg-surface-container border border-outline-variant text-on-surface font-body-base px-sm py-1 min-w-[200px]"
          />
        );
    }
  };

  const currentSettings = settingsData[activeTab];

  return (
    <TradingLayout
      topBar={<TradingTopBar searchPlaceholder="Search Settings..." />}
      sidebar={
        <TradingSidebar
          items={navItems}
          footer={
            <div className="px-lg">
              <p className="font-label-caps text-label-caps text-secondary mb-sm uppercase tracking-widest">Active Jobs</p>
              <div className="flex flex-col gap-xs">
                <div className="bg-surface-container-lowest p-xs border border-outline-variant flex items-center justify-between">
                  <span className="font-code-sm text-code-sm">TRD_ALPHA_V4</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                </div>
                <div className="bg-surface-container-lowest p-xs border border-outline-variant flex items-center justify-between">
                  <span className="font-code-sm text-code-sm">BKLT_SIM_882</span>
                  <span className="w-2 h-2 bg-primary rounded-full"></span>
                </div>
              </div>
            </div>
          }
        />
      }
    >
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center justify-between px-lg py-lg border-b border-outline-variant bg-surface-container-low">
          <div>
            <h1 className="font-display-lg text-display-lg">System Settings</h1>
            <p className="text-body-base text-secondary">Configure system parameters and preferences</p>
          </div>
          <div className="flex gap-sm">
            <button className="flex items-center gap-xs px-md py-1 bg-surface-container-highest border border-outline-variant hover:text-on-surface transition-colors">
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              <span className="font-label-caps text-label-caps">Reset</span>
            </button>
            <button className="flex items-center gap-xs px-md py-1 bg-primary-container text-on-primary-container border border-transparent transition-opacity">
              <span className="material-symbols-outlined text-[16px]">save</span>
              <span className="font-label-caps text-label-caps uppercase">Save Changes</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-md px-lg py-sm border-b border-outline-variant bg-surface-container">
          {(['general', 'performance', 'alerts'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-md py-1 font-label-caps text-label-caps uppercase ${
                activeTab === tab
                  ? 'bg-surface-container-high text-primary border-b-2 border-primary'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-lg">
          <div className="max-w-4xl">
            <div className="bg-surface-container border border-outline-variant">
              {currentSettings.map((setting, index) => (
                <div
                  key={setting.key}
                  className={`px-md py-md ${
                    index < currentSettings.length - 1 ? 'border-b border-outline-variant' : ''
                  } hover:bg-surface-container-high transition-colors`}
                >
                  <div className="flex items-start justify-between gap-md">
                    <div className="flex-1">
                      <div className="font-body-base text-on-surface mb-xs">{setting.key}</div>
                      <div className="font-code-sm text-code-sm text-secondary">{setting.description}</div>
                    </div>
                    <div className="flex items-center gap-sm">{renderSettingInput(setting)}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-lg p-md bg-surface-container-low border border-outline-variant">
              <div className="flex items-start gap-sm">
                <span className="material-symbols-outlined text-[20px] text-primary">info</span>
                <div>
                  <p className="font-body-base text-on-surface mb-xs">Configuration Notice</p>
                  <p className="font-code-sm text-code-sm text-secondary">
                    Changes to system settings may require a service restart to take effect. Ensure all active jobs are
                    completed before applying critical configuration changes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </TradingLayout>
  );
}
