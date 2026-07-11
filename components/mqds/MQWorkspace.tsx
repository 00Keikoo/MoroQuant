'use client';

import React, { useState } from 'react';

interface MQWorkspaceProps {
  children: React.ReactNode;
  inspector?: React.ReactNode;
  console?: React.ReactNode;
  className?: string;
}

export function MQWorkspace({ children, inspector, console: consolePanel, className = '' }: MQWorkspaceProps) {
  const [inspectorVisible, setInspectorVisible] = useState(!!inspector);
  const [consoleVisible, setConsoleVisible] = useState(!!consolePanel);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto">
          {children}
        </div>
        {inspector && inspectorVisible && (
          <div className="w-[300px] lg:w-[400px] overflow-hidden">
            {inspector}
          </div>
        )}
      </div>
      {consolePanel && consoleVisible && (
        <div className="h-[200px] border-t border-[var(--color-mq-border)] overflow-hidden">
          {consolePanel}
        </div>
      )}
    </div>
  );
}
