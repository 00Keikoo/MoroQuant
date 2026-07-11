'use client';

import React, { useState } from 'react';

interface MQTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface MQTabsProps {
  tabs: MQTab[];
  defaultTab?: string;
  className?: string;
}

export function MQTabs({ tabs, defaultTab, className = '' }: MQTabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const activeContent = tabs.find(tab => tab.id === activeTab)?.content;

  return (
    <div className={className}>
      <div className="flex border-b border-[var(--color-mq-border)]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 h-[var(--header-height)] text-[var(--font-size-body)] font-medium transition-colors focus-visible:outline focus-visible:outline-1 focus-visible:outline-[var(--color-mq-accent)] focus-visible:outline-offset-2 ${
              activeTab === tab.id
                ? 'text-[var(--color-mq-accent)] border-b-2 border-[var(--color-mq-accent)]'
                : 'text-[var(--color-mq-text-secondary)] hover:text-[var(--color-mq-text-primary)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="mt-4">
        {activeContent}
      </div>
    </div>
  );
}
