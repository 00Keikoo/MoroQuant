'use client';

import React from 'react';
import { Search } from 'lucide-react';

interface MQSearchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  onSearch?: (value: string) => void;
}

export function MQSearch({ onSearch, className = '', ...props }: MQSearchProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSearch?.(e.target.value);
    props.onChange?.(e);
  };

  return (
    <div className={`relative ${className}`}>
      <Search
        className="absolute left-2 top-1/2 -translate-y-1/2 text-[var(--color-mq-text-muted)]"
        size={14}
      />
      <input
        type="text"
        className="w-full h-8 pl-8 pr-3 bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] text-[var(--font-size-body)] text-[var(--color-mq-text-primary)] placeholder:text-[var(--color-mq-text-muted)] focus:outline focus:outline-1 focus:outline-[var(--color-mq-accent)] focus:outline-offset-0"
        onChange={handleChange}
        {...props}
      />
    </div>
  );
}
