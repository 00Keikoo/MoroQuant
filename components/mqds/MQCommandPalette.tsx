'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

export interface MQCommand {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  onExecute: () => void;
  keywords?: string[];
}

interface MQCommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  commands: MQCommand[];
  placeholder?: string;
}

export function MQCommandPalette({
  isOpen,
  onClose,
  commands,
  placeholder = 'Search commands...'
}: MQCommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredCommands = commands.filter(cmd => {
    const searchText = `${cmd.label} ${cmd.description} ${cmd.keywords?.join(' ')}`.toLowerCase();
    return searchText.includes(query.toLowerCase());
  });

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filteredCommands[selectedIndex]) {
        e.preventDefault();
        filteredCommands[selectedIndex].onExecute();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/80">
      <div className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] shadow-xl w-full max-w-2xl">
        <div className="flex items-center gap-2 px-3 h-12 border-b border-[var(--color-mq-border)]">
          <Search size={16} className="text-[var(--color-mq-text-muted)]" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={placeholder}
            className="flex-1 bg-transparent border-none outline-none text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] placeholder:text-[var(--color-mq-text-muted)]"
          />
        </div>
        <div className="max-h-96 overflow-auto">
          {filteredCommands.length === 0 ? (
            <div className="px-3 py-8 text-center text-[var(--font-size-small)] text-[var(--color-mq-text-muted)]">
              No commands found
            </div>
          ) : (
            filteredCommands.map((cmd, index) => (
              <button
                key={cmd.id}
                onClick={() => {
                  cmd.onExecute();
                  onClose();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                  index === selectedIndex
                    ? 'bg-[var(--color-mq-accent-dim)] border-l-2 border-[var(--color-mq-accent)]'
                    : 'hover:bg-[var(--color-mq-accent-dim)]'
                }`}
              >
                {cmd.icon && (
                  <div className="text-[var(--color-mq-text-muted)]">
                    {cmd.icon}
                  </div>
                )}
                <div className="flex-1">
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-primary)]">
                    {cmd.label}
                  </div>
                  {cmd.description && (
                    <div className="text-[var(--font-size-small)] text-[var(--color-mq-text-secondary)]">
                      {cmd.description}
                    </div>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
